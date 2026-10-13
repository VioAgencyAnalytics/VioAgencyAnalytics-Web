"""Viewer login and report access; no service credential reaches the browser."""
import re
import secrets
from dataclasses import asdict
from urllib.parse import parse_qs, quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.bundle_safety import check_safe_payload
from app.config import get_settings
from app.repositories.admin_bundle import AdminBundleConfigError, AdminBundleContractError
from app.repositories.viewer import AdminViewerRepository, ViewerError
from app.routes.pages import templates
from app.routes.published import HEADERS
from app.services.bundle import BundleService, BundleServiceError
from app.mappers.dashboard import dashboard_context, preview_dashboard

router = APIRouter(tags=['viewer access'])
SESSION = 'kdh_viewer_session'
CSRF = 'kdh_viewer_csrf'


def repository(request: Request, settings=Depends(get_settings)):
    try:
        return AdminViewerRepository(settings.report_admin_base_url, settings.report_service_token.get_secret_value(),
                                     settings.report_request_timeout_seconds, viewer_session=request.cookies.get(SESSION, ''))
    except AdminBundleConfigError:
        raise ViewerError(503, 'Chưa cấu hình kết nối báo cáo với Admin.') from None


def next_path(value):
    return value if isinstance(value, str) and re.fullmatch(r'/(?:reports(?:/rpt_[a-f0-9]{32})?|internal-preview/[a-f0-9]{32})(?:\?revision=[1-9][0-9]{0,8})?', value) else '/reports'


def error_page(request, error):
    return templates.TemplateResponse(request=request, name='pages/published/error.html',
        context={'title': 'Chưa thể mở báo cáo', 'code': 'access', 'message': str(error)},
        status_code=error.status if isinstance(error, ViewerError) else error.status_code, headers=HEADERS)


async def form(request):
    raw = await request.body()
    if len(raw) > 4096 or not request.headers.get('content-type', '').startswith('application/x-www-form-urlencoded'):
        raise ViewerError(400, 'Biểu mẫu không hợp lệ.')
    try:
        values = parse_qs(raw.decode('utf-8'), keep_blank_values=True, max_num_fields=12, errors='strict')
    except (UnicodeError, ValueError):
        raise ViewerError(400, 'Biểu mẫu không hợp lệ.') from None
    if any(len(value) != 1 for value in values.values()):
        raise ViewerError(400, 'Biểu mẫu bị trùng trường.')
    values = {key: value[0] for key, value in values.items()}
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise ViewerError(403, 'Nguồn gửi biểu mẫu không hợp lệ.')
    expected = request.cookies.get(CSRF, '')
    if not expected or not secrets.compare_digest(expected.encode(), values.get('csrf', '').encode()):
        raise ViewerError(403, 'Phiên bảo vệ đã đổi. Tải lại trang rồi thử lại.')
    return values


def safe_json(response, settings):
    try:
        payload = response.json()
        check_safe_payload(payload, (settings.report_service_token.get_secret_value(),))
        if not isinstance(payload, dict):
            raise ValueError()
        return payload
    except (ValueError, AdminBundleContractError):
        raise ViewerError(502, 'Dữ liệu báo cáo chưa đúng cấu trúc hoặc chứa trường không được phép hiển thị.') from None


@router.get('/login')
def login_page(request: Request):
    nonce = secrets.token_urlsafe(32)
    response = templates.TemplateResponse(request=request, name='pages/published/login.html',
        context={'title': 'Đăng nhập báo cáo', 'csrf': nonce, 'next': next_path(request.query_params.get('next'))}, headers=HEADERS)
    response.set_cookie(CSRF, nonce, httponly=True, samesite='lax', secure=request.url.scheme == 'https', max_age=28800)
    return response


@router.post('/login')
async def login(request: Request, settings=Depends(get_settings)):
    try:
        data = await form(request)
        email, password = data.get('email', ''), data.get('password', '')
        if not email or len(email) > 254 or not password or len(password) > 256:
            raise ViewerError(400, 'Nhập email và mật khẩu hợp lệ.')
        upstream = repository(request, settings)
        session = upstream.login(email, password)
        response = RedirectResponse(next_path(data.get('next')), status_code=303, headers=HEADERS)
        response.set_cookie(SESSION, session, httponly=True, samesite='lax', secure=request.url.scheme == 'https', max_age=28800)
        return response
    except ViewerError as exc:
        return error_page(request, exc)


@router.post('/logout')
async def logout(request: Request, settings=Depends(get_settings)):
    try:
        await form(request)
        repository(request, settings).call('DELETE', '/api/internal/v1/viewer-session')
    except ViewerError as exc:
        if exc.status != 401:
            return error_page(request, exc)
    response = RedirectResponse('/login', status_code=303, headers=HEADERS)
    response.delete_cookie(SESSION)
    response.delete_cookie(CSRF)
    return response


@router.get('/reports')
def reports(request: Request, settings=Depends(get_settings)):
    try:
        response = safe_json(repository(request, settings).call('GET', '/api/internal/v1/viewer/report-bundles'), settings)
        if not isinstance(response.get('reports'), list) or any(
                not isinstance(item, dict) or not isinstance(item.get('report_id'), str)
                or not re.fullmatch(r'rpt_[a-f0-9]{32}', item['report_id']) or type(item.get('revision')) is not int
                or item['revision'] < 1 or item.get('status') not in ('provisional', 'final') for item in response['reports']):
            raise ViewerError(502, 'Danh sách báo cáo không hợp lệ.')
        return templates.TemplateResponse(request=request, name='pages/published/list.html',
            context={'title': 'Báo cáo được cấp quyền', 'reports': response['reports'], 'csrf': request.cookies.get(CSRF, '')}, headers=HEADERS)
    except ViewerError as exc:
        return RedirectResponse('/login', status_code=303, headers=HEADERS) if exc.status == 401 else error_page(request, exc)


@router.get('/reports/{report_id}')
def report(request: Request, report_id: str, settings=Depends(get_settings)):
    try:
        revision_text = request.query_params.get('revision')
        if (not re.fullmatch(r'rpt_[a-f0-9]{32}', report_id) or set(request.query_params) - {'revision', 'section', 'view'}
                or any(len(request.query_params.getlist(key)) > 1 for key in request.query_params)):
            raise ViewerError(400, 'Mã báo cáo hoặc bộ lọc không hợp lệ.')
        if revision_text is not None and not re.fullmatch(r'[1-9][0-9]{0,8}', revision_text):
            raise ViewerError(400, 'Revision không hợp lệ.')
        bundle = BundleService(repository(request, settings)).get_report(report_id, int(revision_text) if revision_text else None)
        selected = request.query_params.get('section', bundle.default_section)
        if selected not in [section.key for section in bundle.sections]:
            raise ViewerError(404, 'Section không nằm trong báo cáo được xuất bản.')
        context = dashboard_context(bundle, selected, request.url.path)
        return templates.TemplateResponse(request=request, name=context['snapshot_template'],
            context={**context, 'viewer_mode': True, 'csrf': request.cookies.get(CSRF, '')}, headers=HEADERS)
    except ViewerError as exc:
        if exc.status == 401:
            destination = next_path(request.url.path + ('?revision=' + revision_text if revision_text else ''))
            return RedirectResponse('/login?next=' + quote(destination, safe=''), status_code=303, headers=HEADERS)
        return error_page(request, exc)
    except BundleServiceError as exc:
        return error_page(request, exc)


@router.get('/internal-preview/{candidate_id}')
def internal_preview(request: Request, candidate_id: str, settings=Depends(get_settings)):
    try:
        if not re.fullmatch(r'[a-f0-9]{32}', candidate_id):
            raise ViewerError(404, 'Không tìm thấy bản xem trước.')
        payload = safe_json(repository(request, settings).call('GET', '/api/internal/v1/marketing-preview/' + candidate_id), settings)
        if payload.get('kind') != 'marketing_internal_preview' or payload.get('publishable') is not False:
            raise ViewerError(502, 'Bản xem trước không đúng phạm vi nội bộ.')
        if (not isinstance(payload.get('candidate'), dict) or not isinstance(payload['candidate'].get('marketing'), dict)
                or not isinstance(payload['candidate']['marketing'].get('preview'), dict) or not isinstance(payload.get('issues'), list)):
            raise ViewerError(502, 'Bản xem trước không hợp lệ.')
        bundle = preview_dashboard(payload['candidate'], payload['issues'], candidate_id)
        if request.query_params.get('section', bundle.default_section) != bundle.default_section:
            raise ViewerError(404, 'Section không nằm trong bản xem trước.')
        context = dashboard_context(bundle, bundle.default_section, request.url.path, preview=True)
        return templates.TemplateResponse(request=request, name=context['snapshot_template'],
            context={**context, 'viewer_mode': True, 'csrf': request.cookies.get(CSRF, '')}, headers=HEADERS)
    except ViewerError as exc:
        if exc.status == 401:
            return RedirectResponse('/login?next=' + quote(request.url.path, safe=''), status_code=303, headers=HEADERS)
        return error_page(request, exc)
