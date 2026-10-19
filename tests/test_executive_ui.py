"""Presentation regressions using isolated Bundles; no provider requests."""
import json
import re
from copy import deepcopy

import pytest
from tests.test_viewer import env, use_viewer_session, REPORT_ID
from tests.test_seo_snapshot import seo_fixture


def render(client, section):
    use_viewer_session(client)
    response = client.get(f'/reports/{REPORT_ID}?revision=2&section={section}')
    assert response.status_code == 200
    return response.text


@pytest.mark.parametrize('section', ['overview', 'seo', 'facebook_ads', 'facebook_content', 'tiktok', 'youtube'])
def test_published_header_keeps_source_export_and_fixed_period(env, section):
    client, _, _, raw = env
    raw['sections'][section] = deepcopy(raw['sections']['seo'])
    raw['sections'][section]['report_type'] = section
    raw['navigation'] = {'default_section': section, 'sections': [section]}
    before = deepcopy(raw)
    html = render(client, section)
    assert 'id="period-switcher"' not in html
    assert 'aria-label="Nguồn dữ liệu"' in html
    assert 'aria-label="Xuất báo cáo"' in html
    assert 'id="date-range"' in html
    assert raw['period']['start'] in html and raw['period']['end'] in html
    assert 'Revision 2' in html
    assert 'executive.css' in html
    assert raw == before


def test_seo_copy_preserves_zero_missing_tiers_and_original_values(env):
    client, _, _, raw = env
    raw['sections'] = seo_fixture()['sections']
    raw['comparison'] = None
    before = deepcopy(raw)
    html = render(client, 'seo')
    payload = json.loads(re.search(r'<script id="snapshot-data" type="application/json">(.*?)</script>', html, re.S)[1])
    dashboard = payload['dashboard']
    assert [k['value'] for k in dashboard['kpis']] == [None, 0, None, 2, None, None]
    assert [t['metric']['value'] for t in dashboard['keyword_tiers']] == [0, 2, 4, 6, 8, 10]
    assert all(k['previous'] is None for k in dashboard['kpis'])
    assert 'Chưa có kỳ so sánh' in html and 'Chưa có dữ liệu' in html
    assert 'Không cộng các mốc' in html
    assert 'không phải số từ khóa duy nhất' in html
    assert 'data-keyword-tier="5">0</dd>' in html
    assert 'GA4 toàn website không đồng nghĩa với Organic Search' in html
    assert raw == before


def test_facebook_static_copy_does_not_invent_scope_or_provider_connection(env):
    client, _, _, raw = env
    raw['client']['name'] = 'Khách hàng kiểm thử độc lập'
    raw['sections']['facebook_ads'] = deepcopy(raw['sections']['seo'])
    raw['sections']['facebook_ads']['report_type'] = 'facebook_ads'
    raw['navigation'] = {'default_section': 'facebook_ads', 'sections': ['facebook_ads']}
    html = render(client, 'facebook_ads')
    assert 'Khách hàng kiểm thử độc lập' in html
    for claim in ('Toàn hệ thống KinderHealth', 'chiến dịch đang chạy', 'Chưa kết nối Meta Marketing API / CRM', '<th>Clicks (CTR)</th>', '<th>Chi Tiêu / Ngân Sách</th>'):
        assert claim not in html
    assert '<th>Chi tiêu</th>' in html and '<th>Lượt nhấp</th>' in html
    assert 'Báo cáo tối ưu · Chưa khả dụng' in html


def test_executive_briefing_preserves_approved_text_and_conditions(env):
    from tests.test_marketing_view import released_bundle

    client, _, _, raw = env
    section = deepcopy(released_bundle()['sections']['seo'])
    section['report_type'] = 'overview'
    data = section['data']
    data['evidence'][0].update(claim='Nhận định fixture đã duyệt', source='Nguồn fixture')
    extra = deepcopy(data['evidence'][0])
    extra.update(claim='Nhận định thứ hai phải được giữ nguyên')
    data['evidence'].append(extra)
    data['opportunities'][0].update(reason='Lý do fixture', conditions=['Điều kiện bắt buộc fixture'])
    raw['sections'] = {'overview': section}
    raw['navigation'] = {'default_section': 'overview', 'sections': ['overview']}
    before = deepcopy(raw)
    html = render(client, 'overview')
    assert html.index('id="kpi-grid"') < html.index('id="insights"') < html.index('id="channel-performance"')
    assert html.count('id="insights"') == 1
    for text in ('Nhận định fixture đã duyệt', 'Nguồn fixture',
                 'Nhận định thứ hai phải được giữ nguyên', 'Lý do fixture',
                 'Điều kiện bắt buộc fixture', 'Inspect source'):
        assert text in html
    assert 'Unapproved fixture suggestion' not in html
    assert 'Xem thêm 1 nhận định' in html
    assert raw == before


def test_empty_executive_briefing_has_no_invented_claims(env):
    client, _, _, raw = env
    raw['sections'] = {'overview': {'report_type': 'overview', 'valid': True, 'data': {}}}
    raw['navigation'] = {'default_section': 'overview', 'sections': ['overview']}
    html = render(client, 'overview')
    assert 'Chưa có nhận định được phép công bố.' in html
    assert 'Chưa có đề xuất được duyệt.' in html
    assert 'Chưa có kế hoạch hành động được duyệt.' in html
    assert 'data-report-channel="overview"' in html
