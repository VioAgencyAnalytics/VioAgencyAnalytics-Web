"""Presentation of frozen reports. Missing observations never become zero."""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from app.customer_data import display
from app.customer_comparisons import metric_change, organic_sessions_metric
from app.customer_metric_semantics import goal_assessment


def rank_bands(rows, rank='rank', state='state'):
    bands = [0] * 6
    for row in rows:
        value = row.get(rank)
        if value is None:
            band = 4 if row.get(state) == 'outside_top100' else 5
        else:
            band = sum(value > ceiling for ceiling in (10, 20, 30, 100))
        bands[band] += 1
    return bands


def rank_overview(rows, period):
    first_page, second, third, fourth_to_tenth, outside, unknown = rank_bands(rows)
    title = 'Báo cáo thứ hạng'
    try:
        first = date.fromisoformat(period['start'])
        last = date.fromisoformat(period['end'])
    except (KeyError, TypeError, ValueError):
        pass
    else:
        if (first.year, first.month) == (last.year, last.month) and first.day == 1 and last.day == monthrange(first.year, first.month)[1]:
            title += f' tháng {last.month}/{last.year}'
        else:
            title += f' {first:%d/%m/%Y} – {last:%d/%m/%Y}'
    return {
        'title': title, 'total': len(rows),
        'counts': {'page1': first_page, 'pages2_3': second + third, 'pages4_10': fourth_to_tenth,
                   'unknown': unknown, 'outside': outside},
    }


def number(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def chart_reading(value, key):
    parsed = number(value)
    return parsed if parsed is not None and parsed >= (1 if key == 'position' else 0) else None


def extra_chart(data, old, metric):
    period = data.get('snapshot') or {}
    first = date.fromisoformat(period.get('start_date') or data['period']['start'])
    last = date.fromisoformat(period.get('end_date') or data['period']['end'])
    key = metric['key']
    position = key == 'position'
    minimum = int(position)
    values = {row['date']:row['values'].get(key) for row in data.get('daily', [])}
    points = [(stamp, reading) for stamp, value in values.items()
              if first.isoformat() <= stamp <= last.isoformat() and (reading := chart_reading(value, key)) is not None]
    if not points:
        return None
    days = (last-first).days+1
    maximum = max(value for _,value in points) or Decimal(1)
    if maximum == minimum:
        maximum += 1
    span = maximum - minimum
    rows = [{'date':(first+timedelta(days=i)).isoformat(),'value':values.get((first+timedelta(days=i)).isoformat())} for i in range(days)]
    previous = []
    prior_metric = next((row for row in old.get('metrics',[]) if row['key'] == metric['key']), None) if old else None
    compatible = prior_metric and prior_metric['unit'] == metric['unit'] and prior_metric.get('currency') == metric.get('currency')
    if compatible:
        old_period = old.get('snapshot') or {}
        old_first = date.fromisoformat(old_period.get('start_date') or old['period']['start'])
        old_last = date.fromisoformat(old_period.get('end_date') or old['period']['end'])
        values_old = {row['date']:row['values'].get(metric['key']) for row in old.get('daily',[])}
        previous = [{'date':(old_first+timedelta(days=i)).isoformat(),'value':values_old.get((old_first+timedelta(days=i)).isoformat())}
                    for i in range((old_last-old_first).days+1)]
    step = 510 / days
    return {'label':metric['label'],'rows':rows,'previous':previous,'kind':'line','unit':metric['unit'],'currency':None,
        'reverse_y':position,
        'first':first.strftime('%d/%m'),'last':last.strftime('%d/%m'),'maximum':display(maximum,metric['unit']),
        'observed':len(points),'days':days,'bars':[{'x':round(66+step*(date.fromisoformat(stamp)-first).days,2),
            'y':round(154-float((value-minimum)/span*132),2),'height':round(float((value-minimum)/span*132),2),'width':max(.5,step*.7),
            'title':stamp+' · '+display(value,metric['unit'])} for stamp,value in points]}


def prepare(compiled):
    seo_sources = [item for item in compiled['sources'] if item['id'] in ('seo', 'ga4', 'gsc')]
    other_sources = [item for item in compiled['sources'] if item['id'] not in ('seo', 'ga4', 'gsc')]
    compiled['sources'] = seo_sources + other_sources
    compiled['chapters'] = []
    if seo_sources:
        compiled['chapters'].append({'id': 'seo-website', 'name': 'SEO & Website'})
        seo_sources[0]['chapter_heading'] = 'SEO & Website'
    compiled['chapters'].extend({'id': item['id'], 'name': item['name']} for item in other_sources)
    for item in compiled['sources']:
        if item['id'] == 'seo':
            report = item['data']
            keywords = report['keywords']
            item['keyword_groups'] = [{'title': title, 'kind': kind, 'rows': [row for row in keywords if select(row)]}
                for title, kind, select in (
                    ('Bộ từ khóa cam kết', 'contract', lambda row: bool(row.get('committed'))),
                    ('Từ khóa ngách · theo dõi mở rộng', 'niche', lambda row: not row.get('committed') and row.get('segment') == 'niche'),
                    ('Từ khóa chính / phụ · theo dõi mở rộng', 'tracked',
                     lambda row: not row.get('committed') and row.get('segment') != 'niche'))]
            present = {source['id']:source['data'] for source in compiled['sources']}
            search = present.get('gsc', {})
            search_rows = next((table['rows'] for table in search.get('tables', []) if table['id'] == 'queries'), [])
            observations = {}
            for row in search_rows:
                observations.setdefault(row['query'], []).append(row)
            for group in item['keyword_groups']:
                group['search'] = bool(group['rows'] and search.get('state') == 'ready'
                    and report.get('effectiveness', {}).get('sources', {}).get('gsc', {}).get('state') != 'wrong_website'
                    and all(row.get('role_origin') == 'gsc' and not row.get('observed_date') for row in group['rows']))
                if group['search']:
                    for row in group['rows']:
                        matches = observations.get(row['keyword'], [])
                        row['search_values'] = matches[0] if len(matches) == 1 else {}
            item['coverage'] = [{'label':label,'available':available,'note':note} for label,available,note in (
                ('GA4 · lưu lượng & thiết bị',present.get('ga4',{}).get('state')=='ready','Google Analytics 4'),
                ('GSC · tìm kiếm & quốc gia',present.get('gsc',{}).get('state')=='ready','Search Console'),
                ('Thứ hạng từ khóa',any(row.get('observed_date') for row in keywords),'Spineditor · file có ngày đo'),
                ('Danh sách bài viết',bool(report.get('content',{}).get('items')),'Website / sổ nội dung'),
                ('Từ khóa ngách / phụ',any(row.get('segment')=='niche' or row['role']=='secondary' for row in keywords),'GSC / phân loại đã quản lý'),
                ('Cam kết & tiến độ dự án',bool(report.get('project',{}).get('plan')),'Phiên bản cam kết và bằng chứng'))]
            item['distribution'] = {'title': 'Phân bố thứ hạng', 'label': 'từ khóa', 'unit': 'count', 'max_slices': 6,
                'rows': [{'label': row['label'], 'value': row['count']} for row in item['data']['distribution']],
                'note': 'Tỷ trọng các nhóm thứ hạng trong bộ từ khóa đang theo dõi.'}
            continue
        data, old = item['data'], item.get('previous')
        devices = next((table['rows'] for table in data.get('tables',[]) if table['id']=='devices'), [])
        item['device_distribution'] = {'title':'Phân bổ phiên theo thiết bị', 'label':'phiên', 'unit':'count', 'max_slices':5,
            'rows':[{'label':{'mobile':'Điện thoại','desktop':'Máy tính','tablet':'Máy tính bảng'}.get(row['deviceCategory'],row['deviceCategory']),
                     'value':row['sessions']} for row in devices],
            'note':'Số phiên theo thiết bị trong bản GA4; không phải tỷ lệ người dùng duy nhất.'} if devices else None
        labels = {metric['key']: metric['label'] for metric in data['metrics']}
        for target in data.get('targets', {}).get('items', []):
            target['label'] = labels.get(target['key'], target['key'])
            target['assessment'] = goal_assessment(target['status'], data.get('period', {}).get('is_open', False))
        previous_metrics = {row['key']: row for row in old['metrics']} if old else {}
        comparable_scope = bool(old and data.get('scope') == old.get('scope') and data.get('source') == old.get('source')
            and data.get('connection') == old.get('connection') and data.get('asset') and old.get('asset')
            and data['asset']['id'] == old['asset']['id'] and data.get('snapshot') and old.get('snapshot')
            and data['snapshot']['timezone'] == old['snapshot']['timezone'])
        item['comparison_label'] = (item.get('comparison') or compiled.get('comparison') or {}).get('label', 'Kỳ liền trước')
        item['current_period'] = {key: data.get('snapshot', {}).get(field) or data['period'][key]
                                  for key, field in (('start', 'start_date'), ('end', 'end_date'))} if data.get('snapshot') else data.get('period')
        item['previous_period'] = {key: old['snapshot'][field] for key, field in (('start', 'start_date'), ('end', 'end_date'))} if comparable_scope else (item.get('comparison') or compiled.get('comparison'))
        item['comparison_note'] = ''
        if comparable_scope:
            day_count = lambda value: (date.fromisoformat(value['end']) - date.fromisoformat(value['start'])).days + 1
            current_days, previous_days = day_count(item['current_period']), day_count(item['previous_period'])
            item['comparison_note'] = f'{current_days} ngày đang xem / {previous_days} ngày đối chiếu.' + (' Hai kỳ khác số ngày; tổng chưa chuẩn hóa theo ngày.' if current_days != previous_days else '')
        item['comparisons'] = []
        item['comparison_metrics'] = []
        compared_metrics = list(data['metrics'])
        if item['id'] == 'ga4':
            compared_metrics.append(organic_sessions_metric(data))
            if old:
                previous_metrics['organic_sessions'] = organic_sessions_metric(old)
        for metric in compared_metrics if comparable_scope else []:
            prior = previous_metrics.get(metric['key'], {})
            change = metric_change(metric, metric, prior)
            item['comparison_metrics'].append(change)
            if change['status'] != 'ready':
                continue
            delta = change['summary'].replace('Kỳ đối chiếu bằng 0;', 'Mốc trước bằng 0;')
            item['comparisons'].append({'label': metric['label'], 'actual': display(metric['value'], metric['unit'], metric.get('currency')),
                'previous': display(prior['value'], prior['unit'], prior.get('currency')), 'delta': delta,
                'lifetime': False, 'effect': change['effect'], 'effect_label': change['effect_label'],
                'difference': change['difference_label']})
        item['chart'] = None
        chosen = next((metric for metric in data['metrics'] if any(
            chart_reading(row['values'].get(metric['key']), metric['key']) is not None for row in data.get('daily', []))), None)
        if not chosen:
            continue
        points = [(row['date'], chart_reading(row['values'].get(chosen['key']), chosen['key'])) for row in data['daily']]
        points = sorted((stamp, value) for stamp, value in points if value is not None)
        if not points:
            continue
        first = date.fromisoformat(item['current_period']['start'])
        last = date.fromisoformat(item['current_period']['end'])
        days = max(1, (last - first).days + 1)
        position = chosen['key'] == 'position'
        minimum = int(position)
        maximum = max(value for _, value in points) or Decimal(1)
        if maximum == minimum:
            maximum += 1
        span = maximum - minimum
        step = 510 / days
        bars = []
        for stamp, value in points:
            offset = (date.fromisoformat(stamp) - first).days
            if not 0 <= offset < days:
                continue
            height = float((value - minimum) / span * 132)
            bars.append({'x': round(66 + step * offset + step * .15, 2), 'y': round(154 - height, 2),
                'height': round(height, 2), 'width': round(max(.5, step * .7), 2),
                'title': stamp + ' · ' + chosen['label'] + ': ' + display(value, chosen['unit'], chosen.get('currency'))})
        current_values = {row['date']: row['values'].get(chosen['key']) for row in data['daily']}
        series = [{'date': (first + timedelta(days=offset)).isoformat(),
                   'value': current_values.get((first + timedelta(days=offset)).isoformat())} for offset in range(days)]
        previous_series = []
        previous_metric = previous_metrics.get(chosen['key'])
        if (comparable_scope and previous_metric and metric_change(chosen, chosen, previous_metric)['status'] == 'ready'
                and previous_metric.get('currency') == chosen.get('currency')
                and old['asset']['id'] == data['asset']['id']
                and old['snapshot']['timezone'] == data['snapshot']['timezone']):
            old_first, old_last = date.fromisoformat(item['previous_period']['start']), date.fromisoformat(item['previous_period']['end'])
            old_values = {row['date']: row['values'].get(chosen['key']) for row in old.get('daily', [])}
            previous_series = [{'date': (old_first + timedelta(days=offset)).isoformat(),
                'value': old_values.get((old_first + timedelta(days=offset)).isoformat())}
                for offset in range((old_last - old_first).days + 1)]
        item['chart'] = {'label': chosen['label'], 'bars': bars, 'first': first.strftime('%d/%m'), 'last': last.strftime('%d/%m'),
                         'rows': series, 'previous': previous_series if 'comparison' in compiled.get('sections', []) else [],
                         'unit': chosen['unit'], 'currency': chosen.get('currency'),
                         'reverse_y': position,
                         'kind': 'line' if item['id'] in ('ga4', 'gsc', 'youtube') else 'bar',
                         'maximum': display(maximum, chosen['unit'], chosen.get('currency')), 'observed': len(bars), 'days': days}
        item['extra_charts'] = []
        for key in {'ga4':('sessions','page_views'),'gsc':('impressions','position')}.get(item['id'],()):
            metric = next((row for row in data['metrics'] if row['key']==key and row['key']!=chosen['key']),None)
            chart = extra_chart(data, old if comparable_scope and 'comparison' in compiled.get('sections', []) else None, metric) if metric else None
            if chart:
                item['extra_charts'].append(chart)
    from app.customer_seo_compact import build
    compiled['compact_seo'] = build(compiled)
    return compiled
