"""PDF generation reopens the exact scoped report and only issues a receipt for valid bytes."""
import json

import pytest

from app import customer_pdf, customer_report_notes
from app.customer_auth import SESSION, CustomerError
from test_customer_auth import TOKEN, csrf_headers, stack
from test_customer_data import prepare
from test_customer_report_layouts import platform_report
from test_customer_report_notes import page_and_fields, saved_notes


def test_pdf_receipt_requires_current_report_proof_and_separate_verified_save(stack, saved_notes, monkeypatch):
    client, _, state, _ = stack
    prepare(state)
    state['source_data'] = platform_report('gsc')
    client.cookies.set(SESSION, TOKEN)
    headers = csrf_headers(client)
    page, fields = page_and_fields(client, '/workspace/reports/data?source=gsc')
    settings = json.loads(page.select_one('#report-note-reader').string)['pdf']
    endpoint = settings.pop('endpoint')
    note_editor = json.loads(page.select_one('#report-note-editor').string)
    finalized = 'Lead đã chốt nội dung kiểm tra PDF.'
    confirmation = {'client_id': note_editor['client_id'], 'proof': note_editor['proof'], 'version': note_editor['version'],
                    'action': 'finalize', 'notes': {**fields, 'summary': finalized}}
    assert client.post(note_editor['endpoint'], json=confirmation, headers=headers).status_code == 200

    rendered, writes = [], []

    async def render(html, path):
        rendered.append(path)
        assert b'data-pdf-render="true"' in html
        assert finalized.encode() in html
        assert b'data-report-pdf' not in html
        return b'%PDF-1.7\n' + b' ' * 1200 + b'\n%%EOF\n'

    async def backend(request, method, path, data):
        assert path.endswith('/notifications/pdf-saved')
        writes.append(data)
        return {'recorded': True}

    monkeypatch.setattr(customer_pdf, 'render_pdf', render)
    monkeypatch.setattr(customer_pdf, 'backend', backend)
    assert client.post(endpoint, json=settings).status_code == 403
    assert client.post(endpoint, json={**settings, 'query': 'source=ga4'}, headers=headers).status_code == 403
    assert not rendered
    snapshot = state['source_data']['snapshot']
    original = snapshot['id']
    snapshot['id'] = '9' * 32
    assert client.post(endpoint, json=settings, headers=headers).status_code == 409
    snapshot['id'] = original
    pdf = client.post(endpoint, json=settings, headers=headers)
    assert pdf.status_code == 200, pdf.text
    assert len(rendered) == 1 and not writes and pdf.headers['content-type'] == 'application/pdf'
    saved = {key: settings[key] for key in ('client_id', 'form', 'report_id')}
    saved['receipt'] = pdf.headers['x-vio-pdf-receipt']
    assert client.post(endpoint + '/saved', json={**saved, 'report_id': '9' * 32}, headers=headers).status_code == 403
    assert not writes
    result = client.post(endpoint + '/saved', json=saved, headers=headers)
    assert result.status_code == 200 and result.json() == {'recorded': True}
    assert len(writes) == 1 and writes[0]['report_id'] == original and 'receipt' not in writes[0]


@pytest.mark.parametrize('change, expected', [('finalized', 409), ('client_changed', 409), ('expired_session', 401)])
def test_pdf_rechecks_selected_client_and_finalized_notes_after_render(stack, saved_notes, monkeypatch, change, expected):
    client, _, state, _ = stack
    prepare(state)
    state['source_data'] = platform_report('gsc')
    client.cookies.set(SESSION, TOKEN)
    headers = csrf_headers(client)
    page, fields = page_and_fields(client, '/workspace/reports/data?source=gsc')
    ticket = json.loads(page.select_one('#report-note-reader').string)['pdf']
    endpoint = ticket.pop('endpoint')
    scope = state['source_data']['scope']
    records, _ = saved_notes

    async def render(html, _path):
        assert b'data-note-final="true"' not in html
        if change == 'finalized':
            records[(scope['workspace_id'], scope['client_id'], ticket['report_key'])] = {
                'scope': scope, 'report_key': ticket['report_key'], 'status': 'finalized', 'version': 1,
                'updated_at': '2026-11-25T03:15:00Z', 'notes': fields, 'can_edit': True}
        else:
            async def access_lost(*args):
                raise CustomerError(expected, 'Phạm vi phiên đã thay đổi.', change)

            monkeypatch.setattr(customer_report_notes, 'backend', access_lost)
        return b'%PDF-1.7\n' + b' ' * 1200 + b'\n%%EOF\n'

    monkeypatch.setattr(customer_pdf, 'render_pdf', render)
    response = client.post(endpoint, json=ticket, headers=headers)
    assert response.status_code == expected, response.text
    assert 'x-vio-pdf-receipt' not in response.headers
    if change == 'finalized':
        assert 'Nhận xét vừa được chốt' in response.json()['error']
