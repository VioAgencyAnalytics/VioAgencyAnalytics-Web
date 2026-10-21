"""Admin-exported synthetic contract; no runtime data or provider requests."""
import json
from copy import deepcopy
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.mappers.facebook_content import content_report
from app.mappers.dashboard import dashboard_context
from app.schemas.bundle_view import BundleView, SectionView, QualityView
from app.repositories.admin_bundle import AdminBundleContractError
from app.mappers.bundle import BundleViewMapper


def fixture():
    return json.loads((Path(__file__).parent / 'fixtures/facebook_content_report_v1.json').read_text(encoding='utf-8'))


def bundle_fixture():
    """Embed the actual Admin-generated contract in the existing sealed-test envelope."""
    payload = json.loads((Path(__file__).parent / 'fixtures/facebook_content_vio.json').read_text(encoding='utf-8'))
    source = fixture()
    source.update(contract_version='meta-reporting-v1', data_origin='provider_origin_confirmed')
    raw = source['content_report']
    payload['period'] = deepcopy(raw['period'])
    data = payload['sections']['facebook_content']['data']
    data['params'].update(raw['period'])
    data['sources']['facebook_content'] = source
    data['marketing']['widgets'] = [dict(m, verified=m['value'] is not None, publishable=m['value'] is not None,
                                        source='facebook_content', comparison=None)
                                   for m in raw['metrics'] if 'metric_id' in m]
    return payload


def test_full_bundle_mapper_uses_admin_metrics_and_same_contract():
    p = bundle_fixture(); before = deepcopy(p)
    bundle = BundleViewMapper().map(p, p['report']['id'], 1)
    context = dashboard_context(bundle, 'facebook_content', '/reports/' + bundle.report_id)
    assert context['dashboard']['content_report'] == fixture()['content_report']
    metrics = context['dashboard']['visible_content_kpis']
    assert [m['value'] for m in metrics] == [2, 3]
    assert p == before


def test_contract_copied_without_recompute_and_original_layout_renders():
    source = fixture(); original = deepcopy(source)
    raw = source['content_report']
    result = content_report(raw, source, raw['period'], True)
    assert result == raw and result is not raw
    section = SectionView('facebook_content', 'fb', 'Facebook Content', 'facebook-content', raw['period'],
                          True, 'available', QualityView(), content_report=result,
                          source_identity=raw['identity'], timezone='UTC', fetched_at=raw['fetched_at'])
    bundle = BundleView('fixture-report', 1, 'provisional', 'Fixture', 'Fixture', raw['period'], None,
                        None, None, QualityView(), [section], 'facebook_content')
    context = dashboard_context(bundle, 'facebook_content', '/reports/fixture-report')
    html = Environment(loader=FileSystemLoader('templates'), autoescape=select_autoescape()).get_template(
        'pages/facebook_content/index.html').render(**context)
    assert 'Product' in html and 'fc-format-list' in html and 'fc-topic-grid' in html
    assert 'https://www.facebook.com/1234/posts/1' in html
    assert '&lt;script&gt;Editorial fixture' in html
    assert '<script>Editorial fixture' not in html
    assert 'Dữ liệu mẫu KinderHealth' not in html
    assert source == original
    assert 'fc-topics' in context['dashboard']['visible_content_sections']
    assert 'fc-insights' in context['dashboard']['visible_content_sections']
    assert 'fc-reach' not in context['dashboard']['visible_content_sections']
    table = context['dashboard']['visible_content_tables'][0]
    assert table['rows'][0]['reactions_lifetime']['value'] == 0
    assert table['rows'][0]['shares_lifetime']['value'] is None


@pytest.mark.parametrize('case', ['client', 'period', 'timezone', 'unapproved', 'unapproved_note',
                                'post_scope', 'false_zero', 'nan_percent', 'unsafe_url', 'numeric_tamper'])
def test_invalid_contract_fails_closed(case):
    source = fixture(); raw = deepcopy(source['content_report'])
    if case == 'client': raw['identity']['client_id'] = 'foreign'
    if case == 'period': raw['period']['end'] = '2026-09-03'
    if case == 'timezone': raw['timezone'] = 'Asia/Ho_Chi_Minh'
    if case == 'unapproved': raw['review_status'] = 'pending_review'
    if case == 'unapproved_note': raw['sections']['posts']['commentary']['status'] = 'pending_review'
    if case == 'post_scope': raw['sections']['posts']['rows'][0]['post_id'] = '999_1'
    if case == 'false_zero': raw['sections']['posts']['rows'][0]['reach'] = 0
    if case == 'nan_percent': raw['sections']['formats']['rows'][0]['percent'] = float('nan')
    if case == 'unsafe_url': raw['sections']['posts']['rows'][0]['permalink_url'] = 'https://evil.invalid/'
    if case == 'numeric_tamper': raw['sections']['posts']['rows'][0]['reactions_lifetime'] = 999
    with pytest.raises(AdminBundleContractError):
        content_report(raw, source, source['content_report']['period'], True)


def test_old_report_has_no_injected_contract():
    assert content_report(None, fixture(), {'start': '2026-09-01', 'end': '2026-09-02'}, True) == {}
