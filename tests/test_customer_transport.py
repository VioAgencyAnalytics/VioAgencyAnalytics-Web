"""Private Web/Admin boundary failures must not mutate twice or leak internals."""
from copy import deepcopy
import json

import httpx
import pytest
from fastapi.testclient import TestClient

import main
import app.customer_auth as auth
import app.customer_transport as transport
from test_customer_auth import stack, csrf_headers, ORIGIN, TOKEN


@pytest.fixture
def upstream(stack, monkeypatch):
    client, _, state, settings = stack
    headers = csrf_headers(client)
    requests = []
    response = {'status':200, 'payload':{'message':'OK'}}
    def handler(request):
        requests.append(request)
        assert request.headers['authorization'] == 'Bearer '+settings.customer_service_token.get_secret_value()
        assert request.headers['accept-encoding']=='identity'
        if response.get('exception'):
            raise response['exception']('PRIVATE_INTERNAL_HOST',request=request)
        if 'raw' in response:
            return httpx.Response(response['status'],content=response['raw'],headers=response.get('headers',{'Content-Type':'application/json'}))
        return httpx.Response(response['status'],json=response['payload'],headers=response.get('headers'))
    # Preserve the original mock factory before replacing the shared httpx attribute.
    from httpx._client import AsyncClient
    monkeypatch.setattr(auth.httpx,'AsyncClient',lambda **kwargs:AsyncClient(**kwargs,transport=httpx.MockTransport(handler)))
    return client, requests, response, headers


@pytest.mark.parametrize('failure',[httpx.ConnectError,httpx.ReadTimeout,httpx.RemoteProtocolError])
def test_network_failure_is_safe_and_never_retries_a_mutation(upstream,failure):
    client,calls,response,headers=upstream;response['exception']=failure
    result=client.post('/api/customer/auth/login',json={'email':'qa@example.invalid','password':'QA_PRIVATE_PASSWORD'},headers=headers)
    assert result.status_code==503
    assert len(calls)==1
    assert 'PRIVATE_' not in result.text
    assert result.json()['code'] in ('service_timeout','service_unavailable')
    assert result.headers['cache-control']=='no-store'


@pytest.mark.parametrize('raw,headers',[
    (b'<html>PRIVATE_STACK</html>',{'Content-Type':'text/html'}),
    (b'{"message":"PRIVATE_BAD_JSON"',{'Content-Type':'application/json'}),
    (b'{"message": "first", "message":"PRIVATE_DUPLICATE"}',{'Content-Type':'application/json'}),
    (b'{"number":NaN}',{'Content-Type':'application/json'}),
    (b'{"number":1e10000}',{'Content-Type':'application/json'}),
    (b'[]',{'Content-Type':'application/json'}),
    (b'{"message":"PRIVATE_BODY"}',{'Content-Type':'application/json','Content-Encoding':'br'}),
    (b'{}',{'Content-Type':'application/json','Content-Length':str(transport.MAX_RESPONSE_BYTES+1)}),
])
def test_bad_envelope_or_json_fails_closed_without_raw_body(upstream,raw,headers):
    client,calls,response,csrf=upstream;response.update(raw=raw,headers=headers)
    result=client.post('/api/customer/workspaces',json={},headers=csrf)
    assert result.status_code==502
    assert len(calls)==1 and 'PRIVATE_' not in result.text
    assert result.json()['code']=='service_response'


def test_size_budget_applies_without_content_length(upstream,monkeypatch):
    client,calls,response,headers=upstream
    monkeypatch.setattr(transport,'MAX_RESPONSE_BYTES',100)
    response.update(raw=b'{"message":"'+b'x'*200+b'"}',headers={'Content-Type':'application/json','Content-Length':'0'})
    assert client.post('/api/customer/workspaces',json={},headers=headers).status_code==502
    assert len(calls)==1


def test_redirect_never_follows_service_key_or_sets_browser_cookie(upstream):
    client,calls,response,headers=upstream
    response.update(status=302,headers={'Location':'https://external.invalid/PRIVATE','Set-Cookie':'forged=1'})
    result=client.post('/api/customer/workspaces',json={},headers=headers)
    assert result.status_code==502 and len(calls)==1
    assert 'location' not in result.headers and not client.cookies.get('forged')


@pytest.mark.parametrize('status,body,expected',[
    (500,{'error':'PRIVATE_STACK postgres://user:password@host','code':'invalid'},503),
    (503,{'error':'PRIVATE_TOKEN','code':'provider_setup_required'},503),
    (401,{'error':'PRIVATE_AUTH','code':'service_auth'},503),
    (409,{'error':{'token':'PRIVATE_OBJECT'},'code':['PRIVATE_CODE']},409),
    (422,{'error':'access_token=PRIVATE_LEAK','code':'invalid'},422),
    (422,{'error':'https://backend.invalid/?code=PRIVATE_LEAK','code':'invalid'},422),
])
def test_safe_errors_keep_actionable_status_without_internal_detail(upstream,status,body,expected):
    client,calls,response,headers=upstream;response.update(status=status,payload=body)
    result=client.post('/api/customer/workspaces',json={},headers=headers)
    assert result.status_code==expected
    assert 'PRIVATE_' not in result.text
    assert isinstance(result.json()['error'],str) and isinstance(result.json()['code'],str)
    assert len(calls)==1


def test_success_defense_preserves_business_null_zero_decimal_and_invitation_code(upstream):
    client,_,response,headers=upstream
    response['payload']={'message':'OK','access_token':'PRIVATE_ROOT','session_token':'PRIVATE_SESSION',
        'data':{'credential':'PRIVATE_NESTED','clientSecret':'PRIVATE_NESTED','value':None,'zero':0,'spend':'1.700001'},'invitation':{'code':'share-by-user'}}
    result=client.post('/api/customer/workspaces',json={},headers=headers)
    assert result.status_code==200 and 'PRIVATE_' not in result.text
    assert result.json()=={'message':'OK','data':{'value':None,'zero':0,'spend':'1.700001'},'invitation':{'code':'share-by-user'}}


@pytest.mark.parametrize('age',[True,-1,0,2592001,'2592000',{'token':'PRIVATE'}])
def test_bad_session_age_is_controlled_error_without_setting_session(upstream,age):
    client,_,response,headers=upstream
    response['payload']={'session_token':TOKEN,'session_max_age':age,'redirect':'/workspace/onboarding'}
    result=client.post('/api/customer/auth/login',json={},headers=headers)
    assert result.status_code==502 and not client.cookies.get(auth.SESSION)


@pytest.mark.parametrize('change',[
    {'workspace_id':'f'*32},{'connection_id':'f'*32},{'client_id':[]},{'version':True},
    {'assets':[{'id':'properties/1','name':None}]},
    {'assets':[{'id':'one','name':'QA'},{'id':'one','name':'QA duplicate'}]},
])
def test_discovery_rejects_wrong_scope_or_invalid_dto(change):
    payload={'workspace_id':'a'*32,'client_id':'b'*32,'connection_id':'c'*32,'version':1,'assets':[{'id':'properties/1','name':'QA'}]}
    with pytest.raises(auth.CustomerError):
        auth.provider_result('workspaces/'+'a'*32+'/connections/'+'c'*32+'/discover',{**payload,**change},None)


@pytest.mark.parametrize('change',[
    {'connection_id':'f'*32},{'asset_id':{}},{'sync':{'id':'e'*32,'status':'unknown'}},{'sync':{'id':None,'status':'queued'}},
])
def test_selection_rejects_wrong_connection_or_job(change):
    payload={'connection_id':'c'*32,'asset_id':'d'*32,'sync':{'id':'e'*32,'status':'queued'}}
    with pytest.raises(auth.CustomerError):
        auth.provider_result('workspaces/'+'a'*32+'/connections/'+'c'*32+'/select',{**payload,**change},None)


def test_discovery_pins_client_inside_the_workspace():
    payload={'workspace_id':'a'*32,'client_id':'d'*32,'connection_id':'c'*32,'version':1,'assets':[]}
    with pytest.raises(auth.CustomerError) as error:
        auth.provider_result('workspaces/'+'a'*32+'/connections/'+'c'*32+'/discover',payload,None,'b'*32)
    assert error.value.code=='connection_scope'


@pytest.mark.parametrize('extra',[{}, {'config_id':'not-numeric'}, {'config_id':'123','override_default_response_type':'false'}])
def test_meta_business_login_requires_the_application_configuration(stack,extra):
    from urllib.parse import urlencode
    client,_,state,settings=stack
    state['provider_url']='https://www.facebook.com/v26.0/dialog/oauth?'+urlencode({
        'client_id':'123456','redirect_uri':ORIGIN+'/auth/customer/providers/meta/callback',
        'response_type':'code','state':'QA_ONLY_STATE',**extra})
    response=client.post('/api/customer/workspaces/'+'a'*32+'/providers/instagram/start',
        json={'client_id':'b'*32},headers=csrf_headers(client))
    assert response.status_code==502


@pytest.mark.parametrize('platform',['ga4',[],None])
def test_meta_callback_cannot_return_google_or_invalid_source(stack,platform):
    client,_,state,_=stack;csrf_headers(client)
    state['provider_finish']={'workspace_id':'a'*32,'client_id':'b'*32,'connection_id':'c'*32,'platform_id':platform}
    result=client.get('/auth/customer/providers/meta/callback?state=qa-state&code=qa-code',follow_redirects=False)
    assert result.status_code==303 and result.headers['location'].endswith('oauth=provider_failed')


def test_private_payload_structure_budget_is_enforced():
    value={};nested=value
    for _ in range(42):nested['child']={};nested=nested['child']
    with pytest.raises(ValueError):transport.public_payload(value,'/session')


@pytest.mark.parametrize('payload',[{}, {'user':None,'workspace':None,'workspaces':{}},
    {'user':{'id':'x'},'workspace':None,'workspaces':[]},
    {'user':None,'workspace':{'id':'../private'},'workspaces':[]},
    {'user':None,'workspace':None,'workspaces':[{'id':[]}]}])
def test_malformed_session_is_a_controlled_boundary_error(upstream,payload):
    client,_,response,_=upstream;response['payload']=payload
    result=client.get('/api/customer/session')
    assert result.status_code==502 and result.json()['code']=='service_response'
