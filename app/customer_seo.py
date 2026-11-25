"""Private SEO/report UI and bounded upload proxy; Admin owns all persisted data."""
import asyncio
import re
import secrets
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.customer_auth import (BINDING, SESSION, HEADERS, CustomerError, backend, browser_binding,
    configuration, csrf_value, client_fingerprint, read_body, error_response, set_cookie)
from app.customer_transport import read_payload, public_error, public_payload
from app.routes.pages import templates

router = APIRouter(tags=['customer seo and reports'])
ID = re.compile(r'[a-f0-9]{32}')
MAX_FILE = 2 * 1024 * 1024
COMPARISON_PARAMETERS = ('comparison', 'comparison_start', 'comparison_end')


def check_id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise CustomerError(404, 'Không tìm thấy dữ liệu.')


def query(request, allowed):
    if set(request.query_params) - set(allowed) or any(len(request.query_params.getlist(key)) != 1 for key in request.query_params):
        raise CustomerError(422, 'Bộ lọc không hợp lệ.')
    if any(len(value) > 2000 for value in request.query_params.values()):
        raise CustomerError(422, 'Bộ lọc quá dài.')
    return '?' + urlencode(dict(request.query_params)) if request.query_params else ''


def scoped(payload, workspace_id, client_id=None):
    if (not isinstance(payload, dict) or not isinstance(payload.get('scope'), dict)
            or payload['scope'].get('workspace_id') != workspace_id
            or client_id is not None and payload['scope'].get('client_id') != client_id):
        raise CustomerError(502, 'Dữ liệu không đúng Workspace hoặc khách hàng.', 'snapshot_scope')
    return payload


def seo_projection(payload, workspace_id, client_id=None):
    scoped(payload, workspace_id, client_id)
    if not isinstance(payload.get('keywords'), list) or len(payload['keywords']) > 2000:
        raise CustomerError(502, 'Bộ từ khóa không hợp lệ.')
    fields = ('id', 'keyword', 'topic', 'role', 'segment', 'committed', 'version', 'rank', 'previous_period_rank', 'change',
              'observed_date', 'url', 'state', 'source_previous_rank', 'previous_period_state', 'previous_observed_date', 'movement',
              'role_origin', 'role_reviewed')
    payload['keywords'] = [{key: row.get(key) for key in fields} for row in payload['keywords']]
    for row in payload['keywords']:
        for field in ('rank', 'previous_period_rank', 'source_previous_rank'):
            if row[field] is not None and (type(row[field]) is not int or not 1 <= row[field] <= 1000):
                raise CustomerError(502, 'Thứ hạng không hợp lệ.')
        if row['url'] and (not isinstance(row['url'], str) or urlsplit(row['url']).scheme not in ('http', 'https')):
            raise CustomerError(502, 'URL thứ hạng không hợp lệ.')
    if 'content' in payload:
        items = payload['content'].get('items')
        if not isinstance(items, list) or len(items) > 2000:
            raise CustomerError(502, 'Danh sách bài viết không hợp lệ.')
        allowed = ('id', 'version', 'updated_at', 'title', 'kind', 'month', 'publication_status', 'published_date',
                   'review_status', 'accepted_date', 'url', 'draft_url', 'topic', 'archived', 'provenance')
        payload['content']['items'] = [{key: row.get(key) for key in allowed} for row in items]
        for row in payload['content']['items']:
            for key in ('url', 'draft_url'):
                if row[key] and (not isinstance(row[key], str) or urlsplit(row[key]).scheme not in ('http', 'https') or urlsplit(row[key]).username):
                    raise CustomerError(502, 'Liên kết bài viết không hợp lệ.')
            evidence = row.get('provenance')
            if evidence is not None:
                if not isinstance(evidence, dict):
                    raise CustomerError(502, 'Nguồn bài viết không hợp lệ.')
                row['provenance'] = {key: evidence.get(key) for key in ('source', 'fetched_at', 'published_date', 'title')}
    if payload.get('effectiveness') is not None:
        from app.customer_data import numeric
        if not isinstance(payload['effectiveness'], dict):
            raise CustomerError(502, 'Hiệu quả bài viết không hợp lệ.')
        items = payload['effectiveness'].get('items')
        if not isinstance(items, list) or len(items) > 2000:
            raise CustomerError(502, 'Hiệu quả bài viết không hợp lệ.')
        for row in items:
            try:
                address = urlsplit(row['url']) if isinstance(row, dict) and isinstance(row.get('url'), str) else None
                valid_url = address and address.scheme in ('http', 'https') and address.hostname and not address.username
            except ValueError:
                valid_url = False
            if not valid_url:
                raise CustomerError(502, 'URL hiệu quả bài viết không hợp lệ.')
            ids = row.get('ids', [row.get('id')])
            if (not isinstance(ids, list) or len(ids) > 2000
                    or any(not isinstance(value, str) or not ID.fullmatch(value) for value in ids)):
                raise CustomerError(502, 'Liên kết công việc bài viết không hợp lệ.')
            row['ids'] = ids
            for group in ('values', 'previous'):
                if not isinstance(row.get(group), dict):
                    raise CustomerError(502, 'Chỉ số bài viết không hợp lệ.')
                row[group] = {key:numeric(row[group].get(key), 'percent' if key == 'ctr' else 'number')
                              for key in ('views','clicks','impressions','ctr','position')}
        payload['effectiveness']['items'] = [{key:row.get(key) for key in ('id','ids','title','url','values','previous')} for row in items]
    from app.customer_seo_reports import rank_overview
    payload['rank_overview'] = rank_overview(payload['keywords'], payload.get('period') or {})
    return payload


@router.get('/api/customer/workspaces/{workspace_id}/seo/discovery')
async def seo_discovery(request: Request, workspace_id: str):
    try:
        check_id(workspace_id)
        suffix = query(request, ('start', 'end'))
        payload = scoped(await backend(request, 'GET', '/workspaces/' + workspace_id + '/seo/discovery' + suffix), workspace_id)
        if not isinstance(payload.get('items'), list) or len(payload['items']) > 2000:
            raise CustomerError(502, 'Bảng từ khóa không hợp lệ.')
        payload['items'] = [{key: row.get(key) for key in ('keyword', 'page', 'role', 'reason', 'clicks', 'impressions', 'ctr', 'position', 'tracked')}
                            for row in payload['items'] if isinstance(row, dict)]
        for row in payload['items']:
            address = row['page']
            if address and (not isinstance(address, str) or urlsplit(address).scheme not in ('http', 'https') or urlsplit(address).username):
                raise CustomerError(502, 'Trang đích của từ khóa không hợp lệ.')
            if isinstance(row['tracked'], dict):
                row['tracked'] = {key: row['tracked'].get(key) for key in ('id', 'role', 'role_origin', 'role_reviewed')}
        return JSONResponse(payload, headers=HEADERS)
    except CustomerError as error:
        return error_response(error)


@router.get('/api/customer/workspaces/{workspace_id}/seo')
async def seo_api(request: Request, workspace_id: str):
    try:
        check_id(workspace_id)
        suffix = query(request, ('start', 'end', 'profile', 'client_id', *COMPARISON_PARAMETERS))
        from app.customer_comparisons import parameters
        parameters(request.query_params, default='previous')
        payload = await backend(request, 'GET', '/workspaces/' + workspace_id + '/seo' + suffix)
        return JSONResponse(seo_projection(payload, workspace_id), headers=HEADERS)
    except CustomerError as error:
        return error_response(error)


@router.post('/api/customer/workspaces/{workspace_id}/seo/{action}')
async def seo_write(request: Request, workspace_id: str, action: str):
    try:
        check_id(workspace_id)
        if action not in ('import-preview', 'confirm', 'keywords', 'plan', 'work', 'content-preview', 'content-confirm', 'content', 'project', 'keyword-from-gsc', 'website-sync', 'keywords-sync'):
            raise CustomerError(404, 'Không tìm thấy thao tác.')
        path = '/workspaces/' + workspace_id + '/seo/' + action
        if action not in ('import-preview', 'content-preview'):
            payload = await backend(request, 'POST', path, await read_body(request))
        else:
            settings = configuration(request)
            binding = browser_binding(request)
            if (request.headers.get('origin') != settings.customer_web_origin or not binding
                    or not secrets.compare_digest(request.headers.get('X-CSRF-Token', '').encode(), csrf_value(binding, settings).encode())):
                raise CustomerError(403, 'Phiên bảo vệ đã thay đổi. Tải lại trang.', 'csrf')
            if request.headers.get('content-type') != 'application/octet-stream':
                raise CustomerError(415, 'Định dạng tải lên không hợp lệ.')
            suffix = query(request, ('client_id', 'filename', 'website', 'device', 'location', 'language'))
            raw = bytearray()
            async for chunk in request.stream():
                raw.extend(chunk)
                if len(raw) > MAX_FILE:
                    raise CustomerError(413, 'File tối đa 2 MB.')
            headers = {'Authorization': 'Bearer ' + settings.customer_service_token.get_secret_value(),
                'X-Customer-Session': request.cookies.get(SESSION, ''), 'X-Customer-Client': client_fingerprint(request, settings),
                'Content-Type': 'application/octet-stream', 'Accept-Encoding': 'identity'}
            try:
                async with asyncio.timeout(45):
                    async with httpx.AsyncClient(timeout=40, follow_redirects=False, trust_env=False) as client:
                        async with client.stream('POST', settings.customer_backend_url + '/api/internal/customer' + path + suffix, content=bytes(raw), headers=headers) as response:
                            if 300 <= response.status_code < 400:
                                raise CustomerError(502, 'Dịch vụ trả về địa chỉ không hợp lệ.')
                            payload = await read_payload(response)
                            if response.status_code >= 400:
                                raise CustomerError(*public_error(response.status_code, payload))
                payload = public_payload(payload, path)
            except (httpx.HTTPError, TimeoutError):
                raise CustomerError(503, 'Chưa xác nhận được bản xem trước. Thử lại sau.', 'service_timeout') from None
            except (ValueError, TypeError):
                raise CustomerError(502, 'Bản xem trước không hợp lệ.') from None
            scoped(payload, workspace_id, request.query_params.get('client_id'))
        return JSONResponse(payload, headers=HEADERS)
    except CustomerError as error:
        return error_response(error)


@router.get('/api/customer/workspaces/{workspace_id}/compiled-reports')
async def compiled_index(request: Request, workspace_id: str):
    try:
        check_id(workspace_id)
        query(request, ())
        return JSONResponse(scoped(await backend(request, 'GET', '/workspaces/' + workspace_id + '/compiled-reports'), workspace_id), headers=HEADERS)
    except CustomerError as error:
        return error_response(error)


@router.post('/api/customer/workspaces/{workspace_id}/compiled-reports')
async def compiled_create(request: Request, workspace_id: str):
    try:
        check_id(workspace_id)
        payload = await backend(request, 'POST', '/workspaces/' + workspace_id + '/compiled-reports', await read_body(request))
        check_id(payload.get('id', ''))
        return JSONResponse({'id': payload['id'], 'message': payload.get('message'), 'href': '/workspace/reports/combined?report=' + payload['id']}, headers=HEADERS)
    except CustomerError as error:
        return error_response(error)


async def page_context(request):
    settings = configuration(request)
    account = await backend(request, 'GET', '/session')
    if not account.get('workspace'):
        raise CustomerError(409, 'Chọn Workspace trước khi tiếp tục.', 'workspace_required')
    workspace_id = account['workspace']['id']
    details = await backend(request, 'GET', '/workspaces/' + workspace_id)
    if details.get('workspace', {}).get('id') != workspace_id:
        raise CustomerError(409, 'Workspace đã thay đổi.', 'workspace_changed')
    return settings, account, details


async def page_error(request, error):
    if error.status == 401:
        return RedirectResponse('/workspace/login', 303, headers=HEADERS)
    if error.code == 'workspace_required':
        return RedirectResponse('/workspace/onboarding', 303, headers=HEADERS)
    return templates.TemplateResponse(request=request, name='customer/live/error.html',
        context={'title': 'SEO & Báo cáo', 'customer_page': 'error', 'customer_live': True, 'message': error.message}, status_code=error.status, headers=HEADERS)


@router.get('/workspace/seo')
async def seo_page(request: Request):
    try:
        settings, account, details = await page_context(request)
        query(request, ('start', 'end', 'profile', 'tab', *COMPARISON_PARAMETERS))
        response = templates.TemplateResponse(request=request, name='customer/live/seo.html',
            context={'title': 'SEO & Từ khóa', 'customer_page': 'channels', 'customer_live': True, 'customer_seo_live': True,
                     'account': account, 'details': details}, headers=HEADERS)
        if not browser_binding(request):
            set_cookie(response, BINDING, secrets.token_urlsafe(48), settings)
        return response
    except CustomerError as error:
        return await page_error(request, error)


@router.get('/workspace/reports/combined')
async def compiled_page(request: Request):
    try:
        settings, account, details = await page_context(request)
        query(request, ('report', 'sources', 'start', 'end', 'seo_profile', 'template', 'style', 'palette', 'order', 'hidden', *COMPARISON_PARAMETERS))
        from app.customer_report_presets import compiled_id, compiled_preset, seo_modules
        from app.customer_report_styles import style_context
        record = request.query_params.get('report')
        compiled = None
        if record:
            check_id(record)
            workspace_id = account['workspace']['id']
            compiled = scoped(await backend(request, 'GET', '/workspaces/' + workspace_id + '/compiled-reports/' + record), workspace_id,
                              (details.get('selected_client') or {}).get('id'))
            from app.customer_data import display, project
            from app.customer_report_view import build
            for item in compiled['sources']:
                if item['id'] == 'seo':
                    item['data'] = seo_projection(item['data'], workspace_id, compiled['scope']['client_id'])
                else:
                    item['data'] = project(item['data'], workspace_id)
                    item['view'] = build(item['data'])
                    if item.get('previous'):
                        item['previous'] = project(item['previous'], workspace_id)
        from app.customer_data import display
        preset_source, preset = compiled_preset(compiled.get('presentation') if compiled else request.query_params.get('template'))
        selected_style = request.query_params.get('style', compiled.get('style') if compiled else None)
        palette = request.query_params.get('palette', compiled.get('palette') if compiled else None)
        order = request.query_params.get('order', compiled.get('order') if compiled else None)
        hidden = request.query_params.get('hidden', compiled.get('hidden') if compiled else None)
        styling = style_context(selected_style, palette, preset, order, hidden)
        builder_style = styling['report_style'].key if not compiled and any(value is not None for value in (selected_style, palette, order, hidden)) else None
        modules = seo_modules(preset_source, preset)
        review = None
        if compiled:
            from app.compiled_commentary import compiled_sections
            from app.customer_report_notes import attach as attach_notes
            from app.customer_seo_reports import prepare
            compiled = prepare(compiled)
            review = await attach_notes(request, settings, compiled['scope'], {'form': 'compiled', 'id': record}, compiled_sections(compiled, modules))
        response = templates.TemplateResponse(request=request, name='customer/live/compiled-report.html' if compiled else 'customer/live/compiled-builder.html',
            context={'title': compiled['name'] if compiled else 'Báo cáo tổng hợp', 'customer_page': 'reports', 'customer_live': True,
                'customer_compiled_live': True, 'compiled': compiled, 'display': display, 'account': account, 'details': details, 'report_review': review,
                'report_preset': preset, 'preset_source': preset_source, 'seo_modules': modules,
                'presentation': compiled_id(preset_source, preset) if preset else None,
                'builder_style': builder_style, **styling,
                'compiled_sources': [('seo','SEO & Từ khóa'),('ga4','Google Analytics 4'),('gsc','Search Console'),('facebook_content','Facebook Content'),('facebook_ads','Facebook Ads'),('google_ads','Google Ads'),('instagram','Instagram'),('youtube','YouTube'),('business_profile','Google Business Profile'),('tiktok_ads','TikTok Ads')]}, headers=HEADERS)
        if not browser_binding(request):
            set_cookie(response, BINDING, secrets.token_urlsafe(48), settings)
        return response
    except CustomerError as error:
        return await page_error(request, error)
