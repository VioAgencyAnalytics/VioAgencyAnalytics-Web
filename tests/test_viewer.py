"""Customer routes use separate end-user sessions AND the backend credential."""
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

import main
from app.config import Settings, get_settings
from app.repositories.viewer import AdminViewerRepository
from app.routes import viewer
from tests.bundle_fixtures import SERVICE_TOKEN, published_bundle

REPORT_ID = 'rpt_' + 'a' * 32
SESSION = 'isolated-viewer-session'


@pytest.fixture
def env(monkeypatch):
    settings = Settings(_env_file=None, app_env='test', debug=False,
                        report_admin_base_url='https://admin.invalid', report_service_token=SERVICE_TOKEN)
    bundle = published_bundle()
    bundle['report']['id'] = REPORT_ID
    calls, replies = [], {}

    def handler(request):
        calls.append(request)
        assert request.headers['Authorization'] == 'Bearer ' + SERVICE_TOKEN
        path = request.url.path
        if path in replies:
            return replies[path]
        if path == '/api/auth/login':
            return httpx.Response(200, json={}, headers={'Set-Cookie': 'kdh_session=' + SESSION + '; HttpOnly; Path=/'})
        if request.headers.get('X-KDH-Viewer-Session') != SESSION:
            return httpx.Response(401)
        if path == '/api/internal/v1/viewer-session':
            return httpx.Response(200, json={'logged_out': True})
        if path.endswith('/report-bundles'):
            return httpx.Response(200, json={'reports': [{'report_id': REPORT_ID, 'revision': 2, 'status': 'provisional', 'name': 'Fixture'}]})
        return httpx.Response(200, json=bundle)

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(viewer, 'repository', lambda request, config: AdminViewerRepository(
        settings.report_admin_base_url, SERVICE_TOKEN, client=upstream, viewer_session=request.cookies.get(viewer.SESSION, '')))
    monkeypatch.setattr(main, 'get_runtime_mode', lambda: SimpleNamespace(app_env='test'))
    main.app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(main.app, base_url='https://new.invalid') as client:
        yield client, calls, replies, bundle
    main.app.dependency_overrides.clear()
    upstream.close()


def sign_in(client, next_url='/reports'):
    page = client.get('/login')
    assert 'HttpOnly' in page.headers['set-cookie'] and 'Secure' in page.headers['set-cookie']
    assert page.headers['referrer-policy'] == 'same-origin'
    csrf = client.cookies.get(viewer.CSRF)
    result = client.post('/login', data={'csrf': csrf, 'email': 'viewer@example.test', 'password': 'test-only-password', 'next': next_url},
                         headers={'Origin': 'https://new.invalid'}, follow_redirects=False)
    assert result.status_code == 303
    return result


def test_login_reports_and_revision_use_server_identity_without_leaking_it(env):
    client, calls, _, _ = env
    assert client.get('/reports', follow_redirects=False).status_code == 303
    result = sign_in(client, '/reports/' + REPORT_ID + '?revision=2')
    assert result.headers['location'].endswith('?revision=2')
    assert client.get('/reports').status_code == 200
    page = client.get('/reports/' + REPORT_ID + '?revision=2')
    assert page.status_code == 200 and 'DEMO' in page.text
    assert SERVICE_TOKEN not in page.text and SESSION not in page.text
    assert calls[-1].url.path == '/api/internal/v1/viewer/report-bundles/' + REPORT_ID
    assert calls[-1].url.params['revision'] == '2'
    assert 'no-store' in page.headers['cache-control']


@pytest.mark.parametrize('mode', ['no_csrf', 'wrong_csrf', 'foreign_origin', 'null_origin', 'duplicate', 'invalid_utf8'])
def test_login_csrf_and_form_validation(env, mode):
    client, calls, _, _ = env
    client.get('/login')
    data = {'email': 'test@example.test', 'password': 'test-only', 'csrf': client.cookies.get(viewer.CSRF)}
    headers = {}
    if mode == 'no_csrf': data.pop('csrf')
    if mode == 'wrong_csrf': data['csrf'] = 'incorrect'
    if mode == 'foreign_origin': headers['Origin'] = 'https://foreign.invalid'
    if mode == 'null_origin': headers['Origin'] = 'null'
    if mode in ('duplicate', 'invalid_utf8'):
        content = b'csrf=a&csrf=b' if mode == 'duplicate' else b'csrf=\xff'
        response = client.post('/login', content=content, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    else:
        response = client.post('/login', data=data, headers=headers)
    assert response.status_code in (400, 403) and not calls


def test_open_redirect_and_logout_session_revocation(env):
    client, calls, _, _ = env
    assert sign_in(client, '//evil.invalid').headers['location'] == '/reports'
    denied = client.post('/logout', data={'csrf': 'wrong'})
    assert denied.status_code == 403
    response = client.post('/logout', data={'csrf': client.cookies.get(viewer.CSRF)}, follow_redirects=False)
    assert response.status_code == 303 and calls[-1].method == 'DELETE'
    assert not client.cookies.get(viewer.SESSION)


@pytest.mark.parametrize('status', [401, 403, 404, 500])
def test_expired_denied_or_upstream_error_is_safe(env, status):
    client, _, replies, _ = env
    sign_in(client)
    replies['/api/internal/v1/viewer/report-bundles/' + REPORT_ID] = httpx.Response(status, text=SERVICE_TOKEN)
    response = client.get('/reports/' + REPORT_ID, follow_redirects=False)
    assert response.status_code == {401: 303, 403: 403, 404: 404, 500: 502}[status]
    assert SERVICE_TOKEN not in response.text


@pytest.mark.parametrize('payload', [[], {'reports': [{'report_id': '../draft', 'revision': 1, 'status': 'final'}]}, {'access_token': 'test-only'}])
def test_invalid_or_sensitive_list_fails_closed(env, payload):
    client, _, replies, _ = env
    sign_in(client)
    replies['/api/internal/v1/viewer/report-bundles'] = httpx.Response(200, json=payload)
    assert client.get('/reports').status_code == 502


def test_internal_preview_stays_admin_only(env):
    client, _, replies, _ = env
    sign_in(client)
    path = '/api/internal/v1/marketing-preview/' + 'b' * 32
    replies[path] = httpx.Response(403)
    assert client.get('/internal-preview/' + 'b' * 32).status_code == 403
    replies[path] = httpx.Response(200, json={'kind': 'marketing_internal_preview', 'publishable': False, 'issues': ['provider_origin_unconfirmed'],
        'candidate': {'marketing': {'preview': {'period': {'start': '2026-09-01', 'end': '2026-09-03'}, 'comparison': {}, 'widgets': [], 'opportunity_candidates': []}}}})
    page = client.get('/internal-preview/' + 'b' * 32)
    assert page.status_code == 200 and 'CHƯA XUẤT BẢN' in page.text
    assert SERVICE_TOKEN not in page.text


@pytest.mark.parametrize('path', ['/overview', '/report/seo', '/api/reports', '/demo-bundles/' + REPORT_ID])
def test_production_disables_legacy_mock_and_demo_routes(env, monkeypatch, path):
    client, calls, _, _ = env
    monkeypatch.setattr(main, 'get_runtime_mode', lambda: SimpleNamespace(app_env='production'))
    assert client.get(path).status_code == 404
    assert client.get('/', follow_redirects=False).headers['location'] == '/login'
    assert client.get('/api/v1/health').status_code == 200 and not calls


def test_bad_report_scope_cannot_call_upstream(env):
    client, calls, _, _ = env
    for suffix in ('?revision=0', '?revision=1&revision=2', '?client_id=other'):
        assert client.get('/reports/' + REPORT_ID + suffix).status_code == 400
    assert not calls
