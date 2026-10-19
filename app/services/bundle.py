"""Read published snapshots through the existing Admin repository only."""
from app.bundle_safety import check_safe_payload
from app.mappers.bundle import BundleViewMapper
from app.repositories.admin_bundle import (
    AdminBundleRepository, AdminBundleConfigError, AdminBundleAuthError,
    AdminBundleNotFoundError, AdminBundleSnapshotError, AdminBundleTimeoutError,
    AdminBundleUnavailableError, AdminBundleUpstreamError, AdminBundleContractError,
)
from app.schemas.bundle_view import BundleView


class BundleServiceError(RuntimeError):
    def __init__(self, code: str, status_code: int, message: str) -> None:
        super().__init__(message)
        self.code, self.status_code = code, status_code


ERRORS = (
    (AdminBundleConfigError, 'configuration', 503, 'Chưa cấu hình kết nối báo cáo với Admin.'),
    (AdminBundleAuthError, 'admin_unauthorized', 502, 'Admin trả 401: thông tin xác thực giữa hai backend chưa hợp lệ.'),
    (AdminBundleNotFoundError, 'not_found', 404, 'Không tìm thấy báo cáo hoặc revision đã xuất bản.'),
    (AdminBundleSnapshotError, 'snapshot_required', 409, 'Admin trả 409: báo cáo chưa có snapshot hợp lệ.'),
    (AdminBundleTimeoutError, 'timeout', 504, 'Hết thời gian chờ Admin. Vui lòng thử lại sau.'),
    (AdminBundleUnavailableError, 'unavailable', 503, 'Hiện chưa kết nối được Admin.'),
    (AdminBundleUpstreamError, 'upstream', 502, 'Admin trả lỗi khi đọc báo cáo.'),
    (AdminBundleContractError, 'contract', 502, 'Report Bundle không đúng contract được hỗ trợ hoặc không an toàn để hiển thị.'),
)


class BundleService:
    def __init__(self, repository: AdminBundleRepository, mapper: BundleViewMapper | None = None) -> None:
        self.repository = repository
        self.mapper = mapper or BundleViewMapper()

    def get_report(self, report_id: str, revision: int | None = None) -> BundleView:
        try:
            payload = self.repository.get_bundle(report_id, revision)
            check_safe_payload(payload, (self.repository.service_token,))
            return self.mapper.map(payload, report_id, revision)
        except tuple(item[0] for item in ERRORS) as exc:
            for error, code, status, message in ERRORS:
                if isinstance(exc, error):
                    raise BundleServiceError(code, status, message) from None
            raise AssertionError('Unmapped bundle error') from None
        except (TypeError, KeyError, ValueError, RecursionError, AttributeError):
            raise BundleServiceError('contract', 502, 'Cấu trúc dữ liệu snapshot không hợp lệ; nội dung thô được ẩn.') from None
