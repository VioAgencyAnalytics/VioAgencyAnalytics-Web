"""Browser-bound authorization-code handoff, with backend-only redemption."""
import base64
import hashlib
import json
import re
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import get_settings
from app.viewer_environment import viewer_settings
from app.admin_access import public_origin
from app.routes import viewer
from app.routes.pages import templates
from app.routes.published import HEADERS
from app.repositories.viewer import ViewerError

router = APIRouter(tags=['viewer handoff'])
HANDOFF_HEADERS = {**HEADERS, 'Referrer-Policy': 'no-referrer'}


def binding_cookie(secure):
    return ('__Host-' if secure else '') + viewer.COOKIE_PREFIX + '_handoff'


@router.get('/auth/handoff/start')
def start(request: Request, settings=Depends(viewer_settings)):
    try:
        query = request.query_params
        mode, target, revision = query.get('mode'), query.get('target_id', ''), query.get('revision', '')
        if (set(query) - {'mode', 'target_id', 'revision'} or any(len(query.getlist(k)) != 1 for k in query)
                or mode not in ('published', 'preview')
                or not re.fullmatch(r'rpt_[a-f0-9]{32}' if mode == 'published' else r'[a-f0-9]{32}', target)
                or (mode == 'published' and not re.fullmatch(r'[1-9][0-9]{0,8}', revision))
                or (mode == 'preview' and revision)):
            raise ViewerError(400, 'Chọn đúng báo cáo và revision trước khi mở.')
        origin = public_origin(settings.report_new_public_url)
        admin = public_origin(settings.report_admin_public_url)
        if str(request.base_url).rstrip('/') != origin:
            return RedirectResponse(origin + request.url.path + '?' + urlencode(dict(query)), 303, headers=HANDOFF_HEADERS)
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        result = viewer.repository(request, settings).call('POST', '/api/internal/v1/handoffs', {
            'state': state, 'challenge': challenge, 'target_id': target,
            'revision': int(revision) if revision else 0, 'mode': mode, 'audience': origin,
            'callback': origin + '/auth/handoff/callback'}).json()
        transaction = result.get('transaction', '')
        if not isinstance(transaction, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', transaction):
            raise ViewerError(502, 'Giao dịch chuyển phiên không hợp lệ.')
        # Never trust an upstream/browser supplied arbitrary redirect.
        response = RedirectResponse(admin + '/viewer/authorize?transaction=' + transaction, 303, headers=HANDOFF_HEADERS)
        secure = origin.startswith('https:')
        pending = base64.urlsafe_b64encode(json.dumps({'transaction': transaction, 'state': state, 'verifier': verifier,
            'target_id': target, 'revision': int(revision) if revision else 0, 'mode': mode}).encode()).decode()
        response.set_cookie(binding_cookie(secure), pending, httponly=True, secure=secure, samesite='lax', max_age=600)
        return response
    except (ValueError, TypeError, KeyError):
        return viewer.error_page(request, ViewerError(502, 'Giao dịch chuyển phiên không hợp lệ.'))
    except ViewerError as exc:
        return viewer.error_page(request, exc)


@router.get('/auth/handoff/callback')
def callback_page(request: Request, settings=Depends(viewer_settings)):
    csrf = request.cookies.get(viewer.CSRF) or secrets.token_urlsafe(32)
    response = templates.TemplateResponse(request=request, name='pages/published/handoff.html',
        context={'csrf': csrf}, headers=HANDOFF_HEADERS)
    response.set_cookie(viewer.CSRF, csrf, httponly=True, secure=request.url.scheme == 'https',
                        samesite='lax', max_age=28800)
    return response


@router.post('/auth/handoff/callback')
async def callback(request: Request, settings=Depends(viewer_settings)):
    try:
        origin = public_origin(settings.report_new_public_url)
        secure = origin.startswith('https:')
        if (str(request.base_url).rstrip('/') != origin or request.headers.get('origin') != origin
                or request.headers.get('content-type') != 'application/json'):
            raise ViewerError(403, 'Nguồn chuyển phiên không hợp lệ.')
        raw = await request.body()
        if len(raw) > 2048:
            raise ViewerError(400, 'Mã chuyển phiên không hợp lệ.')
        data = json.loads(raw)
        pending = json.loads(base64.urlsafe_b64decode(request.cookies.get(binding_cookie(secure), '')))
        if (not isinstance(data, dict) or set(data) != {'transaction', 'state', 'code'}
                or any(not isinstance(data[k], str) or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', data[k]) for k in data)
                or not secrets.compare_digest(data['state'], pending['state'])
                or not secrets.compare_digest(data['transaction'], pending['transaction'])):
            raise ViewerError(400, 'Giao dịch đã hết hạn hoặc khác trình duyệt. Mở lại báo cáo từ Admin.')
        result = viewer.repository(request, settings).call('POST', '/api/internal/v1/handoffs/redeem', {
            **data, 'verifier': pending['verifier'], 'audience': origin, 'callback': origin + request.url.path}).json()
        if (any(result.get(key) != pending[key] for key in ('target_id', 'revision', 'mode'))
                or not isinstance(result.get('session'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{64}', result['session'])):
            raise ViewerError(502, 'Phiên nhận được không khớp báo cáo đã chọn.')
        target = ('/reports/' + pending['target_id'] + '?revision=' + str(pending['revision'])
                  if pending['mode'] == 'published' else '/internal-preview/' + pending['target_id'])
        response = JSONResponse({'location': target}, headers=HANDOFF_HEADERS)
        response.set_cookie(viewer.SESSION, result['session'], httponly=True, secure=secure, samesite='lax', max_age=28800)
        response.set_cookie(viewer.CSRF, secrets.token_urlsafe(32), httponly=True, secure=secure, samesite='lax', max_age=28800)
        response.delete_cookie(binding_cookie(secure), secure=secure, httponly=True, samesite='lax')
        return response
    except (ValueError, KeyError, TypeError):
        return JSONResponse({'error': 'Phiên chuyển tiếp không hợp lệ. Mở lại báo cáo từ Admin.'}, 400, headers=HANDOFF_HEADERS)
    except ViewerError as exc:
        return JSONResponse({'error': str(exc)}, exc.status, headers=HANDOFF_HEADERS)
