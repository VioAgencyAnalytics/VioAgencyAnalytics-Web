"""The overview shell must not invent provider values or reuse legacy scopes."""
from app.mappers.customer_overview import build_overview


def test_overview_starts_empty_with_explicit_customer_scope_and_catalogue():
    details = {'workspace': {'id': 'w', 'currency': 'USD', 'timezone': 'UTC'},
               'selected_client': {'id': 'client-owned'}}
    catalogue = {'platforms': [{'id': 'ga4', 'name': 'Google Analytics 4'}],
                 'connections': [{'id': 'legacy-not-owned'}]}
    data = build_overview(details, catalogue)
    assert data['scope'] == {'workspace_id': 'w', 'client_id': 'client-owned'}
    assert data['currency'] == 'USD'
    assert data['connections'] == [] and data['reports'] == []
    assert data['last_updated_at'] is None
    assert set(data['metrics']) == {'spend', 'impressions', 'clicks', 'conversions'}
    assert all(item['value'] is None and item['previous'] is None for item in data['metrics'].values())
    assert all(not item['points'] for item in data['trends'].values())
    assert data['platforms'][0]['id'] == 'ga4'


def test_no_selection_no_catalogue_and_independent_empty_models():
    details = {'workspace': {'id': 'w'}}
    a = build_overview(details, {})
    b = build_overview(details, {})
    assert a['scope']['client_id'] is None
    assert a['platforms'] == []
    a['metrics']['spend']['value'] = 0
    a['trends']['spend']['points'].append({'value': 0})
    assert b['metrics']['spend']['value'] is None
    assert not b['trends']['spend']['points']
