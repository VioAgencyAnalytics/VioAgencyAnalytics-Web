"""Two explicit loopback origins, one Viewer application, isolated Admin ACLs."""
import secrets
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request

from app.config import Settings, get_settings
from app.admin_access import public_origin


def viewer_settings(request: Request, settings: Settings = Depends(get_settings)):
    if not settings.report_vio_viewer_enabled:
        return settings
    try:
        primary = public_origin(settings.report_new_public_url)
        vio = public_origin(settings.report_vio_new_public_url)
        a, b = urlsplit(primary), urlsplit(vio)
        main_admin = public_origin(settings.report_admin_public_url)
        vio_admin = public_origin(settings.report_vio_admin_public_url)
        main_token = settings.report_service_token.get_secret_value()
        vio_token = settings.report_vio_service_token.get_secret_value()
        if (a.scheme != 'http' or b.scheme != 'http' or a.hostname != 'localhost'
                or b.hostname != '127.0.0.1' or a.port != b.port or not a.port
                or main_admin == vio_admin
                or urlsplit(main_admin).hostname not in ('localhost', '127.0.0.1')
                or urlsplit(vio_admin).hostname not in ('localhost', '127.0.0.1')
                or not settings.report_vio_admin_base_url
                or settings.report_admin_base_url == settings.report_vio_admin_base_url
                or min(len(main_token), len(vio_token)) < 32
                or secrets.compare_digest(main_token, vio_token)):
            raise ValueError()
    except Exception:
        raise HTTPException(503, 'Cấu hình hai môi trường báo cáo chưa hợp lệ.') from None
    origin = str(request.base_url).rstrip('/')
    if origin == primary:
        return settings
    if origin != vio:
        raise HTTPException(421, 'Mở báo cáo từ đúng Admin của môi trường.')
    return settings.model_copy(update={
        'report_admin_base_url': settings.report_vio_admin_base_url,
        'report_admin_public_url': vio_admin,
        'report_new_public_url': vio,
        'report_service_token': settings.report_vio_service_token,
        'report_preview_enabled': False,
    })
