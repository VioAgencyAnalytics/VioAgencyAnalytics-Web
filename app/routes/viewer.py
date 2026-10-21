"""Dashboard access through Admin sessions; New never collects credentials."""
import os
import re
import secrets
from urllib.parse import parse_qs, urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.bundle_safety import check_safe_payload
from app.admin_access import admin_entry
from app.config import get_settings
from app.viewer_environment import viewer_settings
from app.repositories.admin_bundle import AdminBundleConfigError, AdminBundleContractError
from app.repositories.viewer import AdminViewerRepository, ViewerError
from app.routes.pages import templates
from app.routes.published import HEADERS
from app.services.bundle import BundleService, BundleServiceError
from app.mappers.dashboard import dashboard_context, preview_dashboard

router = APIRouter(tags=['viewer access'])
COOKIE_PREFIX = os.getenv('KDH_VIEWER_COOKIE_PREFIX', 'kdh')
if not re.fullmatch(r'[a-z][a-z0-9_]{0,31}', COOKIE_PREFIX):
    raise RuntimeError('Invalid Viewer cookie namespace.')
SESSION = COOKIE_PREFIX + '_viewer_session'
CSRF = COOKIE_PREFIX + '_viewer_csrf'


def repository(request: Request, settings=Depends(viewer_settings)):
    try:
        return AdminViewerRepository(settings.report_admin_base_url, settings.report_service_token.get_secret_value(),
                                     settings.report_request_timeout_seconds, viewer_session=request.cookies.get(SESSION, ''))
    except AdminBundleConfigError:
        raise ViewerError(503, 'Chưa cấu hình kết nối báo cáo với Admin.') from None


def resume_report(target, revision=None):
    scope = {'mode': 'published' if revision is not None else 'preview', 'target_id': target}
    if revision is not None:
        scope['revision'] = revision
    return RedirectResponse('/auth/handoff/start?' + urlencode(scope), 303, headers=HEADERS)


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


@router.get('/')
@router.get('/login', include_in_schema=False)
@router.get('/reports')
def admin_selection(request: Request, settings=Depends(viewer_settings)):
    # Old bookmarks remain usable, but authentication and selection live on Admin.
    # Query strings (including arbitrary next URLs) never select the redirect host.
    try:
        return RedirectResponse(admin_entry(settings), 303, headers=HEADERS)
    except ViewerError as exc:
        return error_page(request, exc)


@router.post('/logout')
async def logout(request: Request, settings=Depends(viewer_settings)):
    try:
        destination = admin_entry(settings)
        await form(request)
        repository(request, settings).call('DELETE', '/api/internal/v1/viewer-session')
    except ViewerError as exc:
        if exc.status != 401:
            return error_page(request, exc)
    response = RedirectResponse(destination, status_code=303, headers=HEADERS)
    response.delete_cookie(SESSION)
    response.delete_cookie(CSRF)
    return response


@router.get('/reports/{report_id}')
def report(request: Request, report_id: str, settings=Depends(viewer_settings)):
    try:
        revision_text = request.query_params.get('revision')
        if (not re.fullmatch(r'rpt_[a-f0-9]{32}', report_id) or set(request.query_params) - {'revision', 'section', 'view'}
                or any(len(request.query_params.getlist(key)) > 1 for key in request.query_params)):
            raise ViewerError(400, 'Mã báo cáo hoặc bộ lọc không hợp lệ.')
        if revision_text is not None and not re.fullmatch(r'[1-9][0-9]{0,8}', revision_text):
            raise ViewerError(400, 'Revision không hợp lệ.')
        if revision_text is None:
            return admin_selection(request, settings)
        bundle = BundleService(repository(request, settings)).get_report(report_id, int(revision_text))
        if settings.app_env == 'production' and bundle.provenance == 'demo':
            raise ViewerError(502, 'Báo cáo chứa dữ liệu mẫu; không được hiển thị trong production.')
        selected = request.query_params.get('section', bundle.default_section)
        if selected not in [section.key for section in bundle.sections]:
            raise ViewerError(404, 'Section không nằm trong báo cáo được xuất bản.')
        context = dashboard_context(bundle, selected, request.url.path)
        return templates.TemplateResponse(request=request, name=context['snapshot_template'],
            context={**context, 'viewer_mode': True, 'csrf': request.cookies.get(CSRF, '')}, headers=HEADERS)
    except ViewerError as exc:
        if exc.status == 401:
            return resume_report(report_id, revision_text)
        return error_page(request, exc)
    except BundleServiceError as exc:
        return error_page(request, exc)


@router.get('/internal-preview/{candidate_id}')
def internal_preview(request: Request, candidate_id: str, settings=Depends(viewer_settings)):
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
            return resume_report(candidate_id)
        return error_page(request, exc)
