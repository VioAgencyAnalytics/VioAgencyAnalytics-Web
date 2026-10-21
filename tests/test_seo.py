import csv
import io

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_seo_page_uses_reference_and_shared_navigation():
    response = client.get('/report/seo')
    assert response.status_code == 200
    assert 'SEO &amp; lưu lượng website' in response.text
    assert '420.500' in response.text
    assert 'Phễu Chuyển Đổi SEO' in response.text
    assert 'Thứ hạng từ khóa' in response.text
    assert '/static/js/pages/seo.js' in response.text
    assert '/static/js/pages/overview.js' not in response.text
    assert 'href="/report/seo" aria-current="page"' in response.text


def test_seo_period_scales_counts_but_preserves_rates_and_rankings():
    payload = client.get('/api/v1/reports/seo?start=2026-09-24&end=2026-09-30').json()
    assert payload['data_source'] == 'mock'
    assert payload['period']['days'] == 7
    assert payload['fields']['impressions'] == '98.117'
    assert payload['fields']['clicks'] == '9.296'
    assert payload['fields']['cr'] == '1,28%'
    assert payload['fields']['top10'] == '148'
    assert payload['keywords'][0]['position'] == 2
    assert payload['keywords'][0]['clicks'] == round(6420 * 7 / 30)
    assert payload['chart_dates'][0] == '24/09'
    assert payload['chart_dates'][-1] == '30/09'


def test_seo_rejects_invalid_period_and_export_filters():
    for path in ['/api/v1/reports/seo', '/api/v1/reports/seo/export']:
        for query in ['start=2026-09-30&end=2026-09-01', 'start=2025-01-01', 'end=2027-01-01', 'start=bad']:
            assert client.get(path + '?' + query).status_code == 422
    assert client.get('/api/v1/reports/seo/export?rank=unknown').status_code == 422


def test_seo_csv_respects_rank_and_search_filters():
    response = client.get('/api/v1/reports/seo/export', params={'rank': 'top3', 'query': 'tiêm chủng', 'start': '2026-09-24', 'end': '2026-09-30'})
    assert response.status_code == 200
    assert response.content.startswith(b'\xef\xbb\xbf')
    rows = list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))
    assert rows[1] == ['Từ ngày', '2026-09-24', 'Đến ngày', '2026-09-30']
    header = next(i for i, row in enumerate(rows) if row and row[0] == 'Từ khóa')
    keywords = []
    for row in rows[header + 1:]:
        if not row:
            break
        keywords.append(row)
    assert len(keywords) == 2
    assert {row[0] for row in keywords} == {'tiêm chủng cho bé', 'trung tâm tiêm chủng quận 1'}
    assert all(int(row[3]) <= 3 for row in keywords)
    assert 'KDH-SEO-2026-09-24-2026-09-30.csv' in response.headers['content-disposition']


def test_seo_one_day_range_has_one_chart_date():
    response = client.get('/api/v1/reports/seo?start=2026-09-30&end=2026-09-30')
    assert response.status_code == 200
    assert response.json()['chart_dates'] == ['30/09']
