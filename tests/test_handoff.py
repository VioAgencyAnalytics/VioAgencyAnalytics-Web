import json
import secrets
from types import SimpleNamespace
from urllib.parse import urlencode

import httpx
import pytest
from fastapi.testclient import TestClient
import main
from app.config import Settings, get_settings
from app.repositories.viewer import AdminViewerRepository
from app.routes import viewer

REPORT = 'rpt_' + 'a' * 32


@pytest.fixture
def handoff(monkeypatch):
    settings = Settings(_env_file=None, debug=False, app_env='production', report_admin_base_url='https://internal.invalid',
        report_admin_public_url='https://admin.invalid', report_new_public_url='https://new.invalid', report_service_token='test-service')
    state = {'calls': [], 'status': 200}
    def handle(request):
        assert request.headers['Authorization'] == 'Bearer test-service'
        state['calls'].append(request)
        data = json.loads(request.content)
        if request.url.path.endswith('/handoffs'):
            state['create'] = data; state['transaction'] = secrets.token_urlsafe(32)
            return httpx.Response(200, json={'transaction': state['transaction'], 'authorize_url': 'https://evil.invalid/'})
        if state['status'] != 200:
            return httpx.Response(state['status'])
        return httpx.Response(200, json={'session': secrets.token_urlsafe(48),
            **{k:state['create'][k] for k in ('target_id','revision','mode')}})
    upstream = httpx.Client(transport=httpx.MockTransport(handle))
    monkeypatch.setattr(viewer, 'repository', lambda request, _: AdminViewerRepository(settings.report_admin_base_url, 'test-service',
        client=upstream, viewer_session=request.cookies.get(viewer.SESSION, '')))
    monkeypatch.setattr(main, 'get_runtime_mode', lambda: SimpleNamespace(app_env='production'))
    main.app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(main.app, base_url='https://new.invalid') as client:
        yield client, state
    main.app.dependency_overrides.clear()
    upstream.close()


def start(client, state):
    response = client.get('/auth/handoff/start?' + urlencode({'mode':'published','target_id':REPORT,'revision':7}), follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'].startswith('https://admin.invalid/viewer/authorize?')
    assert 'HttpOnly' in response.headers['set-cookie'] and 'Secure' in response.headers['set-cookie']
    return {'transaction':state['transaction'],'state':state['create']['state'],'code':secrets.token_urlsafe(48)}


def test_start_callback_pins_revision_and_rotates_session(handoff):
    client, state = handoff; data = start(client, state)
    result = client.post('/auth/handoff/callback', json=data, headers={'Origin':'https://new.invalid'})
    assert result.status_code == 200
    assert result.json() == {'location':'/reports/' + REPORT + '?revision=7'}
    assert not client.cookies.get('__Host-kdh_handoff')
    assert client.cookies.get(viewer.SESSION) and client.cookies.get(viewer.CSRF)
    assert 'test-service' not in result.text and data['code'] not in result.text
    assert state['create']['audience'] == 'https://new.invalid'
    assert state['create']['callback'] == 'https://new.invalid/auth/handoff/callback'


@pytest.mark.parametrize('case', ['missing_cookie','state','transaction','origin','no_origin','extra_field'])
def test_browser_binding_and_csrf_fail_closed(handoff, case):
    client, state = handoff; data = start(client, state); headers = {'Origin':'https://new.invalid'}
    if case == 'missing_cookie': client.cookies.clear()
    if case in ('state','transaction'): data[case] = secrets.token_urlsafe(32)
    if case == 'origin': headers['Origin'] = 'https://evil.invalid'
    if case == 'no_origin': headers = {}
    if case == 'extra_field': data['revision'] = 8
    result = client.post('/auth/handoff/callback', json=data, headers=headers)
    assert result.status_code in (400,403) and len(state['calls']) == 1


def test_identity_conflict_keeps_existing_account(handoff):
    client, state = handoff; data = start(client, state)
    client.cookies.set(viewer.SESSION, 'existing-account')
    state['status'] = 409
    result = client.post('/auth/handoff/callback', json=data, headers={'Origin':'https://new.invalid'})
    assert result.status_code == 409 and 'tài khoản khác' in result.text
    assert client.cookies.get(viewer.SESSION) == 'existing-account'
    assert state['calls'][-1].headers['X-KDH-Viewer-Session'] == 'existing-account'


@pytest.mark.parametrize('query', ['mode=published&target_id='+REPORT, 'mode=preview&target_id='+REPORT, 'mode=published&target_id='+REPORT+'&revision=1&next=https://evil.invalid', 'mode=published&target_id='+REPORT+'&revision=1&revision=2'])
def test_start_rejects_ambiguous_or_unpinned_scope(handoff, query):
    client, state = handoff
    assert client.get('/auth/handoff/start?' + query).status_code == 400
    assert not state['calls']


def test_canonical_host_before_browser_binding_and_clean_callback(handoff):
    client, state = handoff
    result = client.get('https://alias.invalid/auth/handoff/start?mode=published&target_id='+REPORT+'&revision=1', follow_redirects=False)
    assert result.status_code == 303 and result.headers['location'].startswith('https://new.invalid/')
    assert not state['calls']
    result = client.get('/auth/handoff/callback')
    assert result.status_code == 200 and result.headers['referrer-policy'] == 'no-referrer'
    assert 'https://' not in result.text and '/static/js/pages/handoff.js' in result.text
