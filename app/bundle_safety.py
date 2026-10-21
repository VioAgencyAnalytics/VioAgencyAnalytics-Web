"""Never render credential-bearing payloads or executable/untrusted source URLs."""
import math
import re
from urllib.parse import unquote, urlsplit, parse_qsl

from app.repositories.admin_bundle import AdminBundleContractError

SENSITIVE = re.compile(r'token|secret|password|authorization|credential|api[_-]?key|private[_-]?key', re.I)


def check_safe_payload(value: object, secrets: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if SENSITIVE.search(str(key)):
                raise AdminBundleContractError('Bundle chứa trường nhạy cảm; không được hiển thị.')
            check_safe_payload(str(key), secrets)
            check_safe_payload(item, secrets)
    elif isinstance(value, list):
        for item in value:
            check_safe_payload(item, secrets)
    elif isinstance(value, str):
        decoded = unquote(value)
        if any(secret and (secret in value or secret in decoded) for secret in secrets) or re.search(r'Bearer\s+\S+|-----BEGIN .*PRIVATE KEY-----|(?:access_token|refresh_token|client_secret|api_key|password)\s*[=:]\s*\S+', decoded, re.I):
            raise AdminBundleContractError('Bundle chứa thông tin nhạy cảm; không được hiển thị.')
    elif isinstance(value, float) and not math.isfinite(value):
        raise AdminBundleContractError('Bundle chứa số không hợp lệ.')


def safe_url(value: object) -> str | None:
    if not isinstance(value, str) or any(ord(c) < 33 for c in value) or '\\' in value:
        return None
    try:
        url = urlsplit(value)
        if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
            return None
        if any(SENSITIVE.search(k) for k, _ in parse_qsl(url.query)) or SENSITIVE.search(url.fragment):
            return None
        return value
    except ValueError:
        return None
