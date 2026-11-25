"""Report periods/plans are projected safely and GET cannot queue provider work."""
from copy import deepcopy
import pytest

from test_customer_auth import stack, csrf_headers
from test_customer_data import prepare
from app.customer_data import project, CustomerError


def controls(data, manage=True):
    data.update(calendar={'today':'2026-11-10','latest_closed_date':'2026-11-09','timezone':'Asia/Ho_Chi_Minh','max_days':90},
        period={'start':'2026-10-01','end':'2026-10-02','data_start':'2026-10-01','data_end':'2026-10-02','is_open':False,'mode':'custom'},
        permissions={'sync':manage,'private':'NEVER_FORWARD'},targets={'asset_id':data['asset']['id'],
        'start':'2026-10-01','end':'2026-10-02','can_manage':manage,'updated_at':None,'credential':'NEVER_FORWARD','items':[
            {'key':'users','unit':'count','direction':'at_least','version':1,'status':'met','value':'0','input_value':'0',
             'currency':None,'actual':3,'ratio':None,'difference':'3','relation':'above','private':'NEVER_FORWARD'},
            {'key':'rate','unit':'percent','direction':'at_least','version':1,'status':'met','value':'0.2','input_value':'20',
             'currency':None,'actual':.25,'ratio':'1.25','difference':'0.05','relation':'above'}]})
    return data


def test_custom_period_is_forwarded_as_read_only_and_full_goal_table_renders(stack):
    client,calls,state,_=stack;prepare(state);controls(state['source_data'])
    before=len(calls)
    response=client.get('/workspace/reports/data?source=ga4&start=2026-10-01&end=2026-10-02')
    assert response.status_code==200,response.text
    assert all(call.method=='GET' for call in calls[before:])
    read=next(call for call in calls[before:] if call.url.path.endswith('/data/ga4'))
    assert read.url.query==b'start=2026-10-01&end=2026-10-02'
    for phrase in ('report-period-form','report-goals-edit','report-goals-dialog','So sánh KPI','125%','5 điểm phần trăm','Mục tiêu bằng 0'):
        assert phrase in response.text
    assert 'NEVER_FORWARD' not in response.text


def test_viewer_can_see_comparisons_but_not_mutation_controls(stack):
    client,_,state,_=stack;prepare(state);controls(state['source_data'],manage=False)
    response=client.get('/workspace/reports/data?source=ga4')
    assert response.status_code==200
    assert 'So sánh KPI' in response.text and '125%' in response.text
    assert 'id="report-goals-edit"' not in response.text and 'id="report-sync"' not in response.text


@pytest.mark.parametrize('query',['start=2026-10-01','end=2026-10-02','start=2026-02-30&end=2026-03-01',
    'start=2026-01-01&end=2026-04-01','start=2026-10-01&end=2026-10-02&snapshot='+'e'*32,
    'start=2026-10-01&start=2026-10-02&end=2026-10-03'])
def test_invalid_ranges_fail_before_backend_transport(stack,query):
    client,calls,state,_=stack;prepare(state)
    before=len(calls)
    assert client.get('/api/customer/workspaces/'+'a'*32+'/data/ga4?'+query).status_code==422
    assert len(calls)==before


@pytest.mark.parametrize('field,value',[('asset_id','f'*32),('start','2026-10-02'),('can_manage',False)])
def test_goals_scope_and_permission_are_allowlisted(field,value):
    from test_customer_data import report
    payload=controls(report());payload['targets'][field]=value
    if field=='can_manage':
        assert not project(payload,'a'*32)['targets']['can_manage']
    else:
        with pytest.raises(CustomerError):project(payload,'a'*32)


@pytest.mark.parametrize('change',[{'unit':'currency'},{'key':'unknown'},{'input_value':'25'},
    {'actual':True},{'status':{}},{'value':'-1'},{'key':[]}])
def test_malformed_or_mislabeled_plan_cannot_reach_the_browser(change):
    from test_customer_data import report
    payload=controls(report());payload['targets']['items'][0].update(change)
    with pytest.raises(CustomerError):project(payload,'a'*32)


def test_plan_write_reuses_csrf_and_does_not_forward_private_response_fields(stack):
    client,calls,state,_=stack;prepare(state)
    path='/api/customer/workspaces/'+'a'*32+'/targets/ga4'
    body={'client_id':'b'*32,'asset_id':'c'*32,'start':'2026-11-01','end':'2026-11-30','items':[]}
    before=len(calls)
    assert client.post(path,json=body).status_code==403 and len(calls)==before
    response=client.post(path,json=body,headers=csrf_headers(client))
    assert response.status_code==200 and set(response.json())=={'message'}
    assert calls[-1].method=='POST' and calls[-1].url.path.endswith('/targets/ga4')
    assert client.post(path.replace('/ga4','/unknown'),json=body,headers=csrf_headers(client)).status_code==404


def test_open_period_retains_monthly_goal_and_shows_data_through_date(stack):
    client,_,state,_=stack;prepare(state);data=controls(state['source_data'])
    data['period'].update(start='2026-10-01',end='2026-10-31',data_end='2026-10-02',is_open=True)
    data['calendar'].update(today='2026-10-03',latest_closed_date='2026-10-02')
    data['targets']['end']='2026-10-31'
    response=client.get('/workspace/reports/data?source=ga4')
    assert response.status_code==200,response.text
    assert '01/10/2026 – 31/10/2026' in response.text
    assert 'mục tiêu cả kỳ' in response.text and '02/10/2026' in response.text
