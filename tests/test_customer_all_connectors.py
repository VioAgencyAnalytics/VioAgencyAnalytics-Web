"""BFF allowlist, callback normalization and presentation for every source."""
import json
from urllib.parse import urlencode
import pytest

from test_customer_auth import stack, csrf_headers, ORIGIN, TOKEN
from test_customer_data import report, prepare
import app.customer_auth as auth
from app.customer_report_view import build


@pytest.mark.parametrize('source,provider,host,path',[
    ('google_ads','google','accounts.google.com','/o/oauth2/v2/auth'),
    ('youtube','google','accounts.google.com','/o/oauth2/v2/auth'),
    ('business_profile','google','accounts.google.com','/o/oauth2/v2/auth'),
    ('instagram','meta','www.facebook.com','/v26.0/dialog/oauth'),
    ('tiktok_ads','tiktok','business-api.tiktok.com','/portal/auth'),
])
def test_provider_start_all_new_sources_only_forwards_safe_url(stack,source,provider,host,path):
    client,calls,state,_ = stack
    state['logged_in']=True; client.cookies.set(auth.SESSION,TOKEN)
    query={'state':'QA_ONLY_STATE','redirect_uri':ORIGIN+'/auth/customer/providers/'+provider+'/callback'}
    query.update({'app_id':'123456'} if provider=='tiktok' else {'client_id':'QA_ONLY_CLIENT','response_type':'code'})
    if provider=='meta':query.update(config_id='123458',override_default_response_type='true')
    state['provider_url']='https://'+host+path+'?'+urlencode(query)
    address='/api/customer/workspaces/'+'a'*32+'/providers/'+source+'/start'
    result=client.post(address,json={'client_id':'b'*32},headers=csrf_headers(client))
    assert result.status_code==200
    assert result.json()=={'authorization_url':state['provider_url']}
    assert set(json.loads(calls[-1].content))=={'client_id','browser_binding'}
    assert 'NEVER_FORWARD' not in result.text
    state['provider_url'] += '&client_secret=NEVER_FORWARD'
    assert client.post(address,json={'client_id':'b'*32},headers=csrf_headers(client)).status_code==502


def test_tiktok_callback_uses_auth_code_never_login_kit_code_and_rejects_duplicates(stack):
    client,calls,state,_=stack; state['logged_in']=True; client.cookies.set(auth.SESSION,TOKEN)
    csrf_headers(client)
    state['provider_finish']={'workspace_id':'a'*32,'client_id':'b'*32,'connection_id':'c'*32,'platform_id':'tiktok_ads'}
    path='/auth/customer/providers/tiktok/callback'
    result=client.get(path+'?state=QA_ONLY_STATE&auth_code=QA_ONLY_ADVERTISER_CODE&code=QA_ONLY_OTHER_CODE&id=123',follow_redirects=False)
    assert result.status_code==303 and 'platform=tiktok_ads' in result.headers['location']
    body=json.loads(calls[-1].content)
    assert body['code']=='QA_ONLY_ADVERTISER_CODE'
    assert 'QA_ONLY_OTHER_CODE' not in calls[-1].content.decode()
    before=len(calls)
    result=client.get(path+'?state=x&auth_code=x&auth_code=y',follow_redirects=False)
    assert result.headers['location'].endswith('oauth=oauth_state') and len(calls)==before
    assert result.headers['cache-control']=='no-store'


@pytest.mark.parametrize('source',['ga4','gsc','google_ads','facebook_ads','tiktok_ads','instagram','youtube','business_profile'])
def test_every_report_has_cover_readable_controls_and_no_provider_secret(stack,source):
    client,_,state,_=stack; prepare(state)
    state['source_data']=report(source)
    state['data_catalogue']['platforms']=[{'id':source,'name':'QA Connector'}]
    result=client.get('/workspace/reports/data?source='+source)
    assert result.status_code==200,result.text
    for element in ('report-summary','report-kpis','report-trends','report-detail','report-method','data-print'):
        assert 'id="'+element+'"' in result.text
    assert 'connector-report.css' in result.text
    assert '<script>inert</script>' not in result.text and 'NEVER_FORWARD' not in result.text


def test_report_view_counts_zero_as_observation_and_never_invents_missing_metrics():
    value=report()
    view=build(value)
    assert view['days']==2 and view['observed_days']==1
    assert view['available']==3 and view['total']==4
    assert view['missing']==['Xem trang']


@pytest.mark.parametrize('code,expected',[
    ('provider_setup_required','Vio cần hoàn tất cấu hình API'),
    ('provider_account_required','Tài khoản chưa có nguồn dữ liệu phù hợp'),
    ('provider_scopes','Tài khoản chưa có đủ quyền đọc'),
    ('provider_rate_limit','Nền tảng đang giới hạn lượt đọc'),
    ('provider_reauth','Quyền truy cập đã hết hiệu lực'),
    ('QA_ONLY_PRIVATE_ERROR','Lần đồng bộ chưa thành công'),
])
def test_failed_sync_has_safe_specific_guidance_in_report(stack,code,expected):
    client,_,state,_=stack;prepare(state)
    value=report('ga4',state='sync_error')
    value['latest_sync']={'id':'e'*32,'status':'failed','error_code':code}
    state['source_data']=value
    result=client.get('/workspace/reports/data?source=ga4')
    assert result.status_code==200,result.text
    assert expected in result.text
    assert 'QA_ONLY_PRIVATE_ERROR' not in result.text


def test_callback_preserves_safe_setup_error_without_returning_vendor_body(stack,monkeypatch):
    client,_,state,_=stack;state['logged_in']=True;client.cookies.set(auth.SESSION,TOKEN)
    csrf_headers(client)
    async def failure(*args,**kwargs):
        raise auth.CustomerError(503,'QA_ONLY_VENDOR_PRIVATE_BODY','provider_setup_required')
    monkeypatch.setattr(auth,'backend',failure)
    result=client.get('/auth/customer/providers/google/callback?state=QA_ONLY_STATE&code=QA_ONLY_CODE',follow_redirects=False)
    assert result.status_code==303
    assert result.headers['location']=='/workspace/integrations?oauth=provider_setup_required'
    assert 'QA_ONLY' not in result.text and 'QA_ONLY' not in result.headers['location']


def test_reusing_google_application_copies_app_settings_only_and_keeps_signin_separate(tmp_path,monkeypatch):
    from test_configure_customer_providers import fixture
    # Independent fixture prevents any access to the real ignored configuration.
    import importlib.util
    from pathlib import Path
    root=Path(__file__).resolve().parents[1];monkeypatch.syspath_prepend(str(root/'scripts'))
    spec=importlib.util.spec_from_file_location('configure_all_fixture',root/'scripts/configure_customer_providers.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    config={'CUSTOMER_WEB_ORIGIN':'https://localhost:8444','CUSTOMER_SERVICE_TOKEN':'QA_ONLY_'+'x'*48,
        'DATABASE_URL':'postgresql://vio_customer:qa-only@127.0.0.1:5434/vio_customer','POSTGRES_PASSWORD':'qa-only',
        'ENCRYPTION_KEY':'QA_ONLY_KEY','CUSTOMER_GOOGLE_CLIENT_ID':'qa.apps.googleusercontent.com',
        'CUSTOMER_GOOGLE_CLIENT_SECRET':'QA_ONLY_APP_SECRET_LONG','CUSTOMER_SMTP_PASSWORD':'QA_ONLY_SMTP'}
    (tmp_path/'config.json').write_text(json.dumps(config))
    module.configure('google',tmp_path,reuse_signin=True)
    saved=json.loads((tmp_path/'config.json').read_text())
    assert all(saved[key]==value for key,value in config.items())
    assert saved['CUSTOMER_DATA_GOOGLE_CLIENT_ID']==config['CUSTOMER_GOOGLE_CLIENT_ID']
    assert 'QA_ONLY_APP_SECRET_LONG' not in (tmp_path/'docker-web.env').read_text()
