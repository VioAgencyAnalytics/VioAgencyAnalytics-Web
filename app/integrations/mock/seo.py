"""SEO demonstration data transcribed from the supplied HTML reference."""
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
import json
from pathlib import Path

from app.integrations.mock.overview import DEFAULT_START, DEFAULT_END, format_number, validate_range


@lru_cache
def reference():
    return json.loads(Path(__file__).with_name('seo_reference.json').read_text(encoding='utf-8'))


def seo_payload(start: date | None = None, end: date | None = None, filters=None):
    start, end = start or DEFAULT_START, end or DEFAULT_END
    validate_range(start, end)
    days = (end - start).days + 1
    ratio = days / 30
    sample = reference()
    fields = {}
    for key, field in sample['fields'].items():
        value, kind = field['text'], field['kind']
        if ratio == 1 or kind == 'fixed':
            fields[key] = value
        elif kind == 'compact':
            scaled = float(value.rstrip('K')) * 1000 * ratio
            fields[key] = f'{scaled / 1000:.1f}K' if scaled >= 1000 else format_number(scaled)
        else:
            fields[key] = format_number(int(value.replace('.', '')) * ratio)
    metrics = [
        dict(key='impressions', label='Tổng lượt hiển thị', value=round(420500 * ratio), unit='', delta=15.4),
        dict(key='clicks', label='Lượt click tự nhiên', value=round(39840 * ratio), unit='', delta=24.1),
        dict(key='users', label='Organic Users', value=round(32180 * ratio), unit='', delta=21.8),
        dict(key='top10', label='Từ khóa Top 10', value=148, unit='từ khóa', delta=12),
        dict(key='leads', label='Leads từ SEO', value=round(412 * ratio), unit='Leads', delta=19.5),
        dict(key='cr', label='Tỷ lệ chuyển đổi', value=1.28, unit='%', delta=.15),
    ]
    keywords = [{**row, 'clicks': round(row['clicks'] * ratio), 'impressions': round(row['impressions'] * ratio)} for row in sample['keywords']]
    landings = [{**row, **{key: round(row[key] * ratio) for key in ['users', 'clicks', 'leads']}} for row in sample['landings']]
    offsets = [0, 4, 9, 14, 19, 24, 29] if days == 30 else sorted(set(round(i * (days - 1) / 6) for i in range(7)))
    return {
        'report_type': 'seo', 'data_source': 'mock', 'generated_at': datetime.now(timezone.utc).isoformat(),
        'filters': filters or {}, 'metrics': metrics, 'fields': fields, 'keywords': keywords, 'landings': landings,
        'period': {'start': start.isoformat(), 'end': end.isoformat(), 'days': days,
                   'previous_start': (start - timedelta(days=days)).isoformat(), 'previous_end': (start - timedelta(days=1)).isoformat()},
        'chart_dates': [(start + timedelta(days=offset)).strftime('%d/%m') for offset in offsets],
        # Retain the existing report API summary for clients of /reports/seo.
        'data': {'summary': {'title': 'SEO & Lưu lượng Website', 'status': 'mock', 'items': metrics},
                 'series': {'labels': ['Tuần 1', 'Tuần 2', 'Tuần 3', 'Tuần 4'], 'values': [7840, 8720, 11080, 12200]}},
    }


def filter_keywords(rows, rank='all', query=''):
    predicates = {
        'all': lambda row: True,
        'top3': lambda row: 1 <= row['position'] <= 3,
        'new': lambda row: row['previous'] > 10 >= row['position'],
        'risers': lambda row: row['previous'] - row['position'] >= 5,
    }
    predicates.update({f'top{k}': lambda row, limit=k: 1 <= row['position'] <= limit for k in (5, 10, 20, 30, 50, 100)})
    match = predicates[rank]
    query = query.strip().casefold()
    return [row for row in rows if match(row) and (not query or query in (row['keyword'] + ' ' + row['landing']).casefold())]
