"""Customer dashboard composition from allowlisted, immutable saved-data DTOs.

No provider calls, cross-platform grand totals, daily unique-user summation, or
currency conversion. The four existing display positions follow one source.
"""
from datetime import date, timedelta
from decimal import Decimal, localcontext
from urllib.parse import urlencode
import re

from fastapi.responses import JSONResponse

from app.customer_auth import HEADERS, CustomerError, backend, error_response
from app.customer_data import SOURCES, project, project_index
from app.customer_report_view import MEANINGS, SPECIFIC_MEANINGS


SLOTS = ('spend', 'impressions', 'clicks', 'conversions')
FOCUS = {
    'facebook_content': ('posts_published', 'reactions_lifetime', 'comments_lifetime', 'shares_lifetime'),
    'facebook_ads': ('spend', 'impressions', 'clicks', 'leads'),
    'google_ads': ('spend', 'impressions', 'clicks', 'conversions'),
    'tiktok_ads': ('spend', 'impressions', 'clicks', 'conversions'),
    'ga4': ('active_users', 'sessions', 'page_views', 'engagement_rate'),
    'gsc': ('clicks', 'impressions', 'ctr', 'position'),
    'youtube': ('views', 'watch_minutes', 'subscribers_gained', 'average_view_seconds'),
    'instagram': ('posts_published', 'likes_lifetime', 'comments_lifetime', 'followers'),
    'business_profile': ('website_clicks', 'call_clicks', 'directions', 'maps_mobile'),
}


def report_href(source, snapshot=None, period=None, comparison=None):
    path = '/workspace/reports/facebook-content' if source == 'facebook_content' else '/workspace/reports/data'
    values = {} if source == 'facebook_content' else {'source': source}
    if period:
        values.update(start=period['start'], end=period['end'])
    elif snapshot:
        values['snapshot'] = snapshot['id']
    if comparison and comparison['mode'] != 'none':
        values['comparison'] = comparison['mode']
        if comparison['mode'] == 'custom' and comparison.get('period'):
            values.update(comparison_start=comparison['period']['start'], comparison_end=comparison['period']['end'])
    return path + ('?' + urlencode(values) if values else '')


def filters(request):
    from app.customer_comparisons import PARAMETERS, parameters
    values = request.query_params
    if set(values) - ({'source', 'start', 'end', 'granularity'} | PARAMETERS) or any(len(values.getlist(key)) != 1 for key in values):
        raise CustomerError(422, 'Bộ lọc Dashboard không hợp lệ.', 'report_period_input')
    source = values.get('source', 'all')
    comparison, custom = parameters(values)
    granularity = values.get('granularity', 'day')
    if source not in SOURCES | {'all'} or granularity not in ('day','week','month'):
        raise CustomerError(422, 'Nguồn hoặc kỳ so sánh không hợp lệ.', 'report_period_input')
    start, end = values.get('start'), values.get('end')
    if start is not None or end is not None:
        try:
            first, last = date.fromisoformat(start), date.fromisoformat(end)
            if first.isoformat() != start or last.isoformat() != end or first > last or (last-first).days > 89:
                raise ValueError()
        except (ValueError, TypeError):
            raise CustomerError(422, 'Chọn kỳ hợp lệ, tối đa 90 ngày.', 'report_period_input') from None
    return source, {'start': start, 'end': end} if start else None, comparison, granularity, custom


def group_points(points, spec, granularity):
    if granularity == 'day':
        return points
    # A daily unique count or ratio cannot yield a weekly unique count/ratio.
    if spec['aggregation'] not in ('sum','decimal_sum','sum_complete_days'):
        return []
    groups = {}
    for point in points:
        day = date.fromisoformat(point['date'])
        label = (day-timedelta(days=day.weekday())).isoformat() if granularity == 'week' else day.replace(day=1).isoformat()
        groups.setdefault(label,[]).append(point)
    with localcontext() as context:
        context.prec = 100
        result=[]
        for rows in groups.values():
            values=[row['value'] for row in rows]
            value=sum(Decimal(str(item)) for item in values) if all(item is not None for item in values) else None
            result.append({'date':rows[0]['date'], 'value':None if value is None else format(value,'f') if spec['unit']=='currency' else int(value) if value==value.to_integral_value() else float(value)})
        return result


def compose(index, catalogue, report, previous=None, granularity='day'):
    sources = index['sources']
    focused = report['source'] if report else None
    output = {'schema_version': 1, 'scope': index['scope'], 'focus': focused, 'period': report.get('period') if report else None,
              'snapshot': report.get('snapshot') if report else None, 'source_name': report['connector']['name'] if report else '',
              'calendar': report.get('calendar') if report else None,
              'asset_name': report['asset']['name'] if report and report.get('asset') else '',
              'state': report['state'] if report else 'empty', 'metrics': {}, 'trends': {}, 'sources': [], 'reports': [],
              'connections': [], 'campaigns': [], 'report_href': report_href(focused, snapshot=report.get('snapshot'),
                  period=report.get('period') if report.get('period',{}).get('mode')=='custom' else None,
                  comparison=report.get('comparison')) if report else None,
              'last_updated_at': (report.get('snapshot') or {}).get('fetched_at') if report else None,
              'published': False, 'comparison_available': bool(previous and previous.get('snapshot')),
              'comparison': report.get('comparison') if report else None}
    for row in catalogue.get('connections', []):
        if (row.get('workspace_id'), row.get('client_id')) != (index['scope']['workspace_id'], index['scope']['client_id']):
            raise CustomerError(409, 'Phạm vi dữ liệu đã thay đổi. Vui lòng tải lại.', 'client_changed')
        output['connections'].append({key: row.get(key) for key in ('workspace_id', 'client_id', 'platform_id', 'state')})
    for source in sources:
        snapshot = source.get('snapshot')
        item = {key: source[key] for key in ('source', 'state', 'asset', 'snapshot', 'metrics')}
        item['name'] = source['connector']['name']
        item['href'] = report_href(source['source'], snapshot) if snapshot else '/workspace/integrations?platform='+source['source']
        item['latest_sync_failed'] = (source.get('latest_sync') or {}).get('status') == 'failed'
        output['sources'].append(item)
        if snapshot:
            output['reports'].append({'source': source['source'], 'name': item['name'], 'asset_name': (source['asset'] or {}).get('name'),
                'start': snapshot['start_date'], 'end': snapshot['end_date'], 'created_at': snapshot['created_at'], 'href': item['href'],
                'status': 'saved', 'latest_sync_failed': item['latest_sync_failed']})
    output['reports'].sort(key=lambda row: (row['created_at'], row['source']), reverse=True)
    if not report:
        return output
    metrics = {item['key']: item for item in report['metrics']}
    specs = {item['key']: item for item in report['connector']['metrics']}
    goals = {item['key']: item for item in report['targets']['items']}
    old = {item['key']: item for item in previous['metrics']} if previous and previous.get('snapshot') else {}
    changes = {item['key']: item for item in (report.get('comparison') or {}).get('items', [])}
    for slot, key in zip(SLOTS, FOCUS[focused]):
        spec = specs.get(key)
        if not spec:
            continue
        metric = metrics.get(key, {})
        currency = metric.get('currency')
        prior = old.get(key, {})
        # Stock/lifetime values are observations at fetch time, not comparable
        # in-period growth. Never label their delta as previous-period growth.
        prior_value = prior.get('value') if spec['grain'] != 'snapshot' and prior.get('currency') == currency else None
        meaning = SPECIFIC_MEANINGS.get((focused, key), MEANINGS.get(spec['aggregation'], 'Theo định nghĩa nguồn.'))
        goal = goals.get(key)
        output['metrics'][slot] = {key: spec[key] for key in ('key', 'label', 'unit', 'grain', 'aggregation')}
        output['metrics'][slot].update(value=metric.get('value'), previous=prior_value, currency=currency, hint=meaning,
            status='ready' if metric.get('value') is not None else 'empty', source_label=output['source_name'],
            comparison=changes.get(key),
            target={key: goal.get(key) for key in ('status', 'direction', 'value', 'ratio', 'currency', 'assessment')} if goal else None)
        points = [{'date': row['date'], 'value': row['values'].get(key)} for row in report['daily']]
        # Supply every day explicitly so the chart cannot bridge missing days.
        if report.get('snapshot') and spec['grain'] != 'snapshot':
            first, last = date.fromisoformat(report['snapshot']['start_date']), date.fromisoformat(report['snapshot']['end_date'])
            known = {point['date']: point['value'] for point in points}
            points = [{'date': (first+timedelta(days=offset)).isoformat(), 'value': known.get((first+timedelta(days=offset)).isoformat())}
                      for offset in range((last-first).days+1)]
        else:
            points = []
        points = group_points(points, spec, granularity)
        output['trends'][slot] = {'status': 'ready' if any(point['value'] is not None for point in points) else 'empty',
                                  'points': points, 'currency': currency, 'unit': spec['unit']}
    # Preserve campaign daily rows, rather than inventing campaign budgets,
    # statuses or all-period totals from a truncated daily table.
    if focused in ('facebook_ads', 'google_ads'):
        table = next((item for item in report['tables'] if item['id'] == 'campaigns'), None)
        if table:
            output['campaigns_truncated'] = table['truncated']
            for number, row in enumerate(table['rows']):
                output['campaigns'].append({'id': str(number), 'name': row.get('campaign_name') or row.get('campaign') or 'Chiến dịch',
                    'date': row.get('date'), 'platform_id': focused, 'workspace_id': index['scope']['workspace_id'],
                    'client_id': index['scope']['client_id'], 'state': 'unknown', 'data_status': 'ready',
                    'currency': (report['snapshot'] or {}).get('currency'),
                    'result_label': 'Lead' if focused == 'facebook_ads' else 'Chuyển đổi',
                    'values': {'spend': row.get('spend_decimal') if focused == 'facebook_ads' else row.get('spend'),
                               'clicks': row.get('clicks'), 'conversions': row.get('leads') if focused == 'facebook_ads' else row.get('conversions')}})
    return output


async def read(request, workspace_id):
    try:
        if not re.fullmatch(r'[a-f0-9]{32}', workspace_id):
            raise CustomerError(404, 'Không tìm thấy Workspace.')
        source, period, comparison, granularity, custom = filters(request)
        base = '/workspaces/'+workspace_id
        index = project_index(await backend(request, 'GET', base+'/data'), workspace_id)
        catalogue = await backend(request, 'GET', base+'/integrations')
        selected = (catalogue.get('selected_client') or {}).get('id')
        if catalogue.get('workspace', {}).get('id') != workspace_id or selected != index['scope']['client_id']:
            raise CustomerError(409, 'Khách hàng đã thay đổi. Vui lòng tải lại.', 'client_changed')
        if source == 'all':
            ready = [row for row in index['sources'] if row['state'] == 'ready' and row.get('snapshot')]
            ready.sort(key=lambda row: (row['snapshot']['created_at'], row['source']), reverse=True)
            source = ready[0]['source'] if ready else None
        report = previous = None
        if source and selected:
            suffix = '?'+urlencode(period) if period else ''
            report = project(await backend(request, 'GET', base+'/data/'+source+suffix), workspace_id)
            if report['scope'] != index['scope'] or report['source'] != source:
                raise CustomerError(409, 'Phạm vi báo cáo đã thay đổi.', 'client_changed')
            if period and any(report.get('period',{}).get(key)!=value for key,value in period.items()):
                raise CustomerError(502, 'Báo cáo trả về không đúng kỳ đang chọn.', 'snapshot_scope')
            from app.customer_comparisons import attach
            previous = await attach(request, report, base+'/data/'+source, project, mode=comparison, custom=custom)
        current = await backend(request, 'GET', base)
        if current.get('workspace', {}).get('id') != workspace_id or (current.get('selected_client') or {}).get('id') != selected:
            raise CustomerError(409, 'Khách hàng đã thay đổi. Vui lòng tải lại.', 'client_changed')
        return JSONResponse(compose(index, catalogue, report, previous, granularity), headers=HEADERS)
    except CustomerError as error:
        return error_response(error)
