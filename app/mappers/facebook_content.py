"""Validate and copy the Admin-owned content contract; no metric calculation."""
from copy import deepcopy
from datetime import datetime
from math import isfinite
from urllib.parse import urlsplit, parse_qs

from app.repositories.admin_bundle import AdminBundleContractError


def content_report(raw, source, period, released):
    if raw is None:
        return {}
    def require(condition):
        if not condition:
            raise AdminBundleContractError('Cấu trúc Facebook Content không khớp bản phát hành.')
    require(isinstance(raw, dict) and raw.get('schema_version') == 'facebook-content-report-v1')
    require(raw.get('source') == 'facebook_content' and raw.get('identity') == source.get('identity'))
    require(raw.get('period') == period and raw.get('timezone') == source.get('timezone'))
    require(raw.get('fetched_at') == source.get('fetched_at'))
    require(raw.get('review_status') == ('approved' if released else 'pending_review'))
    sections = raw.get('sections')
    require(isinstance(sections, dict) and set(sections) == {'overview', 'formats', 'topics', 'posts', 'engagement', 'reach', 'insights'})
    for key, item in sections.items():
        require(isinstance(item, dict) and item.get('key') == key and isinstance(item.get('rows'), list))
        require(item.get('status') in ('available', 'partial', 'unsupported', 'no_data', 'pending_review'))
        note = item.get('commentary')
        if note is not None:
            require(isinstance(note, dict) and note.get('origin') == 'editorial' and isinstance(note.get('text'), str))
            require(note.get('status') == ('approved' if released else 'pending_review'))
        if key in ('formats', 'topics'):
            for row in item['rows']:
                require(isinstance(row, dict) and isinstance(row.get('label'), str))
                require(type(row.get('count')) is int and row['count'] >= 0)
                require(type(row.get('percent')) in (int, float) and isfinite(row['percent']) and 0 <= row['percent'] <= 100)
    original = {row['post_id']: row for row in source.get('entries', [])}
    rows = sections['posts']['rows']
    require(all(isinstance(row, dict) and isinstance(row.get('post_id'), str) for row in rows))
    require(len(rows) == len(original) and {row['post_id'] for row in rows} == set(original))
    insights = validate_insights(raw.get('insights'), source, period, require)
    for row in rows:
        saved = original[row['post_id']]
        require(all(row.get(k) == saved.get(k) for k in ('date', 'title', 'message', 'format',
                    'reactions_lifetime', 'comments_lifetime', 'shares_lifetime')))
        require(all(row.get(k) is None for k in ('reach', 'engagements', 'engagement_rate', 'link_clicks')))
        for metric in ('post_media_view', 'post_total_media_view_unique'):
            measurement = insights.get((row['post_id'], metric))
            require(row.get(metric + '_lifetime') == (measurement['value'] if measurement else None))
        url = row.get('permalink_url')
        if url is not None:
            require(isinstance(url, str))
            try:
                parsed = urlsplit(url)
                page, post = row['post_id'].split('_', 1)
                query = parse_qs(parsed.query)
                require(parsed.scheme == 'https' and parsed.hostname == 'www.facebook.com'
                        and not parsed.username and not parsed.password and parsed.port in (None, 443)
                        and page == source['identity']['external_id']
                        and (parsed.path == f'/{page}/posts/{post}' or
                             (parsed.path == '/permalink.php' and query == {'story_fbid': [post], 'id': [page]})))
            except ValueError:
                require(False)
    return deepcopy(raw)


def validate_insights(projected, source, period, require):
    """Validate saved measurements and copy Admin's projection; never compute KPIs."""
    saved = source.get('insights')
    if projected is None:
        require(saved is None)
        return {}
    catalog = {
        'page_media_view': ('page', 'day', 'sum_exact_intervals'),
        'page_total_media_view_unique': ('page', 'day', 'non_additive'),
        'page_post_engagements': ('page', 'day', 'sum_exact_intervals'),
        'page_follows': ('page', 'day', 'stock_non_additive'),
        'post_media_view': ('post', 'lifetime', 'per_post_snapshot'),
        'post_total_media_view_unique': ('post', 'lifetime', 'non_additive'),
    }
    statuses = {'available', 'partial', 'permission_denied', 'task_missing', 'version_unconfirmed',
                'invalid_token', 'invalid_metric_or_parameter', 'transport_error', 'invalid_response',
                'empty_unconfirmed', 'budget_exhausted', 'pagination_incomplete'}
    require(isinstance(saved, dict) and isinstance(projected, dict))
    require(saved.get('schema_version') == 'meta-content-insights-v1')
    require(saved.get('page_id') == source['identity']['external_id'])
    require(saved.get('requested_period') == period and saved.get('report_timezone') == source.get('timezone'))
    require(saved.get('measurement_timezone') == 'provider_end_time')
    require(all(projected.get(k) == v for k, v in saved.items() if k != 'measurements'))
    require(isinstance(saved.get('measurements'), list) and isinstance(projected.get('measurements'), list))
    require(len(saved['measurements']) == len(projected['measurements']) <= 64)
    require(isinstance(saved.get('permissions'), list) and isinstance(saved.get('page_tasks'), list))
    originals = {r['post_id'] for r in source.get('entries', [])}
    found, chart_rows = {}, []
    for raw, row in zip(saved['measurements'], projected['measurements']):
        require(isinstance(raw, dict) and isinstance(row, dict) and raw.get('metric') in catalog)
        require(all(row.get(k) == v for k, v in raw.items() if k != 'reason'))
        scope, measurement_period, aggregation = catalog[raw['metric']]
        require((raw.get('scope'), raw.get('period'), raw.get('aggregation')) == (scope, measurement_period, aggregation))
        require(raw.get('object_id') == saved['page_id'] if scope == 'page' else raw.get('object_id') in originals)
        identity = (raw['object_id'], raw['metric'])
        require(identity not in found)
        found[identity] = row
        require(raw.get('status') in statuses and raw.get('unit') == 'count')
        require(isinstance(raw.get('values'), list) and len(raw['values']) <= (90 if measurement_period == 'day' else 1))
        require(isinstance(row.get('label'), str) and isinstance(row.get('reason'), str))
        require(row.get('report_status') in statuses | {'period_boundary_mismatch'})
        require(row.get('value') is None or type(row['value']) is int and row['value'] >= 0)
        coverage = row.get('coverage')
        require(isinstance(coverage, dict) and type(coverage.get('available')) is int and type(coverage.get('expected')) is int)
        require(coverage['available'] >= 0 and coverage['expected'] >= 0)
        require(coverage.get('unit') == ('days' if measurement_period == 'day' else 'observations'))
        for point in raw['values']:
            require(isinstance(point, dict) and set(point) == {'value', 'end_time'})
            require(point['value'] is None or type(point['value']) is int and point['value'] >= 0)
            if measurement_period == 'day' or point['end_time'] is not None:
                try:
                    require(isinstance(point['end_time'], str) and datetime.fromisoformat(point['end_time'].replace('Z', '+00:00')).tzinfo is not None)
                except (TypeError, ValueError):
                    require(False)
        if raw['values']:
            require({'read_insights', 'pages_read_engagement'}.issubset(saved['permissions']))
            require('ANALYZE' in saved['page_tasks'] and saved.get('graph_version') == 'v26.0')
        if row['report_status'] != 'available':
            require(row['value'] is None)
        elif measurement_period == 'lifetime':
            require(len(raw['values']) == 1 and row['value'] == raw['values'][0]['value'])
        elif aggregation != 'sum_exact_intervals':
            require(row['value'] is None)
        if measurement_period == 'day' and raw['values'] and raw['status'] in ('available', 'partial'):
            chart_rows.append(raw)
    charts = projected.get('charts')
    require(isinstance(charts, list) and len(charts) == len(chart_rows))
    for chart, row in zip(charts, chart_rows):
        require(isinstance(chart, dict) and chart.get('timezone') == 'provider_end_time')
        require(chart.get('labels') == [p['end_time'] for p in row['values']])
        require(chart.get('values') == [p['value'] for p in row['values']])
        require(chart.get('status') == row['status'] and chart.get('unit') == 'count')
        require(chart.get('title') == row['label'] + ' · mốc kết thúc ngày Meta')
        require(chart.get('source') == 'Facebook Page Insights' and chart.get('kind') == 'bar')
    return found
