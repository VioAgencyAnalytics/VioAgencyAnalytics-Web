from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlsplit

import httpx


class AdminBundleRepositoryError(RuntimeError):
    """Base error for Admin Report Bundle access."""


class AdminBundleConfigError(AdminBundleRepositoryError):
    """Local configuration is missing or invalid."""


class AdminBundleAuthError(AdminBundleRepositoryError):
    """Admin rejected the service token."""


class AdminBundleNotFoundError(AdminBundleRepositoryError):
    """Requested published report/revision does not exist."""


class AdminBundleSnapshotError(AdminBundleRepositoryError):
    """Published bundle exists but does not have a usable snapshot."""


class AdminBundleUnavailableError(AdminBundleRepositoryError):
    """Admin API could not be reached."""


class AdminBundleTimeoutError(AdminBundleUnavailableError):
    """Admin did not respond before the configured deadline."""


class AdminBundleUpstreamError(AdminBundleRepositoryError):
    """Admin returned an unexpected HTTP error."""


class AdminBundleContractError(AdminBundleRepositoryError):
    """Admin returned JSON that does not match Report Bundle schema v1."""


class AdminBundleRepository:
    SCHEMA_VERSION = "1.0"
    PUBLISHED_STATUSES = {"provisional", "final"}

    def __init__(
        self,
        base_url: str,
        service_token: str,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.strip().rstrip("/")
        self.service_token = service_token.strip()
        self.timeout_seconds = timeout_seconds
        self.client = client

        self._validate_config()

    def _validate_config(self) -> None:
        if not self.base_url:
            raise AdminBundleConfigError(
                "REPORT_ADMIN_BASE_URL chưa được cấu hình."
            )

        try:
            parsed = urlsplit(self.base_url)
            parsed.port  # Validate malformed/out-of-range ports without exposing the URL.
        except ValueError:
            raise AdminBundleConfigError("REPORT_ADMIN_BASE_URL không hợp lệ.") from None

        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or any(ord(char) < 33 for char in self.base_url)
            or "\\" in self.base_url
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise AdminBundleConfigError(
                "REPORT_ADMIN_BASE_URL không hợp lệ."
            )

        if not self.service_token:
            raise AdminBundleConfigError(
                "REPORT_SERVICE_TOKEN chưa được cấu hình."
            )

        if self.timeout_seconds <= 0:
            raise AdminBundleConfigError(
                "REPORT_REQUEST_TIMEOUT_SECONDS phải lớn hơn 0."
            )

    def get_bundle(
        self,
        report_id: str,
        revision: int | None = None,
    ) -> dict[str, Any]:
        report_id = report_id.strip()

        if not report_id:
            raise ValueError("report_id không được để trống.")

        if revision is not None and (
            type(revision) is not int
            or revision <= 0
        ):
            raise ValueError(
                "revision phải là số nguyên dương."
            )

        encoded_report_id = quote(
            report_id,
            safe="",
        )

        url = (
            f"{self.base_url}"
            f"/api/internal/v1/report-bundles/"
            f"{encoded_report_id}"
        )

        params = (
            {"revision": str(revision)}
            if revision is not None
            else None
        )

        headers = {
            "Authorization": (
                f"Bearer {self.service_token}"
            ),
            "Accept": "application/json",
        }

        try:
            response = self._request(
                url=url,
                params=params,
                headers=headers,
            )
        except httpx.TimeoutException:
            raise AdminBundleTimeoutError(
                "Hết thời gian chờ VioAgencyAnalytics Admin."
            ) from None
        except httpx.RequestError:
            raise AdminBundleUnavailableError(
                "Không thể kết nối VioAgencyAnalytics Admin."
            ) from None

        if response.status_code == 401:
            raise AdminBundleAuthError(
                "VioAgencyAnalytics Admin từ chối REPORT_SERVICE_TOKEN."
            )

        if response.status_code == 404:
            raise AdminBundleNotFoundError(
                "Không tìm thấy report/revision đã được xuất bản."
            )

        if response.status_code == 409:
            raise AdminBundleSnapshotError(
                "Report Bundle chưa có immutable snapshot hợp lệ."
            )

        if response.status_code != 200:
            raise AdminBundleUpstreamError(
                "VioAgencyAnalytics Admin trả về lỗi "
                f"HTTP {response.status_code}."
            )

        try:
            payload = response.json()
        except ValueError:
            raise AdminBundleContractError(
                "VioAgencyAnalytics Admin không trả về JSON hợp lệ."
            ) from None

        self._validate_contract(
            payload,
            expected_report_id=report_id,
        )

        if revision is not None and payload['report']['revision'] != revision:
            raise AdminBundleContractError("report.revision không khớp revision được yêu cầu.")

        return payload

    def _request(
        self,
        *,
        url: str,
        params: dict[str, str] | None,
        headers: dict[str, str],
    ) -> httpx.Response:
        if self.client is not None:
            return self.client.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
                follow_redirects=False,
            )

        with httpx.Client(
            timeout=self.timeout_seconds
        ) as client:
            return client.get(
                url,
                params=params,
                headers=headers,
                follow_redirects=False,
            )

    def _validate_contract(
        self,
        payload: Any,
        *,
        expected_report_id: str,
    ) -> None:
        if not isinstance(payload, dict):
            raise AdminBundleContractError(
                "Report Bundle phải là JSON object."
            )

        if payload.get("schema_version") != self.SCHEMA_VERSION:
            raise AdminBundleContractError(
                "Report Bundle schema_version không được hỗ trợ."
            )

        required = {
            "report",
            "client",
            "period",
            "comparison",
            "freshness",
            "quality",
            "navigation",
            "branding",
            "sections",
        }

        missing = required - payload.keys()

        if missing:
            raise AdminBundleContractError(
                "Report Bundle thiếu trường bắt buộc: "
                + ", ".join(sorted(missing))
            )

        report = payload.get("report")

        if not isinstance(report, dict):
            raise AdminBundleContractError(
                "report phải là JSON object."
            )

        if report.get("id") != expected_report_id:
            raise AdminBundleContractError(
                "report.id không khớp report được yêu cầu."
            )

        revision = report.get("revision")

        if (
            type(revision) is not int
            or revision <= 0
        ):
            raise AdminBundleContractError(
                "report.revision không hợp lệ."
            )

        if not isinstance(report.get("status"), str) or report["status"] not in self.PUBLISHED_STATUSES:
            raise AdminBundleContractError(
                "Report-New chỉ được đọc "
                "provisional hoặc final bundle."
            )

        if not isinstance(payload.get("sections"), dict):
            raise AdminBundleContractError(
                "sections phải là JSON object."
            )
