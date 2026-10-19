from copy import deepcopy
import pytest
from tests.test_viewer import env, use_viewer_session, REPORT_ID
from app.mappers.bundle import BundleViewMapper
from app.mappers.dashboard import dashboard_context, display
from tests.bundle_fixtures import published_bundle


@pytest.mark.parametrize('section', ['overview','seo','facebook_ads','facebook_content','tiktok','youtube'])
def test_original_channel_templates_are_bound_and_mock_scripts_absent(env, section):
    client, _, _, bundle = env
    raw = deepcopy(bundle['sections']['seo']); raw['report_type'] = section
    bundle['sections'][section] = raw
    bundle['navigation']['sections'] = [section]
    bundle['navigation']['default_section'] = section
    use_viewer_session(client)
    response = client.get('/reports/'+REPORT_ID+'?revision=2&section='+section)
    assert response.status_code == 200
    assert 'dashboard-sidebar' in response.text and 'snapshot-data' in response.text
    assert 'src="/static/js/pages/snapshot.js"' in response.text
    for script in ('seo','overview','facebook-ads','facebook-content','video','published'):
        assert 'src="/static/js/pages/'+script+'.js"' not in response.text
    for claim in ('128% Mục Tiêu', '4 video mẫu', 'mô phỏng theo độ dài', 'Tất cả (148)'):
        assert claim not in response.text
    assert 'href="/overview"' not in response.text and 'href="/report/' not in response.text


def test_series_gap_null_zero_and_no_unapproved_claim():
    raw = published_bundle()
    raw['sections']['seo']['data']['sources']['ga4']['daily'] = [{'date':'2026-09-01','sessions':0},{'date':'2026-09-03','sessions':4}]
    raw['sections']['seo']['data']['evidence'] = [{'claim':'Unapproved claim'}]
    bundle = BundleViewMapper().map(raw, raw['report']['id'],2)
    chart = bundle.sections[0].charts[0]
    assert chart.values == [0,None,4]
    assert chart.labels == ['2026-09-01','2026-09-02','2026-09-03']
    assert bundle.sections[0].evidence == []
    assert display(0) == '0' and display(None) == 'Chưa có dữ liệu'
    assert display(.125,'ratio') == '12,50%'


def test_no_organic_users_or_marketing_totals_inferred():
    raw = published_bundle()
    bundle = BundleViewMapper().map(raw,raw['report']['id'],2)
    seo = dashboard_context(bundle,'seo','/reports/'+REPORT_ID)['dashboard']
    assert next(m for m in seo['kpis'] if m['label']=='Organic Users')['value'] is None
    overview = dashboard_context(bundle,'overview','/reports/'+REPORT_ID)['dashboard']
    assert all(m['value'] is None for m in overview['kpis'])


def test_forbidden_section_and_submenu_preserve_revision(env):
    client, calls, _, _ = env; use_viewer_session(client)
    response = client.get('/reports/'+REPORT_ID+'?revision=2&section=seo&view=thu-hang-tu-khoa')
    assert response.status_code == 200 and 'revision=2&amp;section=seo&amp;view=thu-hang-tu-khoa' in response.text
    assert client.get('/reports/'+REPORT_ID+'?revision=2&section=youtube').status_code == 404
    assert all('/api/reports/' not in str(call.url) for call in calls)


@pytest.mark.parametrize('channel,metrics,expected', [
    ('facebook_ads', {'clicks':1000, 'link_clicks':7, 'conversions':20}, {'facebook_ads.link_clicks':7,'facebook_ads.lead_conversion_rate':None}),
    ('facebook_content', {'posts_published':8,'engagements':0,'followers_gained':4,'post_clicks':55},
        {'facebook_content.posts_published':8,'facebook_content.engagements':0,'facebook_content.followers_gained':4,'facebook_content.link_clicks':None}),
    ('tiktok', {'video_views':90,'leads':6,'conversions':33,'cost_per_conversion':42}, {'tiktok_ads.video_views':90,'tiktok_ads.leads':6,'tiktok_ads.cost_per_lead':None}),
    ('youtube', {'impressions_ctr':0.125,'subscribers_gained':0}, {'youtube.impressions_ctr':0.125,'youtube.subscribers_gained':0}),
])
def test_catalog_metrics_keep_designed_meanings(channel, metrics, expected):
    from app.mappers.dashboard import metric_cards
    from app.schemas.bundle_view import SectionView, QualityView, MetricView
    source = 'tiktok_ads' if channel == 'tiktok' else channel
    section = SectionView(channel,channel,channel,channel,{},True,'available',QualityView())
    section.metrics = [MetricView(key,key,value,source_key=source) for key,value in metrics.items()]
    cards = {m['key']:m['value'] for m in metric_cards(section,channel)}
    # Alias rows retain their source key in the underlying view model.
    for key,value in expected.items():
        assert cards.get(key, cards.get(key.split('.')[1])) == value


def test_explicit_daily_chart_gaps_and_duplicate_dates():
    raw = published_bundle()
    source = raw['sections']['seo']['data']['sources']['ga4']
    source['charts'] = [dict(title='Explicit', type='line', labels=['2026-09-03','2026-09-01'], values=[4,0]),
                        dict(title='Duplicate', type='line', labels=['2026-09-01','2026-09-01'], values=[1,2])]
    section = BundleViewMapper().map(raw, raw['report']['id'],2).sections[0]
    assert next(c for c in section.charts if c.title=='Explicit').values == [0,None,4]
    assert not any(c.title=='Duplicate' for c in section.charts)


def test_preview_channel_is_selected_from_source_without_publishing():
    from app.mappers.dashboard import preview_dashboard
    candidate={'marketing':{'preview':{'widgets':[{'metric_id':'youtube.views','value':42}]}},'sources':{},'params':{}}
    bundle=preview_dashboard(candidate, [], 'a'*32)
    assert bundle.default_section == 'youtube' and bundle.status == 'draft'

def test_seo_multi_source_qa_contract():
    """
    QA-only: verify New can render 3 sources inside
    one SEO section without inventing missing KPIs.
    """
    raw = published_bundle()

    seo_data = raw["sections"]["seo"]["data"]

    # Synthetic data, never real provider observations.
    seo_data["sources"] = {
        "gsc": {
            "label": "GSC QA",
            "status": "ready",
            "latest_available_date": "2026-09-30",
            "totals": {
                "impressions": 12500,
                "clicks": 620,
            },
            "daily": [
                {
                    "date": "2026-09-28",
                    "clicks": 10,
                    "impressions": 200,
                },
                {
                    "date": "2026-09-29",
                    "clicks": 13,
                    "impressions": 240,
                },
                {
                    "date": "2026-09-30",
                    "clicks": 20,
                    "impressions": 300,
                },
            ],
        },
        "ga4": {
            "label": "GA4 QA",
            "status": "ready",
            "latest_available_date": "2026-09-30",
            "totals": {
                "activeUsers": 880,
                "sessions": 1100,
            },
        },
        "keywords": {
            "label": "Keywords QA",
            "status": "ready",
            "latest_available_date": "2026-09-30",
            "totals": {
                "top10": 18,
            },
            "entries": [
                {
                    "date": "2026-09-30",
                    "keyword": "khám nhi",
                    "url": "/kham-nhi",
                    "position": 3,
                }
            ],
        },
    }

    bundle = BundleViewMapper().map(
        raw,
        raw["report"]["id"],
        2,
    )

    context = dashboard_context(
        bundle,
        "seo",
        "/reports/" + raw["report"]["id"],
    )

    dashboard = context["dashboard"]

    # Designed SEO KPI order:
    # Impressions, Clicks, Organic Users,
    # Top 10, SEO Leads, Conversion Rate.
    values = [
        card["value"]
        for card in dashboard["kpis"]
    ]

    assert values == [
        12500,
        620,
        None,
        18,
        None,
        None,
    ]

    # The three GSC daily observations must be
    # available for the chart renderer.
    assert any(
        chart["labels"] == [
            "2026-09-28",
            "2026-09-29",
            "2026-09-30",
        ]
        and chart["values"] == [10, 13, 20]
        for chart in dashboard["charts"]
    )

    # Keyword detail is preserved as a table.
    assert dashboard["keyword_tables"]
    assert (
        dashboard["keyword_tables"][0]
        ["rows"][0]["keyword"]["value"]
        == "khám nhi"
    )
