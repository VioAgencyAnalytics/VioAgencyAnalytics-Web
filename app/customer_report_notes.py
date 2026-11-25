"""Web review controls for validated reports. Admin owns versioning and storage."""
import hashlib
import hmac
import json
import re
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.customer_auth import HEADERS, SESSION, CustomerError, backend, configuration, error_response, read_body
from app.customer_pdf import ticket as pdf_ticket


router = APIRouter(tags=['customer report notes'])
BODY_LIMIT = 256 * 1024
MAX_NOTES = 100
MAX_NOTE_LENGTH = 600
ID = re.compile(r'[a-f0-9]{32}')
HASH = re.compile(r'[a-f0-9]{64}')
SECTION = re.compile(r'[a-z][a-z0-9_]{0,63}')


def platform_reference(report, form, preset=None):
    """Changing the data, scope, comparison or targets starts a new review."""
    snapshot = report.get('snapshot')
    if report.get('state') != 'ready' or not snapshot:
        return None
    previous = report.get('comparison') or {}
    period = report.get('period') or {}
    return {'form': form, 'source': report['source'], 'snapshot': snapshot['id'],
            **({'template': preset.key} if preset else {}),
            'dates': [period.get('start') or snapshot['start_date'], period.get('end') or snapshot['end_date']],
            'open': period.get('is_open', False),
            'comparison': [previous.get('period'), (previous.get('snapshot') or {}).get('id')] if previous.get('mode') not in (None, 'none') else None,
            'targets': [{key: item.get(key) for key in ('key', 'version', 'value', 'direction', 'currency')}
                        for item in (report.get('targets') or {}).get('items', []) if item.get('value') is not None]}


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def sign(settings, token, scope, report_key, sections):
    return hmac.new(settings.customer_service_token.get_secret_value().encode(),
                    b'report-notes:' + encode([token, scope, report_key, sorted(sections)]), hashlib.sha256).hexdigest()


def path(workspace_id, report_key):
    return f'/workspaces/{workspace_id}/report-notes/{report_key}'


def valid_notes(notes, *, empty=False):
    return (isinstance(notes, dict) and (empty or bool(notes)) and len(notes) <= MAX_NOTES
            and all(SECTION.fullmatch(key) and isinstance(value, str) and 0 < len(value.strip()) <= MAX_NOTE_LENGTH
                    and not any(ord(char) < 32 and char not in '\n\r\t' or 0xd800 <= ord(char) <= 0xdfff for char in value)
                    for key, value in notes.items()))


def projected(value, scope, report_key):
    if (not isinstance(value, dict) or value.get('scope') != scope or value.get('report_key') != report_key
            or value.get('status') not in ('suggested', 'draft', 'finalized')
            or type(value.get('version')) is not int or value['version'] < 0
            or type(value.get('can_edit')) is not bool
            or not valid_notes(value.get('notes'), empty=value['status'] == 'suggested')
            or value['status'] == 'suggested' and bool(value['notes'])
            or (value['status'] == 'suggested') != (value['version'] == 0)
            or (value['status'] == 'suggested') != (value.get('updated_at') is None)
            or value.get('updated_at') is not None and not isinstance(value['updated_at'], str)):
        raise CustomerError(502, 'Chưa tải được nhận xét của bản báo cáo.', 'report_note_input')
    return {key: value[key] for key in ('status', 'notes', 'version', 'can_edit', 'updated_at')}


async def saved_review(request, scope, report_key):
    endpoint = path(scope['workspace_id'], report_key) + '?' + urlencode({'client_id': scope['client_id']})
    return projected(await backend(request, 'GET', endpoint), scope, report_key)


async def attach(request, settings, scope, reference, sections):
    review = {'sections': {key: {**item, 'finalized': False} for key, item in sections.items()},
              'status': 'suggested', 'updated_at': None, 'reader': None, 'editor': None, 'load_error': False}
    if not reference or not sections or not scope.get('client_id'):
        return review
    report_key = hashlib.sha256(encode(reference)).hexdigest()
    review['report_key'] = report_key
    endpoint = path(scope['workspace_id'], report_key)
    suffix = '?' + urlencode({'client_id': scope['client_id']})
    token = request.cookies.get(SESSION, '')
    review['reader'] = {'endpoint': '/api/customer' + endpoint + suffix, 'proof': sign(settings, token, scope, report_key, [])}
    if not getattr(request.state, 'pdf_render', False):
        review['reader']['pdf'] = pdf_ticket(request, settings, scope, reference, report_key)
    try:
        saved = await saved_review(request, scope, report_key)
    except CustomerError as error:
        if error.status in (401, 403) or error.code in ('client_changed', 'workspace_changed', 'workspace_access'):
            raise
        # Data remains readable if the notes service is unavailable.
        review['load_error'] = True
        return review

    review.update(status=saved['status'], updated_at=saved['updated_at'])
    for key, item in review['sections'].items():
        if key in saved['notes']:
            item.update(text=saved['notes'][key], finalized=saved['status'] == 'finalized')
    if saved['can_edit'] and saved['status'] != 'finalized':
        review['editor'] = {'endpoint': '/api/customer' + endpoint, 'client_id': scope['client_id'],
                            'version': saved['version'], 'max_length': MAX_NOTE_LENGTH,
                            'proof': sign(settings, token, scope, report_key, sections)}
    return review


@router.get('/api/customer/workspaces/{workspace_id}/report-notes/{report_key}')
async def read(request: Request, workspace_id: str, report_key: str):
    try:
        settings = configuration(request)
        client_id = request.query_params.get('client_id', '')
        proof = request.headers.get('X-Report-Note-Proof', '')
        if (not ID.fullmatch(workspace_id) or not HASH.fullmatch(report_key) or not ID.fullmatch(client_id)
                or set(request.query_params) != {'client_id'} or len(request.query_params.getlist('client_id')) != 1):
            raise CustomerError(404, 'Không tìm thấy bản nhận xét.', 'report_note_input')
        scope = {'workspace_id': workspace_id, 'client_id': client_id}
        verified = sign(settings, request.cookies.get(SESSION, ''), scope, report_key, [])
        if not HASH.fullmatch(proof) or not hmac.compare_digest(proof, verified):
            raise CustomerError(403, 'Phạm vi nhận xét đã thay đổi. Tải lại báo cáo trước khi tiếp tục.', 'report_note_input')
        saved = await saved_review(request, scope, report_key)
        return JSONResponse({'status': saved['status'], 'notes': saved['notes']}, headers=HEADERS)
    except CustomerError as error:
        return error_response(error)


@router.post('/api/customer/workspaces/{workspace_id}/report-notes/{report_key}')
async def write(request: Request, workspace_id: str, report_key: str):
    try:
        if not ID.fullmatch(workspace_id) or not HASH.fullmatch(report_key):
            raise CustomerError(404, 'Không tìm thấy bản nhận xét.', 'report_note_input')
        data = await read_body(request, max_bytes=BODY_LIMIT)
        if (set(data) != {'client_id', 'version', 'action', 'notes', 'proof'}
                or not isinstance(data['client_id'], str) or not ID.fullmatch(data['client_id'])
                or type(data['version']) is not int or data['version'] < 0
                or data['action'] not in ('save', 'finalize') or not valid_notes(data['notes'])
                or not isinstance(data['proof'], str) or not HASH.fullmatch(data['proof'])):
            raise CustomerError(422, 'Nhập nhận xét cho từng mục trước khi lưu hoặc chốt.', 'report_note_input')
        scope = {'workspace_id': workspace_id, 'client_id': data['client_id']}
        proof = data.pop('proof')
        verified = sign(configuration(request), request.cookies.get(SESSION, ''), scope, report_key, data['notes'])
        if not hmac.compare_digest(proof, verified):
            raise CustomerError(403, 'Phạm vi nhận xét đã thay đổi. Tải lại báo cáo trước khi tiếp tục.', 'report_note_input')
        payload = await backend(request, 'POST', path(workspace_id, report_key), data)
        saved = projected(payload, scope, report_key)
        expected_status = 'finalized' if data['action'] == 'finalize' else 'draft'
        if saved['status'] != expected_status or saved['notes'].keys() != data['notes'].keys():
            raise CustomerError(502, 'Phản hồi lưu nhận xét chưa hợp lệ. Tải lại báo cáo để kiểm tra.', 'report_note_input')
        return JSONResponse(saved, headers=HEADERS)
    except CustomerError as error:
        return error_response(error)
