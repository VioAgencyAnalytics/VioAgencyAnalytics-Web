from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_overview_report_endpoint():
    response = client.get('/api/v1/reports/overview')
    assert response.status_code == 200
    payload = response.json()
    assert payload['report_type'] == 'overview'
    assert 'metrics' in payload
    assert len(payload['metrics']) >= 4


def test_report_endpoint_with_filters():
    response = client.get('/api/v1/reports/seo?period=monthly&channel=search')
    assert response.status_code == 200
    payload = response.json()
    assert payload['report_type'] == 'seo'
    assert payload['filters']['period'] == 'monthly'


def test_overview_filters_and_contribution_totals():
    response = client.get('/api/v1/reports/overview?start=2026-09-24&end=2026-09-30')
    assert response.status_code == 200
    payload = response.json()
    assert payload['data_source'] == 'mock'
    assert payload['period']['days'] == 7
    assert payload['period']['previous_end'] == '2026-09-23'
    assert payload['fields']['reach'] == '112.548'
    assert payload['fields']['channel_0_summary'].endswith('(↑ 19,5%)')
    leads = next(metric['value'] for metric in payload['metrics'] if metric['key'] == 'leads')
    assert sum(payload['charts']['channel_mix']['values']) == leads


def test_overview_rejects_invalid_ranges():
    for query in ['start=2026-09-30&end=2026-09-01', 'start=2025-01-01', 'end=2027-01-01', 'start=not-a-date']:
        assert client.get('/api/v1/reports/overview?' + query).status_code == 422


def test_overview_csv_uses_selected_period():
    import csv
    import io

    response = client.get('/api/v1/reports/overview/export?start=2026-09-24&end=2026-09-30')
    assert response.status_code == 200
    assert response.content.startswith(b'\xef\xbb\xbf')
    assert 'attachment' in response.headers['content-disposition']
    rows = list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))
    assert rows[1] == ['Từ ngày', '2026-09-24', 'Đến ngày', '2026-09-30']
    assert rows[4][1] == '112548'


def test_overview_renders_reference_dashboard():
    response = client.get('/overview')
    assert response.status_code == 200
    assert '>Tổng quan</h1>' in response.text
    assert '482.350' in response.text
    assert '/static/css/dist/dashboard.css' in response.text
    assert 'cdn.tailwindcss.com' not in response.text


def test_facebook_ads_page_renders():
    response = client.get('/report/facebook-ads')
    assert response.status_code == 200
    assert '<h1>Facebook Ads</h1>' in response.text
    assert '26.400.000 ₫' in response.text
    assert 'Leads Thành Công' in response.text


def test_facebook_ads_api_renders_all_dynamic_fragments_with_filters():
    response = client.get('/api/v1/reports/facebook-ads?campaign=893120492')
    assert response.status_code == 200
    payload = response.json()

    assert set(payload['fragments']) == {
        'kpis', 'campaigns', 'funnel', 'audience', 'creatives', 'insights',
    }
    assert 'data-campaign-id="893120492"' in payload['fragments']['campaigns']
    assert 'data-campaign-id="893120491"' not in payload['fragments']['campaigns']
    assert '<strong>Leads</strong>' in payload['fragments']['funnel']
    assert 'Hồ sơ đối tượng mẫu' in payload['fragments']['audience']
    assert 'Bác sĩ tư vấn dinh dưỡng cho bé' not in payload['fragments']['creatives']
    assert 'Vấn Đề Cần Chú Ý' in payload['fragments']['insights']
