"""Synthetic SEO contract regressions; never provider observations."""
from copy import deepcopy

import pytest

from app.mappers.bundle import BundleViewMapper
from app.mappers.dashboard import dashboard_context, KEYWORD_TIERS
from app.config import get_settings
from main import app
from tests.bundle_fixtures import published_bundle
from tests.test_marketing_view import released_bundle
from tests.test_viewer import env, use_viewer_session, REPORT_ID


def seo_fixture(released=False):
    raw = released_bundle() if released else published_bundle()
    data = raw['sections']['seo']['data']
    data['sources']['gsc'] = {'label': 'GSC fixture', 'totals': {'clicks': 0, 'ctr': .125},
        'daily': [{'date': '2026-09-01', 'clicks': 0}, {'date': '2026-09-03', 'clicks': 4}]}
    data['sources']['keywords'] = {'label': 'Keywords fixture', 'latest_available_date': '2026-09-30',
        'totals': {f'top{k}': i * 2 for i, k in enumerate(KEYWORD_TIERS)},
        'previous': {f'top{k}': i for i, k in enumerate(KEYWORD_TIERS)},
        'entries': [{'keyword': f'keyword-{i}', 'url': '/fixture', 'position': rank,
                     'date': '2026-09-30', 'previous_position': rank + 2 if rank else None,
                     'change': 2 if rank else None, 'device': 'mobile'}
                    for i, rank in enumerate([1, 5, 6, 10, 11, 20, 21, 30, 31, 50, 51, 100, 101, 0, None])]}
    return raw


def context(raw):
    bundle = BundleViewMapper().map(raw, raw['report']['id'], 2)
    return dashboard_context(bundle, 'seo', '/reports/' + raw['report']['id'])['dashboard']


def test_six_saved_tiers_are_cumulative_values_not_recounted_rows():
    raw = seo_fixture()
    before = deepcopy(raw)
    view = context(raw)
    assert [t['limit'] for t in view['keyword_tiers']] == [5, 10, 20, 30, 50, 100]
    assert [t['metric']['value'] for t in view['keyword_tiers']] == [0, 2, 4, 6, 8, 10]
    assert [t['metric']['previous'] for t in view['keyword_tiers']] == [0, 1, 2, 3, 4, 5]
    assert view['keyword_tiers'][0]['metric']['text'] == '0'
    assert raw == before
    assert [c['value'] for c in view['kpis']] == [None, 0, None, 2, None, None]
    assert any(m['key'] == 'sessions' and m['value'] == 123 for m in view['traffic_metrics'])
    assert any(c['values'] == [0, None, 4] for c in view['charts'])


def test_missing_and_ambiguous_tiers_stay_missing():
    raw = seo_fixture()
    source = raw['sections']['seo']['data']['sources']['keywords']
    source['totals'].pop('top30')
    source['kpis'] = [{'key': 'top50', 'value': 999}]
    tiers = {t['limit']: t['metric'] for t in context(raw)['keyword_tiers']}
    assert tiers[30] is None and tiers[50] is None


def test_release_tiers_only_use_approved_widgets():
    raw = seo_fixture(released=True)
    data = raw['sections']['seo']['data']
    data['marketing']['widgets'].append({'metric_id': 'keywords.top10', 'value': 42,
        'verified': True, 'publishable': True, 'unit': 'count', 'source': 'Approved Keywords'})
    tiers = {t['limit']: t['metric'] for t in context(raw)['keyword_tiers']}
    assert tiers[10]['value'] == 42
    assert tiers[5] is None and tiers[30] is None


def test_explicitly_disabled_comparison_hides_saved_rank_changes():
    raw = seo_fixture()
    raw['sections']['seo']['data']['params']['compare'] = False
    view = context(raw)
    assert view['keyword_tables'][0]['rows'][0]['change']['value'] is None
    assert view['keyword_tiers'][1]['metric']['previous'] is None


def test_qualified_and_alias_metrics_do_not_choose_conflicting_top10():
    raw = seo_fixture()
    raw['sections']['seo']['data']['sources']['keywords']['kpis'] = [{'key': 'keywords.top10', 'value': 999}]
    view = context(raw)
    assert view['kpis'][3]['value'] is None
    assert view['keyword_tiers'][1]['metric'] is None


@pytest.mark.parametrize('comparison', [None, {'start': '2026-07-01', 'end': '2026-07-31'}])
@pytest.mark.parametrize('explicit', [False, True])
def test_unverified_comparison_is_hidden_in_keyword_tables(comparison, explicit):
    raw = seo_fixture()
    raw['comparison'] = comparison
    source = raw['sections']['seo']['data']['sources']['keywords']
    if explicit:
        rows = source.pop('entries')
        source['tables'] = [{'columns': [{'key': key} for key in rows[0]], 'rows': rows}]
    view = context(raw)
    row = view['keyword_tables'][0]['rows'][0]
    assert row['previous_position']['value'] is None and row['change']['value'] is None
    assert row['position']['value'] == 1 and row['date']['value'] == '2026-09-30'
    assert all(t['metric']['previous'] is None for t in view['keyword_tiers'])


def test_keyword_scope_duplicates_and_landing_path_are_preserved():
    raw = seo_fixture()
    sources = raw['sections']['seo']['data']['sources']
    sources['keywords']['entries'].append(deepcopy(sources['keywords']['entries'][0]))
    sources['ga4']['pages'] = [{'landingPage': '/saved-landing', 'sessions': 7, 'date': '2026-09-01'}]
    view = context(raw)
    assert len(view['keyword_tables'][0]['rows']) == 16
    assert view['keyword_tables'][0]['rows'][0]['device']['value'] == 'mobile'
    assert any('trùng từ khóa/ngày/URL' in w for w in view['quality']['warnings'])
    assert view['landing_tables'][0]['rows'][0]['landingPage']['value'] == '/saved-landing'
    assert view['landing_tables'][0]['rows'][0]['sessions']['value'] == 7


def test_rendered_seo_keeps_snapshot_contract_and_revision(env):
    client, _, _, raw = env
    raw['sections'] = seo_fixture()['sections']
    use_viewer_session(client)
    response = client.get('/reports/' + REPORT_ID + '?revision=2&section=seo')
    assert response.status_code == 200
    for k in KEYWORD_TIERS:
        assert f'data-keyword-tier="{k}"' in response.text
        assert f'Top {k} (1–{k})' in response.text
    assert 'data-row-date="2026-09-30" data-position="1"' in response.text
    assert 'Ngày tracking' in response.text and 'data-snapshot-rank' in response.text
    assert '/static/js/pages/seo.js' not in response.text
    assert 'revision=2&amp;section=seo' in response.text


def test_production_viewer_rejects_mock_bundle_even_after_auth(env):
    client, _, _, _ = env
    settings = app.dependency_overrides[get_settings]()
    app.dependency_overrides[get_settings] = lambda: settings.model_copy(update={'app_env': 'production'})
    use_viewer_session(client)
    response = client.get('/reports/' + REPORT_ID + '?revision=2')
    assert response.status_code == 502
    assert 'snapshot-data' not in response.text
    assert 'không được hiển thị trong production' in response.text


def test_production_viewer_still_renders_approved_non_demo_snapshot(env):
    client, _, _, raw = env
    settings = app.dependency_overrides[get_settings]()
    app.dependency_overrides[get_settings] = lambda: settings.model_copy(update={'app_env': 'production'})
    raw['sections'] = released_bundle()['sections']
    raw['navigation'] = {'default_section': 'seo', 'sections': ['seo']}
    use_viewer_session(client)
    response = client.get('/reports/' + REPORT_ID + '?revision=2')
    assert response.status_code == 200 and 'snapshot-data' in response.text


@pytest.mark.parametrize('limit', KEYWORD_TIERS)
def test_demo_filter_and_csv_use_cumulative_top_k(env, limit):
    from app.integrations.mock.seo import filter_keywords
    rows = [{'position': p, 'keyword': str(p), 'landing': '/'} for p in [0, 1, 5, 6, 10, 20, 30, 50, 100, 101]]
    assert [r['position'] for r in filter_keywords(rows, f'top{limit}')] == [r['position'] for r in rows if 1 <= r['position'] <= limit]
    client, _, _, _ = env
    assert client.get(f'/api/v1/reports/seo/export?rank=top{limit}').status_code == 200
