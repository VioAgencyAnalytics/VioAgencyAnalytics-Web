"""BFF and presentation for the common, private connector data contract."""
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
import math
import re
import secrets
from urllib.parse import urlencode

from fastapi.responses import JSONResponse, RedirectResponse

from app.customer_auth import (BINDING, HEADERS, CustomerError, backend, browser_binding,
    configuration, error_response, set_cookie)
from app.routes.pages import templates
from app.customer_transport import PROVIDERS


SOURCES = frozenset(PROVIDERS)
STATES = frozenset(('no_client', 'not_connected', 'planned', 'select_asset', 'syncing', 'sync_error', 'empty', 'ready', 'invalid', 'future_period'))
UNITS = frozenset(('count', 'number', 'percent', 'currency'))


def invalid():
    raise CustomerError(502, 'Dữ liệu connector không hợp lệ.', 'snapshot_invalid')


def string(value, limit=500):
    if not isinstance(value, str) or len(value) > limit:
        invalid()
    return value


def numeric(value, unit, *, bounded_rate=True):
    if value is None:
        return None
    if unit == 'currency' and isinstance(value, str):
        try:
            amount = Decimal(value)
            if len(value) > 60 or not amount.is_finite() or amount < 0:
                invalid()
            return value
        except InvalidOperation:
            invalid()
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if (not finite or value < 0 or (unit == 'percent' and bounded_rate and value > 1)):
        invalid()
    return value


def rows(value, limit):
    if not isinstance(value, list) or len(value) > limit or any(not isinstance(r, dict) for r in value):
        invalid()
    return value


def scalar_record(value, fields):
    if value is None:
        return None
    if not isinstance(value, dict):
        invalid()
    result = {key: value.get(key) for key in fields}
    if any(v is not None and type(v) not in (str, int) for v in result.values()):
        invalid()
    return result


def connector(value, source):
    if not isinstance(value, dict) or value.get('id') != source or value.get('mapping_version') != 1:
        invalid()
    result = {k: string(value.get(k), 150) for k in ('id', 'name', 'icon', 'color', 'asset_label', 'provider', 'mapping_status')}
    result.update(mapping_version=1, adapter_ready=value.get('adapter_ready') is True, application_owner='vio')
    result['metrics'] = []
    for row in rows(value.get('metrics'), 20):
        if row.get('unit') not in UNITS:
            invalid()
        result['metrics'].append({k: string(row.get(k), 150) for k in ('key', 'label', 'unit', 'field', 'aggregation', 'grain')})
    # Capabilities are deliberately closed until a separate publication flow exists.
    result['capabilities'] = {'saved_data': result['adapter_ready'], 'live_provider_reads': False, 'publish': False, 'export': False}
    return result


def project(payload, workspace_id, *, summary=False):
    if (not isinstance(payload, dict) or payload.get('source') not in SOURCES or payload.get('state') not in STATES
            or not isinstance(payload.get('scope'), dict) or payload['scope'].get('workspace_id') != workspace_id):
        raise CustomerError(502, 'Dữ liệu nguồn trả về không đúng phạm vi.', 'snapshot_scope')
    scope = {k: payload['scope'].get(k) for k in ('workspace_id', 'client_id')}
    if scope['client_id'] is not None and not re.fullmatch(r'[a-f0-9]{32}', string(scope['client_id'], 32)):
        invalid()
    result = {'schema_version': 1, 'mapping_version': 1, 'source': payload['source'], 'scope': scope,
              'state': payload['state'], 'published': False, 'connector': connector(payload.get('connector'), payload['source'])}
    if payload.get('availability') not in ('available', 'not_configured', 'planned'):
        invalid()
    result['availability'] = payload['availability']
    for key, fields in {'asset': ('id', 'name', 'external_id'),
        'snapshot': ('id', 'created_at', 'start_date', 'end_date', 'fetched_at', 'timezone', 'currency'),
        'latest_sync': ('id', 'status', 'start_date', 'end_date', 'created_at', 'finished_at', 'error_code')}.items():
        result[key] = scalar_record(payload.get(key), fields)
    if result['latest_sync'] and result['latest_sync'].get('error_code') is not None:
        safe_errors = {'provider_reauth', 'provider_rate_limit', 'provider_scopes', 'provider_page_limit',
                       'provider_bad_response', 'provider_timeout', 'provider_unavailable',
                       'provider_setup_required', 'provider_account_required', 'sync_cancelled', 'worker_interrupted'}
        if result['latest_sync']['error_code'] not in safe_errors:
            result['latest_sync']['error_code'] = 'provider_unavailable'
    specs = {r['key']: r for r in result['connector']['metrics']}
    ads = result['source'] in ('facebook_ads', 'google_ads', 'tiktok_ads')
    result['metrics'] = []
    for metric in rows(payload.get('metrics'), 20):
        key, unit = metric.get('key'), metric.get('unit')
        if key not in specs or unit != specs[key]['unit'] or metric.get('status') not in ('available', 'no_data', 'partial'):
            invalid()
        result['metrics'].append({**{k: specs[key][k] for k in ('key', 'label', 'unit', 'aggregation', 'grain')},
            'value': numeric(metric.get('value'), unit, bounded_rate=not (ads and key == 'ctr')), 'status': metric['status'],
            'currency': string(metric['currency'], 3) if metric.get('currency') is not None else None})
    if result['state'] == 'ready' and (not scope['client_id'] or not result['asset'] or not result['snapshot']):
        invalid()
    from app.customer_report_controls import project as controls
    result.update(controls(payload,result['connector']['metrics'],result['metrics'],result['asset'],result['snapshot']))
    if summary:
        return result
    if payload.get('schema_version') != 1 or payload.get('mapping_version') != 1:
        invalid()
    result['client'] = scalar_record(payload.get('client'), ('id', 'name'))
    if (result['client']['id'] if result['client'] else None) != scope['client_id']:
        invalid()
    result['connection'] = scalar_record(payload.get('connection'), ('id', 'version', 'status'))
    result['periods'] = [scalar_record(p, ('id', 'created_at', 'start_date', 'end_date')) for p in rows(payload.get('periods'), 30)]
    result['daily'] = []
    for row in rows(payload.get('daily'), 90):
        stamp = string(row.get('date'), 10)
        try:
            if date.fromisoformat(stamp).isoformat() != stamp:
                invalid()
        except ValueError:
            invalid()
        if not isinstance(row.get('values'), dict) or set(row['values']) - set(specs):
            invalid()
        result['daily'].append({'date': stamp, 'values': {
            key: numeric(v, specs[key]['unit'], bounded_rate=not (ads and key == 'ctr')) for key, v in row['values'].items()}})
    result['tables'] = []
    for table in rows(payload.get('tables'), 5):
        columns = []
        for col in rows(table.get('columns'), 12):
            if col.get('unit') not in UNITS | {'text'}:
                invalid()
            columns.append({k: string(col.get(k), 150) for k in ('key', 'label', 'unit')})
        if type(table.get('total_rows')) is not int or table['total_rows'] < 0:
            invalid()
        values = [{col['key']: (string(r[col['key']], 500) if r.get(col['key']) is not None else None) if col['unit'] == 'text' else numeric(r.get(col['key']), col['unit'])
                   for col in columns} for r in rows(table.get('rows'), 200)]
        result['tables'].append({'id': string(table.get('id'), 100), 'title': string(table.get('title'), 150),
            'columns': columns, 'rows': values, 'total_rows': table['total_rows'], 'truncated': table.get('truncated') is True})
    notes = payload.get('notes')
    if not isinstance(notes, list) or len(notes) > 12:
        invalid()
    result['notes'] = [string(n, 500) for n in notes]
    return result


def project_index(payload, workspace_id):
    if (not isinstance(payload, dict) or payload.get('schema_version') != 1
            or not isinstance(payload.get('scope'), dict) or payload['scope'].get('workspace_id') != workspace_id):
        invalid()
    sources = [project(row, workspace_id, summary=True) for row in rows(payload.get('sources'), 9)]
    if {r['source'] for r in sources} != SOURCES or len(sources) != 9 or any(r['scope'] != payload['scope'] for r in sources):
        invalid()
    return {'schema_version': 1, 'scope': sources[0]['scope'], 'sources': sources, 'published': False}


def query(request, *, page=False):
    from app.customer_report_controls import query as report_query
    return report_query(request,include_source=page,include_template=page)


async def read(request, workspace_id, source=None):
    try:
        if not re.fullmatch(r'[a-f0-9]{32}', workspace_id) or (source is not None and source not in SOURCES):
            raise CustomerError(404, 'Không tìm thấy nguồn dữ liệu.')
        if source is None and request.query_params:
            raise CustomerError(422, 'Bộ lọc danh mục không hợp lệ.', 'snapshot_input')
        suffix = '/'+source+query(request) if source else ''
        payload = await backend(request, 'GET', '/workspaces/'+workspace_id+'/data'+suffix)
        if source and payload.get('source') != source:
            raise CustomerError(502, 'Connector trả về không đúng nguồn.', 'snapshot_scope')
        result = project(payload, workspace_id) if source else project_index(payload, workspace_id)
        if source:
            from app.customer_comparisons import assert_period, attach
            wanted = {key: request.query_params[key] for key in ('start', 'end') if key in request.query_params}
            assert_period(result, wanted)
            await attach(request, result, '/workspaces/'+workspace_id+'/data/'+source, project)
        return JSONResponse(result, headers=HEADERS)
    except CustomerError as error:
        return error_response(error)


def display(value, unit='number', currency=None):
    if value is None or isinstance(value, bool):
        return '—'
    try:
        with localcontext() as context:
            context.prec = 100
            number = Decimal(str(value))
            if not number.is_finite() or number < 0:
                return '—'
            if unit == 'percent':
                number *= 100
            # Currency precision never changes fractional conversions, minutes,
            # position or rates in a VND account's detail table.
            digits = 0 if unit == 'currency' and currency == 'VND' or unit == 'count' and number == number.to_integral_value() else 2
            quantum = Decimal(1).scaleb(-digits)
            rounded = number.quantize(quantum, rounding=ROUND_HALF_EVEN)
            suffix = '%' if unit == 'percent' else ' '+currency if unit == 'currency' and currency else ''
            if 0 < number < quantum:
                return ('<1' if digits == 0 else '<0,01') + suffix
            formatted = f'{rounded:,.{digits}f}'.replace(',', '_').replace('.', ',').replace('_', '.')
            if unit != 'currency' and ',' in formatted:
                formatted = formatted.rstrip('0').rstrip(',')
            return formatted + suffix
    except (InvalidOperation, ValueError):
        return '—'


async def page(request, source=None):
    try:
        settings = configuration(request)
        suffix = query(request, page=source is None)
        source = source or request.query_params.get('source', 'ga4')
        if source not in SOURCES:
            raise CustomerError(404, 'Không tìm thấy connector.')
        from app.customer_report_presets import get_preset
        from app.customer_report_styles import style_context
        preset = get_preset(source, request.query_params.get('template'))
        styling = style_context(request.query_params.get('style'), request.query_params.get('palette'), preset,
                                request.query_params.get('order'), request.query_params.get('hidden'))
        try:
            account = await backend(request, 'GET', '/session')
        except CustomerError as error:
            if error.status == 401:
                return RedirectResponse('/workspace/login', 303, headers=HEADERS)
            raise
        if not account.get('workspace'):
            return RedirectResponse('/workspace/onboarding', 303, headers=HEADERS)
        workspace_id = account['workspace']['id']
        details = await backend(request, 'GET', '/workspaces/'+workspace_id)
        report = project(await backend(request, 'GET', '/workspaces/'+workspace_id+'/data/'+source+suffix), workspace_id)
        if report['source'] != source:
            raise CustomerError(502, 'Connector trả về không đúng nguồn.', 'snapshot_scope')
        catalogue = await backend(request, 'GET', '/workspaces/'+workspace_id+'/integrations')
        selected = details.get('selected_client')
        if details.get('workspace', {}).get('id') != workspace_id or (selected['id'] if selected else None) != report['scope']['client_id']:
            raise CustomerError(409, 'Khách hàng đã thay đổi. Vui lòng tải lại.', 'client_changed')
        if catalogue.get('workspace', {}).get('id') != workspace_id or (catalogue['selected_client']['id'] if catalogue.get('selected_client') else None) != report['scope']['client_id']:
            raise CustomerError(409, 'Khách hàng đã thay đổi. Vui lòng tải lại.', 'client_changed')
        from app.customer_comparisons import assert_period, attach
        assert_period(report, {key: request.query_params[key] for key in ('start', 'end') if key in request.query_params})
        await attach(request, report, '/workspaces/'+workspace_id+'/data/'+source, project)
        connectors = [{'id': p['id'], 'name': string(p['name'], 150)} for p in catalogue.get('platforms', []) if p.get('id') in SOURCES]
        from app.customer_report_view import build as report_view
        from app.customer_report_notes import attach as attach_notes, platform_reference
        from app.report_commentary import platform
        view = report_view(report)
        focus = None
        if preset:
            from app.customer_report_focus import focus_report
            focus, sections = focus_report(preset, report, view['layout'])
        else:
            sections = platform(report, view['layout'])
        review = await attach_notes(request, settings, report['scope'], platform_reference(report, 'platform', preset), sections)
        response = templates.TemplateResponse(request=request, name='customer/live/data-report.html',
            context={'title': report['connector']['name'], 'customer_page': 'reports', 'customer_live': True,
                'customer_data_live': True, 'account': account, 'details': details, 'report': report, 'view': view,
                'display': display, 'connectors': connectors, 'report_review': review, 'report_preset': preset,
                'report_focus': focus, **styling}, headers=HEADERS)
        if not browser_binding(request):
            set_cookie(response, BINDING, secrets.token_urlsafe(48), settings)
        return response
    except CustomerError as error:
        return templates.TemplateResponse(request=request, name='customer/live/error.html',
            context={'title': 'Dữ liệu nền tảng', 'customer_page': 'error', 'customer_live': True, 'message': error.message},
            status_code=error.status, headers=HEADERS)
