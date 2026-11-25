"""Bounded private Admin transport, shared by all Customer source requests.

No automatic retries: consent callbacks and mutations may already have committed
when a connection drops. The caller must re-read state or use its idempotency key.
"""
import json
import math
import re

MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_RESPONSE_NODES = 250000
PROVIDERS = {
    'facebook_content': 'meta', 'facebook_ads': 'meta', 'instagram': 'meta',
    'ga4': 'google', 'gsc': 'google', 'google_ads': 'google', 'youtube': 'google',
    'business_profile': 'google', 'tiktok_ads': 'tiktok',
}
SESSION_PATHS = {'/auth/login', '/auth/register', '/auth/google/finish'}
PRIVATE_FIELDS = frozenset(('accesstoken', 'refreshtoken', 'idtoken', 'credential',
    'encryptedcredential', 'clientsecret', 'appsecret', 'password', 'passwordhash',
    'smtppassword', 'servicetoken', 'encryptionkey', 'codeverifier', 'authorization'))
ERROR_CODES = frozenset(('invalid', 'customer_error', 'account_exists', 'account_link_required',
    'already_member', 'asset_required', 'client_access', 'client_changed', 'client_conflict',
    'client_limit', 'client_permission', 'configuration', 'connection_access', 'connection_input',
    'connection_permission', 'connection_version', 'connector_not_configured', 'connector_unavailable',
    'connector_unknown', 'credentials', 'email_delivery', 'email_not_configured', 'email_token',
    'email_unverified', 'email_verification_required', 'google_cancelled', 'google_identity',
    'google_not_configured', 'google_configuration', 'google_unavailable', 'google_failed', 'google_clock',
    'idempotency_conflict', 'invitation_invalid', 'invitation_pending', 'member_permission',
    'member_version', 'oauth_state', 'provider_account_required', 'provider_asset_scope',
    'provider_bad_response', 'provider_cancelled', 'provider_identity', 'provider_open_day',
    'provider_page_limit', 'provider_rate_limit', 'provider_reauth', 'provider_scopes',
    'provider_setup_required', 'provider_timeout', 'provider_unavailable', 'rate_limited',
    'report_note_input', 'report_note_finalized', 'report_note_version', 'report_period_input', 'report_template', 'service_auth', 'settings_version', 'snapshot_access', 'snapshot_input',
    'snapshot_invalid', 'sync_cancelled', 'sync_request_conflict', 'target_access', 'target_currency',
    'target_input', 'target_version', 'unauthenticated', 'workspace_access', 'workspace_changed',
    'workspace_permission'))
SERVER_MESSAGES = {
    'provider_setup_required': 'Vio cần hoàn tất cấu hình API của nền tảng. Vui lòng liên hệ hỗ trợ.',
    'connector_not_configured': 'Vio chưa cấu hình ứng dụng cho nguồn này. Vui lòng liên hệ hỗ trợ.',
    'provider_timeout': 'Nền tảng phản hồi chậm. Vui lòng kiểm tra trạng thái rồi thử lại.',
    'provider_bad_response': 'Nền tảng chưa trả dữ liệu hợp lệ. Vui lòng thử lại sau.',
    'provider_page_limit': 'Lượng dữ liệu vượt giới hạn lần đọc. Hãy chọn kỳ ngắn hơn.',
    'provider_unavailable': 'Chưa đọc được dữ liệu từ nền tảng. Vui lòng thử lại sau.',
    'email_delivery': 'Chưa gửi được email. Vui lòng thử lại sau.',
    'email_not_configured': 'Chức năng gửi email chưa được cấu hình. Vui lòng liên hệ hỗ trợ.',
    'google_not_configured': 'Đăng nhập Google chưa được cấu hình. Bạn có thể đăng nhập bằng email.',
    'google_configuration': 'Vio cần kiểm tra cấu hình đăng nhập Google. Bạn có thể đăng nhập bằng email.',
    'google_unavailable': 'Chưa kết nối được Google. Vui lòng thử lại sau.',
}


def normalized_key(value):
    return value.lower().replace('_', '').replace('-', '')


def public_payload(value, path):
    """Defense in depth for identity/workspace DTOs as well as source projections.

    Values, null, zero and decimal strings are preserved. Session material can
    only reach login_response at the root of a session-issuing endpoint, where it
    is moved into an HttpOnly cookie. Invitation codes are a separate feature.
    """
    visited = 0
    def copy(item, depth=0):
        nonlocal visited
        visited += 1
        if depth > 40 or visited > MAX_RESPONSE_NODES:
            raise ValueError('Admin response exceeds structural budget')
        if isinstance(item, dict):
            result = {}
            for key, entry in item.items():
                name = normalized_key(key)
                if name == 'sessiontoken':
                    if depth == 0 and path in SESSION_PATHS:
                        result[key] = entry
                    continue
                if name in PRIVATE_FIELDS or any(name.endswith(suffix) for suffix in ('clientsecret', 'appsecret', 'smtppassword', 'servicetoken', 'encryptionkey')):
                    continue
                result[key] = copy(entry, depth + 1)
            return result
        if isinstance(item, list):
            return [copy(entry, depth + 1) for entry in item]
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError('Non-finite Admin value')
        return item
    result = copy(value)
    if path == '/config':
        if any(type(result.get(key)) is not bool for key in ('google','email_delivery')):
            raise ValueError('Invalid Customer capabilities')
        return {key: result[key] for key in ('google','email_delivery')}
    if path == '/session':
        user, workspace, workspaces = result.get('user'), result.get('workspace'), result.get('workspaces')
        if ('user' not in result or 'workspace' not in result or not isinstance(workspaces,list) or len(workspaces)>1000
                or any(not isinstance(row,dict) or not isinstance(row.get('id'),str)
                    or not re.fullmatch(r'[a-f0-9]{32}',row['id']) for row in workspaces)
                or workspace is not None and (not isinstance(workspace,dict) or not isinstance(workspace.get('id'),str)
                    or not re.fullmatch(r'[a-f0-9]{32}',workspace['id']))
                or user is not None and (not isinstance(user,dict)
                    or any(not isinstance(user.get(key),str) or not user[key] or len(user[key])>254 for key in ('id','name','email'))
                    or type(user.get('email_verified')) not in (bool,int) or user['email_verified'] not in (0,1))):
            raise ValueError('Invalid Customer session')
        if user is not None:
            result['user'] = {key:user[key] for key in ('id','name','email','email_verified')}
    return result


def decode_payload(raw):
    def constant(_value):
        raise ValueError('Non-finite Admin JSON')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate Admin JSON field')
            result[key] = value
        return result
    value = json.loads(raw, parse_constant=constant, object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError('Admin JSON must be an object')
    return value


async def read_payload(response):
    media = response.headers.get('content-type', '').split(';', 1)[0].strip().lower()
    length = response.headers.get('content-length')
    if (media not in ('application/json', 'application/problem+json')
            or response.headers.get('content-encoding', 'identity').lower() != 'identity'
            or length is not None and (not length.isascii() or not length.isdigit() or int(length) > MAX_RESPONSE_BYTES)):
        raise ValueError('Invalid Admin response envelope')
    raw = bytearray()
    async for chunk in response.aiter_bytes(chunk_size=65536):
        if len(raw) + len(chunk) > MAX_RESPONSE_BYTES:
            raise ValueError('Admin response too large')
        raw.extend(chunk)
    return decode_payload(raw)


def public_error(status, payload):
    """Keep known public 4xx validation messages; never expose upstream 5xx bodies."""
    code = payload.get('code')
    code = code if isinstance(code, str) and code in ERROR_CODES else 'customer_error'
    if code == 'service_auth':
        return 503, 'Chưa cấu hình kết nối dịch vụ tài khoản.', 'service_unavailable'
    fallback = {401: 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
                403: 'Bạn chưa có quyền thực hiện thao tác này.', 404: 'Không tìm thấy dữ liệu trong phạm vi truy cập.',
                409: 'Dữ liệu đã thay đổi. Hãy tải lại trạng thái trước khi tiếp tục.',
                429: 'Đã có quá nhiều yêu cầu. Vui lòng thử lại sau.'}.get(status, 'Không thể hoàn tất yêu cầu. Vui lòng kiểm tra thông tin và thử lại.')
    if status >= 500:
        return 503, SERVER_MESSAGES.get(code, 'Chưa kết nối được dịch vụ tài khoản. Vui lòng thử lại.'), code
    message = payload.get('error')
    if (not isinstance(message, str) or not message.strip() or len(message) > 500
            or code == 'customer_error' or any(ord(c) < 32 for c in message)
            or re.search(r'(?:https?://|postgres(?:ql)?://|Bearer\s|(?:access[_-]?token|refresh[_-]?token|client[_-]?secret|password|credential)\s*[:=])', message, re.I)):
        message = fallback
    return status, message, code
