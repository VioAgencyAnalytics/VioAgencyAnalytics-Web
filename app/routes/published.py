"""Protected development preview. Viewer login/ACL is a separate NEW-2 task."""
from dataclasses import asdict
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import Settings, get_settings
from app.repositories.admin_bundle import AdminBundleRepository, AdminBundleConfigError
from app.routes.pages import templates
from app.services.bundle import BundleService, BundleServiceError
from app.mappers.dashboard import dashboard_context

router = APIRouter(tags=['published reports'])
basic = HTTPBasic(auto_error=False)
HEADERS = {
    'Cache-Control': 'no-store, private', 'Pragma': 'no-cache',
    # Preserve Origin on same-origin form POSTs; disclose no referrer externally.
    'X-Robots-Tag': 'noindex, nofollow', 'Referrer-Policy': 'same-origin',
    'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY',
    'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
}


def require_preview_access(report_id: str, settings: Annotated[Settings, Depends(get_settings)],
                           credentials: Annotated[HTTPBasicCredentials | None, Depends(basic)]) -> Settings:
    password = settings.report_preview_password.get_secret_value()
    if settings.app_env == 'production' or not settings.report_preview_enabled:
        raise HTTPException(404, 'Báo cáo chưa được mở cho người xem.', headers=HEADERS)
    if not settings.report_preview_username or len(password) < 24 or not settings.report_preview_allowed_ids or password == settings.report_service_token.get_secret_value():
        raise HTTPException(503, 'Preview chưa được cấu hình quyền truy cập riêng.', headers=HEADERS)
    user = credentials.username if credentials else ''
    supplied = credentials.password if credentials else ''
    valid_user = secrets.compare_digest(user.encode('utf-8'), settings.report_preview_username.encode('utf-8'))
    valid_password = secrets.compare_digest(supplied.encode('utf-8'), password.encode('utf-8'))
    if not (valid_user and valid_password):
        raise HTTPException(401, 'Cần tài khoản preview được cấp riêng.', headers={**HEADERS, 'WWW-Authenticate': 'Basic realm="KDH report preview"'})
    if report_id not in settings.report_preview_allowed_ids:
        raise HTTPException(404, 'Không có báo cáo trong phạm vi được cấp.', headers=HEADERS)
    return settings


def get_bundle_service(settings: Annotated[Settings, Depends(require_preview_access)]) -> BundleService:
    try:
        return BundleService(AdminBundleRepository(settings.report_admin_base_url, settings.report_service_token.get_secret_value(), settings.report_request_timeout_seconds))
    except AdminBundleConfigError:
        raise HTTPException(503, 'Chưa cấu hình kết nối backend với Admin.', headers=HEADERS) from None


@router.get('/published/{report_id}')
def published_report(request: Request, report_id: str, service: Annotated[BundleService, Depends(get_bundle_service)],
                     revision: Annotated[int | None, Query(gt=0, le=999999999)] = None,
                     section: str | None = None):
    try:
        bundle = service.get_report(report_id, revision)
    except BundleServiceError as exc:
        return templates.TemplateResponse(request=request, name='pages/published/error.html',
            context={'title': 'Chưa thể mở báo cáo', 'code': exc.code, 'message': str(exc)}, status_code=exc.status_code, headers=HEADERS)
    selected = section or bundle.default_section
    if selected not in [s.key for s in bundle.sections]:
        raise HTTPException(404, 'Section không nằm trong Bundle.', headers=HEADERS)
    # Only mapped display data is passed to Jinja, never settings or the raw bundle.
    context = dashboard_context(bundle, selected, request.url.path)
    return templates.TemplateResponse(request=request, name=context['snapshot_template'], context=context, headers=HEADERS)
