"""Shared loopback Viewer must never mix upstreams, tokens or browser sessions."""
import json
import secrets

import httpx
import pytest
from fastapi.testclient import TestClient

import main
from app.config import Settings, get_settings
from app.repositories.viewer import AdminViewerRepository
from app.routes import viewer


REPORT = 'rpt_' + 'a' * 32


@pytest.fixture
def shared(monkeypatch):
    settings = Settings(_env_file=None, app_env='production', report_vio_viewer_enabled=True,
        report_admin_base_url='http://main-backend:8090', report_admin_public_url='http://localhost:8090',
        report_new_public_url='http://localhost:8080', report_service_token='m' * 48,
        report_vio_admin_base_url='http://vio-backend:8090', report_vio_admin_public_url='http://localhost:8191',
        report_vio_new_public_url='http://127.0.0.1:8080', report_vio_service_token='v' * 48)
    calls = []
    pending = {}
    def handle(request):
        host = request.url.host
        assert request.headers['Authorization'] == 'Bearer ' + ('m' if host == 'main-backend' else 'v') * 48
        calls.append((host, request.url.path, request.headers.get('X-KDH-Viewer-Session', '')))
        if request.url.path.endswith('/handoffs'):
            body = json.loads(request.content)
            pending[host] = {**body, 'transaction': secrets.token_urlsafe(32)}
            return httpx.Response(200, json={'transaction': pending[host]['transaction']})
        if request.url.path.endswith('/redeem'):
            body = json.loads(request.content)
            assert body['transaction'] == pending[host]['transaction']
            assert body['callback'] == pending[host]['callback']
            return httpx.Response(200, json={'session': ('M' if host == 'main-backend' else 'V') * 64,
                **{k: pending[host][k] for k in ('target_id', 'revision', 'mode')}})
        return httpx.Response(401)
    upstream = httpx.Client(transport=httpx.MockTransport(handle))
    monkeypatch.setattr(viewer, 'repository', lambda request, s: AdminViewerRepository(
        s.report_admin_base_url, s.report_service_token.get_secret_value(), client=upstream,
        viewer_session=request.cookies.get(viewer.SESSION, '')))
    main.app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(main.app, base_url='http://localhost:8080') as client:
        yield client, settings, calls, pending
    main.app.dependency_overrides.clear()
    upstream.close()


def test_two_origins_bind_transactions_sessions_and_upstreams(shared):
    client, _, calls, pending = shared
    for origin, admin, host, session in (
            ('http://localhost:8080', 'http://localhost:8090', 'main-backend', 'M' * 64),
            ('http://127.0.0.1:8080', 'http://localhost:8191', 'vio-backend', 'V' * 64)):
        r = client.get(origin + '/auth/handoff/start?mode=published&target_id=' + REPORT + '&revision=1', follow_redirects=False)
        assert r.status_code == 303 and r.headers['location'].startswith(admin + '/viewer/authorize?')
        p = pending[host]
        assert p['audience'] == origin and p['callback'] == origin + '/auth/handoff/callback'
        r = client.post(origin + '/auth/handoff/callback', headers={'Origin': origin},
            json={'state': p['state'], 'transaction': p['transaction'], 'code': secrets.token_urlsafe(48)})
        assert r.status_code == 200
        assert r.json()['location'] == '/reports/' + REPORT + '?revision=1'
        assert 'Domain=' not in r.headers['set-cookie']
        client.get(origin + '/reports/' + REPORT + '?revision=1', follow_redirects=False)
        assert calls[-1][0] == host and calls[-1][2] == session
    client.get('http://localhost:8080/reports/' + REPORT + '?revision=1', follow_redirects=False)
    assert calls[-1][0] == 'main-backend' and calls[-1][2] == 'M' * 64


def test_vio_cannot_redeem_primary_transaction(shared):
    client, _, calls, pending = shared
    client.get('/auth/handoff/start?mode=published&target_id=' + REPORT + '&revision=1', follow_redirects=False)
    p = pending['main-backend']
    r = client.post('http://127.0.0.1:8080/auth/handoff/callback', headers={'Origin': 'http://127.0.0.1:8080'},
        json={'state': p['state'], 'transaction': p['transaction'], 'code': secrets.token_urlsafe(48)})
    assert r.status_code == 400 and len(calls) == 1


@pytest.mark.parametrize('path', ['/?client_id=client_kinderhealth', '/reports?backend=http://evil.invalid'])
def test_browser_cannot_select_backend_by_query(shared, path):
    client, _, calls, _ = shared
    r = client.get('http://127.0.0.1:8080' + path, follow_redirects=False)
    assert r.status_code == 303 and r.headers['location'] == 'http://localhost:8191/viewer/reports'
    assert not calls


def test_unknown_host_and_duplicate_query_denied(shared):
    client, _, calls, _ = shared
    assert client.get('http://evil.invalid:8080/reports').status_code == 421
    assert client.get('/auth/handoff/start?mode=published&target_id=' + REPORT + '&revision=1&revision=2').status_code == 400
    assert not calls


@pytest.mark.parametrize('field,value', [
    ('report_vio_new_public_url', 'http://localhost:8080'),
    ('report_vio_new_public_url', 'https://example.test'),
    ('report_vio_admin_base_url', 'http://main-backend:8090'),
    ('report_vio_admin_public_url', 'http://localhost:8090'),
    ('report_vio_service_token', 'm' * 48),
])
def test_ambiguous_configuration_fails_closed(shared, field, value):
    from pydantic import SecretStr
    client, settings, calls, _ = shared
    setattr(settings, field, SecretStr(value) if field.endswith('token') else value)
    assert client.get('/reports', follow_redirects=False).status_code == 503
    assert not calls


def test_disabled_preserves_single_admin(shared):
    client, settings, calls, _ = shared
    settings.report_vio_viewer_enabled = False
    r = client.get('/reports', follow_redirects=False)
    assert r.status_code == 303 and r.headers['location'] == 'http://localhost:8090/viewer/reports'
    assert not calls
