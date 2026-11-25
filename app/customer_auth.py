"""Customer BFF: identity remains in Admin; the browser receives only an opaque cookie."""
import hashlib
import hmac
import logging
import re
import secrets
import asyncio
from functools import lru_cache
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.routes.pages import templates
from app.customer_transport import PROVIDERS, public_error, public_payload, read_payload

router = APIRouter(tags=['customer identity'])
logger = logging.getLogger(__name__)
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
               'X-Customer-Client': client_fingerprint(request, settings),
               'Accept': 'application/json', 'Accept-Encoding': 'identity'}
    try:
        async with asyncio.timeout(45):
            async with httpx.AsyncClient(timeout=httpx.Timeout(40, connect=5), follow_redirects=False, trust_env=False) as client:
                async with client.stream(method, settings.customer_backend_url + '/api/internal/customer' + path, json=data, headers=headers) as response:
                    if 300 <= response.status_code < 400:
                        raise ValueError('Admin redirects are not followed')
                    payload = await read_payload(response)
                    status = response.status_code
        if status >= 400:
            raise CustomerError(*public_error(status, payload))
        return public_payload(payload, path.split('?', 1)[0])
    except (httpx.TimeoutException, TimeoutError):
        raise CustomerError(503, 'Dịch vụ phản hồi chậm. Hãy kiểm tra trạng thái trước khi thử lại.', 'service_timeout') from None
    except httpx.HTTPError:
        raise CustomerError(503, 'Chưa kết nối được dịch vụ tài khoản. Vui lòng thử lại.', 'service_unavailable') from None
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise CustomerError(502, 'Dịch vụ trả về phản hồi chưa hợp lệ. Vui lòng thử lại.', 'service_response') from None


async def read_body(request, max_bytes=16384):
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
        if len(raw) > max_bytes:
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


def login_response(request, payload, *, redirect=False):
    raw = payload.pop('session_token', None)
    age = payload.pop('session_max_age', None)
    if not isinstance(raw, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', raw):
        raise CustomerError(502, 'Dịch vụ trả về phiên đăng nhập không hợp lệ.')
    if age is not None and (type(age) is not int or not 1 <= age <= 30 * 86400):
        raise CustomerError(502, 'Dịch vụ trả về thời hạn phiên không hợp lệ.')
    settings = configuration(request)
    destination = payload.pop('redirect', '/workspace/onboarding')
    if destination not in ('/workspace', '/workspace/onboarding'):
        raise CustomerError(502, 'Địa chỉ sau đăng nhập không hợp lệ.')
    response = (RedirectResponse(destination, 303, headers=HEADERS) if redirect
                else JSONResponse({**payload, 'redirect': destination}, headers=HEADERS))
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


POST_PATHS = {'auth/register', 'auth/login', 'auth/logout', 'auth/google/start', 'branding/preview',
              'auth/email/reset', 'auth/email/verify', 'auth/email/confirm', 'workspaces', 'workspaces/join'}


def google_login_result(payload, settings):
    """Only return a validated identity consent URL, never extra backend fields."""
    address = payload.get('authorization_url')
    try:
        if not isinstance(address, str) or len(address) > 8192 or any(ord(c) < 33 for c in address):
            raise ValueError()
        url = urlsplit(address)
        query = parse_qs(url.query, keep_blank_values=True)
        expected = {'client_id', 'redirect_uri', 'response_type', 'scope', 'state', 'nonce',
                    'code_challenge', 'code_challenge_method', 'prompt'}
        if (url.scheme != 'https' or url.netloc != 'accounts.google.com' or url.fragment
                or url.path != '/o/oauth2/v2/auth' or set(query) != expected
                or any(len(value) != 1 for value in query.values())
                or not query['client_id'][0]
                or query['redirect_uri'] != [settings.customer_web_origin + '/auth/customer/google/callback']
                or query['response_type'] != ['code'] or query['code_challenge_method'] != ['S256']
                or query['prompt'] != ['select_account']
                or sorted(query['scope'][0].split()) != ['email', 'openid', 'profile']
                or any(not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', query[key][0])
                       for key in ('state', 'nonce', 'code_challenge'))):
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise CustomerError(502, 'Chưa mở được đăng nhập Google. Vui lòng thử lại.') from None
    return {'authorization_url': address}


def provider_result(path, payload, settings, expected_client_id=None):
    """Project only safe provider DTO fields; never forward credentials to JS."""
    if '/providers/' in path:
        source = path.split('/')[-2]
        provider = PROVIDERS[source]
        address = payload.get('authorization_url')
        try:
            url = urlsplit(address)
            query = parse_qs(url.query, keep_blank_values=True)
            allowed = {'client_id','redirect_uri','response_type','state','access_type','prompt','scope',
                       'code_challenge','code_challenge_method','nonce'} if provider=='google' else {
                       'app_id','redirect_uri','state'} if provider=='tiktok' else {
                       'client_id','redirect_uri','response_type','state','config_id','override_default_response_type'}
            host = {'google':'accounts.google.com','meta':'www.facebook.com','tiktok':'business-api.tiktok.com'}[provider]
            valid_path = (url.path=='/o/oauth2/v2/auth' if provider=='google' else url.path in ('/portal/auth','/portal/auth/')
                          if provider=='tiktok' else bool(re.fullmatch(r'/v\d+\.\d+/dialog/oauth',url.path)))
            if (not isinstance(address,str) or len(address)>8192 or url.scheme!='https' or url.fragment
                    or url.netloc!=host or not valid_path
                    or set(query)-allowed or any(len(v)!=1 for v in query.values())
                    or (provider!='tiktok' and query.get('response_type')!=['code'])
                    or not query.get('state', [''])[0] or len(query['state'][0])>128
                    or not query.get('app_id' if provider=='tiktok' else 'client_id', [''])[0]
                    or provider=='meta' and (not re.fullmatch(r'\d+',query.get('config_id',[''])[0])
                        or query.get('override_default_response_type')!=['true'])
                    or query.get('redirect_uri')!=[settings.customer_web_origin+'/auth/customer/providers/'+provider+'/callback']):
                raise ValueError()
        except (TypeError, ValueError, AttributeError):
            raise CustomerError(502,'Địa chỉ cấp quyền không hợp lệ.') from None
        return {'authorization_url': address}
    action = path.rsplit('/',1)[-1]
    if action=='discover':
        assets = payload.get('assets')
        parts = path.split('/')
        if (payload.get('workspace_id')!=parts[1] or payload.get('connection_id')!=parts[3]
                or not isinstance(payload.get('client_id'),str) or not re.fullmatch(r'[a-f0-9]{32}',payload['client_id'])
                or type(payload.get('version')) is not int or payload['version']<1
                or expected_client_id is not None and payload['client_id']!=expected_client_id):
            raise CustomerError(502,'Danh sách tài sản không thuộc kết nối đang chọn.','connection_scope')
        if (not isinstance(assets,list) or len(assets)>15000 or any(not isinstance(a,dict)
                or not isinstance(a.get('id'),str) or not 1<=len(a['id'])<=2048
                or not isinstance(a.get('name'),str) or not 1<=len(a['name'])<=2048
                or any(a.get(key) is not None and (not isinstance(a[key],str) or len(a[key])>100) for key in ('currency','timezone')) for a in assets)
                or len({a['id'] for a in assets})!=len(assets)):
            raise CustomerError(502,'Danh sách tài sản không hợp lệ.')
        return {**{key:payload.get(key) for key in ('connection_id','workspace_id','client_id','version')},
                'assets':[{key:asset.get(key) for key in ('id','name','currency','timezone')} for asset in assets]}
    if action in ('select','sync'):
        job = payload.get('sync')
        if (not isinstance(job,dict) or not isinstance(job.get('id'),str) or not re.fullmatch(r'[a-f0-9]{32}',job['id'])
                or job.get('status') not in ('queued','running','succeeded','failed','cancelled')):
            raise CustomerError(502,'Trạng thái đồng bộ không hợp lệ.')
        if action=='select' and (payload.get('connection_id')!=path.split('/')[3]
                or not isinstance(payload.get('asset_id'),str) or not re.fullmatch(r'[a-f0-9]{32}',payload['asset_id'])):
            raise CustomerError(502,'Kết quả không thuộc kết nối đang chọn.','connection_scope')
        return {**({key:payload.get(key) for key in ('connection_id','asset_id')} if action=='select' else {}),
                'sync':{key:job.get(key) for key in ('id','status')}}
    return {key:payload.get(key) for key in ('message','provider_revoked')}


@router.post('/api/customer/{path:path}')
async def customer_mutation(request: Request, path: str):
    try:
        data = await read_body(request)
        if (path not in POST_PATHS
                and not re.fullmatch(r'workspaces/[a-f0-9]{32}/(select|invitations|tour|clients)', path)
                and not re.fullmatch(r'workspaces/[a-f0-9]{32}/clients/[a-f0-9]{32}/(select|update|archive|restore)',path)
                and not re.fullmatch(r'workspaces/[a-f0-9]{32}/settings', path)
                and not re.fullmatch(r'workspaces/[a-f0-9]{32}/members/[a-f0-9]{32}/(role|remove)', path)
                and not re.fullmatch(r'workspaces/[a-f0-9]{32}/invitations/[a-f0-9]{32}/revoke', path)
                and not re.fullmatch(r'workspaces/[a-f0-9]{32}/providers/(ga4|gsc|facebook_content|facebook_ads|google_ads|instagram|youtube|business_profile|tiktok_ads)/start', path)
                and not re.fullmatch(r'workspaces/[a-f0-9]{32}/targets/(ga4|gsc|facebook_content|facebook_ads|google_ads|instagram|youtube|business_profile|tiktok_ads)', path)
                and not re.fullmatch(r'workspaces/[a-f0-9]{32}/connections/[a-f0-9]{32}/(discover|select|sync|disconnect)', path)):
            raise CustomerError(404, 'Không tìm thấy chức năng.')
        if path == 'auth/google/start':
            data = {'remember': data.get('remember') is True, 'browser_binding': hashlib.sha256(browser_binding(request).encode()).hexdigest()}
        if re.fullmatch(r'workspaces/[a-f0-9]{32}/providers/(ga4|gsc|facebook_content|facebook_ads|google_ads|instagram|youtube|business_profile|tiktok_ads)/start', path):
            if set(data) != {'client_id'}:
                raise CustomerError(422, 'Thông tin kết nối không hợp lệ.')
            data = {**data, 'browser_binding': hashlib.sha256(browser_binding(request).encode()).hexdigest()}
        payload = await backend(request, 'POST', '/' + path, data)
        if path == 'auth/google/start':
            payload = google_login_result(payload, configuration(request))
        if path == 'branding/preview':
            from app.customer_branding import preview_result
            payload = preview_result(payload)
        if re.fullmatch(r'workspaces/[a-f0-9]{32}/targets/(ga4|gsc|facebook_content|facebook_ads|google_ads|instagram|youtube|business_profile|tiktok_ads)',path):
            message=payload.get('message')
            if not isinstance(message,str) or len(message)>250:
                raise CustomerError(502,'Chưa xác nhận được mục tiêu KPI.')
            payload={'message':message}
        if re.fullmatch(r'workspaces/[a-f0-9]{32}/(providers/[^/]+/start|connections/[a-f0-9]{32}/[^/]+)',path):
            payload = provider_result(path,payload,configuration(request),data.get('client_id'))
        if path in ('auth/register', 'auth/login'):
            return login_response(request, payload)
        response = JSONResponse(payload, headers=HEADERS)
        if path == 'auth/logout' or (path == 'auth/email/confirm' and data.get('kind') == 'reset'):
            response.delete_cookie(SESSION, path='/')
            response.delete_cookie(BINDING, path='/')
        return response
    except CustomerError as exc:
        return error_response(exc)


@router.get('/auth/customer/providers/{provider}/callback')
async def provider_callback(request: Request, provider: str):
    if provider not in ('google', 'meta', 'tiktok'):
        return error_response(CustomerError(404, 'Không tìm thấy chức năng.'))
    try:
        configuration(request)
        binding = browser_binding(request)
        if not binding or any(len(request.query_params.getlist(key)) > 1 for key in ('state', 'code', 'auth_code', 'error')):
            raise CustomerError(400, 'Phiên cấp quyền không hợp lệ.', 'oauth_state')
        data = {key: request.query_params.get(key, '') for key in ('state', 'code', 'error')}
        if provider == 'tiktok':
            # Marketing API returns auth_code and may also return a different
            # code parameter. Only its documented auth_code is exchanged.
            data['code'] = request.query_params.get('auth_code', '')
        data['browser_binding'] = hashlib.sha256(binding.encode()).hexdigest()
        payload = await backend(request, 'POST', '/providers/' + provider + '/finish', data)
        if (not all(isinstance(payload.get(key),str) and re.fullmatch(r'[a-f0-9]{32}',payload[key])
                    for key in ('workspace_id','client_id','connection_id'))
                or not isinstance(payload.get('platform_id'),str) or PROVIDERS.get(payload['platform_id'])!=provider):
            raise CustomerError(502, 'Kết quả cấp quyền không hợp lệ.', 'provider_failed')
        return RedirectResponse('/workspace/integrations?oauth=connected&connection=' + payload['connection_id'] + '&platform=' + payload['platform_id'],303,headers=HEADERS)
    except CustomerError as exc:
        if exc.status == 404:
            return error_response(exc)
        allowed = {'provider_cancelled','oauth_state','provider_scopes','workspace_changed','client_changed',
                   'email_verification_required','connector_not_configured','provider_reauth',
                   'provider_setup_required','provider_account_required','provider_rate_limit'}
        code = exc.code if exc.code in allowed else 'provider_failed'
        return RedirectResponse('/workspace/integrations?oauth=' + code,303,headers=HEADERS)


@router.get('/api/customer/workspaces/{workspace_id}')
async def workspace_detail(request: Request, workspace_id: str):
    try:
        if not re.fullmatch(r'[a-f0-9]{32}', workspace_id):
            raise CustomerError(404, 'Không tìm thấy Workspace.')
        return JSONResponse(await backend(request, 'GET', '/workspaces/' + workspace_id), headers=HEADERS)
    except CustomerError as exc:
        return error_response(exc)


@router.get('/api/customer/workspaces/{workspace_id}/logo')
async def workspace_logo(request: Request, workspace_id: str):
    from app.customer_branding import read
    return await read(request, workspace_id)


@router.get('/api/customer/workspaces/{workspace_id}/integrations')
async def workspace_integrations(request: Request, workspace_id: str):
    try:
        if not re.fullmatch(r'[a-f0-9]{32}', workspace_id):
            raise CustomerError(404, 'Không tìm thấy Workspace.')
        return JSONResponse(await backend(request, 'GET', '/workspaces/' + workspace_id + '/integrations'), headers=HEADERS)
    except CustomerError as exc:
        return error_response(exc)


@router.get('/api/customer/workspaces/{workspace_id}/channels/facebook-content')
async def customer_facebook_content(request: Request,workspace_id: str):
    from app.customer_meta import read
    return await read(request,workspace_id)


@router.get('/api/customer/workspaces/{workspace_id}/data')
async def customer_data_index(request: Request, workspace_id: str):
    from app.customer_data import read
    return await read(request, workspace_id)


@router.get('/api/customer/workspaces/{workspace_id}/data/{source}')
async def customer_source_data(request: Request, workspace_id: str, source: str):
    from app.customer_data import read
    return await read(request, workspace_id, source)


@router.get('/workspace/reports/data')
async def customer_data_page(request: Request):
    from app.customer_data import page
    return await page(request)


@router.get('/api/customer/workspaces/{workspace_id}/members')
async def workspace_members(request: Request, workspace_id: str):
    return await workspace_management_read(request, workspace_id, 'members')


@router.get('/api/customer/workspaces/{workspace_id}/settings')
async def workspace_settings(request: Request, workspace_id: str):
    return await workspace_management_read(request, workspace_id, 'settings')


async def workspace_management_read(request, workspace_id, section):
    try:
        if not re.fullmatch(r'[a-f0-9]{32}', workspace_id):
            raise CustomerError(404, 'Không tìm thấy Workspace.')
        return JSONResponse(await backend(request, 'GET', '/workspaces/' + workspace_id + '/' + section), headers=HEADERS)
    except CustomerError as exc:
        return error_response(exc)


@router.get('/auth/customer/google/callback')
async def google_callback(request: Request):
    try:
        configuration(request)
        binding = browser_binding(request)
        if (not binding or any(len(request.query_params.getlist(key)) > 1 for key in ('state', 'code', 'error'))
                or not request.query_params.get('state')
                or bool(request.query_params.get('code')) == bool(request.query_params.get('error'))):
            raise CustomerError(400, 'Phiên đăng nhập đã hết hạn.', 'oauth_state')
        data = {key: request.query_params.get(key, '') for key in ('state', 'code', 'error')}
        data['browser_binding'] = hashlib.sha256(binding.encode()).hexdigest()
        payload = await backend(request, 'POST', '/auth/google/finish', data)
        return login_response(request, payload, redirect=True)
    except CustomerError as exc:
        if exc.status == 404:
            return error_response(exc)
        allowed = {'google_cancelled', 'oauth_state', 'account_link_required', 'google_configuration',
                   'google_unavailable', 'google_clock', 'google_identity'}
        code = exc.code if exc.code in allowed else 'google_failed'
        logger.warning('Customer Google callback failed: code=%s status=%s', code, exc.status)
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
        if page in ('', 'integrations', 'dashboard', 'channels', 'reports', 'members', 'settings'):
            if not user.get('workspace'):
                return RedirectResponse('/workspace/onboarding', 303, headers=HEADERS)
            suffix = '/' + page if page in ('integrations', 'members', 'settings') else ''
            details = await backend(request, 'GET', '/workspaces/' + user['workspace']['id'] + suffix)
        name = 'overview' if page == '' else page
        if page == 'reports' and any(key in request.query_params for key in ('report', 'category', 'q')):
            from app.customer_report_templates import LIBRARY, TEMPLATE_BY_SLUG, catalogue_filters
            previous = request.query_params.get('report', '')
            slug = 'combined' if previous == 'overview' else previous.replace('_', '-')
            item = TEMPLATE_BY_SLUG.get(slug)
            if item or 'category' in request.query_params or 'q' in request.query_params:
                url = (item.preview_url if item else LIBRARY) + catalogue_filters(request.query_params)
                return RedirectResponse(url, 303, headers=HEADERS)
        overview = library = None
        if page in ('', 'dashboard', 'channels', 'reports'):
            from app.mappers.customer_overview import build_overview
            catalogue = await backend(request, 'GET', '/workspaces/' + user['workspace']['id'] + '/integrations')
            if catalogue.get('workspace', {}).get('id') != details['workspace']['id']:
                raise CustomerError(409, 'Workspace đã thay đổi. Vui lòng tải lại trang.', 'workspace_changed')
            if page in ('channels', 'reports'):
                from app.mappers.customer_library import build_library
                try:
                    library = build_library(details, catalogue)
                except ValueError:
                    raise CustomerError(409, 'Khách hàng đã thay đổi. Vui lòng tải lại trang.', 'workspace_changed') from None
            elif page == 'dashboard':
                from app.mappers.customer_marketing import build_marketing
                overview = build_marketing(details, catalogue)
            else:
                overview = build_overview(details, catalogue)
        response = templates.TemplateResponse(request=request, name=f'customer/live/{name}.html',
            context={'title': {'login':'Đăng nhập','overview':'Tổng quan Workspace','onboarding':'Thiết lập Workspace','integrations':'Kết nối nền tảng','dashboard':'Dashboard Marketing','channels':'Phân tích kênh','reports':'Trung tâm Báo cáo','members':'Thành viên','settings':'Cài đặt'}[name],
                     'customer_page': name, 'customer_live': True, 'account': user, 'details': details,
                     'overview': overview, 'library': library}, headers=HEADERS)
        if not browser_binding(request):
            set_cookie(response, BINDING, secrets.token_urlsafe(48), settings)
        return response
    except CustomerError as exc:
        return templates.TemplateResponse(request=request, name='customer/live/error.html',
            context={'title': 'Kết nối tài khoản', 'customer_page': 'error', 'customer_live': True,
                     'message': exc.message}, status_code=exc.status, headers=HEADERS)


@router.get('/api/customer/workspaces/{workspace_id}/analytics')
async def customer_saved_analytics(request: Request, workspace_id: str):
    from app.customer_analytics import read
    return await read(request, workspace_id)
