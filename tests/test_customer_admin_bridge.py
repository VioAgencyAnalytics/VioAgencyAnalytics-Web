"""Opt-in real Web BFF + Admin/worker contract acceptance using synthetic providers.

Set VIO_ADMIN_TEST_ROOT to the sibling Admin checkout and install its test
dependencies. No live account, project database, SMTP or external HTTP is used.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

import pytest

ADMIN = os.environ.get('VIO_ADMIN_TEST_ROOT')
if not ADMIN:
    pytest.skip('Opt-in cross-repository Customer contract test', allow_module_level=True)
pytest.importorskip('flask')
ADMIN = Path(ADMIN).resolve()
if not (ADMIN/'kdh/customer_provider_worker.py').is_file():
    raise RuntimeError('VIO_ADMIN_TEST_ROOT must be an Admin checkout')
sys.path[:0] = [str(ADMIN), str(ADMIN/'tests')]

def load_fixture(name, filename):
    spec = importlib.util.spec_from_file_location(name, ADMIN/'tests'/filename)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

extended = load_fixture('_bridge_extended', 'test_customer_all_connectors.py')
core = load_fixture('_bridge_core', 'test_customer_providers.py')
import test_customer_identity as identity_fixture
from kdh.customer_provider_worker import CustomerProviderWorker
from kdh.customer_provider_adapters import SOURCES as ADMIN_SOURCES
from kdh.customer_operations import read_operations, parameters as operations_parameters
from werkzeug.datastructures import MultiDict

from fastapi.testclient import TestClient
import httpx
from pydantic import SecretStr
import main
import app.customer_auth as auth
from app.customer_transport import PROVIDERS


class Response:
    def __init__(self, value): self.status_code, self.value = 200, value
    def json(self): return self.value
    def iter_content(self, chunk_size=16384): yield json.dumps(self.value).encode()
    def __enter__(self): return self
    def __exit__(self, *_args): pass


def core_request(fixture, source, method, url, **kwargs):
    """Fixture provider wire formats; production adapters still parse and attest."""
    body, query = kwargs.get('json', {}), kwargs.get('params', {})
    assert not kwargs.get('allow_redirects', False)
    if source in ('ga4', 'gsc'):
        if url.endswith(':runReport'):
            names = [row['name'] for row in body['metrics']]
            dims = [row['name'] for row in body.get('dimensions', [])]
            day = body['dateRanges'][0]['startDate']
            dimensions = {'date':day.replace('-', ''),'sessionDefaultChannelGroup':'Organic Search','pagePath':'/'}
            metrics = {'activeUsers':'3','sessions':'0','screenPageViews':'5','engagementRate':'0.25'}
            return Response({'rows':[{'dimensionValues':[{'value':dimensions[d]} for d in dims],
                'metricValues':[{'value':metrics[n]} for n in names]}], 'metadata':{'timeZone':'Asia/Ho_Chi_Minh','currencyCode':'VND'}})
        if url.endswith('/searchAnalytics/query'):
            dims = body.get('dimensions', []); dimensions={'date':body['startDate'],'query':'QA <script>inert</script>'}
            return Response({'rows':[{'keys':[dimensions[d] for d in dims], 'clicks':0, 'impressions':100, 'ctr':0, 'position':2.5}]})
        return fixture.response(method,url,**kwargs)
    if url.endswith('/debug_token'):
        response=fixture.meta_response(method,url,**kwargs)
        value=response.json(); value['data']['scopes'] += ['ads_read']
        return Response(value)
    account={'id':'act_1234','name':'QA Ads','account_status':1,'currency':'USD','timezone_name':'America/New_York'}
    if url.endswith('/me/adaccounts'): return Response({'data':[account]})
    if url.endswith('/act_1234'): return Response(account)
    if url.endswith('/act_1234/insights'):
        period=json.loads(query['time_range'])
        return Response({'data':[] if query.get('level')=='campaign' else [{'date_start':period['since'],
            'date_stop':period['since'],'spend':'0.00','impressions':'100','clicks':'0'}]})
    if url.endswith('/1234/posts'):
        day=fixture.store.one('SELECT start_date FROM customer_provider_sync_jobs ORDER BY created_at DESC LIMIT 1')['start_date']
        return Response({'data':[{'id':'1234_5678','created_time':day+'T12:00:00+00:00',
            'message':'QA content <script>inert</script>','permalink_url':'https://www.facebook.com/1234/posts/5678',
            'reactions':{'summary':{'total_count':0}},'comments':{'summary':{'total_count':0}}}]})
    if url.endswith('/insights'): return Response({'data':[]})
    if url.endswith('/1234'): return Response({'id':'1234','name':'QA Page'})
    return fixture.meta_response(method,url,**kwargs)


@pytest.fixture(params=list(PROVIDERS))
def bridge(request,monkeypatch):
    source=request.param
    fixture=(core.CustomerProviderTests() if source in ('ga4','gsc','facebook_content','facebook_ads')
             else extended.CustomerAllConnectorTests())
    if os.getenv('TEST_DATABASE_URL'):
        fixture.fixture_type=identity_fixture.CustomerPostgresTests
    fixture.setUp()
    try:
        fixture.source=source
        backend=fixture.app
        origin=backend.config['CUSTOMER_WEB_ORIGIN']
        settings=auth.CustomerSettings(customer_auth_enabled=True,customer_backend_url='http://127.0.0.1:8094',
            customer_web_origin=origin,customer_service_token=SecretStr(backend.config['CUSTOMER_SERVICE_TOKEN']))
        monkeypatch.setattr(auth,'customer_settings',lambda:settings)
        monkeypatch.setattr(main,'get_runtime_mode',lambda:SimpleNamespace(app_env='test'))
        calls=[]
        def transport(request):
            assert request.url.host=='127.0.0.1' and request.url.path.startswith('/api/internal/customer/')
            calls.append((request.method,request.url.path))
            with backend.test_client() as flask:
                response=flask.open(request.url.raw_path.decode(),method=request.method,data=request.content,headers=dict(request.headers))
            return httpx.Response(response.status_code,content=response.data,headers={'Content-Type':response.content_type})
        from httpx._client import AsyncClient
        monkeypatch.setattr(auth.httpx,'AsyncClient',lambda **kwargs:AsyncClient(**kwargs,transport=httpx.MockTransport(transport)))
        provider=fixture.request if isinstance(fixture,extended.CustomerAllConnectorTests) else lambda *a,**kw:core_request(fixture,source,*a,**kw)
        with TestClient(main.app,base_url=origin) as client:
            def headers():
                response=client.get('/api/customer/session')
                assert response.status_code==200,response.text
                return {'Origin':origin,'X-CSRF-Token':response.json()['csrf']}
            login=client.post('/api/customer/auth/login',json={'email':'owner@example.test','password':identity_fixture.PASSWORD},headers=headers())
            assert login.status_code==200,login.text
            ws=fixture.workspace['id']; base='/api/customer/workspaces/'+ws
            response=client.post(base+'/select',json={},headers=headers())
            assert response.status_code==200,response.text
            with patch('requests.request',side_effect=provider):
                yield SimpleNamespace(source=source,fixture=fixture,client=client,headers=headers,base=base,calls=calls,config=backend.config)
    finally:
        fixture.doCleanups()


def test_source_connect_sync_goals_and_reports_across_real_services(bridge):
    b=bridge; source=b.source; client=b.client
    assert PROVIDERS==ADMIN_SOURCES
    details=client.get(b.base).json(); brand=details['clients'][0]['id']
    chosen=client.post(b.base+'/clients/'+brand+'/select',json={},headers=b.headers())
    assert chosen.status_code==200,chosen.text
    before=b.fixture.store.one('SELECT COUNT(*) AS n FROM customer_provider_sync_jobs')['n']
    response=client.post(b.base+'/providers/'+source+'/start',json={'client_id':brand},headers=b.headers())
    assert response.status_code==200,response.text
    query=parse_qs(urlsplit(response.json()['authorization_url']).query)
    claims={'sub':'qa-subject','email':'qa@example.invalid','iss':'https://accounts.google.com','nonce':query.get('nonce',[''])[0]}
    provider=PROVIDERS[source]
    callback='/auth/customer/providers/'+provider+'/callback'
    with patch('google.oauth2.id_token.verify_oauth2_token',return_value=claims):
        response=client.get(callback,params={'state':query['state'][0],
            'auth_code' if provider=='tiktok' else 'code':'QA_ONLY_AUTH_CODE'},follow_redirects=False)
    assert response.status_code==303 and 'oauth=connected' in response.headers['location'],response.headers.get('location')
    row=b.fixture.store.one('SELECT id,version FROM customer_provider_connections WHERE workspace_id=? AND platform_id=?',(b.fixture.workspace['id'],source))
    actions=b.base+'/connections/'+row['id']
    body={'client_id':brand,'version':row['version']}
    discovered=client.post(actions+'/discover',json=body,headers=b.headers())
    assert discovered.status_code==200,discovered.text
    assert discovered.json()['workspace_id']==b.fixture.workspace['id']
    assert discovered.json()['assets']
    selected=client.post(actions+'/select',json={**body,'external_id':discovered.json()['assets'][0]['id']},headers=b.headers())
    assert selected.status_code==200,selected.text
    repeat=client.post(actions+'/select',json={**body,'external_id':discovered.json()['assets'][0]['id']},headers=b.headers())
    assert repeat.status_code==200 and selected.json()['sync']['id']==repeat.json()['sync']['id']
    assert b.fixture.store.one('SELECT COUNT(*) AS n FROM customer_provider_sync_jobs')['n']==before+1
    assert CustomerProviderWorker(b.fixture.f.service).run_one()
    job=b.fixture.store.one('SELECT status,error_code FROM customer_provider_sync_jobs WHERE id=?',(selected.json()['sync']['id'],))
    assert job['status']=='succeeded',job
    # Every GET below must work without provider HTTP or other business writes.
    with patch('requests.request',side_effect=AssertionError('Read must never call provider')):
        report=client.get(b.base+'/data/'+source)
        assert report.status_code==200,report.text
        data=report.json();assert data['state']=='ready' and data['source']==source
        assert data['scope']=={'workspace_id':b.fixture.workspace['id'],'client_id':brand}
        assert data['snapshot'] and data['published'] is False
        page=client.get('/workspace/reports/data',params={'source':source})
        assert page.status_code==200,page.text[:200]
        assert 'report-kpis' in page.text
        overview=client.get('/api/customer/workspaces/'+b.fixture.workspace['id']+'/analytics',params={'source':source})
        assert overview.status_code==200,overview.text[:200]
        assert overview.json()['focus']==source and overview.json()['state']=='ready'
        assert overview.json()['snapshot']['id']==data['snapshot']['id']
        assert overview.json()['scope']==data['scope']
        # Operations observes the exact same job/snapshot, without Marketing payload.
        metadata=read_operations(
            b.fixture.store,b.config,'snapshots',operations_parameters(MultiDict({'workspace':b.fixture.workspace['id']}),'snapshots'))
        assert metadata['pagination']['total']==1
        assert metadata['items'][0]['job_id']==selected.json()['sync']['id']
        assert 'payload' not in metadata['items'][0]
    original_hash=b.fixture.store.one('SELECT payload_hash FROM customer_provider_snapshots WHERE id=?',(data['snapshot']['id'],))['payload_hash']
    metric=next(m for m in data['metrics'] if m['unit'] in ('count','number'))
    goal={'client_id':brand,'asset_id':data['asset']['id'],'start':data['period']['start'],'end':data['period']['end'],
        'items':[{'key':metric['key'],'input_value':'0','direction':'at_least','version':0}]}
    saved=client.post(b.base+'/targets/'+source,json=goal,headers=b.headers())
    assert saved.status_code==200,saved.text
    assert client.post(b.base+'/targets/'+source,json=goal,headers=b.headers()).status_code==409
    updated=client.get(b.base+'/data/'+source)
    assert updated.status_code==200,updated.text
    target=next(row for row in updated.json()['targets']['items'] if row['key']==metric['key'])
    assert target['value']=='0' and target['version']==1
    assert b.fixture.store.one('SELECT payload_hash FROM customer_provider_snapshots WHERE id=?',(data['snapshot']['id'],))['payload_hash']==original_hash
    # A different user sees none of this Workspace's data through the same BFF.
    changed=client.post('/api/customer/auth/register',json={'name':'Other','email':'other@example.invalid','password':identity_fixture.PASSWORD},headers=b.headers())
    assert changed.status_code==200,changed.text
    denied=client.get(b.base+'/data/'+source)
    assert denied.status_code in (403,404) and data['snapshot']['id'] not in denied.text
    account=b.fixture.f.service.session(client.cookies.get(auth.SESSION))['account_id']
    from kdh.core import now
    b.fixture.store.execute('INSERT INTO customer_memberships (workspace_id,account_id,role,created_at) VALUES (?,?,?,?)',
        (b.fixture.workspace['id'],account,'viewer',now()))
    assert client.post(b.base+'/select',json={},headers=b.headers()).status_code==200
    assert client.post(b.base+'/clients/'+brand+'/select',json={},headers=b.headers()).status_code==200
    assert client.get(b.base+'/data/'+source).status_code==200
    assert client.post(actions+'/sync',json={**body,'start':goal['start'],'end':goal['end'],'request_key':'f'*32},headers=b.headers()).status_code==403
    assert client.post(b.base+'/targets/'+source,json=goal,headers=b.headers()).status_code==403
    for result in (response,discovered,selected,repeat,report,page,overview,saved):
        for private in ('QA_ONLY_ACCESS','QA_ONLY_PAGE_ACCESS','QA_ONLY_REFRESH','QA_ONLY_META_ACCESS','QA_ONLY_GOOGLE_APP_SECRET','session_token'):
            assert private not in result.text
