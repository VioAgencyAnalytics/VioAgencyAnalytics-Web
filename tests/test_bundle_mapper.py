from copy import deepcopy

import pytest

from app.mappers.bundle import BundleViewMapper
from app.repositories.admin_bundle import AdminBundleContractError
from bundle_fixtures import REPORT_ID, published_bundle


def mapped(data=None):
    return BundleViewMapper().map(data or published_bundle(), REPORT_ID, 2)


def test_navigation_order_default_and_unpublished_sections():
    view = mapped()
    assert [s.key for s in view.sections] == ['seo','overview']
    assert view.default_section == 'seo'
    assert 'not-published' not in [s.key for s in view.sections]
    assert view.sections[0].report_type == 'seo'


def test_preserves_snapshot_values_nulls_and_no_recalculation():
    original = published_bundle(); before = deepcopy(original)
    view = mapped(original).sections[0]
    metrics = {m.key:m for m in view.metrics}
    assert metrics['sessions'].value == 123  # daily sum is 5, not 123
    assert metrics['sessions'].previous == 100
    assert metrics['sessions'].delta is None  # no locally calculated 23%
    assert metrics['activeUsers'].value is None and not metrics['activeUsers'].available
    assert metrics['screenPageViews'].value == 0 and metrics['screenPageViews'].available
    assert view.charts[0].values == [2,None,3]
    assert 'leads' not in metrics
    assert original == before


def test_empty_chart_evidence_opportunity_and_unknown_provenance():
    data = published_bundle(); data['sections']['seo']['data']['params']['demo'] = False
    view = mapped(data)
    assert view.provenance == 'unverified'
    assert view.sections[1].metrics == [] and view.sections[1].charts == []
    assert view.sections[0].evidence == [] and view.sections[0].opportunities == []


def test_default_fallback_and_absent_snapshot():
    data = published_bundle(); data['navigation'].update(default_section='missing', sections=['missing','overview','seo'])
    view = mapped(data)
    assert view.default_section == 'overview'
    assert [s.key for s in view.sections] == ['overview','seo']
    assert view.quality.warnings


@pytest.mark.parametrize('field,value', [('schema_version','2.0'), ('comparison',[]), ('sections',[]), ('navigation',{})])
def test_reject_invalid_contract(field, value):
    data = published_bundle(); data[field] = value
    with pytest.raises(AdminBundleContractError):
        mapped(data)


@pytest.mark.parametrize('status', ['draft','archived'])
def test_reject_unpublished_status(status):
    data = published_bundle(); data['report']['status'] = status
    with pytest.raises(AdminBundleContractError): mapped(data)


@pytest.mark.parametrize('field,value', [('id','wrong-id'), ('revision',3)])
def test_reject_wrong_identity_or_revision(field,value):
    data = published_bundle(); data['report'][field] = value
    with pytest.raises(AdminBundleContractError): mapped(data)


def test_quality_demo_unsupported_and_missing_data():
    data = published_bundle(); data['sections']['overview'].update(report_type='future-unsupported', data={'totals':{'foo':10}})
    view = mapped(data)
    assert view.provenance == 'demo'
    assert view.sections[1].state == 'unsupported' and view.sections[1].metrics == []
    assert view.quality.status == 'partial'
    assert 'GA4 fixture: Thiếu một ngày trong fixture' in view.sections[0].quality.warnings


def test_mismatched_periods_are_not_rendered_as_valid():
    data = published_bundle(); data['sections']['seo']['data']['params']['start'] = '2026-08-01'
    section = mapped(data).sections[0]
    assert section.state == 'unavailable' and not section.metrics
    data = published_bundle(); data['sections']['seo']['data']['params']['previous_start'] = '2026-07-01'
    section = mapped(data).sections[0]
    assert section.metrics[0].previous is None and section.quality.warnings


def test_explicit_components_are_copied_without_inference_and_unsafe_links_removed():
    data = published_bundle(); content = data['sections']['seo']['data']
    content['charts'] = [{'type':'donut','labels':['A','B'],'values':[3,7],'title':'Fixture distribution'}]
    content['evidence'] = [{'review_status':'approved','claim':'Kết luận fixture từ Admin','metric':'sessions','before':0,'after':2,'url':'javascript:alert(1)'}]
    content['opportunities'] = [{'title':'Đề xuất fixture từ Admin','priority':'high','supporting_data':['Fixture evidence'], 'conditions':['Điều kiện fixture']}]
    view = mapped(data).sections[0]
    assert view.charts[0].kind == 'donut'
    assert view.evidence[0].before == 0 and view.evidence[0].url is None
    assert view.opportunities == []  # A title alone is not release approval.


def test_google_ratio_units_preserved():
    data = published_bundle(); source = data['sections']['seo']['data']['sources']['ga4']
    source['totals']['engagementRate'] = .125
    metric = next(m for m in mapped(data).sections[0].metrics if m.key == 'engagementRate')
    assert metric.value == .125 and metric.unit == 'tỷ lệ (0–1)'


@pytest.mark.parametrize('status', ['provisional', 'final'])
def test_published_statuses_accepted(status):
    data = published_bundle(); data['report']['status'] = status
    assert mapped(data).status == status


def test_explicit_table_units_links_and_missing_cells():
    data = published_bundle()
    data['sections']['seo']['data']['tables'] = [{
        'title': 'Bảng fixture', 'columns': [{'key': 'spend', 'label': 'Chi tiêu', 'unit': 'VND'}, {'key': 'url'}],
        'rows': [{'spend': 0, 'url': 'https://example.test/verified'}, {'url': 'javascript:alert(1)'}],
    }]
    table = mapped(data).sections[0].tables[0]
    assert table.columns[0]['unit'] == 'VND'
    assert table.rows[0]['spend']['value'] == 0 and table.rows[1]['spend']['value'] is None
    assert table.rows[0]['url']['url'] == 'https://example.test/verified'
    assert table.rows[1]['url']['url'] is None
