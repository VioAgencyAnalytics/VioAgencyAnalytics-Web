"""Consumes Admin-generated offline fixture; no Insights computation in New."""
import json
from copy import deepcopy
from pathlib import Path

import pytest
from app.mappers.facebook_content import content_report
from app.mappers.bundle import BundleViewMapper
from app.mappers.dashboard import dashboard_context
from app.repositories.admin_bundle import AdminBundleContractError
from test_content_report_contract import bundle_fixture


def fixture():
    return json.loads((Path(__file__).parent / 'fixtures/facebook_content_insights_v1.json').read_text(encoding='utf-8'))


def test_admin_projection_maps_without_recomputing_or_relabelling():
    source = fixture(); before = deepcopy(source)
    result = content_report(source['content_report'], source, source['content_report']['period'], True)
    assert result == source['content_report']
    payload = bundle_fixture()
    source.update(contract_version='meta-reporting-v1', data_origin='provider_origin_confirmed')
    payload['sections']['facebook_content']['data']['sources']['facebook_content'] = source
    bundle = BundleViewMapper().map(payload, payload['report']['id'], 1)
    view = dashboard_context(bundle, 'facebook_content', '/reports/' + bundle.report_id)['dashboard']
    cards = {m['key']: m for m in view['visible_content_kpis']}
    assert cards['facebook_content.page_media_view']['value'] == 3
    assert 'reach' not in cards['facebook_content.page_media_view']['label'].lower()
    assert 'facebook_content.page_total_media_view_unique' not in cards
    assert 'facebook_content.page_follows' not in cards
    assert len(view['visible_content_charts']) >= 4
    assert view['visible_content_tables'][0]['rows'][0]['post_media_view_lifetime']['value'] == 0
    assert view['visible_content_tables'][0]['rows'][1]['post_media_view_lifetime']['value'] is None
    assert source['content_report'] == before['content_report']


@pytest.mark.parametrize('case', ['page', 'period', 'missing_permission', 'task', 'raw', 'unique_total', 'lifetime', 'chart', 'post'])
def test_untrusted_insights_contract_fails_closed(case):
    source = fixture(); raw = deepcopy(source['content_report'])
    if case == 'page': source['insights']['page_id'] = '9999'
    if case == 'period': source['insights']['requested_period']['end'] = '2026-09-05'
    if case == 'missing_permission':
        source['insights']['permissions'] = []; raw['insights']['permissions'] = []
    if case == 'task':
        source['insights']['page_tasks'] = []; raw['insights']['page_tasks'] = []
    if case == 'raw': raw['insights']['measurements'][0]['values'][0]['value'] = 9
    if case == 'unique_total': raw['insights']['measurements'][1]['value'] = 3
    if case == 'lifetime': raw['insights']['measurements'][4]['value'] = 900
    if case == 'chart': raw['insights']['charts'][0]['values'] = [999]
    if case == 'post': raw['sections']['posts']['rows'][0]['post_media_view_lifetime'] = 999
    with pytest.raises(AdminBundleContractError):
        content_report(raw, source, source['content_report']['period'], True)


def test_partial_measurement_copies_zero_and_gap_without_a_total():
    source = fixture()
    raw = source['insights']['measurements'][0]
    projected = source['content_report']['insights']['measurements'][0]
    for row in (raw, projected):
        row['values'][1]['value'] = None
        row['status'] = 'partial'
        row['reason'] = 'Thiếu một phần số đo.'
    projected.update(value=None, report_status='partial')
    projected['coverage']['available'] = 1
    chart = source['content_report']['insights']['charts'][0]
    chart.update(status='partial', values=[0, None])
    result = content_report(source['content_report'], source, source['content_report']['period'], True)
    assert result['insights']['measurements'][0]['value'] is None
    assert result['insights']['charts'][0]['values'] == [0, None]


def test_insights_render_uses_seven_sections_and_exact_admin_scope():
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    source = fixture()
    payload = bundle_fixture()
    source.update(contract_version='meta-reporting-v1', data_origin='provider_origin_confirmed')
    payload['sections']['facebook_content']['data']['sources']['facebook_content'] = source
    bundle = BundleViewMapper().map(payload, payload['report']['id'], 1)
    context = dashboard_context(bundle, 'facebook_content', '/reports/' + bundle.report_id)
    html = Environment(loader=FileSystemLoader('templates'), autoescape=select_autoescape()).get_template(
        'pages/facebook_content/index.html').render(**context)
    for key in ('summary', 'formats', 'topics', 'posts', 'engagement', 'reach', 'insights'):
        assert f'id="fc-{key}"' in html
    assert 'Toàn Page · kỳ đã chốt' in html
    assert 'data-snapshot-kpi="facebook_content.page_media_view"' in html
    assert 'data-snapshot-kpi="facebook_content.page_follows"' not in html
    assert 'Lượt xem tích lũy' in html
    assert source['content_report']['sections']['reach']['reason'] in html
    assert 'Dữ liệu mẫu KinderHealth' not in html
