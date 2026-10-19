"""Release presentation fixtures; no provider authorization is implied by them."""
import pytest

from app.mappers.bundle import BundleViewMapper
from app.repositories.admin_bundle import AdminBundleContractError
from tests.bundle_fixtures import REPORT_ID, published_bundle


def released_bundle():
    bundle = published_bundle()
    bundle['navigation'] = {'sections': ['seo'], 'default_section': 'seo'}
    section = bundle['sections']['seo']
    section['quality'] = {'status': 'complete', 'warnings': []}
    data = section['data']
    data['params']['demo'] = False
    data['dataset_kind'] = 'marketing_release_snapshot_v1'
    data['release'] = {'schema_version': '1.0', 'state': 'release_approved', 'provider_origin_confirmed': True,
        'approval_id': 'fixture-review', 'seal': 'fixture-envelope-not-real', 'checks': [{'status': 'provider_origin_confirmed', 'issues': []}]}
    data['marketing'] = {'kind': 'approved_release', 'widgets': [
        {'metric_id': 'ga4.sessions', 'label': 'Sessions', 'value': 60, 'verified': True, 'publishable': True,
         'comparison': {'previous_value': 18, 'delta': 42}, 'unit': 'count'},
        {'metric_id': 'ga4.active_users', 'value': None, 'verified': False, 'publishable': False}]}
    data['evidence'] = [{'evidence_id': 'fixture-evidence', 'metric': 'sessions', 'before': 18, 'after': 60,
        'verification': 'provider_origin_confirmed', 'review_status': 'approved', 'asset_id': 'fixture-asset'},
        {'metric': 'unapproved', 'review_status': 'pending'}]
    data['opportunities'] = [{'title': 'Approved fixture suggestion', 'review_status': 'approved', 'action': 'Inspect source',
        'supporting_data': ['ga4.sessions'], 'conditions': ['No causality claim']},
        {'title': 'Unapproved fixture suggestion', 'review_status': 'pending'}]
    data['executive_summary'] = {'limitations': ['Traffic does not establish keyword ranking.']}
    data['platforms'] = {'ga4': {'label': 'Google Analytics 4', 'status': 'included'}, 'youtube': {'label': 'YouTube', 'status': 'not_in_report'}}
    return bundle


def test_approved_release_preserves_kpis_comparison_evidence_and_missing_values():
    result = BundleViewMapper().map(released_bundle(), REPORT_ID, 2)
    view = result.sections[0]
    assert result.provenance == 'provider_origin_confirmed'
    assert (view.metrics[0].value, view.metrics[0].previous, view.metrics[0].delta) == (60, 18, 42)
    assert view.metrics[1].value is None and not view.metrics[1].available
    assert len(view.evidence) == 1 and view.evidence[0].asset_id == 'fixture-asset'
    assert len(view.opportunities) == 1 and view.opportunities[0].conditions == ['No causality claim']
    assert any(chart.values == [18, 60] for chart in view.charts)
    assert view.platforms[1]['status'] == 'not_in_report'
    assert view.limitations and view.approval['approval_id'] == 'fixture-review'


@pytest.mark.parametrize('field,value', [('checks', [None]), ('checks', []), ('provider_origin_confirmed', False), ('state', 'approved_internal'), ('seal', '')])
def test_incomplete_release_metadata_is_rejected(field, value):
    bundle = released_bundle()
    bundle['sections']['seo']['data']['release'][field] = value
    with pytest.raises(AdminBundleContractError):
        BundleViewMapper().map(bundle, REPORT_ID, 2)


@pytest.mark.parametrize('change', ['demo', 'unverified_kpi', 'invalid_comparison', 'invalid_marketing', 'candidate'])
def test_demo_unverified_and_malformed_snapshots_cannot_appear_as_releases(change):
    bundle = released_bundle(); data = bundle['sections']['seo']['data']
    if change == 'demo': data['params']['demo'] = True
    if change == 'unverified_kpi': data['marketing']['widgets'][0]['verified'] = False
    if change == 'invalid_comparison': data['marketing']['widgets'][0]['comparison'] = [1]
    if change == 'invalid_marketing': data['marketing'] = []
    if change == 'candidate': data['dataset_kind'] = 'marketing_release_candidate_v1'
    with pytest.raises(AdminBundleContractError):
        BundleViewMapper().map(bundle, REPORT_ID, 2)
