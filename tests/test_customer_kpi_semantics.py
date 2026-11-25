"""KPI interpretation stays consistent across live, dashboard and frozen reports."""
from copy import deepcopy

import pytest

from app.customer_comparisons import metric_change
from app.customer_metric_semantics import goal_assessment
from app.customer_seo_reports import prepare
from test_customer_comparisons import metric
from test_customer_reporting_controls import controls
from test_customer_data import report
from test_customer_auth import stack


@pytest.mark.parametrize('key,current,previous,effect', [
    ('cpc','12','20','improved'), ('cpc','20','12','declined'),
    ('position',4,8,'improved'), ('position',8,4,'declined'),
    ('clicks',200,100,'improved'), ('clicks',100,200,'declined'),
    ('spend','200','100','context'), ('spend','100','200','context'),
    ('conversions',0,0,'unchanged'),
])
def test_numeric_increase_is_not_automatically_improvement(key,current,previous,effect):
    unit='currency' if isinstance(current,str) else 'count'
    a,b=metric(current,unit,currency='VND' if unit=='currency' else None),metric(previous,unit,currency='VND' if unit=='currency' else None)
    a['key']=b['key']=key
    result=metric_change(a,a,b)
    assert result['effect']==effect
    assert result['actual']==current and result['previous']==previous


def test_absolute_percent_points_and_relative_growth_remain_distinct():
    a,b=metric(.25,'percent'),metric(.20,'percent')
    result=metric_change(a,a,b)
    assert result['summary']=='+5 điểm phần trăm' and result['relative']=='0.25'
    result=metric_change(metric(5),metric(5),metric(0))
    assert result['relative'] is None and 'bằng 0' in result['summary']


def test_open_goal_is_provisional_and_zero_is_not_a_missing_target():
    assert goal_assessment('below_target',True)=={'label':'Đang thực hiện','tone':'in_progress','provisional':True}
    assert goal_assessment('within_limit',True)['label']=='Trong giới hạn hiện tại'
    assert goal_assessment('met',True)['label']=='Đạt đến hiện tại'
    assert goal_assessment('below_target',False)['label']=='Chưa đạt'


def test_frozen_comparisons_preserve_large_decimal_differences_and_exclude_lifetime_growth():
    data=controls(report());old=deepcopy(data)
    data['metrics'][0].update(value='9007199254740993123456789012346.25',unit='currency',currency='USD')
    old['metrics'][0].update(value='9007199254740993123456789012345.25',unit='currency',currency='USD')
    data['metrics'][1].update(value=30,grain='snapshot');old['metrics'][1].update(value=10,grain='snapshot')
    result=prepare({'sources':[{'id':'ga4','data':data,'previous':old}]})['sources'][0]
    assert result['comparisons'][0]['difference']=='1,00 USD'
    assert all(row['label']!=data['metrics'][1]['label'] for row in result['comparisons'])


@pytest.mark.parametrize('change',['asset','scope','connection','timezone','definition'])
def test_frozen_reports_never_compare_incompatible_assets_or_metric_definitions(change):
    data=controls(report());old=deepcopy(data)
    if change=='asset':old['asset']['id']='f'*32
    if change=='scope':old['scope']['client_id']='f'*32
    if change=='connection':old['connection']['version']+=1
    if change=='timezone':old['snapshot']['timezone']='UTC'
    if change=='definition':
        for row in old['metrics']:row['aggregation']='other_definition'
    result=prepare({'sections':['comparison'],'sources':[{'id':'ga4','data':data,'previous':old}]})['sources'][0]
    assert result['comparisons']==[]
    if result['chart']:assert result['chart']['previous']==[]


def test_open_period_uses_provisional_goal_labels_in_the_actual_template(stack):
    from test_customer_data import prepare as setup
    client,_,state,_=stack;setup(state);data=controls(state['source_data'])
    data['calendar'].update(today='2026-10-03',latest_closed_date='2026-10-02')
    data['period'].update(end='2026-10-31',is_open=True)
    data['targets']['end']='2026-10-31'
    response=client.get('/workspace/reports/data?source=ga4')
    assert response.status_code==200,response.text
    assert 'Đạt đến hiện tại' in response.text
    assert 'Mục tiêu bằng 0' in response.text
