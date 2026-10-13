import httpx
import pytest

from app.repositories.admin_bundle import (
    AdminBundleAuthError,
    AdminBundleContractError,
    AdminBundleNotFoundError,
    AdminBundleRepository,
    AdminBundleSnapshotError,
    AdminBundleUnavailableError,
    AdminBundleUpstreamError,
)


BASE_URL = "http://localhost:8090"
SERVICE_TOKEN = "test-service-token"


def valid_payload(
    *,
    report_id: str = "report-001",
    revision: int = 2,
    status: str = "final",
) -> dict:
    return {
        "schema_version": "1.0",
        "report": {
            "id": report_id,
            "revision": revision,
            "status": status,
            "name": "KinderHealth Marketing Report",
        },
        "client": {
            "id": "client_kinderhealth",
            "name": "KinderHealth",
        },
        "period": {
            "start": "2026-09-01",
            "end": "2026-09-30",
        },
        "comparison": None,
        "freshness": {
            "generated_at": "2026-10-07T00:00:00+00:00",
            "published_at": "2026-10-07T00:01:00+00:00",
        },
        "quality": {
            "status": "complete",
            "warnings": [],
        },
        "navigation": {
            "default_section": "overview",
            "sections": ["overview"],
        },
        "branding": {},
        "sections": {
            "overview": {
                "valid": True,
                "quality": {
                    "status": "complete",
                    "warnings": [],
                },
                "data": {},
            }
        },
    }


def make_repository(handler):
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    repository = AdminBundleRepository(
        base_url=BASE_URL,
        service_token=SERVICE_TOKEN,
        timeout_seconds=5,
        client=client,
    )

    return repository, client


def test_get_bundle_sends_bearer_token_and_reads_valid_bundle():
    payload = valid_payload()

    def handler(request: httpx.Request):
        assert request.method == "GET"
        assert (
            request.url.path
            == "/api/internal/v1/report-bundles/report-001"
        )
        assert request.headers["Authorization"] == (
            "Bearer test-service-token"
        )
        assert request.headers["Accept"] == "application/json"

        return httpx.Response(
            200,
            json=payload,
        )

    repository, client = make_repository(handler)

    try:
        result = repository.get_bundle("report-001")
    finally:
        client.close()

    assert result == payload


def test_get_bundle_supports_revision_query():
    payload = valid_payload(revision=3)

    def handler(request: httpx.Request):
        assert request.url.path == (
            "/api/internal/v1/report-bundles/report-001"
        )
        assert request.url.params["revision"] == "3"

        return httpx.Response(
            200,
            json=payload,
        )

    repository, client = make_repository(handler)

    try:
        result = repository.get_bundle(
            "report-001",
            revision=3,
        )
    finally:
        client.close()

    assert result["report"]["revision"] == 3


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (401, AdminBundleAuthError),
        (404, AdminBundleNotFoundError),
        (409, AdminBundleSnapshotError),
        (500, AdminBundleUpstreamError),
    ],
)
def test_admin_http_errors_are_mapped(
    status_code,
    expected_error,
):
    def handler(request: httpx.Request):
        return httpx.Response(
            status_code,
            json={"error": "test"},
        )

    repository, client = make_repository(handler)

    try:
        with pytest.raises(expected_error):
            repository.get_bundle("report-001")
    finally:
        client.close()


def test_network_error_becomes_unavailable_error():
    def handler(request: httpx.Request):
        raise httpx.ConnectError(
            "Admin offline",
            request=request,
        )

    repository, client = make_repository(handler)

    try:
        with pytest.raises(
            AdminBundleUnavailableError
        ):
            repository.get_bundle("report-001")
    finally:
        client.close()


def test_rejects_unsupported_schema_version():
    payload = valid_payload()
    payload["schema_version"] = "2.0"

    def handler(request: httpx.Request):
        return httpx.Response(
            200,
            json=payload,
        )

    repository, client = make_repository(handler)

    try:
        with pytest.raises(
            AdminBundleContractError
        ):
            repository.get_bundle("report-001")
    finally:
        client.close()


def test_rejects_draft_bundle():
    payload = valid_payload(
        status="draft",
    )

    def handler(request: httpx.Request):
        return httpx.Response(
            200,
            json=payload,
        )

    repository, client = make_repository(handler)

    try:
        with pytest.raises(
            AdminBundleContractError
        ):
            repository.get_bundle("report-001")
    finally:
        client.close()


def test_rejects_wrong_report_id():
    payload = valid_payload(
        report_id="another-report",
    )

    def handler(request: httpx.Request):
        return httpx.Response(
            200,
            json=payload,
        )

    repository, client = make_repository(handler)

    try:
        with pytest.raises(
            AdminBundleContractError
        ):
            repository.get_bundle("report-001")
    finally:
        client.close()
