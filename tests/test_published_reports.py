import httpx
import logging
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.repositories.admin_bundle import AdminBundleRepository
from app.routes.published import get_bundle_service, require_preview_access
from app.services.bundle import BundleService
from fastapi import Depends
from main import app
from bundle_fixtures import REPORT_ID, SERVICE_TOKEN, PREVIEW_USER, PREVIEW_PASSWORD, published_bundle


@pytest.fixture
def environment():
    settings = Settings(_env_file=None, debug=False, app_env='test', report_preview_enabled=True,
                        report_preview_username=PREVIEW_USER, report_preview_password=PREVIEW_PASSWORD,
                        report_preview_allowed_ids=[REPORT_ID], report_service_token=SERVICE_TOKEN)
    app.dependency_overrides[get_settings] = lambda:settings
    data = published_bundle()
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json=data)
    with httpx.Client(transport=httpx.MockTransport(handler)) as upstream:
        def factory(authorized=Depends(require_preview_access)):
            return BundleService(AdminBundleRepository('https://admin.invalid',SERVICE_TOKEN,client=upstream))
        app.dependency_overrides[get_bundle_service] = factory
        with TestClient(app) as client:
            yield client, settings, data, calls
    app.dependency_overrides.clear()


def test_protected_render_with_pinned_revision_and_no_secret(environment,caplog):
    caplog.set_level(logging.DEBUG)
    client,settings,data,calls = environment
    response=client.get(f'/published/{REPORT_ID}?revision=2',auth=(PREVIEW_USER,PREVIEW_PASSWORD))
    assert response.status_code == 200
    assert SERVICE_TOKEN not in response.text and PREVIEW_PASSWORD not in response.text
    assert SERVICE_TOKEN not in caplog.text and PREVIEW_PASSWORD not in caplog.text
    assert '987654321' not in response.text and 'not-published' not in response.text
    assert 'Cảnh báo chất lượng fixture' in response.text and 'DEMO' in response.text
    assert 'Chưa có dữ liệu' in response.text and 'dashboard-sidebar' in response.text
    assert 'data-selected="seo"' in response.text and 'revision=2' in response.text
    assert 'no-store' in response.headers['cache-control']
    assert response.headers['x-frame-options'] == 'DENY'
    assert calls[0].url.params['revision'] == '2'


@pytest.mark.parametrize('mode', ['disabled','production','anonymous','wrong_password','outside_allowlist','reuse_token', 'missing_user', 'short_password', 'empty_allowlist'])
def test_viewer_access_denied_before_upstream(environment,mode):
    client,settings,data,calls = environment
    auth=(PREVIEW_USER,PREVIEW_PASSWORD); path=f'/published/{REPORT_ID}'
    if mode == 'disabled': settings.report_preview_enabled=False
    if mode == 'production': settings.app_env='production'
    if mode == 'anonymous': auth=None
    if mode == 'wrong_password': auth=(PREVIEW_USER,'incorrect')
    if mode == 'outside_allowlist': path='/published/other'
    if mode == 'reuse_token': settings.report_preview_password=settings.report_service_token
    if mode == 'missing_user': settings.report_preview_username=''
    if mode == 'short_password': settings.report_preview_password=type(settings.report_preview_password)('too-short')
    if mode == 'empty_allowlist': settings.report_preview_allowed_ids=[]
    response=client.get(path,auth=auth)
    assert response.status_code in (401,404,503)
    assert not calls and SERVICE_TOKEN not in response.text


def test_invalid_revision_and_contract_errors_are_safe(environment):
    client,settings,data,calls = environment
    assert client.get(f'/published/{REPORT_ID}?revision=0',auth=(PREVIEW_USER,PREVIEW_PASSWORD)).status_code == 422
    assert not calls
    data['report']['status']='draft'
    response=client.get(f'/published/{REPORT_ID}',auth=(PREVIEW_USER,PREVIEW_PASSWORD))
    assert response.status_code == 502 and 'contract' in response.text
    assert '18.500.000' not in response.text


def test_html_escapes_source_strings_and_never_uses_demo_navigation(environment):
    client,settings,data,calls=environment
    data['report']['name']='<script>alert(1)</script>'
    response=client.get(f'/published/{REPORT_ID}',auth=(PREVIEW_USER,PREVIEW_PASSWORD))
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in response.text
    assert '<script>alert(1)</script>' not in response.text
    assert '/report/tiktok' not in response.text and 'account-manager' not in response.text


@pytest.mark.parametrize('path', ['/overview','/report/seo','/report/facebook-ads','/report/facebook-content','/report/tiktok','/report/youtube'])
def test_old_demo_pages_still_work_without_viewer_auth(environment,path):
    client,settings,data,calls=environment
    assert client.get(path).status_code == 200
    assert not calls


@pytest.mark.parametrize('upstream_status,expected,code', [(401,502,'admin_unauthorized'), (404,404,'not_found'), (409,409,'snapshot_required'), (500,502,'upstream'), ('timeout',504,'timeout')])
def test_upstream_errors_render_safe_error_page(environment,upstream_status,expected,code):
    client,settings,data,calls=environment
    def handler(request):
        if upstream_status == 'timeout':
            raise httpx.ReadTimeout(SERVICE_TOKEN,request=request)
        return httpx.Response(upstream_status,text=SERVICE_TOKEN)
    with httpx.Client(transport=httpx.MockTransport(handler)) as upstream:
        def factory(authorized=Depends(require_preview_access)):
            return BundleService(AdminBundleRepository('https://admin.invalid',SERVICE_TOKEN,client=upstream))
        app.dependency_overrides[get_bundle_service]=factory
        response=client.get(f'/published/{REPORT_ID}',auth=(PREVIEW_USER,PREVIEW_PASSWORD))
    assert response.status_code == expected and code in response.text
    assert 'Chưa thể mở báo cáo' in response.text and 'no-store' in response.headers['cache-control']
    assert SERVICE_TOKEN not in response.text and 'data-bundle-chart' not in response.text


def test_factory_configuration_error_is_safe_without_an_upstream_call(environment):
    client,settings,data,calls=environment
    settings.report_admin_base_url='https://[broken'
    del app.dependency_overrides[get_bundle_service]
    response=client.get(f'/published/{REPORT_ID}',auth=(PREVIEW_USER,PREVIEW_PASSWORD))
    assert response.status_code == 503 and not calls
    assert '[broken' not in response.text and SERVICE_TOKEN not in response.text


def test_contaminated_payload_does_not_leak_into_html_or_logs(environment,caplog):
    client,settings,data,calls=environment
    data['quality']['warnings'].append(SERVICE_TOKEN)
    response=client.get(f'/published/{REPORT_ID}',auth=(PREVIEW_USER,PREVIEW_PASSWORD))
    assert response.status_code == 502
    assert SERVICE_TOKEN not in response.text and SERVICE_TOKEN not in caplog.text
    for path in ['/static/js/shared/charts.js', '/static/js/pages/published.js']:
        assert SERVICE_TOKEN not in client.get(path).text
