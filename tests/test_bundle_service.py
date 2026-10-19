import logging

import httpx
import pytest

from app.repositories.admin_bundle import AdminBundleRepository, AdminBundleConfigError
from app.services.bundle import BundleService, BundleServiceError
from bundle_fixtures import REPORT_ID, SERVICE_TOKEN, published_bundle


def test_service_uses_existing_repository_and_revision():
    def handler(request):
        assert request.url.params['revision'] == '2'
        assert request.headers['Authorization'] == 'Bearer ' + SERVICE_TOKEN
        return httpx.Response(200, json=published_bundle())
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        view = BundleService(AdminBundleRepository('https://admin.invalid', SERVICE_TOKEN, client=client)).get_report(REPORT_ID,2)
        assert view.revision == 2 and view.report_id == REPORT_ID


@pytest.mark.parametrize('status,code', [(401,'admin_unauthorized'),(404,'not_found'),(409,'snapshot_required'),(500,'upstream'),(302,'upstream')])
def test_http_errors_distinct_and_body_not_exposed(status,code):
    with httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(status,json={'error':SERVICE_TOKEN}))) as client:
        with pytest.raises(BundleServiceError) as error:
            BundleService(AdminBundleRepository('https://admin.invalid', SERVICE_TOKEN, client=client)).get_report(REPORT_ID)
        assert error.value.code == code
        assert SERVICE_TOKEN not in str(error.value)


@pytest.mark.parametrize('error_type,code', [(httpx.ReadTimeout,'timeout'),(httpx.ConnectError,'unavailable')])
def test_network_error_distinction_and_safe_logs(error_type,code,caplog):
    caplog.set_level(logging.DEBUG)
    def handler(request): raise error_type(SERVICE_TOKEN, request=request)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(BundleServiceError) as error:
            BundleService(AdminBundleRepository('https://admin.invalid', SERVICE_TOKEN, client=client)).get_report(REPORT_ID)
        assert error.value.code == code and error.value.__cause__ is None
        assert SERVICE_TOKEN not in caplog.text


@pytest.mark.parametrize('contamination', [{'access_token':'fixture-sensitive'}, {'name':SERVICE_TOKEN}, {'url':'https://example.test/?access_token=fixture-sensitive'}])
def test_rejects_credential_contamination(contamination):
    data = published_bundle(); data['branding'] = contamination
    with httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,json=data))) as client:
        with pytest.raises(BundleServiceError) as error:
            BundleService(AdminBundleRepository('https://admin.invalid',SERVICE_TOKEN,client=client)).get_report(REPORT_ID)
        assert error.value.code == 'contract' and SERVICE_TOKEN not in str(error.value)


def test_repository_rejects_mismatched_revision_and_redirects_without_forwarding_token():
    requests=[]
    def handler(req):
        requests.append(req)
        return httpx.Response(302,headers={'Location':'https://other.invalid/'})
    with httpx.Client(transport=httpx.MockTransport(handler),follow_redirects=True) as client:
        with pytest.raises(BundleServiceError):
            BundleService(AdminBundleRepository('https://admin.invalid',SERVICE_TOKEN,client=client)).get_report(REPORT_ID)
    assert len(requests) == 1
    with httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,json=published_bundle()))) as client:
        with pytest.raises(BundleServiceError) as error:
            BundleService(AdminBundleRepository('https://admin.invalid',SERVICE_TOKEN,client=client)).get_report(REPORT_ID,3)
        assert error.value.code == 'contract'


def test_missing_configuration():
    with pytest.raises(AdminBundleConfigError): AdminBundleRepository('', '')


@pytest.mark.parametrize('url', ['https://[broken', 'https://example.test:bad', 'https://user:password@example.test', 'https://example.test/?token=fixture'])
def test_invalid_configuration_has_safe_typed_error(url):
    with pytest.raises(AdminBundleConfigError) as error:
        AdminBundleRepository(url, SERVICE_TOKEN)
    assert url not in str(error.value)
