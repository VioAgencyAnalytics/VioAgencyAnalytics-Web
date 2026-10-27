"""Customer BFF: identity remains in Admin; the browser receives only an opaque cookie."""
import hashlib
import hmac
import re
import secrets
from functools import lru_cache
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.routes.pages import templates

router = APIRouter(tags=['customer identity'])
SESSION = 'vio_customer_session'
BINDING = 'vio_customer_browser'
HEADERS = {'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex, nofollow',
           'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff',
           'X-Frame-Options': 'DENY'}


class CustomerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', hide_input_in_errors=True)
    customer_auth_enabled: bool = False
    customer_backend_url: str = ''
    customer_service_token: SecretStr = SecretStr('')
    customer_web_origin: str = ''


@lru_cache
def customer_settings():
    return CustomerSettings()


def enabled(request):
    return customer_settings().customer_auth_enabled and not getattr(request.app.state, 'customer_preview', False)


class CustomerError(Exception):
    def __init__(self, status, message, code='customer_error'):
        self.status, self.message, self.code = status, message, code


def configuration(request):
    settings = customer_settings()
    if not enabled(request):
        raise CustomerError(404, 'Không tìm thấy trang.')
    for address in (settings.customer_backend_url, settings.customer_web_origin):
        try:
            parsed = urlsplit(address)
            parsed.port
            if (parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.path or parsed.query
                    or parsed.fragment or parsed.username or parsed.password or '\\' in address
                    or any(ord(c) < 33 for c in address)
                    or (parsed.scheme == 'http' and parsed.hostname not in ('127.0.0.1', 'localhost', '::1'))):
                raise ValueError()
        except (ValueError, TypeError):
            raise CustomerError(503, 'Chưa cấu hình dịch vụ tài khoản khách hàng.') from None
    if len(settings.customer_service_token.get_secret_value()) < 32:
        raise CustomerError(503, 'Chưa cấu hình dịch vụ tài khoản khách hàng.')
    if request.headers.get('host', '') != urlsplit(settings.customer_web_origin).netloc:
        raise CustomerError(400, 'Vui lòng mở đúng địa chỉ Web đã cấu hình.')
    return settings


def browser_binding(request):
    raw = request.cookies.get(BINDING, '')
    return raw if re.fullmatch(r'[A-Za-z0-9_-]{43,128}', raw) else ''


def csrf_value(binding, settings):
    return hmac.new(settings.customer_service_token.get_secret_value().encode(), ('csrf:' + binding).encode(), hashlib.sha256).hexdigest()


def set_cookie(response, name, value, settings, max_age=None):
    response.set_cookie(name, value, max_age=max_age, httponly=True, secure=settings.customer_web_origin.startswith('https:'), samesite='lax', path='/')


def client_fingerprint(request, settings):
    peer = request.client.host if request.client else 'unknown'
    return hmac.new(settings.customer_service_token.get_secret_value().encode(), ('peer:' + peer).encode(), hashlib.sha256).hexdigest()


async def backend(request, method, path, data=None):
    settings = configuration(request)
    headers = {'Authorization': 'Bearer ' + settings.customer_service_token.get_secret_value(),
               'X-Customer-Session': request.cookies.get(SESSION, ''),
               'X-Customer-Client': client_fingerprint(request, settings)}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(40, connect=5), follow_redirects=False, trust_env=False) as client:
            response = await client.request(method, settings.customer_backend_url + '/api/internal/customer' + path, json=data, headers=headers)
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError()
    except (httpx.HTTPError, ValueError):
        raise CustomerError(503, 'Chưa kết nối được dịch vụ tài khoản. Vui lòng thử lại.') from None
    if response.status_code >= 300:
        if payload.get('code') == 'service_auth':
            raise CustomerError(503, 'Chưa cấu hình kết nối dịch vụ tài khoản.')
        raise CustomerError(response.status_code, payload.get('error', 'Không thể hoàn tất yêu cầu.'), payload.get('code', 'customer_error'))
    return payload


async def read_body(request):
    settings = configuration(request)
    binding = browser_binding(request)
    supplied = request.headers.get('X-CSRF-Token', '')
    if (request.headers.get('origin') != settings.customer_web_origin or not binding
            or not secrets.compare_digest(supplied.encode(), csrf_value(binding, settings).encode())):
        raise CustomerError(403, 'Phiên bảo vệ đã thay đổi. Hãy tải lại trang rồi thử lại.', 'csrf')
    if request.headers.get('content-type', '').split(';')[0] != 'application/json':
        raise CustomerError(415, 'Yêu cầu phải là JSON.')
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 16384:
            raise CustomerError(413, 'Yêu cầu quá lớn.')
    import json
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError()
    except (ValueError, UnicodeError):
        raise CustomerError(422, 'Yêu cầu không hợp lệ.') from None
    return data


def error_response(exc):
    return JSONResponse({'error': exc.message, 'code': exc.code}, exc.status, headers=HEADERS)


def login_response(request, payload):
    raw = payload.pop('session_token', None)
    age = payload.pop('session_max_age', None)
    if not isinstance(raw, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', raw):
        raise CustomerError(502, 'Dịch vụ trả về phiên đăng nhập không hợp lệ.')
    settings = configuration(request)
    response = JSONResponse({**payload, 'redirect': '/workspace/onboarding'}, headers=HEADERS)
    set_cookie(response, SESSION, raw, settings, age)
    # Rotate browser binding after login to invalidate the previous CSRF token.
    set_cookie(response, BINDING, secrets.token_urlsafe(48), settings)
    return response


@router.get('/api/customer/session')
async def session_info(request: Request):
    try:
        settings = configuration(request)
        binding = browser_binding(request) or secrets.token_urlsafe(48)
        try:
            data = await backend(request, 'GET', '/session')
        except CustomerError as exc:
            if exc.status != 401:
                raise
            data = {'user': None, 'workspaces': [], 'workspace': None, 'capabilities': await backend(request, 'GET', '/config')}
        response = JSONResponse({**data, 'csrf': csrf_value(binding, settings)}, headers=HEADERS)
        if not browser_binding(request):
            set_cookie(response, BINDING, binding, settings)
        if not data['user']:
            response.delete_cookie(SESSION, path='/')
        return response
    except CustomerError as exc:
        return error_response(exc)


POST_PATHS = {'auth/register', 'auth/login', 'auth/logout', 'auth/google/start',
              'auth/email/reset', 'auth/email/verify', 'auth/email/confirm', 'workspaces', 'workspaces/join'}


@router.post('/api/customer/{path:path}')
async def customer_mutation(request: Request, path: str):
    try:
        data = await read_body(request)
        if path not in POST_PATHS and not re.fullmatch(r'workspaces/[a-f0-9]{32}/(select|invitations|tour)', path):
            raise CustomerError(404, 'Không tìm thấy chức năng.')
        if path == 'auth/google/start':
            data = {'remember': data.get('remember') is True, 'browser_binding': hashlib.sha256(browser_binding(request).encode()).hexdigest()}
        payload = await backend(request, 'POST', '/' + path, data)
        if path in ('auth/register', 'auth/login'):
            return login_response(request, payload)
        response = JSONResponse(payload, headers=HEADERS)
        if path == 'auth/logout' or (path == 'auth/email/confirm' and data.get('kind') == 'reset'):
            response.delete_cookie(SESSION, path='/')
            response.delete_cookie(BINDING, path='/')
        return response
    except CustomerError as exc:
        return error_response(exc)


@router.get('/api/customer/workspaces/{workspace_id}')
async def workspace_detail(request: Request, workspace_id: str):
    try:
        if not re.fullmatch(r'[a-f0-9]{32}', workspace_id):
            raise CustomerError(404, 'Không tìm thấy Workspace.')
        return JSONResponse(await backend(request, 'GET', '/workspaces/' + workspace_id), headers=HEADERS)
    except CustomerError as exc:
        return error_response(exc)


@router.get('/auth/customer/google/callback')
async def google_callback(request: Request):
    try:
        configuration(request)
        binding = browser_binding(request)
        if not binding:
            raise CustomerError(400, 'Phiên đăng nhập đã hết hạn.', 'oauth_state')
        data = {key: request.query_params.get(key, '') for key in ('state', 'code', 'error')}
        data['browser_binding'] = hashlib.sha256(binding.encode()).hexdigest()
        payload = await backend(request, 'POST', '/auth/google/finish', data)
        response = login_response(request, payload)
        response.status_code = 303
        response.headers['location'] = '/workspace/onboarding'
        return response
    except CustomerError as exc:
        if exc.status == 404:
            return error_response(exc)
        allowed = {'google_cancelled', 'oauth_state', 'account_link_required'}
        code = exc.code if exc.code in allowed else 'google_failed'
        return RedirectResponse('/workspace/login?error=' + code, 303, headers=HEADERS)


async def live_page(request, page):
    try:
        settings = configuration(request)
        user = None
        try:
            user = await backend(request, 'GET', '/session')
        except CustomerError as exc:
            if exc.status != 401:
                raise
        if page != 'login' and not user:
            return RedirectResponse('/workspace/login', 303, headers=HEADERS)
        details = None
        if page == '':
            if not user.get('workspace'):
                return RedirectResponse('/workspace/onboarding', 303, headers=HEADERS)
            details = await backend(request, 'GET', '/workspaces/' + user['workspace']['id'])
        name = 'login' if page == 'login' else 'overview' if page == '' else 'onboarding'
        response = templates.TemplateResponse(request=request, name=f'customer/live/{name}.html',
            context={'title': {'login':'Đăng nhập','overview':'Tổng quan Workspace','onboarding':'Thiết lập Workspace'}[name],
                     'customer_page': name, 'customer_live': True, 'account': user, 'details': details}, headers=HEADERS)
        if not browser_binding(request):
            set_cookie(response, BINDING, secrets.token_urlsafe(48), settings)
        return response
    except CustomerError as exc:
        return templates.TemplateResponse(request=request, name='customer/live/error.html',
            context={'title': 'Kết nối tài khoản', 'customer_page': 'error', 'customer_live': True,
                     'message': exc.message}, status_code=exc.status, headers=HEADERS)
