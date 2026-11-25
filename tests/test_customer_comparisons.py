"""Calendar boundaries, saved-data comparison and tenant/metric invariants."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from starlette.datastructures import QueryParams

from app.customer_auth import CustomerError
from app.customer_comparisons import parameters, resolve, metric_change, attach, organic_sessions_metric
from test_customer_auth import stack
from test_customer_data import prepare, report
from test_customer_reporting_controls import controls


def period(start, end, *, through=None):
    return {'start': start, 'end': end, 'data_start': start, 'data_end': through or end,
            'is_open': through is not None, 'mode': 'custom'}


@pytest.mark.parametrize('chosen,mode,expected', [
    (period('2026-11-01','2026-11-30'), 'previous_month', ('2026-10-01','2026-10-31')),
    (period('2026-03-01','2026-03-31'), 'previous_month', ('2026-02-01','2026-02-28')),
    (period('2024-03-01','2024-03-31'), 'previous_month', ('2024-02-01','2024-02-29')),
    (period('2024-02-01','2024-02-29'), 'previous_month', ('2024-01-01','2024-01-31')),
    (period('2026-01-01','2026-01-31'), 'previous_month', ('2025-12-01','2025-12-31')),
    (period('2026-11-01','2026-11-30', through='2026-11-10'), 'previous_month', ('2026-10-01','2026-10-10')),
    (period('2026-11-01','2026-11-30', through='2026-11-10'), 'previous', ('2026-10-22','2026-10-31')),
    (period('2026-11-05','2026-11-11'), 'previous', ('2026-10-29','2026-11-04')),
    (period('2026-11-05','2026-11-11'), 'previous_month', ('2026-10-05','2026-10-11')),
    (period('2026-03-29','2026-03-31'), 'previous_month', ('2026-02-28','2026-02-28')),
    (period('2026-11-01','2026-11-01'), 'previous', ('2026-10-31','2026-10-31')),
])
def test_calendar_windows(chosen, mode, expected):
    assert resolve(chosen, mode) == dict(zip(('start','end'), expected))


def test_custom_windows_can_be_distant_but_each_window_is_at_most_ninety_days():
    value = period('2026-11-01','2026-11-30')
    assert resolve(value, 'custom', {'start':'2025-01-01','end':'2025-03-31'}) == {'start':'2025-01-01','end':'2025-03-31'}
    with pytest.raises(CustomerError):
        resolve(value, 'custom', {'start':'2025-01-01','end':'2025-04-01'})
    with pytest.raises(CustomerError):
        resolve(period('0001-01-01','0001-01-01'), 'previous')
    assert resolve({**value, 'data_start':None, 'data_end':None}, 'previous') is None


@pytest.mark.parametrize('query', [
    'comparison=custom', 'comparison=year',
    'comparison=custom&comparison_start=2026-02-30&comparison_end=2026-03-01',
    'comparison=previous&comparison_start=2026-10-01&comparison_end=2026-10-31',
    'comparison=custom&comparison_start=2026-10-31&comparison_end=2026-10-01',
    'comparison=custom&comparison_start=2026-01-01&comparison_end=2026-04-01',
])
def test_invalid_comparison_input(query):
    with pytest.raises(CustomerError):
        parameters(QueryParams(query))


def metric(value, unit='count', grain='period', currency=None):
    return {'key':'test','label':'Chỉ số','unit':unit,'grain':grain,'aggregation':'provider_period',
            'value':value,'currency':currency}


def test_zero_missing_decimal_money_rates_and_stock_are_not_misrepresented():
    current = metric('9007199254740993.25','currency',currency='USD')
    earlier = metric('9007199254740992.25','currency',currency='USD')
    assert metric_change(current,current,earlier)['difference'] == '1.00'
    zero = metric_change(metric(5),metric(5),metric(0))
    assert zero['relative'] is None and 'bằng 0' in zero['summary']
    assert metric_change(metric(0),metric(0),metric(0))['summary'] == 'Không thay đổi'
    assert metric_change(metric(None),metric(None),metric(5))['status'] == 'no_data'
    rate = metric_change(metric(.25,'percent'),metric(.25,'percent'),metric(.20,'percent'))
    assert rate['summary'] == '+5 điểm phần trăm'
    assert metric_change(metric(8,grain='snapshot'),metric(8,grain='snapshot'),metric(4,grain='snapshot'))['status'] == 'not_comparable'
    assert metric_change(current,current,metric('4','currency',currency='EUR'))['status'] == 'currency_mismatch'
    assert metric_change(metric(8),metric(8),metric(4,'percent'))['status'] == 'not_comparable'


def test_organic_comparison_uses_its_own_channel_and_preserves_missing_zero_and_lower_position():
    data = {'snapshot': {'id': 'a' * 32}, 'tables': [{'id': 'channels', 'rows': [
        {'sessionDefaultChannelGroup': 'Direct', 'sessions': 1000},
        {'sessionDefaultChannelGroup': 'Organic Search', 'sessions': 0}]}]}
    zero = organic_sessions_metric(data)
    assert zero['value'] == 0
    data['tables'][0]['rows'][1]['sessions'] = 50
    actual = organic_sessions_metric(data)
    change = metric_change(actual, actual, zero)
    assert change['actual'] == 50 and change['previous'] == 0 and change['relative'] is None
    assert change['effect'] == 'improved'
    data['tables'][0]['rows'].pop()
    assert organic_sessions_metric(data)['value'] is None
    data['tables'][0]['rows'] = [
        {'sessionDefaultChannelGroup': 'Organic Search', 'sessions': 3},
        {'sessionDefaultChannelGroup': 'Organic Search', 'sessions': 5}]
    assert organic_sessions_metric(data)['value'] is None
    position = {**metric(3, 'number'), 'key': 'position'}
    change = metric_change(position, position, {**position, 'value': 5})
    assert change['effect'] == 'improved' and change['summary'] == '−2 vị trí'


def prior_data():
    data = controls(report())
    data['snapshot'].update(id='f'*32,start_date='2026-09-29',end_date='2026-09-30')
    data['period'].update(start='2026-09-29',end='2026-09-30',data_start='2026-09-29',data_end='2026-09-30')
    data['daily'][0]['date'] = '2026-09-29'
    data['targets'] = None
    return data


def test_report_comparison_is_read_only_and_renders_with_kpi_plans(stack, monkeypatch):
    client, calls, state, _ = stack
    prepare(state); controls(state['source_data'])
    baseline = prior_data(); reads = []
    async def saved_read(request, method, path):
        reads.append((method,path)); return deepcopy(baseline)
    monkeypatch.setattr('app.customer_comparisons.backend',saved_read)
    before = len(calls)
    response = client.get('/workspace/reports/data?source=ga4&comparison=previous')
    assert response.status_code == 200, response.text
    assert reads == [('GET','/workspaces/'+'a'*32+'/data/ga4?start=2026-09-29&end=2026-09-30')]
    assert all(call.method == 'GET' for call in calls[before:])
    for phrase in ('ĐỐI CHIẾU HAI KỲ','So sánh KPI','2026-09-29','điểm phần trăm','report-comparison'):
        assert phrase in response.text
    assert 'NEVER_FORWARD' not in response.text


@pytest.mark.parametrize('mutation', ['asset','connection','version','timezone','period'])
def test_foreign_asset_changed_generation_timezone_or_wrong_period_cannot_be_compared(stack,monkeypatch,mutation):
    client,_,state,_ = stack; prepare(state); controls(state['source_data'])
    baseline = prior_data()
    if mutation == 'asset': baseline['asset']['id'] = '9'*32
    if mutation == 'connection': baseline['connection']['id'] = '8'*32
    if mutation == 'version': baseline['connection']['version'] = 2
    if mutation == 'timezone': baseline['snapshot']['timezone'] = 'UTC'
    if mutation == 'period':
        baseline = controls(report()); baseline['targets'] = None
    async def saved_read(*args): return deepcopy(baseline)
    monkeypatch.setattr('app.customer_comparisons.backend',saved_read)
    response = client.get('/api/customer/workspaces/'+'a'*32+'/data/ga4?comparison=previous')
    assert response.status_code == (502 if mutation == 'period' else 409), response.text


def test_missing_baseline_preserves_current_data_and_never_turns_it_into_zero(stack,monkeypatch):
    client,_,state,_ = stack; prepare(state); controls(state['source_data'])
    async def unavailable(*args): raise CustomerError(503,'Unavailable','backend_unavailable')
    monkeypatch.setattr('app.customer_comparisons.backend',unavailable)
    response = client.get('/api/customer/workspaces/'+'a'*32+'/data/ga4?comparison=previous')
    assert response.status_code == 200
    assert response.json()['metrics'][0]['value'] == 3
    assert response.json()['metrics'][2]['value'] is None
    assert response.json()['comparison']['status'] == 'unavailable'


def test_comparison_exposes_the_pending_job_for_polling_without_queueing_it(stack, monkeypatch):
    client, _, state, _ = stack
    prepare(state); controls(state['source_data'])
    baseline = prior_data()
    baseline.update(snapshot=None, state='empty', latest_sync={
        'id': '9' * 32, 'status': 'running', 'start_date': '2026-09-29', 'end_date': '2026-09-30',
        'created_at': '2026-10-01T00:00:00Z', 'finished_at': None, 'error_code': None})
    for row in baseline['metrics']:
        row.update(value=None, status='no_data')
    reads = []
    async def saved_read(request, method, path):
        reads.append(method)
        return deepcopy(baseline)
    monkeypatch.setattr('app.customer_comparisons.backend', saved_read)
    result = client.get('/api/customer/workspaces/' + 'a' * 32 + '/data/ga4?comparison=previous')
    assert result.status_code == 200, result.text
    comparison = result.json()['comparison']
    assert comparison['status'] == 'syncing'
    assert comparison['latest_sync']['status'] == 'running'
    assert reads == ['GET']


def test_available_baseline_is_reused_when_current_window_is_missing(stack, monkeypatch):
    client, _, state, _ = stack
    prepare(state); controls(state['source_data'])
    current = state['source_data']
    current.update(snapshot=None, state='empty', targets=None)
    for item in current['metrics']:
        item.update(value=None, status='no_data')
    baseline = prior_data()
    async def saved_read(*args): return deepcopy(baseline)
    monkeypatch.setattr('app.customer_comparisons.backend', saved_read)
    response = client.get('/api/customer/workspaces/' + 'a' * 32 + '/data/ga4?comparison=previous')
    assert response.status_code == 200, response.text
    comparison = response.json()['comparison']
    assert comparison['status'] == 'no_current_data' and comparison['snapshot']['id'] == 'f' * 32
    assert comparison['items'][0]['actual'] is None and comparison['items'][0]['previous'] == 3
    assert comparison['items'][0]['relative'] is None


def test_viewer_can_read_period_comparison_but_cannot_queue_sync(stack,monkeypatch):
    client,_,state,_ = stack; prepare(state); controls(state['source_data'],manage=False)
    baseline = prior_data(); baseline.update(snapshot=None,state='empty',metrics=[])
    # A valid missing snapshot DTO still retains the source asset and period.
    async def saved_read(*args):
        data = prior_data(); data['snapshot']=None; data['state']='empty';
        for row in data['metrics']: row.update(value=None,status='no_data')
        return data
    monkeypatch.setattr('app.customer_comparisons.backend',saved_read)
    response = client.get('/workspace/reports/data?source=ga4&comparison=previous')
    assert response.status_code == 200, response.text
    assert 'Chưa có bản lưu đúng kỳ đối chiếu' in response.text
    assert 'id="report-sync-comparison"' not in response.text


def test_future_custom_comparison_is_rejected_without_reading_baseline(monkeypatch):
    current=controls(report())
    request=SimpleNamespace(query_params=QueryParams('comparison=custom&comparison_start=2026-11-01&comparison_end=2026-11-30'))
    async def forbidden(*args): raise AssertionError('Should not read baseline')
    monkeypatch.setattr('app.customer_comparisons.backend',forbidden)
    with pytest.raises(CustomerError): asyncio.run(attach(request,current,'/saved',lambda *args:None))


def test_auto_month_shift_over_limit_keeps_current_report_and_does_not_request_ninety_one_days(monkeypatch):
    current=controls(report())
    current['period']=period('2026-02-01','2026-05-01')
    request=SimpleNamespace(query_params=QueryParams('comparison=previous_month'))
    async def forbidden(*args): raise AssertionError('Must not request a 91-day baseline')
    monkeypatch.setattr('app.customer_comparisons.backend',forbidden)
    asyncio.run(attach(request,current,'/saved',lambda *args:None))
    assert current['metrics'][0]['value']==3
    assert current['comparison']['status']=='unavailable'
    assert '90 ngày' in current['comparison']['message']
