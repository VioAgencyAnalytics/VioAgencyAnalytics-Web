"""Compact layout retains every observation and the selected report sections."""
from copy import deepcopy

from app.customer_seo_compact import build
from app.customer_seo_reports import extra_chart
from test_customer_auth import stack
from test_customer_seo import seo_stack, RECORD


def test_position_chart_in_print_fallback_starts_at_one_and_skips_invalid_ranks():
    data = {
        'snapshot': {'start_date': '2026-10-01', 'end_date': '2026-10-03'},
        'daily': [{'date': f'2026-10-0{day}', 'values': {'position': value}}
                  for day, value in enumerate([7.5, 0.4, 1], 1)],
    }
    metric = {'key': 'position', 'unit': 'number', 'label': 'Vị trí trung bình'}
    chart = extra_chart(data, None, metric)
    assert chart['reverse_y'] and chart['observed'] == 2
    assert [bar['height'] for bar in chart['bars']] == [132, 0]
    assert data['daily'][1]['values']['position'] == 0.4


def test_keyword_columns_keep_all_rows_across_multiple_page_chunks():
    rows = [{'id': str(i), 'keyword': f'Từ khóa {i}', 'rank': None if i == 80 else i + 1,
             'observed_date': '2026-10-15', 'change': 0} for i in range(81)]
    compiled = {'sources': [{'id': 'seo', 'data': {}, 'keyword_groups': [
        {'title': 'Bộ cam kết', 'rows': rows}]}]}
    before = deepcopy(compiled)
    groups = build(compiled)['keywords']
    flattened = [row for group in groups for table in group['tables'] for row in table]
    assert [len(table) for group in groups for table in group['tables']] == [20, 20, 20, 20, 1]
    assert [row['id'] for row in flattened] == [row['id'] for row in rows]
    assert [row['number'] for row in flattened] == list(range(1, 82))
    assert flattened[-1]['rank'] is None
    assert [group['continued'] for group in groups] == [False, True, True]
    assert compiled == before


def test_article_deliverables_share_traffic_without_losing_acceptance_or_drafts():
    content = [{'id': 'new', 'title': 'Bài mới', 'url': 'https://example.test/a', 'kind': 'new',
                'accepted_date': '2026-10-15'},
               {'id': 'update', 'title': 'Cập nhật', 'url': 'https://example.test/a', 'kind': 'update',
                'accepted_date': '2026-10-21'},
               {'id': 'draft', 'title': 'Bản thảo', 'url': '', 'draft_url': 'https://example.test/draft'},
               {'id': 'archived', 'title': 'Ẩn', 'url': 'https://example.test/old', 'archived': True}]
    report = {'content': {'items': content}, 'effectiveness': {'items': [
        {'id': 'new', 'ids': ['new', 'update'], 'title': 'Bài viết', 'values': {'views': 0, 'clicks': None}}]}}
    result = build({'sources': [{'id': 'seo', 'data': report}]})['articles']
    assert len(result) == 2
    assert result[0]['values'] == {'views': 0, 'clicks': None}
    assert [(task['kind'], task['accepted_date']) for task in result[0]['tasks']] == [
        ('new', '2026-10-15'), ('update', '2026-10-21')]
    assert result[1]['draft_url'] == 'https://example.test/draft'
    assert result[1]['values'] == {}


def test_google_summary_preserves_unknowns_zero_custom_targets_and_countries():
    compiled = {'sources': [{'id': 'seo', 'data': {}}, {'id': 'ga4', 'data': {
        'snapshot': {'id': 'snapshot'},
        'metrics': [{'key': 'active_users', 'label': 'Người dùng', 'unit': 'count', 'value': 0},
                    {'key': 'sessions', 'label': 'Phiên', 'unit': 'count', 'value': None}],
        'targets': {'items': [{'key': 'sessions', 'status': 'met', 'value': 100},
                              {'key': 'active_users', 'status': 'not_set', 'value': None}]}},
        'comparisons': [{'label': 'Người dùng', 'previous': '10', 'delta': '−100%', 'effect': 'unfavorable'}]},
        {'id': 'gsc', 'data': {'metrics': [], 'tables': [
            {'id': 'countries', 'rows': [{'country': 'vnm', 'clicks': 0}]}]}}]}
    before = deepcopy(compiled)
    result = build(compiled)
    assert [row['actual'] for row in result['metrics']] == ['0', '—', '—']
    assert result['metrics'][0]['previous'] == '10'
    assert result['metrics'][0]['effect'] == 'unfavorable'
    assert len(result['targets']) == 1 and result['targets'][0]['source'] == 'GA4'
    assert result['countries'] == [{'country': 'vnm', 'clicks': 0}]
    assert compiled == before
    assert build({'sources': [{'id': 'facebook_ads', 'data': {}}]}) is None


def test_optional_sections_do_not_reintroduce_tables_or_comparison_columns(seo_stack):
    client, _, _, saved, _ = seo_stack
    saved['sections'] = ['summary']
    response = client.get('/workspace/reports/combined?report=' + RECORD)
    assert response.status_code == 200
    assert 'Hiệu quả SEO &amp; Website' in response.text
    assert 'aria-label="Thứ hạng và từ khóa mở rộng"' not in response.text
    assert 'aria-label="Bài viết và hiệu quả"' not in response.text
    assert 'aria-label="KPI dự án và tiến độ"' not in response.text
    assert '<th>Kỳ đối chiếu</th>' not in response.text


def test_legacy_plan_below_target_is_distinct_from_missing_data(seo_stack):
    client, _, _, saved, _ = seo_stack
    saved['sources'][0]['data']['plan']['status'] = 'below_target'
    saved['sections'] = ['kpi']
    response = client.get('/workspace/reports/combined?report=' + RECORD)
    assert response.status_code == 200
    assert '<p>Chưa đạt</p>' in response.text
    assert 'Chưa đủ dữ liệu nghiệm thu' not in response.text


def test_kpi_prints_signed_shortfall_and_keeps_missing_data_distinct():
    from jinja2 import Environment, FileSystemLoader
    from app.customer_data import display
    goals = [dict(label='Kỹ thuật', unit='percent', target=100, actual=90, difference=-10,
                  achievement=90, status='below_target'),
             dict(label='Bài mới', unit='count', target=10, actual=12, difference=2,
                  achievement=120, status='met'),
             dict(label='Lưu lượng', unit='count', target=100, actual=None, difference=None,
                  achievement=None, status='no_data')]
    env = Environment(loader=FileSystemLoader('templates'), autoescape=True)
    html = env.get_template('customer/live/components/seo-compact-report.html').render(
        compiled={'sections':['kpi'], 'compact_seo': {'seo': {'data': {
            'project': {'plan': {'name':'SEO', 'version':1}, 'items':goals, 'timeline':None}}}, 'targets':[]}},
        display=display)
    assert '<td>−10 đpt</td>' in html
    assert '<td>+2</td>' in html
    assert '<td>—</td>' in html
    assert 'Chưa đạt' in html and 'Thiếu dữ liệu' in html


def test_madame_matrix_in_print_has_a_plan_and_actual_row_with_distinct_values():
    from bs4 import BeautifulSoup
    from jinja2 import Environment, FileSystemLoader
    from app.customer_data import display

    env = Environment(loader=FileSystemLoader('templates'), autoescape=True)
    timeline = {
        'metrics': [{'key': 'traffic', 'unit': 'count'}, {'key': 'top10_percent', 'unit': 'percent'}],
        'months': [{'month': '2026-01', 'items': [
            {'key': 'traffic', 'target': 4000, 'actual': -123},
            {'key': 'top10_percent', 'target': 20, 'actual': 57.5}
        ]}, {'month': '2026-02', 'items': [
            {'key': 'traffic', 'target': 4000, 'actual': 0},
            {'key': 'top10_percent', 'target': 58, 'actual': 57.5}
        ]}],
        'totals': {'traffic': {'target': 8000, 'actual': -123}, 'top10_percent': {'target': 20}}
    }
    plan = {'template': 'monthly_seo', 'traffic_basis': 'increase', 'traffic_metric': 'ga4_views'}
    component = env.get_template('customer/live/components/seo-kpi-matrix.html').make_module({'display': display})
    table = BeautifulSoup(component.render(timeline, plan), 'html.parser').table
    assert table.select_one('.seo-matrix-banner th')['colspan'] == '5'
    assert [th.get_text(strip=True) for th in table.select('thead tr:last-child th')] == ['STT', 'Tháng', '1', '2', 'Tổng']
    assert table.select_one('.seo-matrix-plan th').get_text(strip=True) == 'Số lượng lưu lượng truy cập tăng thêm lượt/tháng'
    assert [td.get_text(strip=True) for td in table.select('tbody:first-of-type .seo-matrix-actual td')] == ['−123', '0', '']
    assert [td.get_text(strip=True) for td in table.select('tbody:last-of-type .seo-matrix-actual td')] == ['58%', '57,5%', '']
    assert BeautifulSoup(component.value(57.999, 'percent', True, 58), 'html.parser').get_text(strip=True) == '<\u00a058%'
    assert table.select_one('.seo-matrix-total').get_text(strip=True) == '8.000'
