"""New renders Admin-authorized reports without a separate login surface."""
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
                        report_admin_base_url='https://internal.invalid', report_service_token=SERVICE_TOKEN,
                        report_admin_public_url='https://admin.invalid', report_new_public_url='https://new.invalid')
    bundle = published_bundle()
    bundle['report']['id'] = REPORT_ID
    calls, replies = [], {}

    def handler(request):
        calls.append(request)
        assert request.headers['Authorization'] == 'Bearer ' + SERVICE_TOKEN
        path = request.url.path
        if path in replies:
            return replies[path]
        assert path != '/api/auth/login', 'New must never forward a password to Admin'
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


def use_viewer_session(client):
    # Unit fixture only; actual session issuance is exercised by handoff/browser tests.
    client.cookies.set(viewer.SESSION, SESSION, domain='new.invalid', path='/')
    client.cookies.set(viewer.CSRF, 'fixture-csrf', domain='new.invalid', path='/')


@pytest.mark.parametrize('path', ['/', '/login', '/reports', '/login?next=https://evil.invalid', '/reports?next=//evil.invalid'])
def test_entry_routes_return_to_admin_without_a_login_or_list(env, path):
    client, calls, _, _ = env
    response = client.get(path, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == 'https://admin.invalid/viewer/reports'
    assert 'password' not in response.text and 'no-store' in response.headers['cache-control']
    assert not calls


def test_new_does_not_accept_login_credentials(env):
    client, calls, _, _ = env
    response = client.post('/login', data={'email': 'viewer@example.test', 'password': 'test-only-password'})
    assert response.status_code == 405 and not calls
    assert not client.cookies.get(viewer.SESSION)


def test_report_and_revision_use_server_identity_without_leaking_it(env):
    client, calls, _, _ = env
    use_viewer_session(client)
    page = client.get('/reports/' + REPORT_ID + '?revision=2')
    assert page.status_code == 200 and 'DEMO' in page.text
    assert SERVICE_TOKEN not in page.text and SESSION not in page.text
    assert calls[-1].url.path == '/api/internal/v1/viewer/report-bundles/' + REPORT_ID
    assert calls[-1].url.params['revision'] == '2'
    assert 'no-store' in page.headers['cache-control']
    assert 'Về Admin' in page.text and 'action="/login"' not in page.text


@pytest.mark.parametrize('mode', ['no_csrf', 'wrong_csrf', 'foreign_origin', 'null_origin', 'duplicate', 'invalid_utf8'])
def test_end_viewing_session_csrf_and_form_validation(env, mode):
    client, calls, _, _ = env
    use_viewer_session(client)
    data = {'csrf': client.cookies.get(viewer.CSRF)}
    headers = {}
    if mode == 'no_csrf': data.pop('csrf')
    if mode == 'wrong_csrf': data['csrf'] = 'incorrect'
    if mode == 'foreign_origin': headers['Origin'] = 'https://foreign.invalid'
    if mode == 'null_origin': headers['Origin'] = 'null'
    if mode in ('duplicate', 'invalid_utf8'):
        content = b'csrf=a&csrf=b' if mode == 'duplicate' else b'csrf=\xff'
        response = client.post('/logout', content=content, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    else:
        response = client.post('/logout', data=data, headers=headers)
    assert response.status_code in (400, 403) and not calls


def test_end_viewing_session_returns_to_admin(env):
    client, calls, _, _ = env
    use_viewer_session(client)
    denied = client.post('/logout', data={'csrf': 'wrong'})
    assert denied.status_code == 403
    response = client.post('/logout', data={'csrf': client.cookies.get(viewer.CSRF)}, follow_redirects=False)
    assert response.status_code == 303 and calls[-1].method == 'DELETE'
    assert response.headers['location'] == 'https://admin.invalid/viewer/reports'
    assert not client.cookies.get(viewer.SESSION)


@pytest.mark.parametrize('status', [401, 403, 404, 500])
def test_expired_denied_or_upstream_error_is_safe(env, status):
    client, _, replies, _ = env
    use_viewer_session(client)
    replies['/api/internal/v1/viewer/report-bundles/' + REPORT_ID] = httpx.Response(status, text=SERVICE_TOKEN)
    response = client.get('/reports/' + REPORT_ID + '?revision=2', follow_redirects=False)
    assert response.status_code == {401: 303, 403: 403, 404: 404, 500: 502}[status]
    assert SERVICE_TOKEN not in response.text
    if status == 401:
        assert response.headers['location'] == '/auth/handoff/start?mode=published&target_id=' + REPORT_ID + '&revision=2'


@pytest.mark.parametrize('payload', [[], {'candidate': 'invalid'}, {'access_token': 'test-only'}])
def test_invalid_or_sensitive_preview_fails_closed(env, payload):
    client, _, replies, _ = env
    use_viewer_session(client)
    path = '/api/internal/v1/marketing-preview/' + 'b' * 32
    replies[path] = httpx.Response(200, json=payload)
    assert client.get('/internal-preview/' + 'b' * 32).status_code == 502


def test_internal_preview_stays_admin_only(env):
    client, _, replies, _ = env
    use_viewer_session(client)
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
    assert client.get('/', follow_redirects=False).headers['location'] == 'https://admin.invalid/viewer/reports'
    assert client.get('/api/v1/health').status_code == 200 and not calls


def test_bad_report_scope_cannot_call_upstream(env):
    client, calls, _, _ = env
    for suffix in ('?revision=0', '?revision=1&revision=2', '?client_id=other'):
        assert client.get('/reports/' + REPORT_ID + suffix).status_code == 400
    assert not calls


def test_unpinned_report_requires_selection_in_admin(env):
    client, calls, _, _ = env
    response = client.get('/reports/' + REPORT_ID, follow_redirects=False)
    assert response.headers['location'] == 'https://admin.invalid/viewer/reports'
    assert not calls


def test_expired_preview_resumes_via_admin_handoff(env):
    client, _, _, _ = env
    response = client.get('/internal-preview/' + 'b' * 32, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == '/auth/handoff/start?mode=preview&target_id=' + 'b' * 32


@pytest.mark.parametrize('origin', ['https://admin.invalid/evil', 'https://admin.invalid?next=evil',
                                    'https://user:secret@admin.invalid', 'http://admin.invalid', 'https://admin.invalid:bad'])
def test_invalid_admin_origin_fails_without_redirect(env, origin):
    client, calls, _, _ = env
    main.app.dependency_overrides[get_settings]().report_admin_public_url = origin
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 503 and 'location' not in response.headers and not calls
