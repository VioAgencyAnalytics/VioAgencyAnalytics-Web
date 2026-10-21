"""Configured browser origin for Admin-owned authentication and report selection."""
from urllib.parse import urlsplit

from app.repositories.viewer import ViewerError


def public_origin(value):
    value = value.rstrip('/')
    try:
        parsed = urlsplit(value)
        parsed.port
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment
                or '\\' in value or any(ord(char) < 33 for char in value)
                or (parsed.scheme == 'http' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'))):
            raise ValueError()
    except ValueError:
        raise ViewerError(503, 'URL public chưa được cấu hình hợp lệ.') from None
    return value


def admin_entry(settings):
    return public_origin(settings.report_admin_public_url) + '/viewer/reports'
