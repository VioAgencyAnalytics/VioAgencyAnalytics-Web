"""Common report BFF strips private fields and preserves source/tenant semantics."""
import pytest

from test_customer_auth import stack, csrf_headers
from app.customer_data import SOURCES


def report(source='ga4', state='ready'):
    metrics = [
        {'key':'users','label':'Người dùng','unit':'count','field':'totals.activeUsers','aggregation':'provider_period','grain':'period'},
        {'key':'sessions','label':'Phiên','unit':'count','field':'totals.sessions','aggregation':'provider_period','grain':'period'},
        {'key':'views','label':'Xem trang','unit':'count','field':'totals.screenPageViews','aggregation':'provider_period','grain':'period'},
        {'key':'rate','label':'Tỷ lệ tương tác','unit':'percent','field':'totals.engagementRate','aggregation':'provider_period','grain':'period'},
    ]
    return {'schema_version':1,'mapping_version':1,'source':source,'state':state,'availability':'available',
        'connector':{'id':source,'name':'QA Connector','icon':'monitoring','color':'amber','asset_label':'Tài khoản',
            'provider':'google','mapping_status':'available','mapping_version':1,'adapter_ready':True,
            'metrics':metrics,'client_secret':'NEVER_FORWARD','capabilities':{'publish':True}},
        'scope':{'workspace_id':'a'*32,'client_id':'b'*32},'client':{'id':'b'*32,'name':'QA Brand'},
        'asset':{'id':'c'*32,'name':'<script>inert</script>','external_id':'properties/123','access_token':'NEVER_FORWARD'},
        'connection':{'id':'d'*32,'version':1,'status':'connected','credential':'NEVER_FORWARD'},
        'snapshot':{'id':'e'*32,'start_date':'2026-10-01','end_date':'2026-10-02','created_at':'2026-10-03T00:00:00+00:00','fetched_at':'2026-10-03T00:00:00+00:00','timezone':'Asia/Ho_Chi_Minh','adapter_receipt':'NEVER_FORWARD'},
        'periods':[{'id':'e'*32,'start_date':'2026-10-01','end_date':'2026-10-02','created_at':'2026-10-03T00:00:00+00:00'}],
        'latest_sync':None,'metrics':[{**m,'value':v,'status':'no_data' if v is None else 'available','currency':None,'token':'NEVER_FORWARD'} for m,v in zip(metrics,[3,0,None,.25])],
        'daily':[{'date':'2026-10-01','values':{'users':3,'sessions':0,'views':None,'rate':.25},'raw':'NEVER_FORWARD'}],
        'tables':[{'id':'channels','title':'Nguồn truy cập','total_rows':1,'truncated':False,
            'columns':[{'key':'name','label':'Nhóm kênh','unit':'text'},{'key':'sessions','label':'Phiên','unit':'count'}],
            'rows':[{'name':'<img src=x>','sessions':0,'access_token':'NEVER_FORWARD'}]}],
        'notes':['Không cộng số người dùng duy nhất qua các ngày.'],'published':True,'provenance':'NEVER_FORWARD'}


def prepare(state):
    state.update(logged_in=True, workspace={'id':'a'*32,'name':'QA Workspace','role':'viewer'},
        selected_client={'id':'b'*32,'name':'QA Brand'})
    state['clients']=[state['selected_client']]
    state['source_data']=report()
    state['data_index']={'schema_version':1,'scope':{'workspace_id':'a'*32,'client_id':'b'*32},
        'sources':[report(source) for source in sorted(SOURCES)],'published':True,'raw':'NEVER_FORWARD'}
    state['data_catalogue']={'workspace':state['workspace'],'selected_client':state['selected_client'],
        'platforms':[{'id':source,'name':source} for source in sorted(SOURCES)]}


def test_read_api_and_page_require_session_and_exact_host(stack):
    client,calls,state,_=stack
    path='/api/customer/workspaces/'+'a'*32+'/data'
    assert client.get(path).status_code==401
    assert client.get('/workspace/reports/data',follow_redirects=False).headers['location']=='/workspace/login'
    prepare(state)
    assert client.get(path,headers={'Host':'foreign.example.test'}).status_code==400
    result=client.get(path)
    assert result.status_code==200
    assert len(result.json()['sources'])==9 and result.json()['published'] is False
    assert 'NEVER_FORWARD' not in result.text and 'no-store' in result.headers['cache-control']
    headers=csrf_headers(client)
    before=len(calls)
    assert client.post(path+'/ga4',json={},headers=headers).status_code==404
    assert len(calls)==before


def test_projection_preserves_zero_null_ratio_and_strips_nested_credentials(stack):
    client,_,state,_=stack;prepare(state)
    result=client.get('/api/customer/workspaces/'+'a'*32+'/data/ga4')
    assert result.status_code==200,result.text
    data=result.json()
    assert [m['value'] for m in data['metrics']]==[3,0,None,.25]
    assert data['daily'][0]['values']['views'] is None
    assert data['tables'][0]['rows']==[{'name':'<img src=x>','sessions':0}]
    assert data['connector']['capabilities']['publish'] is False and data['published'] is False
    assert 'NEVER_FORWARD' not in result.text
    state['source_data']['metrics'][0]['value']=True
    assert client.get('/api/customer/workspaces/'+'a'*32+'/data/ga4').status_code==502


def test_source_scope_duplicate_and_foreign_filters_fail_before_transport(stack):
    client,calls,state,_=stack;prepare(state)
    base='/api/customer/workspaces/'+'a'*32+'/data'
    for suffix in ('?client_id=foreign','/ga4?snapshot=bad','/ga4?snapshot='+'c'*32+'&snapshot='+'d'*32,'/unknown'):
        before=len(calls)
        assert client.get(base+suffix).status_code in (404,422)
        assert len(calls)==before
    state['source_data']['scope']['workspace_id']='f'*32
    assert client.get(base+'/ga4').status_code==502
    state['source_data']=report('gsc')
    assert client.get(base+'/ga4').status_code==502
    state['data_index']['sources'][0]['scope']['client_id']='f'*32
    assert client.get(base).status_code==502


def test_report_renders_readable_metrics_inert_text_and_common_controls(stack):
    client,_,state,_=stack;prepare(state)
    result=client.get('/workspace/reports/data?source=ga4')
    assert result.status_code==200,result.text
    assert 'data-report.js' in result.text and 'library.js' not in result.text
    for element in ('data-source','data-client','data-period','data-chart','connector-report-data'):
        assert 'id="'+element+'"' in result.text
    assert '25,00%' in result.text and '>0<' in result.text and '—' in result.text
    assert '&lt;script&gt;inert&lt;/script&gt;' in result.text
    assert '<script>inert</script>' not in result.text and '<img src=x>' not in result.text
    assert 'NEVER_FORWARD' not in result.text
    assert client.get('/workspace/reports/data?source=ga4&source=gsc').status_code==422
    state['selected_client']={'id':'f'*32,'name':'Foreign brand'}
    result=client.get('/workspace/reports/data?source=ga4')
    assert result.status_code==409 and 'Foreign brand' not in result.text


@pytest.mark.parametrize('value',[-1,float('nan'),float('inf'),'0',True])
def test_invalid_numeric_observations_are_rejected(value):
    from app.customer_data import CustomerError,project
    payload=report();payload['metrics'][0]['value']=value
    with pytest.raises(CustomerError):
        project(payload,'a'*32)
