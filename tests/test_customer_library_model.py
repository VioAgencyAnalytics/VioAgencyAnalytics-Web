from copy import deepcopy

import pytest

from app.mappers.customer_library import build_library


def fixture():
    workspace = {'id': 'w1', 'currency': 'USD', 'timezone': 'UTC'}
    client = {'id': 'c1', 'name': 'Client <safe>'}
    details = {'workspace': workspace, 'selected_client': client}
    catalogue = {'workspace': workspace, 'selected_client': client, 'platforms': [
        {'id': key, 'name': key} for key in ('facebook_ads', 'tiktok_ads', 'google_ads', 'facebook_content', 'instagram', 'ga4', 'gsc', 'youtube', 'business_profile')],
        'connections': []}
    return details, catalogue


def test_library_has_nine_channels_and_ten_layouts_with_null_metrics():
    details, catalogue = fixture()
    original = deepcopy((details, catalogue))
    view = build_library(details, catalogue)
    assert len(view['channels']) == 9 and len(view['templates']) == 10
    assert view['scope'] == {'workspace_id': 'w1', 'client_id': 'c1'}
    assert view['currency'] == 'USD' and view['timezone'] == 'UTC'
    assert all(m['value'] is None for c in view['templates'] for m in c['metrics'])
    assert view['reports'] == [] and view['exports'] == [] and not view['reports_loaded']
    assert not any(view['capabilities'].values())
    assert (details, catalogue) == original


def test_seo_is_a_composite_and_instagram_is_only_a_source_catalogue_entry():
    view = build_library(*fixture())
    assert next(c for c in view['channels'] if c['id'] == 'seo')['source_ids'] == ['ga4', 'gsc']
    assert 'instagram' in [s['id'] for s in view['sources']]
    assert 'instagram' not in [c['id'] for c in view['channels']]
    view['templates'][1]['metrics'][0]['value'] = 123
    assert view['channels'][0]['metrics'][0]['value'] is None


@pytest.mark.parametrize('foreign', ['workspace', 'client'])
def test_scope_mismatch_is_rejected(foreign):
    details, catalogue = fixture()
    catalogue[foreign if foreign == 'workspace' else 'selected_client'] = {'id': 'other'}
    with pytest.raises(ValueError):
        build_library(details, catalogue)


def test_only_same_tenant_connections_can_affect_status_never_metrics():
    details, catalogue = fixture()
    catalogue['connections'] = [
        {'workspace_id': 'w1', 'client_id': 'c1', 'platform_id': 'facebook_ads', 'state': 'connected'},
        {'workspace_id': 'w1', 'client_id': 'foreign', 'platform_id': 'ga4', 'state': 'syncing'},
        {'workspace_id': 'foreign', 'client_id': 'c1', 'platform_id': 'gsc', 'state': 'expired'},
    ]
    view = build_library(details, catalogue)
    assert view['channels'][0]['state'] == 'empty'
    assert next(c for c in view['channels'] if c['id'] == 'ga4')['state'] == 'not_connected'
    assert all(m['value'] is None for c in view['channels'] for m in c['metrics'])


def test_unselected_client_never_adopts_connection_data():
    details, catalogue = fixture()
    details['selected_client'] = catalogue['selected_client'] = None
    catalogue['connections'] = [{'workspace_id': 'w1', 'client_id': 'c1', 'platform_id': 'ga4', 'state': 'connected'}]
    view = build_library(details, catalogue)
    assert view['scope']['client_id'] is None
    assert all(c['state'] == 'not_connected' for c in view['channels'])
