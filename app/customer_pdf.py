"""Generate private PDFs from the same verified report versions used in Workspace."""
import asyncio
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import re
import shutil
import time
from urllib.parse import unquote, urlencode, urlsplit
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app.customer_auth import HEADERS, SESSION, CustomerError, backend, configuration, error_response, read_body


router = APIRouter(tags=['customer PDF export'])
logger = logging.getLogger(__name__)
HEX_ID = re.compile(r'[a-f0-9]{32}')
HEX_DIGEST = re.compile(r'[a-f0-9]{64}')
RECEIPT = re.compile(r'([a-f0-9]{32})\.(\d{10})\.([a-f0-9]{64})')
PATHS = {'compiled': '/workspace/reports/combined', 'platform': '/workspace/reports/data',
         'facebook_content': '/workspace/reports/facebook-content'}
ORIGIN = 'https://vio-pdf.invalid'
STATIC = Path(__file__).resolve().parents[1] / 'static'
RENDER_SLOTS = asyncio.Semaphore(1)
REPORT_SCRIPTS = {
    '/static/js/customer/' + name for name in ('data-format.js', 'report-charts.js', 'data-report.js', 'facebook-content.js', 'report-order.js')
}


def valid(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def sign(settings, token, purpose, workspace_id, data):
    payload = json.dumps([token, purpose, workspace_id, data], sort_keys=True, separators=(',', ':')).encode('ascii')
    return hmac.new(settings.customer_service_token.get_secret_value().encode(), b'vio-pdf:' + payload, hashlib.sha256).hexdigest()


def ticket(request, settings, scope, reference, report_key):
    form = reference['form']
    report_id = reference['id'] if form == 'compiled' else reference['snapshot']
    params = {'report': report_id} if form == 'compiled' else dict(request.query_params)
    if form == 'compiled':
        params.update({key: request.query_params[key] for key in ('style', 'palette', 'order', 'hidden') if key in request.query_params})
    if form == 'platform':
        params['source'] = reference['source']
    data = {'client_id': scope['client_id'], 'form': form, 'report_id': report_id,
            'report_key': report_key, 'query': urlencode(params)}
    workspace_id = scope['workspace_id']
    return {'endpoint': f'/api/customer/workspaces/{workspace_id}/reports/pdf', **data,
            'proof': sign(settings, request.cookies.get(SESSION, ''), 'render', workspace_id, data)}


def valid_scope(workspace_id, data):
    return (all(valid(HEX_ID, value) for value in (workspace_id, data.get('client_id'), data.get('report_id')))
            and isinstance(data.get('form'), str) and data['form'] in PATHS)


async def report_document(request, data):
    path = PATHS[data['form']]
    scope = {**request.scope, 'method': 'GET', 'path': path, 'raw_path': path.encode('ascii'),
             'query_string': data['query'].encode('ascii'), 'state': {'pdf_render': True, 'runtime_env': 'production'}}
    view_request = Request(scope)
    if data['form'] == 'compiled':
        from app.customer_seo import compiled_page
        response = await compiled_page(view_request)
    elif data['form'] == 'facebook_content':
        from app.customer_meta import page
        response = await page(view_request, report=True)
    else:
        from app.customer_data import page
        response = await page(view_request)
    if response.status_code != 200:
        raise CustomerError(401 if response.status_code == 303 else response.status_code,
                            'Chưa thể mở lại báo cáo để tạo PDF. Hãy tải lại trang.')
    review = getattr(response, 'context', {}).get('report_review') or {}
    if review.get('report_key') != data['report_key']:
        raise CustomerError(409, 'Bản dữ liệu hoặc kỳ đối chiếu đã thay đổi. Tải lại báo cáo trước khi xuất PDF.')
    if review.get('load_error'):
        raise CustomerError(503, 'Chưa tải được nhận xét đã chốt. Hãy thử xuất PDF lại.')
    finalized_at = review['updated_at'] if review['status'] == 'finalized' else None
    return response.body, path, finalized_at


async def check_review(request, workspace_id, data, finalized_at):
    from app.customer_report_notes import saved_review

    scope = {'workspace_id': workspace_id, 'client_id': data['client_id']}
    saved = await saved_review(request, scope, data['report_key'])
    current = saved['updated_at'] if saved['status'] == 'finalized' else None
    if current != finalized_at:
        raise CustomerError(409, 'Nhận xét vừa được chốt. Bấm Xuất PDF lại để lấy bản mới nhất.')


async def render_pdf(html, path):
    from playwright.async_api import async_playwright

    async def serve(route):
        url = urlsplit(route.request.url)
        if url.scheme == 'https' and url.netloc == 'vio-pdf.invalid' and route.request.method == 'GET':
            if route.request.is_navigation_request() and url.path == path:
                await route.fulfill(body=html, content_type='text/html; charset=utf-8')
                return
            if url.path.startswith('/static/') and not route.request.is_navigation_request():
                asset = (STATIC / unquote(url.path[len('/static/'):])).resolve()
                if (asset.is_relative_to(STATIC) and asset.is_file()
                        and (route.request.resource_type != 'script' or url.path in REPORT_SCRIPTS)):
                    await route.fulfill(path=str(asset))
                    return
        await route.abort()

    executable = os.getenv('CUSTOMER_PDF_BROWSER') or shutil.which('chromium')
    if not executable:
        raise CustomerError(503, 'Dịch vụ tạo PDF chưa sẵn sàng. Bạn có thể dùng nút In.')
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(executable_path=executable, headless=True, timeout=12000,
            args=['--disable-background-networking', '--disable-gpu', '--no-proxy-server', '--host-resolver-rules=MAP * ~NOTFOUND'])
        try:
            context = await browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='vi-VN',
                                                reduced_motion='reduce', service_workers='block')
            await context.route('**/*', serve)
            tab = await context.new_page()
            await tab.goto(ORIGIN + path, wait_until='load', timeout=18000)
            await tab.evaluate('document.fonts.ready')
            await tab.locator('#customer-main').wait_for(state='attached', timeout=3000)
            return await tab.pdf(format='A4', print_background=True, prefer_css_page_size=True)
        finally:
            await browser.close()


@router.post('/api/customer/workspaces/{workspace_id}/reports/pdf')
async def create_pdf(request: Request, workspace_id: str):
    try:
        data = await read_body(request)
        if (set(data) != {'client_id', 'form', 'report_id', 'report_key', 'query', 'proof'} or not valid_scope(workspace_id, data)
                or not valid(HEX_DIGEST, data['report_key']) or not valid(HEX_DIGEST, data['proof'])
                or not isinstance(data['query'], str) or not data['query'].isascii() or len(data['query']) > 700):
            raise CustomerError(422, 'Thông tin xuất PDF chưa hợp lệ.')
        settings, token = configuration(request), request.cookies.get(SESSION, '')
        proof = data.pop('proof')
        if not token or not hmac.compare_digest(proof, sign(settings, token, 'render', workspace_id, data)):
            raise CustomerError(403, 'Phạm vi báo cáo đã thay đổi. Hãy mở lại báo cáo.')
        try:
            await asyncio.wait_for(RENDER_SLOTS.acquire(), timeout=4)
        except TimeoutError:
            raise CustomerError(503, 'Vio đang tạo một PDF khác. Hãy thử lại sau ít giây.') from None
        try:
            async with asyncio.timeout(45):
                html, path, finalized_at = await report_document(request, data)
                output = await render_pdf(html, path)
                await check_review(request, workspace_id, data, finalized_at)
        except CustomerError:
            raise
        except Exception as error:
            logger.warning('Customer PDF export failed (%s)', type(error).__name__)
            raise CustomerError(503, 'Chưa tạo được tệp PDF. Hãy thử lại hoặc dùng nút In.') from None
        finally:
            RENDER_SLOTS.release()
        if not (1000 < len(output) <= 24 * 1024 * 1024 and output.startswith(b'%PDF-') and output.rstrip().endswith(b'%%EOF')):
            raise CustomerError(502, 'Tệp PDF chưa hoàn chỉnh. Hãy thử xuất lại.')
        nonce, expires = uuid4().hex, int(time.time()) + 600
        receipt = {**{key: data[key] for key in ('client_id', 'form', 'report_id')}, 'request_id': nonce, 'expires': expires}
        signature = sign(settings, token, 'saved', workspace_id, receipt)
        return Response(output, media_type='application/pdf', headers={**HEADERS,
            'Content-Disposition': 'attachment; filename="Vio-Bao-cao.pdf"',
            'X-Vio-PDF-Receipt': f'{nonce}.{expires}.{signature}'})
    except CustomerError as error:
        return error_response(error)


@router.post('/api/customer/workspaces/{workspace_id}/reports/pdf/saved')
async def confirm_saved(request: Request, workspace_id: str):
    try:
        data = await read_body(request)
        if set(data) != {'client_id', 'form', 'report_id', 'receipt'} or not valid_scope(workspace_id, data):
            raise CustomerError(422, 'Thông tin lưu PDF chưa hợp lệ.')
        value = data.pop('receipt')
        match = RECEIPT.fullmatch(value) if isinstance(value, str) else None
        if not match or int(match[2]) < int(time.time()):
            raise CustomerError(403, 'Phiên xác nhận PDF đã hết hạn.')
        token = request.cookies.get(SESSION, '')
        data['request_id'] = match[1]
        expected = sign(configuration(request), token, 'saved', workspace_id, {**data, 'expires': int(match[2])})
        if not token or not hmac.compare_digest(match[3], expected):
            raise CustomerError(403, 'Phiên xác nhận PDF không thuộc báo cáo này.')
        saved = await backend(request, 'POST', f'/workspaces/{workspace_id}/notifications/pdf-saved', data)
        if saved.get('recorded') is not True:
            raise CustomerError(502, 'Chưa cập nhật được chuông thông báo.')
        return JSONResponse({'recorded': True}, headers=HEADERS)
    except CustomerError as error:
        return error_response(error)
