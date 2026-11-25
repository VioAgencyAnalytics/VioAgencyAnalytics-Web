"""Publication layouts must preserve the saved facts, scope and metric meaning."""
from copy import deepcopy

import pytest

from app.customer_report_layouts import build_layout, distribution
from app.customer_comparisons import metric_change
from test_customer_auth import stack
from test_customer_data import prepare, report


SPECS = {
    'ga4': [('active_users','count'),('sessions','count'),('page_views','count'),('engagement_rate','percent')],
    'gsc': [('clicks','count'),('impressions','count'),('ctr','percent'),('position','number')],
    'facebook_ads': [('spend','currency'),('impressions','count'),('clicks','count'),('leads','count'),('ctr','percent'),('cpc','currency'),('cost_per_result','currency')],
    'google_ads': [('spend','currency'),('impressions','count'),('clicks','count'),('conversions','number'),('ctr','percent'),('cpc','currency')],
    'tiktok_ads': [('spend','currency'),('impressions','count'),('clicks','count'),('conversions','number'),('ctr','percent'),('cpc','currency')],
    'youtube': [('views','count'),('watch_minutes','number'),('subscribers_gained','count'),('average_view_seconds','number')],
    'business_profile': [('website_clicks','count'),('call_clicks','count'),('directions','count'),('search_mobile','count'),('maps_mobile','count')],
    'instagram': [('posts_published','count'),('likes_lifetime','count'),('comments_lifetime','count'),('followers','count')],
}


def platform_report(source):
    value = report(source)
    specs = [{'key': key, 'label': key, 'unit': unit, 'field': 'totals.'+key,
              'aggregation': 'sum_posts_at_fetch' if key.endswith('_lifetime') else 'latest_observation' if key == 'followers' else 'provider_period',
              'grain': 'snapshot' if key.endswith('_lifetime') or key == 'followers' else 'period'} for key,unit in SPECS[source]]
    value['connector']['metrics'] = specs
    value['metrics'] = [{**item,'value':None if index == 0 else 0 if index == 1 else .25 if item['unit'] == 'percent' else '9007199254740993.25' if item['unit'] == 'currency' else 12,
                         'status':'no_data' if index == 0 else 'available','currency':'USD' if item['unit'] == 'currency' else None} for index,item in enumerate(specs)]
    value['daily'] = [{'date':'2026-10-01','values':{item['key']:item['value'] for item in value['metrics'] if item['grain'] != 'snapshot'}}]
    value['snapshot']['currency'] = 'USD'
    value['tables'] = []
    return value


@pytest.mark.parametrize('source',SPECS)
def test_specific_composition_keeps_every_source_metric_exact_and_never_writes(stack,source):
    client,calls,state,_ = stack
    prepare(state)
    state['source_data'] = platform_report(source)
    before = deepcopy(state['source_data'])
    offset = len(calls)
    response = client.get('/workspace/reports/data?source='+source)
    assert response.status_code == 200,response.text
    assert 'data-report-layout="'+build_layout(before)['id']+'"' in response.text
    for item in before['metrics']:
        assert 'data-metric="'+item['key']+'"' in response.text or item['key'] in ('impressions','clicks','ctr') and source == 'google_ads'
    assert 'NEVER_FORWARD' not in response.text and '<script>inert</script>' not in response.text
    assert all(call.method == 'GET' for call in calls[offset:])
    assert state['source_data'] == before


def test_ranked_rows_include_zero_exclude_unknown_and_do_not_turn_dimensions_into_totals():
    data = platform_report('ga4')
    data['tables'] = [{'id':'channels','columns':[{'key':'sessions','unit':'count'}], 'total_rows':300,
        'rows':[{'sessionDefaultChannelGroup':'Unknown','sessions':None},
                {'sessionDefaultChannelGroup':'Zero','sessions':0},
                {'sessionDefaultChannelGroup':'Known','sessions':7}]}]
    before = deepcopy(data)
    layout = build_layout(data)
    rows = layout['rankings']['channels']
    assert [(row['label'],row['value']) for row in rows['rows']] == [('Known',7),('Zero',0)]
    assert rows['missing'] == 1 and rows['loaded'] == 3 and rows['total'] == 300
    assert layout['by_key']['sessions']['value'] == 0 and data == before


def test_distribution_uses_only_loaded_rows_and_refuses_unknown_denominators():
    data = platform_report('ga4')
    data['tables'] = [{'id':'channels', 'total_rows':300,
        'rows':[{'sessionDefaultChannelGroup':'Search','sessions':7},
                {'sessionDefaultChannelGroup':'Direct','sessions':0}]}]
    before = deepcopy(data)
    result = distribution(data)
    assert [row['value'] for row in result['rows']] == [7, 0]
    assert '2 hàng đã tải / 300 hàng nguồn' in result['note']
    assert data == before
    data['tables'][0]['rows'][1]['sessions'] = None
    assert distribution(data)['rows'] == []


def test_campaign_distribution_groups_exact_decimal_cost_within_the_loaded_subset():
    data = platform_report('facebook_ads')
    data['tables'] = [{'id':'campaigns', 'total_rows':3,
        'rows':[{'campaign_name':'A','spend_decimal':'9007199254740993.00'},
                {'campaign_name':'A','spend_decimal':'0.25'},
                {'campaign_name':'B','spend_decimal':'0.00'}]}]
    result = distribution(data)
    assert result['unit'] == 'currency'
    assert result['rows'][0] == {'label':'A','value':'9007199254740993.25'}
    assert data['metrics'][0]['value'] is None


def test_video_links_cannot_use_arbitrary_urls_and_missing_watch_time_stays_missing():
    data = platform_report('youtube')
    data['tables'] = [{'id':'videos','columns':[{'key':'views','unit':'count'}],'total_rows':2,
        'rows':[{'video':'AbCdEf123_-','views':0,'watch_minutes':None}, {'video':'javascript:alert(1)','views':1}]}]
    rows = build_layout(data)['rankings']['videos']['rows']
    assert rows[0]['url'] is None
    assert rows[1]['url'] == 'https://www.youtube.com/watch?v=AbCdEf123_-'
    assert rows[1]['row']['watch_minutes'] is None


def test_currency_comparison_visualization_keeps_decimal_difference_and_zero_baselines():
    spec = {'key':'spend','label':'Chi phí','unit':'currency','grain':'day','aggregation':'decimal_sum'}
    point = lambda value,currency='USD': {**spec,'value':value,'currency':currency}
    change = metric_change(spec,point('9007199254740993.25'),point('9007199254740993.00'))
    assert change['difference'] == '0.25' and change['difference_label'] == '0,25 USD'
    zero = metric_change(spec,point('0'),point('0'))
    assert zero['chart'] == {'actual':0,'previous':0} and zero['relative'] is None
    mismatch = metric_change(spec,point('1'),point('1','VND'))
    assert mismatch['chart'] is None and mismatch['status'] == 'currency_mismatch'
    unknown = metric_change(spec,point(None),point('1'))
    assert unknown['chart'] is None and unknown['previous'] == '1'
