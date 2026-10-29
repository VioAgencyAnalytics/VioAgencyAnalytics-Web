"""BFF cookie/CSRF boundary and production routing; Admin owns identity tests."""
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

import main
import app.customer_auth as auth
from app.design_preview import app as preview

ORIGIN = 'https://customer.example.test'
TOKEN = 'a' * 64
USER = {'id': 'user1', 'name': 'Minh Anh', 'email': 'user@example.test', 'email_verified': 0}


@pytest.fixture
def stack(monkeypatch):
    settings = auth.CustomerSettings(customer_auth_enabled=True, customer_backend_url='https://admin.example.test',
        customer_web_origin=ORIGIN, customer_service_token=SecretStr('private-customer-service-' + 'x' * 32))
    monkeypatch.setattr(auth, 'customer_settings', lambda: settings)
    monkeypatch.setattr(main, 'get_runtime_mode', lambda: SimpleNamespace(app_env='production'))
    calls = []
    state = {'logged_in': False, 'unavailable': False}

    def handler(request):
        calls.append(request)
        assert request.headers['authorization'] == 'Bearer ' + settings.customer_service_token.get_secret_value()
        if state['unavailable']:
            raise httpx.ConnectError('private-internal-host', request=request)
        path = request.url.path.removeprefix('/api/internal/customer')
        if path == '/session':
            if not state['logged_in']:
                return httpx.Response(401, json={'error': 'Đăng nhập lại.', 'code': 'unauthenticated'})
            return httpx.Response(200, json={'user': USER, 'workspaces': [], 'workspace': state.get('workspace'),
                                             'capabilities': {'google': True, 'email_delivery': False}})
        if path == '/config':
            return httpx.Response(200, json={'google': True, 'email_delivery': False})
        if path == '/workspaces/' + 'a' * 32:
            return httpx.Response(200, json={'workspace':state['workspace'],'clients':[], 'member_count':1,
                                             'tour':{'version':1,'step':0,'status':'new'}})
        if path == '/workspaces/' + 'a' * 32 + '/integrations':
            return httpx.Response(200, json={'workspace':state['workspace'],'clients':[], 'selected_client':None,
                'platforms':[], 'categories':[], 'connections':[], 'summary':{'connected_accounts':0},
                'permissions':{'manage_connections':True}})
        if path == '/workspaces/' + 'a' * 32 + '/members':
            return httpx.Response(200, json={'workspace':state['workspace'],'members':[],'invitations':[],'events':[],
                'roles':[{'id':'owner','name':'Chủ sở hữu'}], 'summary':{'active_members':1,'pending_invitations':0},
                'permissions':{'manage_members':True,'view_invitations':True,'view_audit':True,'invite':False,'email_verified':False,'assignable_roles':['admin','member','viewer']}})
        if path == '/workspaces/' + 'a' * 32 + '/settings':
            return httpx.Response(200, json={'workspace':state['workspace'],'member_count':1,
                'profile':{'company_name':'','report_name':'','report_footer':'','accent_color':'#D9232E','default_period':'last30','compare_previous':True,'week_start':'monday','version':1,'updated_at':None},
                'permissions':{'manage_settings':True}})
        if path in ('/auth/login', '/auth/register', '/auth/google/finish'):
            state['logged_in'] = True
            return httpx.Response(200, json={'session_token': TOKEN, 'session_max_age': 2592000, 'user': USER})
        if path == '/auth/logout':
            state['logged_in'] = False
        return httpx.Response(200, json={'message': 'OK'})

    original = httpx.AsyncClient
    monkeypatch.setattr(auth.httpx, 'AsyncClient', lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handler)))
    with TestClient(main.app, base_url=ORIGIN) as client:
        yield client, calls, state, settings


def csrf_headers(client):
    data = client.get('/api/customer/session').json()
    return {'Origin': ORIGIN, 'X-CSRF-Token': data['csrf']}


def test_production_releases_only_live_pages_keeps_preview_isolated(stack):
    client, calls, state, _ = stack
    assert client.get('/workspace/login').status_code == 200
    response = client.get('/workspace/onboarding', follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == '/workspace/login'
    assert client.get('/workspace/integrations', follow_redirects=False).headers['location'] == '/workspace/login'
    assert client.get('/workspace/dashboard', follow_redirects=False).headers['location'] == '/workspace/login'
    for path in ['/workspace/members', '/workspace/settings', '/workspace/channels', '/workspace/reports']:
        assert client.get(path, follow_redirects=False).headers['location'] == '/workspace/login'
    for path in ['/workspace/channels/facebook-content', '/report/facebook-content']:
        assert client.get(path).status_code == 404
    with TestClient(preview) as separate:
        assert 'Bản xem thử' in separate.get('/workspace/login').text
        assert separate.get('/api/customer/session').status_code == 404


def test_cookie_only_session_rotation_csrf_and_logout(stack):
    client, calls, state, _ = stack
    headers = csrf_headers(client)
    binding = client.cookies.get(auth.BINDING)
    response = client.post('/api/customer/auth/login', json={'email': USER['email'], 'password': 'not-exposed'}, headers=headers)
    assert response.status_code == 200
    assert 'session_token' not in response.json()
    assert TOKEN not in response.text
    assert 'session_max_age' not in response.json()
    assert client.cookies.get(auth.SESSION) == TOKEN
    assert client.cookies.get(auth.BINDING) != binding
    cookie = next(c for c in response.headers.get_list('set-cookie') if c.startswith(auth.SESSION + '='))
    for attribute in ['HttpOnly', 'Secure', 'SameSite=lax', 'Max-Age=2592000', 'Path=/']:
        assert attribute in cookie
    assert 'no-store' in response.headers['cache-control']
    assert client.post('/api/customer/auth/logout', json={}, headers=headers).status_code == 403
    assert state['logged_in']
    response = client.post('/api/customer/auth/logout', json={}, headers=csrf_headers(client))
    assert response.status_code == 200
    assert not client.cookies.get(auth.SESSION)
    assert not state['logged_in']


@pytest.mark.parametrize('change', ['no_origin', 'wrong_origin', 'no_csrf', 'wrong_csrf', 'no_binding'])
def test_mutations_reject_cross_origin_and_missing_csrf(stack, change):
    client, calls, _, _ = stack
    headers = csrf_headers(client)
    if change == 'no_origin': headers.pop('Origin')
    if change == 'wrong_origin': headers['Origin'] = 'https://attacker.test'
    if change == 'no_csrf': headers.pop('X-CSRF-Token')
    if change == 'wrong_csrf': headers['X-CSRF-Token'] = 'wrong'
    if change == 'no_binding': client.cookies.clear()
    before = len(calls)
    assert client.post('/api/customer/auth/register', json={}, headers=headers).status_code == 403
    assert len(calls) == before


def test_proxy_allowlist_size_type_host_and_peer_fingerprint(stack):
    client, calls, _, _ = stack
    headers = csrf_headers(client)
    assert client.post('/api/customer/auth/google/finish', json={}, headers=headers).status_code == 404
    assert client.post('/api/customer/../../api/settings', json={}, headers=headers).status_code == 404
    assert client.post('/api/customer/workspaces', content='x' * 16385, headers={**headers,'Content-Type':'application/json'}).status_code == 413
    assert client.post('/api/customer/workspaces', content='{}', headers=headers).status_code == 415
    assert client.post('/api/customer/workspaces', json=[], headers=headers).status_code == 422
    assert client.get('/api/customer/session', headers={'Host':'evil.test'}).status_code == 400
    client.post('/api/customer/workspaces', json={}, headers={**headers, 'X-Forwarded-For':'spoofed', 'X-Customer-Session':'forged'})
    request = calls[-1]
    assert request.headers['x-customer-session'] == ''
    assert len(request.headers['x-customer-client']) == 64
    assert 'spoofed' not in request.headers['x-customer-client']


def test_google_callback_requires_browser_binding_and_hides_code(stack):
    client, calls, _, _ = stack
    response = client.get('/auth/customer/google/callback?state=secret-state&code=secret-code', follow_redirects=False)
    assert response.status_code == 303
    assert not calls
    assert response.headers['location'] == '/workspace/login?error=oauth_state'
    csrf_headers(client)
    response = client.get('/auth/customer/google/callback?state=secret-state&code=secret-code', follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == '/workspace/onboarding'
    assert 'secret-code' not in response.text
    assert 'secret-state' not in response.text
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert client.cookies.get(auth.SESSION) == TOKEN


def test_backend_outage_returns_actionable_error_without_internal_details(stack):
    client, calls, state, settings = stack
    state['unavailable'] = True
    for path in ['/workspace/login', '/api/customer/session']:
        response = client.get(path)
        assert response.status_code == 503
        assert 'private-internal-host' not in response.text
        assert settings.customer_service_token.get_secret_value() not in response.text


def test_disabled_feature_has_no_customer_api(stack):
    client, calls, _, settings = stack
    settings.customer_auth_enabled = False
    assert client.get('/api/customer/session').status_code == 404
    assert client.get('/workspace/login').status_code == 404
    assert not calls


def test_overview_requires_selected_workspace_and_gates_tour_mutation(stack):
    client, calls, state, _ = stack
    assert client.get('/workspace', follow_redirects=False).headers['location'] == '/workspace/login'
    state['logged_in'] = True
    assert client.get('/workspace', follow_redirects=False).headers['location'] == '/workspace/onboarding'
    state['workspace'] = {'id':'a'*32,'name':'Workspace <safe>', 'kind':'agency','website':'','currency':'VND','timezone':'Asia/Ho_Chi_Minh','role':'owner'}
    response = client.get('/workspace')
    assert response.status_code == 200
    assert 'Workspace &lt;safe&gt;' in response.text
    assert 'id="product-tour"' in response.text
    assert 'overview.js' in response.text
    assert '/static/js/customer/workspace.js' not in response.text
    assert client.get('/workspace/', follow_redirects=False).headers['location'] == '/workspace'
    path = '/api/customer/workspaces/' + 'a' * 32 + '/tour'
    assert client.post(path, json={'version':1,'step':0,'status':'active'}).status_code == 403
    assert client.post(path, json={'version':1,'step':0,'status':'active'}, headers=csrf_headers(client)).status_code == 200
    assert calls[-1].url.path.endswith('/tour')


def test_integrations_page_is_authenticated_and_never_loads_mock_workspace_js(stack):
    client, calls, state, _ = stack
    state['logged_in'] = True
    assert client.get('/workspace/integrations', follow_redirects=False).headers['location'] == '/workspace/onboarding'
    state['workspace'] = {'id':'a'*32,'name':'Workspace <safe>', 'role':'owner'}
    response = client.get('/workspace/integrations')
    assert response.status_code == 200
    assert 'Workspace &lt;safe&gt;' in response.text
    assert '/static/js/customer/integrations.js' in response.text
    assert '/static/js/customer/workspace.js' not in response.text
    assert 'KinderHealth' not in response.text
    assert 'HIPAA' not in response.text
    assert 'id="integrations-data"' in response.text
    assert 'no-store' in response.headers['cache-control']
    path = '/api/customer/workspaces/' + 'a'*32 + '/integrations'
    response = client.get(path, headers={'X-Customer-Session':'forged'})
    assert response.status_code == 200
    assert calls[-1].headers['X-Customer-Session'] == ''
    assert calls[-1].url.path == '/api/internal/customer' + path.removeprefix('/api/customer')
    assert client.get('/api/customer/workspaces/bad/integrations').status_code == 404
    assert client.post(path, json={}, headers=csrf_headers(client)).status_code == 404


def test_marketing_dashboard_uses_selected_workspace_and_no_legacy_report_api(stack):
    client, calls, state, _ = stack
    state['logged_in'] = True
    assert client.get('/workspace/dashboard', follow_redirects=False).headers['location'] == '/workspace/onboarding'
    state['workspace'] = {'id':'a'*32, 'name':'Workspace <safe>', 'role':'viewer', 'currency':'VND', 'timezone':'Asia/Ho_Chi_Minh'}
    response = client.get('/workspace/dashboard')
    assert response.status_code == 200
    assert 'Workspace &lt;safe&gt;' in response.text
    assert 'id="marketing-analytics-data"' in response.text
    assert '/static/js/customer/marketing.js' in response.text
    assert '/static/js/customer/workspace.js' not in response.text
    assert '/static/js/customer/overview-dashboard.js' not in response.text
    assert 'KinderHealth' not in response.text
    assert 'no-store' in response.headers['cache-control']
    assert response.headers['x-frame-options'] == 'DENY'
    assert all(req.url.path.startswith('/api/internal/customer/') for req in calls)
    assert client.get('/api/customer/workspaces/' + 'a'*32 + '/dashboard').status_code == 405
    for path in ['/workspace/reports', '/workspace/channels']:
        assert client.get(path).status_code == 200


@pytest.mark.parametrize('action', ['', '/select', '/update', '/archive', '/restore'])
def test_client_bff_allowlist_keeps_cookie_identity_and_csrf(stack, action):
    client, calls, _, settings = stack
    path = '/api/customer/workspaces/' + 'a'*32 + '/clients'
    if action:
        path += '/' + 'b'*32 + action
    before = len(calls)
    assert client.post(path,json={}).status_code == 403
    assert len(calls) == before
    response = client.post(path,json={'version':1},headers={**csrf_headers(client),'X-Customer-Session':'forged'})
    assert response.status_code == 200
    upstream = calls[-1]
    assert upstream.url.path == '/api/internal/customer' + path.removeprefix('/api/customer')
    assert upstream.headers['X-Customer-Session'] == ''
    assert settings.customer_service_token.get_secret_value() not in response.text
    assert client.post(path+'/delete',json={},headers=csrf_headers(client)).status_code == 404


@pytest.mark.parametrize('page', ['members', 'settings'])
def test_workspace_administration_pages_are_authenticated_and_scoped(stack, page):
    client, calls, state, _ = stack
    state['logged_in'] = True
    assert client.get('/workspace/' + page, follow_redirects=False).headers['location'] == '/workspace/onboarding'
    state['workspace'] = {'id':'a'*32,'name':'Workspace <safe>','role':'owner','currency':'VND','timezone':'Asia/Ho_Chi_Minh'}
    response = client.get('/workspace/' + page)
    assert response.status_code == 200
    assert 'Workspace &lt;safe&gt;' in response.text
    assert 'id="workspace-page-data"' in response.text
    assert '/static/js/customer/' + page + '.js' in response.text
    assert '/static/js/customer/workspace.js' not in response.text
    assert 'KinderHealth' not in response.text and 'HIPAA' not in response.text
    assert 'no-store' in response.headers['cache-control']
    reply = client.get('/api/customer/workspaces/' + 'a'*32 + '/' + page, headers={'X-Customer-Session':'forged'})
    assert reply.status_code == 200
    assert calls[-1].headers['X-Customer-Session'] == ''
    assert client.get('/api/customer/workspaces/bad/' + page).status_code == 404


@pytest.mark.parametrize('suffix', ['settings', 'members/'+'b'*32+'/role', 'members/'+'b'*32+'/remove', 'invitations/'+'b'*32+'/revoke'])
def test_workspace_administration_mutations_keep_csrf_and_exact_allowlist(stack, suffix):
    client, calls, state, _ = stack
    state['workspace'] = {'id':'a'*32,'name':'Test','role':'owner'}
    path = '/api/customer/workspaces/'+'a'*32+'/'+suffix
    before = len(calls)
    assert client.post(path,json={}).status_code == 403
    assert len(calls) == before
    assert client.post(path,json={},headers=csrf_headers(client)).status_code == 200
    assert calls[-1].url.path == '/api/internal/customer' + path.removeprefix('/api/customer')
    assert client.post(path+'/delete',json={},headers=csrf_headers(client)).status_code == 404


@pytest.mark.parametrize('page', ['channels', 'reports'])
def test_library_requires_selected_workspace_without_legacy_or_report_writes(stack, page):
    client, calls, state, _ = stack
    state['logged_in'] = True
    assert client.get('/workspace/' + page, follow_redirects=False).headers['location'] == '/workspace/onboarding'
    state['workspace'] = {'id': 'a'*32, 'name': 'Scope <safe>', 'role': 'viewer', 'currency': 'VND', 'timezone': 'Asia/Ho_Chi_Minh'}
    response = client.get('/workspace/' + page)
    assert response.status_code == 200
    assert 'Scope &lt;safe&gt;' in response.text
    assert 'id="library-model"' in response.text
    assert '/static/js/customer/' + page + '.js' in response.text
    assert '/static/js/customer/workspace.js' not in response.text
    assert 'KinderHealth' not in response.text and 'HIPAA' not in response.text
    assert '/report/facebook-content' not in response.text
    assert 'no-store' in response.headers['cache-control']
    assert response.headers['x-frame-options'] == 'DENY'
    assert {r.url.path for r in calls} <= {'/api/internal/customer/session', '/api/internal/customer/workspaces/'+'a'*32, '/api/internal/customer/workspaces/'+'a'*32+'/integrations'}
    before = len(calls)
    for action in ['reports', 'reports/export', 'reports/publish', 'channels/seo']:
        assert client.post('/api/customer/workspaces/'+'a'*32+'/'+action, json={}, headers=csrf_headers(client)).status_code == 404
    assert all('reports' not in r.url.path and 'channels' not in r.url.path for r in calls[before:])


def test_library_rejects_catalogue_from_a_different_client(stack, monkeypatch):
    client, _, state, _ = stack
    state['logged_in'] = True
    state['workspace'] = {'id': 'a'*32, 'name': 'Safe', 'role': 'owner'}
    original = auth.backend

    async def mismatched(request, method, path, data=None):
        value = await original(request, method, path, data)
        if path.endswith('/integrations'):
            value['selected_client'] = {'id': 'foreign-client', 'name': 'Foreign secret'}
        return value

    monkeypatch.setattr(auth, 'backend', mismatched)
    response = client.get('/workspace/reports')
    assert response.status_code == 409
    assert 'Foreign secret' not in response.text
