"""Dashboard facts retain source, period, money, stock and tenant semantics."""
from copy import deepcopy
import pytest

from test_customer_auth import stack
from test_customer_data import prepare, report
from app.customer_analytics import compose, group_points, FOCUS


def source_data(source='ga4'):
    data=report(source)
    names=FOCUS[source]
    for spec,key in zip(data['connector']['metrics'],names):spec['key']=key;spec['label']=key
    for spec,item in zip(data['connector']['metrics'],data['metrics']):item['key']=spec['key'];item['label']=spec['label']
    data['daily']=[{'date':'2026-10-01','values':{names[0]:3,names[1]:0,names[2]:None,names[3]:.25}}]
    data['period']={'start':'2026-10-01','end':'2026-10-02','data_start':'2026-10-01','data_end':'2026-10-02','is_open':False,'mode':'latest'}
    data['targets']={'asset_id':data['asset']['id'],'start':data['period']['start'],'end':data['period']['end'],
                     'can_manage':False,'updated_at':None,'items':[]}
    return data


def state_setup(state):
    prepare(state)
    state['source_data']=source_data()
    for row in state['data_index']['sources']:
        if row['source']=='ga4':row.update(deepcopy(state['source_data']))
        else:row.update(state='not_connected',snapshot=None,asset=None,metrics=[])


def test_analytics_auth_host_scope_and_provider_free_composition(stack):
    client,calls,state,_=stack;path='/api/customer/workspaces/'+'a'*32+'/analytics'
    assert client.get(path).status_code==401
    state_setup(state);before=len(calls)
    response=client.get(path)
    assert response.status_code==200,response.text
    data=response.json()
    assert data['focus']=='ga4' and data['metrics']['spend']['label']=='active_users'
    assert data['metrics']['spend']['value']==3 and data['metrics']['impressions']['value']==0
    assert data['metrics']['clicks']['value'] is None
    assert data['trends']['spend']['points']==[{'date':'2026-10-01','value':3},{'date':'2026-10-02','value':None}]
    assert data['reports'][0]['status']=='saved' and 'snapshot='+'e'*32 in data['reports'][0]['href']
    assert data['report_href']=='/workspace/reports/data?source=ga4&snapshot='+'e'*32
    assert all(call.method=='GET' for call in calls[before:])
    assert not any('/providers/' in call.url.path or '/connections/' in call.url.path for call in calls[before:])
    assert 'NEVER_FORWARD' not in response.text and 'no-store' in response.headers['cache-control']
    assert client.get(path,headers={'Host':'evil.test'}).status_code==400
    state['selected_client']={'id':'f'*32,'name':'Foreign'}
    assert client.get(path).status_code==409


@pytest.mark.parametrize('query',['source=unknown','source=ga4&source=gsc','start=2026-10-01','start=2026-01-01&end=2026-04-01','source=all&client_id=foreign','granularity=year'])
def test_ambiguous_dashboard_filters_fail_before_transport(stack,query):
    client,calls,state,_=stack;state_setup(state);before=len(calls)
    assert client.get('/api/customer/workspaces/'+'a'*32+'/analytics?'+query).status_code==422
    assert len(calls)==before


def test_backend_wrong_period_never_appears_under_custom_dates(stack):
    client,_,state,_=stack;state_setup(state)
    response=client.get('/api/customer/workspaces/'+'a'*32+'/analytics?source=ga4&start=2026-09-01&end=2026-09-30')
    assert response.status_code==502 and response.json()['code']=='snapshot_scope'


def test_native_content_slots_do_not_become_ad_spend_or_growth():
    data=source_data('facebook_content');data['source']='facebook_content'
    for row in data['connector']['metrics'][1:]:row.update(grain='snapshot',aggregation='sum_posts_at_fetch',unit='count')
    for row in data['metrics'][1:]:row.update(grain='snapshot',aggregation='sum_posts_at_fetch',unit='count')
    earlier=deepcopy(data);earlier['metrics'][1]['value']=7
    index={'scope':data['scope'],'sources':[data]};catalogue={'connections':[]}
    result=compose(index,catalogue,data,earlier)
    assert result['metrics']['spend']['key']=='posts_published'
    assert result['metrics']['impressions']['key']=='reactions_lifetime'
    assert result['metrics']['impressions']['previous'] is None
    assert result['trends']['impressions']['points']==[]


def test_money_stays_exact_and_source_totals_do_not_merge_currencies_or_periods():
    one=source_data('google_ads');one['metrics'][0].update(value='9007199254740993.25',unit='currency',currency='USD')
    one['connector']['metrics'][0].update(unit='currency',aggregation='decimal_sum')
    one['daily'][0]['values']['spend']='9007199254740993.25'
    two=deepcopy(one);two['source']='facebook_ads';two['metrics'][0]['currency']='EUR';two['metrics'][0]['value']='50'
    result=compose({'scope':one['scope'],'sources':[one,two]},{'connections':[]},one)
    assert result['metrics']['spend']['value']=='9007199254740993.25' and result['metrics']['spend']['currency']=='USD'
    assert result['sources'][1]['metrics'][0]['value']=='50'
    assert result['trends']['spend']['points'][0]['value']=='9007199254740993.25'


def test_grouping_never_sums_unique_users_or_averages_ratios_or_treats_missing_as_zero():
    points=[{'date':'2026-10-01','value':'9007199254740993.25'},{'date':'2026-10-02','value':'0.75'}]
    assert group_points(points,{'aggregation':'decimal_sum','unit':'currency'},'week')[0]['value']=='9007199254740994.00'
    assert group_points(points,{'aggregation':'provider_period','unit':'count'},'month')==[]
    assert group_points(points,{'aggregation':'clicks/impressions','unit':'percent'},'week')==[]
    points[1]['value']=None
    assert group_points(points,{'aggregation':'decimal_sum','unit':'currency'},'week')[0]['value'] is None
