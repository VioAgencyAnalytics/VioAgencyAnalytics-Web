"""Synthetic published contract; no runtime DB/provider or real release seal."""
import json
from copy import deepcopy
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.mappers.bundle import BundleViewMapper
from app.mappers.dashboard import dashboard_context
from app.repositories.admin_bundle import AdminBundleContractError


def fixture():
    return json.loads((Path(__file__).parent / 'fixtures/facebook_content_vio.json').read_text(encoding='utf-8'))


def mapped(payload):
    return BundleViewMapper().map(payload, payload['report']['id'], 1)


def test_frozen_kpis_coverage_timezone_and_no_recalculation():
    p = fixture(); before = deepcopy(p); view = mapped(p)
    section = view.sections[0]; m = {w.key.split('.')[-1]: w for w in section.metrics}
    assert [m[k].value for k in ('posts_published', 'reactions_lifetime', 'comments_lifetime')] == [15, 80, 10]
    assert m['engagements'].value is None and m['engagements'].status == 'no_data'
    assert m['shares_lifetime'].value is None and m['shares_lifetime'].status == 'partial'
    assert m['shares_lifetime'].coverage == {'available': 7, 'expected': 15, 'unit': 'posts'}
    assert m['reactions_lifetime'].grain == 'snapshot'
    assert m['reactions_lifetime'].aggregation == 'sum_posts_at_fetch'
    assert section.timezone == 'UTC' and section.fetched_at
    assert p == before
    context = dashboard_context(view, 'facebook_content', '/reports/' + view.report_id)
    assert len(context['dashboard']['kpis']) == 2
    assert len(context['dashboard']['lifetime_kpis']) == 3
    env = Environment(loader=FileSystemLoader('templates'), autoescape=select_autoescape())
    rendered = env.get_template('pages/facebook_content/index.html').render(**context)
    assert '28/28 ngày' in rendered and '15/15 bài' in rendered
    assert '0/28 ngày' not in rendered and 'Tích lũy đến ngày chốt' in rendered
    assert 'Múi giờ: UTC' in rendered and 'FIXTURE_ONLY_NOT_A_VALID_RELEASE_SEAL' not in rendered
    assert 'Dữ liệu mẫu KinderHealth' not in rendered
    from html.parser import HTMLParser
    class CardParser(HTMLParser):
        depth = 0
        cards = 0
        def handle_starttag(self, tag, attrs):
            if tag == 'article':
                assert self.depth == 0, 'KPI cards must not nest inside another card'
                self.depth += 1
                self.cards += int('executive-kpi' in dict(attrs).get('class', ''))
        def handle_endtag(self, tag):
            if tag == 'article': self.depth -= 1
    parser = CardParser(); parser.feed(rendered)
    assert parser.depth == 0 and parser.cards == 3


@pytest.mark.parametrize('case', ['wrong_client', 'false_zero', 'bad_coverage', 'unknown_status', 'unpublished', 'wrong_revision'])
def test_invalid_scope_and_missing_semantics_fail_closed(case):
    p = fixture(); data = p['sections']['facebook_content']['data']; widgets = data['marketing']['widgets']
    if case == 'wrong_client': data['sources']['facebook_content']['identity']['client_id'] = 'other'
    if case == 'false_zero': widgets[1]['value'] = 0
    if case == 'bad_coverage': widgets[0]['coverage']['available'] = 99
    if case == 'unknown_status': widgets[0]['status'] = 'verified'
    if case == 'unpublished': p['report']['status'] = 'draft'
    if case == 'wrong_revision': p['report']['revision'] = 2
    with pytest.raises(AdminBundleContractError): mapped(p)


def test_confirmed_zero_is_preserved():
    p = fixture(); p['sections']['facebook_content']['data']['marketing']['widgets'][3]['value'] = 0
    assert mapped(p).sections[0].metrics[3].value == 0


def test_content_presentation_uses_saved_rows_and_never_infers_totals():
    p = presentation_fixture(); before = deepcopy(p)
    context = dashboard_context(mapped(p), 'facebook_content', '/reports/test')
    d = context['dashboard']
    assert [m['value'] for m in d['overview_kpis']] == [15, 80, 10, None, None]
    assert [c['key'] for c in d['detail_tables'][0]['columns']] == [
        'post_id', 'date', 'reactions_lifetime', 'comments_lifetime', 'shares_lifetime']
    source_table = next(t for t in d['tables'] if 'post_id' in {c['key'] for c in t['columns']})
    assert d['detail_tables'][0]['rows'] == source_table['rows']
    assert d['content_charts'][0]['values'] == d['charts'][0]['values']
    assert d['content_charts'][0]['labels'] == d['charts'][0]['labels']
    assert d['content_charts'][0]['kind'] == 'bar'
    assert d['charts'][0]['kind'] == 'line'
    assert '7/15 bài' in ' '.join(d['commentary']['lifetime']['quality'])
    assert all(not n['approved'] for n in d['commentary'].values())
    assert p == before


def test_commentary_follows_changed_values_and_approval_scope():
    p = presentation_fixture()
    data = p['sections']['facebook_content']['data']
    data['marketing']['widgets'][0]['value'] = 0
    data['marketing']['widgets'][2]['value'] = 42
    evidence = data['evidence'][0]
    evidence['claim'] = '<script>Approved literal fixture</script>'
    rejected = deepcopy(evidence)
    rejected.update(claim='UNAPPROVED_NEVER_RENDER', review_status='rejected')
    data['evidence'].append(rejected)
    context = dashboard_context(mapped(p), 'facebook_content', '/reports/test')
    d = context['dashboard']
    assert '0 bài đăng' in d['commentary']['overview']['facts'][0]
    assert any('42 Reactions lifetime' in s for s in d['commentary']['lifetime']['facts'])
    env = Environment(loader=FileSystemLoader('templates'), autoescape=select_autoescape())
    html = env.get_template('pages/facebook_content/index.html').render(**context)
    assert 'UNAPPROVED_NEVER_RENDER' not in html
    assert '&lt;script&gt;Approved literal fixture&lt;/script&gt;' in html
    assert 'data-note-kind="approved"' in html
    assert html.count('class="section-commentary"') == 0
    assert 'Nhận định &amp; hướng triển khai' in html
    assert 'data-saved-row=' in html
    assert 'shares_lifetime' not in [c['key'] for c in d['visible_content_tables'][0]['columns']]


def presentation_fixture():
    p = fixture()
    source = p['sections']['facebook_content']['data']['sources']['facebook_content']
    source['entries'] = [{'post_id':'synthetic_1234567890123456','date':'2026-10-01',
                          'reactions_lifetime':0,'comments_lifetime':4,'shares_lifetime':None}]
    source['daily'] = [{'date':'2026-10-01','posts_published':1}]
    return p


def test_live_report_uses_original_shell_and_hides_empty_components():
    p = presentation_fixture()
    before = deepcopy(p)
    view = dashboard_context(mapped(p), 'facebook_content', '/reports/test')
    env = Environment(loader=FileSystemLoader('templates'), autoescape=select_autoescape())
    html = env.get_template('pages/facebook_content/index.html').render(**view)
    assert 'fc-live-shell' in html and 'fc-agency' not in html
    assert 'fc-top-grid fc-single-panel' in html
    assert 'facebook-content.css?v=insights-chart-20261022' in html
    assert 'Nhịp đăng bài' in html
    assert 'Biểu đồ trong báo cáo' in html and 'fc-posts-panel' in html
    assert 'Published Report Bundle' not in html and 'Frozen Bundle' not in html
    assert 'Chưa có nhận định chuyên môn được phê duyệt.' not in html
    assert 'data-kpi-status="no_data"' not in html and 'data-kpi-status="partial"' not in html
    assert 'fc-response-track' not in html
    assert '<details class="fc-scope-note">' in html
    for key in ('fc-topics', 'fc-reach', 'fc-engagement', 'fc-insights'):
        assert 'id="' + key + '"' not in html
        assert 'href="#' + key + '"' not in html
    assert '<section id="fc-insights" class="fc-panel">' not in html
    assert p == before
    p['sections']['facebook_content']['data']['marketing']['widgets'][2]['value'] = 0
    p['sections']['facebook_content']['data']['marketing']['widgets'][3]['value'] = 0
    context = dashboard_context(mapped(p), 'facebook_content', '/reports/test')
    zero_html = env.get_template('pages/facebook_content/index.html').render(**context)
    assert zero_html.count('class="executive-kpi fc-kpi-card"') == 3 and 'NaN' not in zero_html
    assert context['dashboard']['lifetime_kpis'][0]['value'] == 0
    assert [m['value'] for m in context['dashboard']['visible_content_kpis']] == [15, 0, 0]


def test_partial_column_keeps_missing_cells_and_legitimate_zero():
    p = presentation_fixture()
    entries = p['sections']['facebook_content']['data']['sources']['facebook_content']['entries']
    entries.append(dict(entries[0], post_id='synthetic_second', shares_lifetime=0))
    context = dashboard_context(mapped(p), 'facebook_content', '/reports/test')
    table = context['dashboard']['visible_content_tables'][0]
    assert 'shares_lifetime' in [c['key'] for c in table['columns']]
    assert [r['shares_lifetime']['value'] for r in table['rows']] == [None, 0]
    env = Environment(loader=FileSystemLoader('templates'), autoescape=select_autoescape())
    html = env.get_template('pages/facebook_content/index.html').render(**context)
    assert 'data-null="true"' in html
    assert not any(m['key'].endswith('shares_lifetime') for m in context['dashboard']['visible_content_kpis'])


def test_no_data_hides_panels_but_layout_preview_keeps_full_shell():
    report = mapped(fixture())
    section = report.sections[0]
    section.metrics = []
    section.charts = []
    section.tables = []
    section.evidence = []
    section.opportunities = []
    context = dashboard_context(report, 'facebook_content', '/reports/test')
    d = context['dashboard']
    assert d['visible_content_kpis'] == []
    assert d['visible_content_charts'] == []
    assert d['visible_content_tables'] == []
    assert d['visible_content_sections'] == ['fc-summary']
    env = Environment(loader=FileSystemLoader('templates'), autoescape=select_autoescape())
    html = env.get_template('pages/facebook_content/index.html').render(**context)
    assert 'id="fc-kpis"' not in html and 'id="fc-download"' not in html
    report.report_id = 'layout-preview'
    html = env.get_template('pages/facebook_content/index.html').render(
        **dashboard_context(report, 'facebook_content', '/static/layout-preview'))
    for key in ('fc-kpis', 'fc-posts', 'fc-formats', 'fc-topics', 'fc-engagement', 'fc-reach'):
        assert 'id="' + key + '"' in html


def test_post_links_use_saved_page_and_post_identity_without_mutating_rows():
    p = presentation_fixture()
    page_id = '987654321'
    post_id = page_id + '_123456789'
    p['sections']['facebook_content']['data']['sources']['facebook_content']['entries'][0]['post_id'] = post_id
    before = deepcopy(p)
    report = mapped(p)
    report.sections[0].source_identity.update(external_id='987654321', asset_type='facebook_page')
    view = dashboard_context(report, 'facebook_content', '/reports/test')
    link = 'https://www.facebook.com/permalink.php?story_fbid=123456789&id=' + page_id
    assert view['dashboard']['post_links'] == {post_id: link}
    assert p == before
    source = next(t for t in view['dashboard']['tables'] if 'post_id' in {c['key'] for c in t['columns']})
    assert view['dashboard']['detail_tables'][0]['rows'] == source['rows']
    env = Environment(loader=FileSystemLoader('templates'), autoescape=select_autoescape())
    html = env.get_template('pages/facebook_content/index.html').render(**view)
    assert 'class="fc-post-external"' in html and link.replace('&','&amp;') in html
    assert 'target="_blank" rel="noopener noreferrer"' in html
    assert 'data-snapshot-detail' in html  # Keep saved-row inspection separate.


@pytest.mark.parametrize('post_id', [None, 123, '123_456', 'javascript:alert(1)',
                                    '987654321_123/../../', '987654321_0',
                                    '987654321_１２３', '987654321_123?x=1'])
def test_post_links_reject_wrong_page_or_malformed_id(post_id):
    p = presentation_fixture()
    p['sections']['facebook_content']['data']['sources']['facebook_content']['entries'][0]['post_id'] = post_id
    report = mapped(p)
    report.sections[0].source_identity.update(external_id='987654321', asset_type='facebook_page')
    view = dashboard_context(report, 'facebook_content', '/reports/test')
    assert view['dashboard']['post_links'] == {}
