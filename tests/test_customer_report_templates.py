"""The report catalogue uses the live layouts with isolated illustrative inputs."""

import re

from app.customer_platform_brands import PLATFORM_BRANDS
from app.customer_report_styles import STYLES, style_url
from app.customer_report_templates import CATALOGUE, LIBRARY
from test_customer_auth import stack


def choose_workspace(state):
    state.update(logged_in=True, workspace={
        'id': 'a' * 32, 'name': 'Private Workspace for QA', 'role': 'viewer',
        'kind': 'agency', 'timezone': 'Asia/Ho_Chi_Minh', 'currency': 'VND',
    }, selected_client={'id': 'c' * 32, 'name': 'Private client for QA'})


def test_catalogue_and_previews_require_a_customer_workspace(stack):
    client, _, state, _ = stack
    for url in (LIBRARY, LIBRARY + '/gsc', LIBRARY + '/gsc/position'):
        result = client.get(url, follow_redirects=False)
        assert result.status_code == 303
        assert result.headers['location'] == '/workspace/login'

    state['logged_in'] = True
    assert client.get(LIBRARY, follow_redirects=False).headers['location'] == '/workspace/onboarding'
    choose_workspace(state)
    assert client.get(LIBRARY + '/unknown').status_code == 404


def test_every_platform_has_a_read_only_preview_and_a_real_destination(stack):
    client, calls, state, _ = stack
    choose_workspace(state)
    assert {item.key for item in CATALOGUE} == set(PLATFORM_BRANDS) | {'seo', 'combined'}
    catalogue = client.get(LIBRARY)
    assert catalogue.status_code == 200
    assert catalogue.text.count('data-template-card=') == 66
    assert len(STYLES) == 6
    assert '/workspace/reports/templates/gsc/position' not in catalogue.text
    for item in CATALOGUE:
        assert f'href="{item.preview_url}/design/standard"' in catalogue.text
        preview = client.get(item.preview_url)
        assert preview.status_code == 200, item.key
        assert preview.headers['cache-control'] == 'no-store'
        assert preview.headers['x-frame-options'] == 'DENY'
        assert f'data-report-example="{item.key}"' in preview.text
        assert f'href="{item.use_url}"' in preview.text
        assert 'Dữ liệu minh họa' in preview.text
        assert 'data-report-note=' in preview.text
        assert 'data-report-pdf' not in preview.text
        assert 'id="report-note-reader"' not in preview.text
        assert 'href="https://' not in preview.text
        assert 'Private Workspace for QA' not in preview.text
        assert 'Private client for QA' not in preview.text
        assert '<thead>' in preview.text
        if item.key == 'seo':
            assert 'class="seo-kpi-matrix"' in preview.text
            assert preview.text.count('class="seo-matrix-plan"') == 8
            assert preview.text.count('class="seo-matrix-actual"') == 8
        if item.key == 'gsc':
            assert 'Vị trí trung bình' in preview.text
    assert {(request.method, request.url.path) for request in calls} == {
        ('GET', '/api/internal/customer/session'),
        ('GET', '/api/internal/customer/workspaces/' + 'a' * 32),
    }


def test_existing_layout_links_and_catalogue_filters_still_navigate(stack):
    client, _, state, _ = stack
    choose_workspace(state)
    old_link = client.get('/workspace/reports?report=overview', follow_redirects=False)
    assert old_link.headers['location'] == LIBRARY + '/combined'
    preview = client.get(LIBRARY + '/facebook-ads?category=ads&q=meta')
    assert f'href="{LIBRARY}?category=ads&amp;q=meta"' in preview.text


def test_specialized_previews_have_distinct_sections_and_preserve_use_selection(stack):
    client, _, state, _ = stack
    choose_workspace(state)
    pages = client.get(LIBRARY + '/gsc/pages?platform=gsc')
    assert pages.status_code == 200
    assert 'data-report-block="details"' in pages.text and 'data-table="seo_pages"' in pages.text
    assert 'data-table="queries"' not in pages.text
    assert 'href="/workspace/reports/data?source=gsc&amp;template=pages"' in pages.text
    position = client.get(LIBRARY + '/gsc/position')
    assert 'data-report-block="trend"' in position.text
    assert 'id="data-chart-metric" type="hidden" value="position"' in position.text
    assert 'data-report-block="details"' not in position.text
    keywords = client.get(LIBRARY + '/seo/long-tail')
    assert 'class="sc-page sc-keywords sc-extended"' in keywords.text
    assert 'class="seo-kpi-matrix"' not in keywords.text
    assert 'class="sc-page sc-content"' not in keywords.text
    assert client.get(LIBRARY + '/ga4/position').status_code == 404


def test_every_visual_style_keeps_all_sections_and_notes(stack):
    client, _, state, _ = stack
    choose_workspace(state)
    for item in CATALOGUE:
        base = client.get(item.preview_url).text
        notes = re.findall(r'data-report-note="([^"]+)"', base)
        for style in STYLES:
            response = client.get(f'{item.preview_url}/design/{style.key}')
            assert response.status_code == 200, (item.key, style.key)
            assert f'data-report-style="{style.key}"' in response.text
            assert re.findall(r'data-report-note="([^"]+)"', response.text) == notes
            assert response.text.count('<thead>') == base.count('<thead>')
            assert 'data-report-preset=' not in response.text
            assert style_url(item.use_url, item.key, style).replace('&', '&amp;') in response.text
    assert client.get(LIBRARY + '/gsc/design/unknown').status_code == 404


def test_palette_is_independent_of_layout_and_follows_apply_link(stack):
    client, _, state, _ = stack
    choose_workspace(state)
    styled = client.get(LIBRARY + '/gsc/design/editorial?palette=plum')
    assert styled.status_code == 200
    assert 'data-report-style="editorial" data-report-palette="plum"' in styled.text
    assert 'style=editorial&amp;palette=plum&amp;comparison=previous' in styled.text
    assert 'platform=gsc&amp;palette=plum' in styled.text
    assert client.get(LIBRARY + '/gsc/design/standard?palette=unknown').status_code == 404


def test_full_report_order_reuses_existing_section_keys(stack):
    client, _, state, _ = stack
    choose_workspace(state)
    path = LIBRARY + '/gsc/design/ledger'
    response = client.get(path + '?order=kpi,summary,trend,details&hidden=details')
    assert response.status_code == 200
    assert 'data-report-order="kpi,summary,trend,details" data-report-hidden="details"' in response.text
    assert 'order=kpi%2Csummary%2Ctrend%2Cdetails&amp;hidden=details' in response.text
    assert client.get(path + '?order=kpi,kpi').status_code == 422
    assert client.get(path + '?order=unknown').status_code == 422
    assert client.get(path + '?hidden=details,details').status_code == 422
