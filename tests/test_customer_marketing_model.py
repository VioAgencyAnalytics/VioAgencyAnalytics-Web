"""Dashboard scaffolding must stay empty until a scoped Admin analytics read exists."""
from app.mappers.customer_marketing import build_marketing


def test_dashboard_never_adopts_legacy_metrics_or_connections():
    details = {'workspace': {'id': 'w', 'currency': 'USD', 'timezone': 'UTC'}, 'selected_client': {'id': 'c'}}
    catalogue = {'platforms': [{'id': 'facebook_ads', 'categories': ['ads']}, {'id': 'gsc', 'categories': ['seo']},
                               {'id': 'youtube', 'categories': ['video']}],
                 'connections': [{'id': 'legacy'}], 'campaigns': [{'id': 'legacy'}], 'metrics': {'spend': 100}}
    view = build_marketing(details, catalogue)
    assert view['scope'] == {'workspace_id': 'w', 'client_id': 'c'}
    assert view['currency'] == 'USD' and view['timezone'] == 'UTC'
    assert view['connections'] == view['platform_metrics'] == view['campaigns'] == []
    assert all(item['value'] is None and item['previous'] is None for item in view['metrics'].values())
    assert set(view['trends']) == {'spend', 'impressions', 'clicks', 'conversions'}
    assert all(not item['points'] for item in view['trends'].values())
    assert [p['group'] for p in view['platforms']] == ['paid', 'search', 'content']
    assert all('group' not in p for p in catalogue['platforms'])


def test_no_client_and_mutating_a_model_does_not_populate_the_next_view():
    details = {'workspace': {'id': 'w'}}
    view = build_marketing(details, {})
    view['metrics']['spend']['value'] = 0
    view['campaigns'].append({'id': 'not-real'})
    other = build_marketing(details, {})
    assert other['scope']['client_id'] is None
    assert other['metrics']['spend']['value'] is None
    assert other['platforms'] == other['campaigns'] == []
