"""Backend-only session delegation to Admin, which owns users and report ACLs."""
import httpx

from app.repositories.admin_bundle import AdminBundleRepository
from app.bundle_safety import check_safe_payload


class ViewerError(RuntimeError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class AdminViewerRepository(AdminBundleRepository):
    def __init__(self, *args, viewer_session='', **kwargs):
        super().__init__(*args, **kwargs)
        self.viewer_session = viewer_session

    def call(self, method, path, data=None):
        headers = {'Authorization': 'Bearer ' + self.service_token, 'Accept': 'application/json',
                   'X-KDH-Request': '1', 'X-KDH-Viewer-Session': self.viewer_session}
        try:
            if self.client is not None:
                response = self.client.request(method, self.base_url + path, json=data, headers=headers,
                                               timeout=self.timeout_seconds, follow_redirects=False)
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.request(method, self.base_url + path, json=data, headers=headers, follow_redirects=False)
        except httpx.RequestError:
            raise ViewerError(503, 'Chưa kết nối được hệ thống báo cáo. Vui lòng thử lại.') from None
        if response.status_code != 200:
            messages = {400: 'Giao dịch đã hết hạn, đã dùng hoặc không hợp lệ. Mở lại báo cáo từ Admin.',
                        409: 'New đang đăng nhập bằng tài khoản khác hoặc snapshot chưa hợp lệ. Đăng xuất New rồi mở lại báo cáo từ Admin.',
                        401: 'Email, mật khẩu hoặc phiên đăng nhập chưa hợp lệ.',
                        403: 'Tài khoản không có quyền mở nội dung này.',
                        404: 'Không tìm thấy báo cáo trong phạm vi được cấp.',
                        429: 'Thử đăng nhập quá nhiều lần. Vui lòng chờ rồi thử lại.'}
            raise ViewerError(response.status_code if response.status_code in messages else 502,
                              messages.get(response.status_code, 'Hệ thống chưa trả được báo cáo hợp lệ.'))
        return response

    def login(self, email, password):
        response = self.call('POST', '/api/auth/login', {'email': email, 'password': password})
        session = response.cookies.get('kdh_session')
        if not session:
            raise ViewerError(502, 'Hệ thống chưa cấp phiên đăng nhập.')
        return session

    def get_bundle(self, report_id, revision=None):
        payload = super().get_bundle(report_id, revision)
        check_safe_payload(payload, (self.viewer_session, self.service_token))
        return payload

    def _request(self, *, url, params, headers):
        prefix = self.base_url + '/api/internal/v1/report-bundles/'
        if not url.startswith(prefix):
            raise ViewerError(502, 'Đường dẫn báo cáo không hợp lệ.')
        target = self.base_url + '/api/internal/v1/viewer/report-bundles/' + url[len(prefix):]
        response = super()._request(url=target, params=params,
            headers={**headers, 'X-KDH-Viewer-Session': self.viewer_session})
        if response.status_code in (401, 403):
            raise ViewerError(response.status_code, 'Phiên đã hết hạn hoặc không có quyền xem báo cáo.')
        return response
