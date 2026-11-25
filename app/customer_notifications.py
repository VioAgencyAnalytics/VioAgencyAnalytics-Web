"""Expose only scoped activity summaries and read markers."""
from datetime import datetime
import re
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.customer_auth import HEADERS, CustomerError, backend, error_response, read_body
from app.customer_transport import PROVIDERS


router = APIRouter(tags=['customer notifications'])
ID = re.compile(r'[a-f0-9]{32}')
DIGEST = re.compile(r'[a-f0-9]{64}')
SOURCES = '|'.join(sorted(PROVIDERS))
DESTINATION = re.compile(
    r'/workspace/(?:reports|integrations\?platform=(?:' + SOURCES + r')(?:&reconnect=1)?|'
    r'reports/combined\?report=[a-f0-9]{32}|reports/facebook-content\?snapshot=[a-f0-9]{32}|'
    r'reports/data\?source=(?:' + SOURCES + r')&snapshot=[a-f0-9]{32}|'
    r'seo\?tab=(?:keywords|content)(?:&start=\d{4}-\d{2}-\d{2}&end=\d{4}-\d{2}-\d{2})?)'
)
KINDS = {'connected', 'choose_asset', 'reconnect', 'sync_done', 'sync_failed', 'report_created',
         'notes_finalized', 'pdf_saved', 'seo_import', 'seo_sync_done', 'seo_sync_failed'}
FIELDS = ('id', 'kind', 'at', 'title', 'detail', 'href', 'action', 'source', 'attention', 'read')
LIMIT = 36


def matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def route(workspace_id):
    return f'/workspaces/{workspace_id}/notifications'


def scope_for(workspace_id, client_id):
    if not all(matches(ID, value) for value in (workspace_id, client_id)):
        raise CustomerError(404, 'Không tìm thấy thông báo trong phạm vi này.', 'workspace_access')
    return {'workspace_id': workspace_id, 'client_id': client_id}


def timestamp(value):
    if value is None:
        return True
    try:
        return isinstance(value, str) and len(value) <= 40 and datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False


def project(payload, scope):
    items = payload.get('items')
    if payload.get('scope') != scope or not isinstance(items, list) or len(items) > LIMIT:
        raise CustomerError(502, 'Chưa tải được thông báo của khách hàng đang chọn.')
    for row in items:
        if (not isinstance(row, dict) or set(FIELDS) - row.keys() or not matches(DIGEST, row['id'])
                or not isinstance(row['kind'], str) or row['kind'] not in KINDS or not timestamp(row['at'])
                or not (row['source'] is None or isinstance(row['source'], str) and row['source'] in PROVIDERS)
                or not matches(DESTINATION, row['href']) or any(type(row[key]) is not bool for key in ('attention', 'read'))
                or any(not isinstance(row[key], str) or len(row[key]) > 440 for key in ('title', 'detail', 'action'))):
            raise CustomerError(502, 'Chưa tải được thông báo của khách hàng đang chọn.')
    if len({row['id'] for row in items}) != len(items):
        raise CustomerError(502, 'Thông báo trả về bị trùng. Vui lòng tải lại.')
    return {'scope': scope, 'items': [{key: row[key] for key in FIELDS} for row in items]}


@router.get('/api/customer/workspaces/{workspace_id}/notifications')
async def inbox(request: Request, workspace_id: str):
    try:
        params = request.query_params
        if set(params) != {'client_id'} or len(params.getlist('client_id')) != 1:
            raise CustomerError(422, 'Chọn khách hàng trước khi mở thông báo.')
        scope = scope_for(workspace_id, params['client_id'])
        payload = await backend(request, 'GET', route(workspace_id) + '?' + urlencode({'client_id': scope['client_id']}))
        return JSONResponse(project(payload, scope), headers=HEADERS)
    except CustomerError as error:
        return error_response(error)


@router.post('/api/customer/workspaces/{workspace_id}/notifications/read')
async def mark_read(request: Request, workspace_id: str):
    try:
        data = await read_body(request)
        scope_for(workspace_id, data.get('client_id'))
        ids = data.get('ids')
        if set(data) != {'client_id', 'ids'} or not isinstance(ids, list) or not 1 <= len(ids) <= LIMIT or not all(matches(DIGEST, key) for key in ids):
            raise CustomerError(422, 'Danh sách thông báo không hợp lệ.')
        payload = await backend(request, 'POST', route(workspace_id) + '/read', data)
        confirmed = payload.get('read_ids')
        if not isinstance(confirmed, list) or len(confirmed) > len(ids) or any(key not in ids for key in confirmed):
            raise CustomerError(502, 'Chưa xác nhận được trạng thái đã đọc.')
        return JSONResponse({'read_ids': confirmed}, headers=HEADERS)
    except CustomerError as error:
        return error_response(error)
