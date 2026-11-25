"""SEO BFF boundaries and frozen multi-source report rendering."""
from copy import deepcopy
from types import SimpleNamespace
import json

import httpx
import pytest

from test_customer_auth import stack, csrf_headers
from test_customer_data import prepare, report
from test_customer_reporting_controls import controls
import app.customer_seo as seo
from app.customer_seo_reports import prepare as prepare_report

REAL_CLIENT = httpx.AsyncClient
WORKSPACE, CLIENT, RECORD = 'a' * 32, 'b' * 32, 'f' * 32


def rank_data():
    return {'schema_version': 1, 'scope': {'workspace_id': WORKSPACE, 'client_id': CLIENT},
        'client': {'id': CLIENT, 'name': 'Khách hàng'}, 'website': 'https://example.test',
        'period': {'start': '2026-10-01', 'end': '2026-10-02'},
        'comparison': {'start': '2026-09-29', 'end': '2026-09-30'},
        'keywords': [{'id': '1' * 32, 'keyword': '<script>inert</script>', 'topic': 'Nhóm', 'role': 'secondary',
                      'committed': 1, 'version': 1, 'rank': None, 'previous_period_rank': 8, 'change': None,
                      'observed_date': '2026-10-01', 'url': 'https://example.test/a', 'state': 'unknown', 'source_previous_rank': 42}],
        'stats': {'total': 1, 'ranked': 0, 'top10': 0, 'unknown': 1}, 'distribution': [{'label': 'Chưa có vị trí', 'count': 1}],
        'plan': {'month': '2026-10', 'version': 1, 'keyword_count': 1, 'required': 1, 'top10': 0,
                 'top10_percent': 50, 'measured': 0, 'status': 'insufficient_data'},
        'work': [], 'notes': ['Ô trống chưa xác định.'], 'profile': '', 'profiles': [], 'imports': [], 'import_ids': [],
        'permissions': {'edit': False, 'create_report': False}}


@pytest.fixture
def seo_stack(stack, monkeypatch):
    client, calls, state, settings = stack
    prepare(state)
    state['workspace'].update(timezone='Asia/Ho_Chi_Minh',kind='agency',currency='VND')
    state['selected_client']['website']='https://example.test'
    client.cookies.set('vio_customer_session','opaque-test-session')
    data = rank_data()
    provider = controls(report())
    saved = {'id': RECORD, 'scope': data['scope'], 'name': 'SEO <script>inert</script>', 'client': {'id': CLIENT, 'name': 'Khách hàng'},
        'workspace': {'id': WORKSPACE, 'name': 'VIO', 'timezone': 'Asia/Ho_Chi_Minh'},
        'period': data['period'], 'comparison': data['comparison'], 'created_at': '2026-11-12T00:00:00Z',
        'sources': [{'id': 'seo', 'name': 'SEO & Từ khóa', 'data': data, 'previous': None},
                    {'id': 'ga4', 'name': 'GA4', 'data': provider, 'previous': None}],
        'sections': ['summary', 'comparison', 'kpi', 'details', 'charts', 'seo_work']}
    requests = []
    async def backend(request, method, path, body=None):
        requests.append((method, path, body))
        if path == '/session': return {'user': {'id': 'user1', 'name': 'User', 'email': 'user@example.test'}, 'workspace': state['workspace'], 'workspaces': []}
        if path == '/workspaces/' + WORKSPACE: return {'workspace': state['workspace'], 'clients': state['clients'], 'selected_client': state['selected_client']}
        if '/compiled-reports/' in path: return deepcopy(saved)
        if path.endswith('/compiled-reports'): return {'id': RECORD, 'message': 'Đã lưu'} if method == 'POST' else {'scope': data['scope'], 'reports': [], 'permissions': {'create': False}}
        return deepcopy(data) if method == 'GET' else {'message': 'OK'}
    monkeypatch.setattr(seo, 'backend', backend)
    return client, requests, data, saved, state


def test_new_pages_require_customer_session_in_production(stack):
    client, _, _, _ = stack
    for path in ('/workspace/seo', '/workspace/reports/combined'):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303 and response.headers['location'] == '/workspace/login'


def test_seo_shell_and_combined_builder_use_existing_navigation(seo_stack):
    client, requests, _, _, _ = seo_stack
    response = client.get('/workspace/seo')
    assert response.status_code == 200, response.text
    for name in ('seo-panel-keywords', 'seo-panel-kpi', 'seo-panel-work', 'seo-upload-form', 'seo-common.js', '/workspace/seo'):
        assert name in response.text
    assert 'customer/library.js' not in response.text and 'customer/channels.js' not in response.text
    builder = client.get('/workspace/reports/combined')
    assert builder.status_code == 200, builder.text
    assert 'compiled-builder-form' in builder.text and 'compiled-source' in builder.text
    assert 'customer/reports.js' not in builder.text
    assert all(method == 'GET' for method, _, _ in requests)


def test_scope_projection_preserves_unknown_and_rejects_cross_tenant(seo_stack):
    client, _, data, _, _ = seo_stack
    response = client.get('/api/customer/workspaces/' + WORKSPACE + '/seo')
    assert response.status_code == 200 and response.json()['keywords'][0]['rank'] is None
    data['scope']['workspace_id'] = 'c' * 32
    assert client.get('/api/customer/workspaces/' + WORKSPACE + '/seo').status_code == 502


def test_combined_kpi_preserves_each_currency_and_shows_the_same_gap(seo_stack):
    from bs4 import BeautifulSoup

    client, _, _, saved, _ = seo_stack
    data = controls(report('google_ads'))
    data['snapshot']['currency'] = 'USD'
    spend = {'key':'spend','label':'Chi phí','unit':'currency','field':'totals.spend','aggregation':'decimal_sum','grain':'day'}
    data['connector']['metrics'].append(spend)
    data['metrics'].append({**spend, 'value':'150', 'status':'available', 'currency':'USD'})
    data['targets']['items'].append({'key':'spend','unit':'currency','direction':'at_most','version':1,
        'value':'100','input_value':'100','currency':'EUR','actual':'150','status':'currency_mismatch',
        'ratio':None,'difference':None,'relation':None})
    saved['sources'] = [{'id':'google_ads','name':'Google Ads','data':data,'previous':None}]
    saved['sections'] = ['kpi']
    response=client.get('/workspace/reports/combined?report='+RECORD)
    assert response.status_code==200,response.text
    rows=BeautifulSoup(response.text,'html.parser').select('#chapter-google_ads table tbody tr')
    assert len(rows)==3
    assert [td.get_text(' ',strip=True) for td in rows[-1].select('td')] == ['Chi phí','≤ 100,00 EUR','150,00 USD','Khác tiền tệ']
    assert '125% mục tiêu' in rows[1].get_text(' ',strip=True)
    assert '5 điểm phần trăm' in rows[1].get_text(' ',strip=True)


def test_rank_overview_uses_the_same_period_and_counts_in_web_and_pdf(seo_stack):
    from bs4 import BeautifulSoup

    client, _, data, saved, _ = seo_stack
    sample = data['keywords'][0]
    ranks = [(10, 'ranked')] * 23 + [(11, 'ranked'), (30, 'ranked')] + [(None, 'unknown')] * 15
    data['keywords'] = [{**sample, 'id': f'{i:032x}', 'rank': rank, 'state': state}
                        for i, (rank, state) in enumerate(ranks, 1)]
    data['period'] = {'start': '2026-09-01', 'end': '2026-09-30'}
    saved['period'] = data['period']
    api_path = '/api/customer/workspaces/' + WORKSPACE + '/seo'
    report_path = '/workspace/reports/combined?report=' + RECORD
    overview = client.get(api_path).json()['rank_overview']
    assert overview == {
        'title': 'Báo cáo thứ hạng tháng 9/2026', 'total': 40,
        'counts': {'page1': 23, 'pages2_3': 2, 'pages4_10': 0, 'unknown': 15, 'outside': 0}
    }
    report = BeautifulSoup(client.get(report_path).text, 'html.parser')
    box = report.select_one('.seo-rank-overview')
    assert box.h3.get_text(strip=True) == overview['title']
    assert [int(node.get_text(strip=True)) for node in box.select('[data-rank-overview-count]')] == [23, 2, 0, 15, 0]
    assert box.select_one('[data-rank-overview-group=outside]').has_attr('hidden')
    assert report.select_one(box.a['href']).name == 'figure'

    data['keywords'].extend([{**sample, 'rank': 100, 'state': 'ranked'},
                             {**sample, 'rank': 101, 'state': 'ranked'},
                             {**sample, 'rank': None, 'state': 'outside_top100'}])
    data['period']['start'] = '2026-09-02'
    saved['sections'] = ['details']
    overview = client.get(api_path).json()['rank_overview']
    assert overview['title'] == 'Báo cáo thứ hạng 02/09/2026 – 30/09/2026'
    assert overview['counts'] == {'page1': 23, 'pages2_3': 2, 'pages4_10': 1, 'unknown': 15, 'outside': 2}
    box = BeautifulSoup(client.get(report_path).text, 'html.parser').select_one('.seo-rank-overview')
    assert box.a is None
    assert not box.select_one('[data-rank-overview-group=outside]').has_attr('hidden')


def test_seo_custom_comparison_is_forwarded_read_only_and_invalid_input_never_reaches_backend(seo_stack):
    client,requests,_,_,_=seo_stack
    query='start=2026-10-01&end=2026-10-31&comparison=custom&comparison_start=2026-08-01&comparison_end=2026-08-31'
    response=client.get('/api/customer/workspaces/'+WORKSPACE+'/seo?'+query)
    assert response.status_code==200,response.text
    assert requests[-1]==('GET','/workspaces/'+WORKSPACE+'/seo?'+query,None)
    before=len(requests)
    for invalid in ['comparison=custom','comparison=unknown','comparison=previous&comparison_start=2026-08-01']:
        assert client.get('/api/customer/workspaces/'+WORKSPACE+'/seo?'+invalid).status_code==422
    assert len(requests)==before


def test_writes_keep_csrf_and_json_size_boundary(seo_stack):
    client, requests, _, _, _ = seo_stack
    path = '/api/customer/workspaces/' + WORKSPACE + '/seo/plan'
    before = len(requests)
    assert client.post(path, json={}).status_code == 403
    assert len(requests) == before
    headers = csrf_headers(client)
    assert client.post(path, json={'text': 'x' * 17000}, headers=headers).status_code == 413
    assert client.post(path, json={'client_id': CLIENT}, headers=headers).status_code == 200
    assert client.post('/api/customer/workspaces/' + WORKSPACE + '/seo/anything', json={}, headers=headers).status_code == 404


def test_binary_upload_enforces_csrf_size_and_strips_credentials(seo_stack, monkeypatch):
    client, _, _, _, _ = seo_stack
    path = '/api/customer/workspaces/' + WORKSPACE + '/seo/import-preview?client_id=' + CLIENT + '&filename=rank.csv'
    assert client.post(path, content=b'file', headers={'Content-Type': 'application/octet-stream'}).status_code == 403
    headers = {**csrf_headers(client), 'Content-Type': 'application/octet-stream'}
    assert client.post(path, content=b'x' * (2 * 1024 * 1024 + 1), headers=headers).status_code == 413
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={'scope': {'workspace_id': WORKSPACE, 'client_id': CLIENT}, 'id': 'd' * 32, 'access_token': 'NEVER_FORWARD'})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: REAL_CLIENT(transport=httpx.MockTransport(handler), **kwargs))
    result = client.post(path, content=b'file', headers=headers)
    assert result.status_code == 200, result.text
    assert 'NEVER_FORWARD' not in result.text and seen[0].content == b'file'
    assert seen[0].headers['x-customer-session']


def test_frozen_report_prints_all_selected_sections_and_escapes_content(seo_stack):
    client, _, _, _, _ = seo_stack
    result = client.get('/workspace/reports/combined?report=' + RECORD)
    assert result.status_code == 200, result.text
    for phrase in ('compiled-print', 'Cam kết Top 10', 'Bản dữ liệu đã chốt', 'sr-trend', 'Chưa đủ dữ liệu nghiệm thu', 'Nguồn truy cập'):
        assert phrase in result.text
    assert '<script>inert</script>' not in result.text and '&lt;script&gt;inert&lt;/script&gt;' in result.text
    assert 'NEVER_FORWARD' not in result.text


def test_optional_sections_and_null_currency_rate_comparison(seo_stack):
    client, _, _, saved, _ = seo_stack
    saved['sections'] = ['summary']
    result = client.get('/workspace/reports/combined?report=' + RECORD)
    assert result.status_code == 200
    assert 'Thứ hạng từ khóa</h3>' not in result.text and 'sr-trend"' not in result.text
    new = controls(report()); old = deepcopy(new)
    old['metrics'][0]['value'] = 0; new['metrics'][0]['value'] = 5
    old['metrics'][3]['value'] = .2
    sample = {'sources': [{'id': 'ga4', 'data': new, 'previous': old}]}
    result = prepare_report(sample)['sources'][0]
    assert 'Mốc trước bằng 0' in result['comparisons'][0]['delta']
    assert result['comparisons'][-1]['delta'] == '+5 điểm phần trăm'
    assert 'views' not in [row['label'] for row in result['comparisons']]


def test_delivery_actions_keep_csrf_and_binary_boundaries(seo_stack, monkeypatch):
    client, requests, _, _, _ = seo_stack
    headers = csrf_headers(client)
    for action in ('content', 'project', 'content-confirm', 'keyword-from-gsc', 'website-sync', 'keywords-sync'):
        path = '/api/customer/workspaces/' + WORKSPACE + '/seo/' + action
        before = len(requests)
        assert client.post(path, json={'client_id': CLIENT}).status_code == 403
        assert len(requests) == before
        assert client.post(path, json={'client_id': CLIENT}, headers=headers).status_code == 200
    def handler(request):
        return httpx.Response(200, json={'scope': {'workspace_id': WORKSPACE, 'client_id': CLIENT}, 'id': 'd' * 32, 'access_token': 'NEVER_FORWARD'})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: REAL_CLIENT(transport=httpx.MockTransport(handler), **kwargs))
    path = '/api/customer/workspaces/' + WORKSPACE + '/seo/content-preview?client_id=' + CLIENT + '&filename=content.csv'
    response = client.post(path, content=b'csv', headers={**headers, 'Content-Type': 'application/octet-stream'})
    assert response.status_code == 200 and 'NEVER_FORWARD' not in response.text


def test_content_projection_rejects_bad_urls_and_bounds_rows(seo_stack):
    client, _, data, _, _ = seo_stack
    data['content'] = {'items': [{'title': 'Bài viết', 'url': 'javascript:alert(1)'}]}
    path = '/api/customer/workspaces/' + WORKSPACE + '/seo'
    assert client.get(path).status_code == 502
    data['content']['items'] = [{'title': 'Bài viết', 'url': 'https://example.test/a', 'draft_url': '', 'private_unused': 'drop'}]
    response = client.get(path)
    assert response.status_code == 200 and 'private_unused' not in response.text
    data['content']['items'] *= 2001
    assert client.get(path).status_code == 502


def test_article_provenance_is_allowlisted_and_gsc_roles_are_preserved(seo_stack):
    client, _, data, _, _ = seo_stack
    data['content'] = {'items':[{'title':'Website article', 'url':'https://example.test/a', 'provenance':{
        'source':'wordpress', 'fetched_at':'2026-11-16T00:00:00Z', 'internal_secret':'drop'}}]}
    data['keywords'][0].update(role_origin='gsc', role_reviewed=0)
    result = client.get('/api/customer/workspaces/' + WORKSPACE + '/seo')
    assert result.status_code == 200
    assert result.json()['keywords'][0]['role_reviewed'] == 0
    assert result.json()['content']['items'][0]['provenance']['source'] == 'wordpress'
    assert 'internal_secret' not in result.text


def test_discovery_is_read_only_scoped_and_checks_links(seo_stack, monkeypatch):
    client, requests, _, _, _ = seo_stack
    value = {'scope':{'workspace_id':WORKSPACE, 'client_id':CLIENT}, 'items':[
        {'keyword':'sàn gỗ', 'page':'https://example.test/a', 'clicks':0, 'position':None, 'internal_unused':'drop'}]}
    async def backend(request, method, path, body=None):
        requests.append((method, path, body))
        return deepcopy(value)
    monkeypatch.setattr(seo, 'backend', backend)
    path = '/api/customer/workspaces/' + WORKSPACE + '/seo/discovery?start=2026-10-01&end=2026-10-31'
    result = client.get(path)
    assert result.status_code == 200 and result.json()['items'][0]['clicks'] == 0
    assert result.json()['items'][0]['position'] is None and 'internal_unused' not in result.text
    assert requests[-1][0] == 'GET'
    before = len(requests)
    assert client.get(path + '&start=2026-10-02').status_code == 422
    assert len(requests) == before
    value['items'][0]['page'] = 'javascript:alert(1)'
    assert client.get(path).status_code == 502
    value['scope']['workspace_id'] = 'c' * 32
    assert client.get(path).status_code == 502


def test_article_metrics_projection_preserves_zero_and_rejects_malformed_evidence(seo_stack):
    client, _, data, _, _ = seo_stack
    path = '/api/customer/workspaces/' + WORKSPACE + '/seo'
    item = {'id':RECORD, 'title':'Bài viết', 'url':'https://example.test/a', 'private_unused':'drop',
            'values':{'views':0,'clicks':None,'ctr':0},'previous':{'views':None}}
    data['effectiveness'] = {'items':[deepcopy(item)]}
    result = client.get(path)
    assert result.status_code == 200
    assert result.json()['effectiveness']['items'][0]['values']['views'] == 0
    assert result.json()['effectiveness']['items'][0]['values']['clicks'] is None
    assert 'private_unused' not in result.text
    for invalid in ('javascript:alert(1)','https://person:password@example.test/a','https://[invalid','https:'):
        data['effectiveness']['items'] = [{**deepcopy(item),'url':invalid}]
        assert client.get(path).status_code == 502
    data['effectiveness'] = []
    assert client.get(path).status_code == 502
    for invalid in (True, -1, float('inf')):
        data['effectiveness'] = {'items':[{**deepcopy(item),'values':{'views':invalid}}]}
        assert client.get(path).status_code == 502


def test_report_groups_keep_niche_separate_without_duplicating_committed_words():
    current = rank_data()
    current['keywords'] = [
        {**current['keywords'][0],'id':'1'*32,'committed':1,'segment':'niche'},
        {**current['keywords'][0],'id':'2'*32,'committed':0,'segment':'niche'},
        {**current['keywords'][0],'id':'3'*32,'committed':0,'segment':'general'}]
    item = prepare_report({'sections':['summary','details'],'sources':[{'id':'seo','data':current}]})['sources'][0]
    assert [len(group['rows']) for group in item['keyword_groups']] == [1,1,1]
    ids = [row['id'] for group in item['keyword_groups'] for row in group['rows']]
    assert len(ids) == len(set(ids)) == 3
    assert not next(row for row in item['coverage'] if row['label'].startswith('GA4'))['available']


def test_discovered_keywords_show_gsc_observations_while_spineditor_rank_stays_unknown():
    current = rank_data()
    current['keywords'][0].update(keyword='từ khóa phụ', role_origin='gsc', observed_date=None, committed=0, segment='niche')
    search = {'id':'gsc','data':{'state':'ready','metrics':[],'period':current['period'],
        'tables':[{'id':'queries','rows':[{'query':'từ khóa phụ','clicks':0,'impressions':10,'ctr':0,'position':8}]}]}}
    item = prepare_report({'sections':['details'],'sources':[{'id':'seo','data':current},search]})['sources'][0]
    niche = item['keyword_groups'][1]
    assert niche['search'] is True
    assert niche['rows'][0]['search_values']['clicks'] == 0
    assert niche['rows'][0]['rank'] is None
    current['effectiveness'] = {'sources':{'gsc':{'state':'wrong_website'}}}
    item = prepare_report({'sections':['details'],'sources':[{'id':'seo','data':current},search]})['sources'][0]
    assert item['keyword_groups'][1]['search'] is False
