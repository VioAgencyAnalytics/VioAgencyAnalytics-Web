"""BFF cookie/CSRF boundary and production routing; Admin owns identity tests."""
from types import SimpleNamespace

import json
import httpx
import pytest
from urllib.parse import urlencode
from fastapi.testclient import TestClient
from pydantic import SecretStr

import main
import app.customer_auth as auth
from app.design_preview import app as preview

ORIGIN = 'https://customer.example.test'
TOKEN = 'a' * 64
USER = {'id': 'user1', 'name': 'Minh Anh', 'email': 'user@example.test', 'email_verified': 0}


def google_login_url(**changes):
    query = {'client_id': 'qa-client.apps.googleusercontent.com', 'redirect_uri': ORIGIN + '/auth/customer/google/callback',
             'response_type': 'code', 'scope': 'openid email profile', 'state': 's' * 64, 'nonce': 'n' * 64,
             'code_challenge': 'p' * 43, 'code_challenge_method': 'S256', 'prompt': 'select_account'}
    return 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({**query, **changes})


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
        if path == '/branding/preview' or path.endswith('/logo'):
            if not state['logged_in']:
                return httpx.Response(401,json={'error':'Đăng nhập lại.','code':'unauthenticated'})
            return httpx.Response(200,json=state.get('brand_payload',{'available':False}))
        if path == '/auth/google/start':
            return httpx.Response(200, json={'authorization_url': state.get('google_url', google_login_url()),
                                            'access_token': 'NEVER_FORWARD', 'client_secret': 'NEVER_FORWARD'})
        if '/providers/' in path and path.endswith('/start'):
            from urllib.parse import urlencode
            return httpx.Response(200,json={'authorization_url':state.get('provider_url') or 'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':'qa-client','state':'qa-state','response_type':'code','redirect_uri':ORIGIN+'/auth/customer/providers/google/callback'}), 'access_token':'NEVER_FORWARD'})
        if path in ('/providers/google/finish','/providers/meta/finish','/providers/tiktok/finish'):
            return httpx.Response(state.get('provider_status',200),json=state.get('provider_finish',{'workspace_id':'a'*32,'client_id':'b'*32,'connection_id':'c'*32,'platform_id':'ga4'}))
        if '/connections/' in path:
            if path.endswith('/discover'):
                return httpx.Response(200,json={'workspace_id':'a'*32,'client_id':'b'*32,'connection_id':'c'*32,'version':1,'credential':'NEVER_FORWARD','assets':[{'id':'properties/123','name':'QA property','access_token':'NEVER_FORWARD'}]})
            return httpx.Response(200,json={'connection_id':'c'*32,'asset_id':'d'*32,'sync':{'id':'e'*32,'status':'queued','credential':'NEVER_FORWARD'},'access_token':'NEVER_FORWARD','message':'OK','provider_revoked':False})
        if path == '/workspaces/' + 'a' * 32:
            return httpx.Response(200, json={'workspace':state['workspace'],'clients':state.get('clients',[]),'selected_client':state.get('selected_client'), 'member_count':1,
                                             'tour':{'version':1,'step':0,'status':'new'}})
        if path == '/workspaces/' + 'a' * 32 + '/integrations':
            return httpx.Response(200, json=state.get('data_catalogue', {'workspace':state['workspace'],'clients':[], 'selected_client':None,
                'platforms':[], 'categories':[], 'connections':[], 'summary':{'connected_accounts':0},
                'permissions':{'manage_connections':True}}))
        if path.startswith('/workspaces/'+'a'*32+'/data'):
            if not state['logged_in']:
                return httpx.Response(401, json={'error':'Đăng nhập lại.','code':'unauthenticated'})
            if path.endswith('/data'):
                return httpx.Response(200, json=state.get('data_index', {}))
            return httpx.Response(200, json=state.get('source_data', {}))
        if path == '/workspaces/' + 'a' * 32 + '/channels/facebook-content':
            if not state['logged_in']:
                return httpx.Response(401,json={'error':'Đăng nhập lại.','code':'unauthenticated'})
            return httpx.Response(200,json=state.get('content',{'schema_version':1,'source':'facebook_content',
                'scope':{'workspace_id':'a'*32,'client_id':None},'state':'no_client','client':None,'asset':None,
                'connection':None,'snapshot':None,'latest_sync':None,'periods':[],'metrics':[],'posts':[],
                'daily_posts':[],'insights':[],'credential':'NEVER_FORWARD'}))
        if path == '/workspaces/' + 'a' * 32 + '/members':
            return httpx.Response(200, json={'workspace':state['workspace'],'members':[],'invitations':[],'events':[],
                'roles':[{'id':'owner','name':'Chủ sở hữu'}], 'summary':{'active_members':1,'pending_invitations':0},
                'permissions':{'manage_members':True,'view_invitations':True,'view_audit':True,'invite':False,'email_verified':False,'assignable_roles':['admin','member','viewer']}})
        if path == '/workspaces/' + 'a' * 32 + '/settings':
            return httpx.Response(200, json={'workspace':state['workspace'],'member_count':1,
                'profile':{'company_name':'','report_name':'','report_footer':'','accent_color':'#D9232E','default_period':'last30','compare_previous':True,'week_start':'monday','version':1,'updated_at':None},
                'permissions':{'manage_settings':True}})
        if path in ('/auth/login', '/auth/register', '/auth/google/finish'):
            if path == '/auth/google/finish' and state.get('google_error'):
                return httpx.Response(400, json={'code': state['google_error'], 'error': 'Private provider failure'})
            state['logged_in'] = True
            return httpx.Response(200, json={'session_token': TOKEN, 'session_max_age': 2592000,
                                            'user': USER, 'redirect': state.get('login_redirect', '/workspace/onboarding')})
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
    assert client.get('/workspace/channels/facebook-content',follow_redirects=False).headers['location']=='/workspace/login'
    assert client.get('/report/facebook-content').status_code == 404
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


def test_google_start_projects_identity_only_url_and_binds_real_browser(stack):
    import hashlib
    client, calls, _, _ = stack
    headers = csrf_headers(client)
    binding = client.cookies.get(auth.BINDING)
    response = client.post('/api/customer/auth/google/start',
                           json={'remember': True, 'browser_binding': 'forged'}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {'authorization_url': google_login_url()}
    sent = json.loads(calls[-1].content)
    assert sent == {'remember': True, 'browser_binding': hashlib.sha256(binding.encode()).hexdigest()}
    assert 'NEVER_FORWARD' not in response.text


@pytest.mark.parametrize('url', [
    google_login_url().replace('accounts.google.com', 'attacker.test'),
    google_login_url().replace('https:', 'http:'),
    google_login_url().replace('accounts.google.com', 'user:pass@accounts.google.com'),
    google_login_url() + '#fragment',
    google_login_url() + '&state=duplicate',
    google_login_url(redirect_uri='https://attacker.test/callback'),
    google_login_url(redirect_uri=ORIGIN + '/auth/customer/providers/google/callback'),
    google_login_url(scope='openid email profile https://www.googleapis.com/auth/analytics.readonly'),
    google_login_url(response_type='token'), google_login_url(code_challenge_method='plain'),
    google_login_url(code_challenge='short'), google_login_url(client_id=''),
])
def test_google_start_rejects_unsafe_or_data_authorization_urls(stack, url):
    client, _, state, _ = stack
    state['google_url'] = url
    response = client.post('/api/customer/auth/google/start', json={}, headers=csrf_headers(client))
    assert response.status_code == 502
    assert 'NEVER_FORWARD' not in response.text and 'attacker.test' not in response.text


@pytest.mark.parametrize('query', [
    'state=one&state=two&code=qa-code', 'state=one&code=one&code=two',
    'state=one&error=one&error=two', 'state=one&code=qa-code&error=access_denied',
    'state=&code=qa-code', 'code=qa-code', 'state=one',
])
def test_google_callback_rejects_ambiguous_response_before_backend(stack, query):
    client, calls, _, _ = stack
    csrf_headers(client)
    before = len(calls)
    response = client.get('/auth/customer/google/callback?' + query, follow_redirects=False)
    assert response.headers['location'] == '/workspace/login?error=oauth_state'
    assert len(calls) == before and not client.cookies.get(auth.SESSION)


@pytest.mark.parametrize('destination', ['/workspace', '/workspace/onboarding'])
def test_google_callback_sets_cookie_and_redirects_without_json_identity(stack, destination):
    client, _, state, _ = stack
    state['login_redirect'] = destination
    csrf_headers(client)
    response = client.get('/auth/customer/google/callback?state=qa-state&code=qa-code', follow_redirects=False)
    assert response.headers['location'] == destination
    assert response.content == b''
    assert client.cookies.get(auth.SESSION) == TOKEN
    assert USER['email'] not in response.text and TOKEN not in response.text


def test_google_callback_cancellation_preserves_existing_session_and_is_actionable(stack):
    client, _, state, _ = stack
    csrf_headers(client)
    client.cookies.set(auth.SESSION, TOKEN)
    state['google_error'] = 'google_cancelled'
    response = client.get('/auth/customer/google/callback?state=qa-state&error=access_denied', follow_redirects=False)
    assert response.headers['location'] == '/workspace/login?error=google_cancelled'
    assert client.cookies.get(auth.SESSION) == TOKEN
    assert 'Private provider failure' not in response.text
    state.pop('google_error')
    state['login_redirect'] = 'https://attacker.test/'
    response = client.get('/auth/customer/google/callback?state=qa-state&code=qa-code', follow_redirects=False)
    assert response.headers['location'] == '/workspace/login?error=google_failed'
    assert 'attacker.test' not in response.text


@pytest.mark.parametrize('code', ['google_configuration','google_unavailable','google_clock','google_identity'])
def test_google_callback_preserves_safe_diagnostic_categories_without_provider_details(stack, code):
    client, _, state, _ = stack
    csrf_headers(client)
    state['google_error'] = code
    response = client.get('/auth/customer/google/callback?state=qa-state&code=qa-code', follow_redirects=False)
    assert response.headers['location'] == '/workspace/login?error=' + code
    assert not client.cookies.get(auth.SESSION)
    assert 'Private provider failure' not in response.text


def test_backend_outage_returns_actionable_error_without_internal_details(stack):
    client, calls, state, settings = stack
    state['unavailable'] = True
    for path in ['/workspace/login', '/api/customer/session']:
        response = client.get(path)
        assert response.status_code == 503
        assert 'private-internal-host' not in response.text
        assert settings.customer_service_token.get_secret_value() not in response.text


def test_logo_preview_and_images_require_authentication_and_project_only_raster_bytes(stack):
    import base64
    client, _, state, _ = stack
    path='/api/customer/workspaces/'+'a'*32+'/logo'
    assert client.get(path).status_code == 401
    assert client.post('/api/customer/branding/preview',json={'website':'https://example.com'}).status_code == 403
    png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jR1sAAAAASUVORK5CYII=')
    state['logged_in']=True
    state['brand_payload']={'available':True,'content_type':'image/png','content':base64.b64encode(png).decode(),'credential':'NEVER_FORWARD'}
    response=client.get(path)
    assert response.status_code==200 and response.content==png
    assert response.headers['content-type']=='image/png'
    assert response.headers['cross-origin-resource-policy']=='same-origin'
    assert response.headers['content-security-policy']=="default-src 'none'; sandbox"
    assert 'no-store' in response.headers['cache-control']
    response=client.post('/api/customer/branding/preview',json={'website':'https://example.com'},headers=csrf_headers(client))
    assert response.status_code==200 and set(response.json())=={'available','image'}
    assert response.json()['image'].startswith('data:image/png;base64,') and 'NEVER_FORWARD' not in response.text
    state['brand_payload']={'available':True,'content_type':'image/svg+xml','content':base64.b64encode(b'<svg onload="alert(1)"/>').decode()}
    assert client.get(path).status_code==502
    state['brand_payload']={'available':False}
    assert client.get(path).status_code==204


def test_disabled_feature_has_no_customer_api(stack):
    client, calls, _, settings = stack
    settings.customer_auth_enabled = False
    assert client.get('/api/customer/session').status_code == 404
    assert client.get('/workspace/login').status_code == 404
    assert not calls


def test_provider_start_requires_csrf_and_overwrites_no_browser_binding_from_input(stack):
    import hashlib
    client,calls,state,settings=stack
    state['logged_in']=True
    client.cookies.set(auth.SESSION,TOKEN)
    path='/api/customer/workspaces/'+'a'*32+'/providers/ga4/start'
    assert client.post(path,json={'client_id':'b'*32}).status_code==403
    headers=csrf_headers(client)
    response=client.post(path,json={'client_id':'b'*32},headers=headers)
    assert response.status_code==200
    assert set(response.json())=={'authorization_url'}
    assert 'NEVER_FORWARD' not in response.text
    assert calls[-1].headers['x-customer-session']==TOKEN
    payload=json.loads(calls[-1].content)
    assert payload['browser_binding']==hashlib.sha256(client.cookies.get(auth.BINDING).encode()).hexdigest()
    before=len(calls)
    assert client.post(path,json={'client_id':'b'*32,'browser_binding':'injected'},headers=headers).status_code==422
    assert client.post(path.replace('ga4','unknown_source'),json={'client_id':'b'*32},headers=headers).status_code==404
    assert len(calls)==before
    state['provider_url']='https://evil.invalid/authorize?client_secret=NEVER_FORWARD'
    denied=client.post(path,json={'client_id':'b'*32},headers=headers)
    assert denied.status_code==502 and 'NEVER_FORWARD' not in denied.text


def test_provider_callback_is_bound_and_cannot_create_login_session_or_open_redirect(stack):
    client,calls,state,_=stack
    state['logged_in']=True
    client.cookies.set(auth.SESSION,TOKEN)
    csrf_headers(client)
    path='/auth/customer/providers/google/callback'
    response=client.get(path+'?state=qa-state&code=qa-code',follow_redirects=False)
    assert response.status_code==303
    assert response.headers['location']=='/workspace/integrations?oauth=connected&connection='+'c'*32+'&platform=ga4'
    assert client.cookies.get(auth.SESSION)==TOKEN
    assert calls[-1].url.path.endswith('/providers/google/finish')
    assert set(json.loads(calls[-1].content))=={'state','code','error','browser_binding'}
    before=len(calls)
    duplicate=client.get(path+'?state=first&state=second&code=qa-code',follow_redirects=False)
    assert duplicate.headers['location']=='/workspace/integrations?oauth=oauth_state'
    assert len(calls)==before
    state['provider_finish']={'workspace_id':'https://evil.invalid','client_id':'b'*32,'connection_id':'c'*32,'platform_id':'ga4','access_token':'NEVER_FORWARD'}
    denied=client.get(path+'?state=qa-state&code=qa-code',follow_redirects=False)
    assert denied.headers['location']=='/workspace/integrations?oauth=provider_failed'
    assert 'NEVER_FORWARD' not in denied.text


@pytest.mark.parametrize('action',['discover','select','sync','disconnect'])
def test_provider_connection_actions_project_safe_dtos_only(stack,action):
    client,calls,state,_=stack
    state['logged_in']=True
    client.cookies.set(auth.SESSION,TOKEN)
    path='/api/customer/workspaces/'+'a'*32+'/connections/'+'c'*32+'/'+action
    response=client.post(path,json={'client_id':'b'*32,'version':1},headers=csrf_headers(client))
    assert response.status_code==200
    assert calls[-1].url.path.endswith('/'+action)
    assert 'NEVER_FORWARD' not in response.text
    assert client.post('/api/customer/providers/google/finish',json={},headers=csrf_headers(client)).status_code==404


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


@pytest.mark.parametrize('kind,count,hide_picker,label', [
    ('business', 1, True, 'Thương hiệu'),
    ('business', 2, False, 'Thương hiệu'),
    ('business', 0, False, 'Thương hiệu'),
    ('agency', 1, False, 'Khách hàng'),
    ('agency', 2, False, 'Khách hàng'),
])
def test_integrations_scope_matches_business_or_agency_without_get_mutations(stack, kind, count, hide_picker, label):
    from html.parser import HTMLParser

    class Elements(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids = {}
            self.events = []

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            self.events.extend(key for key in values if key.lower().startswith('on'))
            if values.get('id'):
                self.ids[values['id']] = values

    client, calls, state, _ = stack
    state['logged_in'] = True
    workspace = {'id':'a' * 32, 'name':'Công ty Á Châu', 'kind':kind, 'role':'owner'}
    clients = [{'id':str(index + 1) * 32, 'name':'Thương hiệu <img src=x onerror=alert(1)>'} for index in range(count)]
    state['workspace'] = workspace
    state['data_catalogue'] = {'workspace':workspace, 'clients':clients, 'selected_client':None,
        'platforms':[], 'categories':[], 'connections':[], 'summary':{'connected_accounts':0},
        'permissions':{'manage_connections':True}}
    response = client.get('/workspace/integrations')
    assert response.status_code == 200
    document = Elements()
    document.feed(response.text)
    assert ('hidden' in document.ids['integration-client-picker']) == hide_picker
    assert ('hidden' in document.ids['integration-brand-summary']) != hide_picker
    assert ('hidden' in document.ids['integration-manage-clients']) == hide_picker
    assert f'id="integration-scope-label">{label}</span>' in response.text
    if hide_picker:
        assert 'Kết nối các tài khoản Marketing của doanh nghiệp.' in response.text
        assert 'Thương hiệu &lt;img src=x onerror=alert(1)&gt;' in response.text
    assert document.events == []
    assert all(request.method == 'GET' for request in calls)


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


def test_customer_content_page_and_read_api_are_authenticated_and_projection_is_private(stack):
    client,calls,state,_=stack
    path='/api/customer/workspaces/'+'a'*32+'/channels/facebook-content'
    assert client.get(path).status_code==401
    state['logged_in']=True
    state['workspace']={'id':'a'*32,'name':'QA Workspace','role':'viewer'}
    response=client.get(path)
    assert response.status_code==200 and response.json()['state']=='no_client'
    assert 'NEVER_FORWARD' not in response.text
    assert 'no-store' in response.headers['cache-control']
    page=client.get('/workspace/channels/facebook-content')
    assert page.status_code==200
    assert 'facebook-content.js' in page.text and 'id="fc-client"' in page.text
    assert 'library.js' not in page.text and '/report/facebook-content' not in page.text
    before=len(calls)
    assert client.get(path+'?client_id=foreign').status_code==422
    assert client.get(path+'?snapshot='+'b'*32+'&snapshot='+'c'*32).status_code==422
    assert len(calls)==before


def test_customer_content_rejects_wrong_workspace_scope_and_does_not_open_other_channels(stack):
    client,_,state,_=stack
    state['logged_in']=True
    state['content']={'schema_version':1,'source':'facebook_content','state':'empty','scope':{'workspace_id':'f'*32,'client_id':None},'message':'FOREIGN_CONTENT'}
    response=client.get('/api/customer/workspaces/'+'a'*32+'/channels/facebook-content')
    assert response.status_code==502 and 'FOREIGN_CONTENT' not in response.text
    for path in ('/workspace/channels/facebook-ads','/workspace/channels/seo','/report/facebook-content'):
        assert client.get(path).status_code==404


def test_customer_content_snapshot_renders_missing_zero_and_inert_user_text(stack):
    client,_,state,_=stack
    state['logged_in']=True;state['workspace']={'id':'a'*32,'name':'QA Workspace','role':'viewer'}
    state['selected_client']={'id':'b'*32,'name':'QA Brand'};state['clients']=[state['selected_client']]
    state['content']={'schema_version':1,'source':'facebook_content','scope':{'workspace_id':'a'*32,'client_id':'b'*32},
        'state':'ready','client':state['selected_client'],'asset':{'id':'d'*32,'name':'<img src=x>','external_id':'1234'},
        'snapshot':{'id':'e'*32,'start_date':'2026-10-01','end_date':'2026-10-02','created_at':'2026-10-03T00:00:00+00:00','fetched_at':'2026-10-03T00:00:00+00:00','timezone':'UTC'},
        'connection':{'id':'f'*32,'status':'connected','version':1},'periods':[],
        'metrics':[{'key':'posts_published','label':'Bài đăng','value':0,'status':'available','coverage':{'available':2,'expected':2,'unit':'days','access_token':'NEVER_FORWARD'}}],
        'daily_posts':[{'date':'2026-10-01','posts_published':0}], 'posts':[], 'insights':[], 'access_token':'NEVER_FORWARD'}
    page=client.get('/workspace/channels/facebook-content')
    assert page.status_code==200
    assert '&lt;img src=x&gt;' in page.text and '<img src=x>' not in page.text
    assert 'NEVER_FORWARD' not in page.text
    result=client.get('/api/customer/workspaces/'+'a'*32+'/channels/facebook-content').json()
    assert result['metrics'][0]['value']==0
    assert result['metrics'][0]['coverage']=={'available':2,'expected':2,'unit':'days'}
    report=client.get('/workspace/reports/facebook-content')
    assert report.status_code==200
    assert 'fc-report-document' in report.text and 'id="fc-print"' in report.text
    assert 'Báo cáo đã phát hành' not in report.text and 'NEVER_FORWARD' not in report.text
    assert '&lt;img src=x&gt;' in report.text and '<img src=x>' not in report.text
    assert 'no-store' in report.headers['cache-control']


def test_customer_facebook_report_reuses_session_scope_and_snapshot_validation(stack):
    client,calls,state,_=stack
    assert client.get('/workspace/reports/facebook-content',follow_redirects=False).status_code==303
    state['logged_in']=True;state['workspace']={'id':'a'*32,'name':'QA Workspace','role':'viewer'}
    before=len(calls)
    assert client.get('/workspace/reports/facebook-content?snapshot=bad').status_code==422
    assert not any('/channels/facebook-content' in request.url.path for request in calls[before:])
    state['content']={'schema_version':1,'source':'facebook_content','state':'empty',
                      'scope':{'workspace_id':'f'*32,'client_id':None},'message':'FOREIGN_REPORT'}
    response=client.get('/workspace/reports/facebook-content')
    assert response.status_code==502 and 'FOREIGN_REPORT' not in response.text


def test_customer_facebook_display_rejects_malformed_post_counts(stack):
    client,_,state,_=stack
    state['logged_in']=True;state['workspace']={'id':'a'*32,'name':'QA Workspace','role':'viewer'}
    state['content']={'schema_version':1,'source':'facebook_content','state':'empty',
                      'scope':{'workspace_id':'a'*32,'client_id':None},
                      'posts':[{'post_id':'1234_5678','date':'2026-10-01','shares_lifetime':True}]}
    result=client.get('/api/customer/workspaces/'+'a'*32+'/channels/facebook-content')
    assert result.status_code==502 and result.json()['code']=='snapshot_invalid'
