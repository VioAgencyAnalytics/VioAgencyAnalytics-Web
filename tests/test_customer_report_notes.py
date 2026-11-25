"""Draft selection, scope checks and exact rendering of finalized note text."""
from urllib.parse import parse_qs, urlsplit
import json

import pytest
from bs4 import BeautifulSoup

from app import customer_report_notes as notes
from app.customer_auth import SESSION
from app.customer_comparisons import metric_change
from app.customer_report_layouts import build_layout
from app.report_commentary import comparison, platform, targets
from test_customer_auth import stack, csrf_headers, TOKEN
from test_customer_content_view import content as facebook_fixture
from test_customer_data import prepare, report
from test_customer_report_layouts import SPECS, platform_report
from test_customer_seo import CLIENT, RECORD, seo_stack


@pytest.fixture
def saved_notes(monkeypatch):
    records, requests = {}, []

    async def backend(request, method, address, body=None):
        requests.append((method, address, body))
        url = urlsplit(address)
        parts = url.path.strip('/').split('/')
        workspace_id, report_key = parts[1], parts[3]
        client_id = body['client_id'] if body else parse_qs(url.query)['client_id'][0]
        key = (workspace_id, client_id, report_key)
        base = {'scope': {'workspace_id': workspace_id, 'client_id': client_id}, 'report_key': report_key,
                'status': 'suggested', 'version': 0, 'updated_at': None, 'notes': {}, 'can_edit': True}
        if method == 'POST':
            assert 'proof' not in body
            records[key] = {**base, 'status': 'finalized' if body['action'] == 'finalize' else 'draft',
                            'version': body['version'] + 1, 'updated_at': '2026-11-25T07:00:00Z',
                            'notes': {name: value.strip() for name, value in body['notes'].items()}}
        return records.get(key, base)

    monkeypatch.setattr(notes, 'backend', backend)
    return records, requests


def page_and_fields(client, path):
    response = client.get(path)
    assert response.status_code == 200, response.text[:500]
    page = BeautifulSoup(response.text, 'html.parser')
    rendered = {item['data-report-note']: item.select_one('[data-report-note-text]').get_text()
                for item in page.select('[data-report-note]')}
    fields = {item['data-report-note-field']: item.get_text() for item in page.select('[data-report-note-field]')}
    assert rendered and rendered == fields
    assert len(rendered) == len(page.select('[data-report-note]'))
    return page, rendered


@pytest.mark.parametrize('source', [*SPECS, 'facebook_content'])
def test_platform_reports_attach_every_editable_note_to_visible_section(stack, saved_notes, source):
    client, _, state, _ = stack
    prepare(state)
    state['source_data'] = platform_report(source) if source in SPECS else report(source)
    _, rendered = page_and_fields(client, '/workspace/reports/data?source=' + source)
    detail = 'details_empty' if source in SPECS else 'detail_0'
    assert {'summary', 'trend', detail, 'distribution', 'kpi'} <= rendered.keys()


def test_facebook_content_uses_its_own_post_and_lifetime_observations(stack, saved_notes):
    client, _, state, _ = stack
    prepare(state)
    payload = facebook_fixture()
    payload.update(schema_version=1, source='facebook_content', state='ready', scope=state['source_data']['scope'],
                   client=state['selected_client'], connection={'id': 'd' * 32, 'version': 1, 'status': 'connected'},
                   latest_sync=None, periods=[])
    payload['asset']['id'] = '9' * 32
    payload['snapshot'].update(id='e' * 32, created_at='2026-10-03T00:00:00Z', fetched_at='2026-10-03T00:00:00Z', timezone='UTC')
    state['content'] = payload
    _, rendered = page_and_fields(client, '/workspace/reports/facebook-content')
    assert {'summary', 'trend', 'rank_posts', 'distribution', 'detail_posts'} <= rendered.keys()
    assert 'tích lũy' in rendered['rank_posts']


def test_compiled_seo_and_multi_source_reports_keep_notes_with_selected_sections(seo_stack, saved_notes):
    client, _, _, document, _ = seo_stack
    path = '/workspace/reports/combined?report=' + RECORD
    _, seo = page_and_fields(client, path)
    assert {'seo_performance', 'seo_keywords', 'seo_articles', 'seo_kpi', 'seo_work'} <= seo.keys()
    assert 'Chưa có phép đo' in seo['seo_keywords']

    document['sources'] = [document['sources'][1]]
    _, combined = page_and_fields(client, path)
    assert {'overview', 'ga4_summary', 'ga4_comparison', 'ga4_kpi', 'ga4_trend', 'ga4_detail_0'} <= combined.keys()
    document['sections'] = ['summary']
    _, reduced = page_and_fields(client, path)
    assert set(reduced) == {'overview', 'ga4_summary'}


def test_notes_post_requires_csrf_and_signed_sections_then_renders_exact_final_text(stack, saved_notes):
    client, _, state, _ = stack
    _, requests = saved_notes
    prepare(state)
    state['source_data'] = platform_report('gsc')
    client.cookies.set(SESSION, TOKEN)
    path = '/workspace/reports/data?source=gsc'
    page, fields = page_and_fields(client, path)
    editor = json.loads(page.select_one('#report-note-editor').string)
    reader = json.loads(page.select_one('#report-note-reader').string)
    finalized = 'Đã chốt <b>văn bản</b>.\nGiữ đúng nội dung để xuất PDF.'
    body = {'client_id': CLIENT, 'version': editor['version'], 'proof': editor['proof'], 'action': 'finalize',
            'notes': {**fields, 'summary': finalized}}
    assert client.post(editor['endpoint'], json=body).status_code == 403
    headers = csrf_headers(client)
    before = len(requests)
    for invalid in [{'client_id': '8' * 32}, {'notes': {**fields, 'hidden_section': 'Sai mục'}}, {'proof': '0' * 64}]:
        assert client.post(editor['endpoint'], json={**body, **invalid}, headers=headers).status_code == 403
    assert len(requests) == before
    result = client.post(editor['endpoint'], json=body, headers=headers)
    assert result.status_code == 200, result.text
    assert result.json()['notes']['summary'] == finalized
    assert client.get(reader['endpoint']).status_code == 403
    to_print = client.get(reader['endpoint'], headers={'X-Report-Note-Proof': reader['proof']})
    assert to_print.json() == {'status': 'finalized', 'notes': {**fields, 'summary': finalized}}
    confirmed = BeautifulSoup(client.get(path).text, 'html.parser')
    entry = confirmed.select_one('[data-report-note=summary]')
    assert entry['data-note-final'] == 'true'
    assert entry.select_one('p').get_text() == finalized and not entry.select('b')
    assert confirmed.select_one('#report-note-edit') is None
    assert all(item['data-note-final'] == 'true' for item in confirmed.select('[data-report-note]'))

    state['source_data']['snapshot']['id'] = '2' * 32
    updated, _ = page_and_fields(client, path)
    assert updated.select_one('[data-report-note=summary]')['data-note-final'] == 'false'
    assert json.loads(updated.select_one('#report-note-editor').string)['endpoint'] != editor['endpoint']


def test_automatic_observations_distinguish_zero_missing_and_larger_windows():
    source = platform_report('gsc')
    source['daily'][0]['values']['position'] = None
    layout = build_layout(source)
    report_notes = platform(source, layout)
    assert '0 ở 1 ngày' not in report_notes['trend']['text']  # The lead is missing, not a counted zero.
    assert 'Chưa có chuỗi' in report_notes['trend']['text']
    assert 'Chưa có số liệu cho clicks' in report_notes['summary']['text']
    clicks = next(row for row in source['metrics'] if row['key'] == 'clicks')
    item = metric_change(clicks, {**clicks, 'value': 3}, {**clicks, 'value': 0})
    base = {'status': 'ready', 'items': [item], 'current_days': 2, 'comparison_days': 2}
    assert 'tăng 3' in comparison('gsc', layout, base)
    assert 'độ dài khác nhau' in comparison('gsc', layout, {**base, 'comparison_days': 1})
    kpi = targets([{'label': 'CTR', 'unit': 'percent', 'value': '.0359', 'actual': .0312,
                    'status': 'below_target', 'difference': '.0047'}])
    assert '0,47 điểm phần trăm' in kpi
