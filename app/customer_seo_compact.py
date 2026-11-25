"""Compact presentation of already validated, frozen SEO report data."""
from math import ceil

from app.customer_data import display
from app.customer_comparisons import organic_sessions_metric
from app.customer_seo_reports import number, rank_bands


def compact_keyword_groups(groups):
    for group in groups:
        if group.get('kind') != 'tracked':
            yield group, group.get('kind') == 'niche'
            continue
        primary = [row for row in group['rows'] if row.get('role') != 'secondary']
        secondary = [row for row in group['rows'] if row.get('role') == 'secondary']
        yield {**group, 'title': 'Từ khóa theo dõi', 'rows': primary}, False
        yield {**group, 'title': 'Từ khóa phụ', 'rows': secondary}, True


def build(compiled):
    seo = next((item for item in compiled['sources'] if item['id'] == 'seo'), None)
    if seo is None:
        return None
    sources = {item['id']: item for item in compiled['sources'] if item['id'] in ('ga4', 'gsc')}
    report = seo['data']
    result = {'seo': seo, 'google': list(sources.values()), 'metrics': [], 'charts': [],
              'distributions': [], 'keywords': [], 'extended_keywords': [], 'articles': [],
              'countries': [], 'targets': [], 'rank_bands': []}
    for source, keys in [('ga4', ('active_users', 'sessions', 'organic_sessions', 'page_views', 'engagement_rate')),
                         ('gsc', ('clicks', 'impressions', 'ctr', 'position'))]:
        item = sources.get(source)
        if not item:
            continue
        data = item['data']
        result['targets'].extend({'source': 'GA4' if source == 'ga4' else 'GSC', **goal}
                                 for goal in data.get('targets', {}).get('items', []) if goal['status'] != 'not_set')
        if source == 'gsc':
            result['countries'] = next((table['rows'] for table in data.get('tables', []) if table['id'] == 'countries'), [])
        metrics = {row['key']: row for row in data.get('metrics', [])}
        if source == 'ga4':
            metrics['organic_sessions'] = organic_sessions_metric(data)
        changes = {row['label']: row for row in item.get('comparisons', [])}
        for key in keys:
            metric = metrics.get(key)
            if not metric:
                continue
            change = changes.get(metric['label'])
            result['metrics'].append({'key': key, 'source': 'GA4' if source == 'ga4' else 'GSC',
                'label': metric['label'], 'actual': display(metric.get('value'), metric['unit'], metric.get('currency')),
                'previous': change['previous'] if change else '—', 'delta': change['delta'] if change else '—',
                'effect': change.get('effect') if change else None})
        charts = [chart for chart in [item.get('chart'), *item.get('extra_charts', [])] if chart]
        preferred = ('Phiên truy cập', 'Lượt xem trang / màn hình') if source == 'ga4' else ('Lượt nhấp tự nhiên', 'Lượt hiển thị')
        selected = [chart for label in preferred for chart in charts if chart['label'] == label]
        # Source labels can differ in older snapshots. Keep their observed charts usable.
        selected.extend(chart for chart in charts if chart not in selected)
        result['charts'].extend({'source': source, 'chart': chart} for chart in selected[:2])
        for chart in (item.get('device_distribution'), item.get('view', {}).get('layout', {}).get('distribution')):
            if chart and chart.get('rows') and source == 'ga4':
                result['distributions'].append(chart)

    primary_metrics = ('sessions', 'clicks', 'page_views', 'impressions')
    results_by_key = {item['key']: item for item in result['metrics'] if item['actual'] != '—'}
    result['featured_metrics'] = [results_by_key[key] for key in primary_metrics if key in results_by_key]
    result['detail_metrics'] = [item for item in result['metrics'] if item not in result['featured_metrics']]
    keywords = report.get('keywords', [])
    if keywords:
        labels = ('Top 10 · Trang 1', 'Hạng 11–20 · Trang 2', 'Hạng 21–30 · Trang 3',
                  'Hạng 31–100', 'Ngoài Top 100', 'Chưa có vị trí')
        current = rank_bands(keywords, 'rank', 'state')
        previous = (rank_bands(keywords, 'previous_period_rank', 'previous_period_state')
                    if 'comparison' in compiled.get('sections', []) and any(row.get('previous_observed_date') for row in keywords)
                    else [None] * len(labels))
        scale = max(1, *current, *(value for value in previous if value is not None))
        result['rank_bands'] = [{'label': label, 'count': count, 'prior': prior, 'width': count / scale * 100,
                                'prior_width': prior / scale * 100 if prior is not None else 0}
                               for label, count, prior in zip(labels, current, previous)]
    extended_rows = []
    for group, extended in compact_keyword_groups(seo.get('keyword_groups', [])):
        rows = group['rows']
        if extended:
            extended_rows.extend(rows)
        dates = sorted({row['observed_date'] for row in rows if row.get('observed_date')})
        section = result['extended_keywords' if extended else 'keywords']
        for offset in range(0, len(rows), 40):
            chunk = [{**row, 'number': offset + index + 1} for index, row in enumerate(rows[offset:offset + 40])]
            half = len(chunk) if len(chunk) <= 12 else ceil(len(chunk) / 2)
            section.append({'title': group['title'], 'count': len(rows), 'search': group.get('search', False),
                'dates': dates, 'continued': offset > 0, 'tables': [part for part in (chunk[:half], chunk[half:]) if part]})

    result['extended_summary'] = [
        {'label': 'Từ khóa phụ', 'value': sum(row.get('role') == 'secondary' for row in extended_rows)},
        {'label': 'Từ khóa ngách', 'value': sum(row.get('segment') == 'niche' for row in extended_rows)},
        {'label': 'Có hạng trong Top 100', 'value': sum(row.get('rank') is not None and row['rank'] <= 100 for row in extended_rows)},
    ]
    evidence = report.get('effectiveness', {}).get('items', [])
    by_id = {key: item for item in evidence for key in item.get('ids', [item['id']])}
    grouped = {}
    for article in report.get('content', {}).get('items', []):
        if article.get('archived'):
            continue
        observation = by_id.get(article['id'])
        key = observation['id'] if observation else article.get('url') or article['id']
        if key not in grouped:
            grouped[key] = {'title': observation['title'] if observation else article['title'],
                'url': article.get('url'), 'draft_url': article.get('draft_url'), 'tasks': [],
                'values': observation['values'] if observation else {}}
        grouped[key]['tasks'].append(article)
    result['articles'] = list(grouped.values())
    for key, label, source in [('views', 'Bài có nhiều lượt xem nhất', 'GA4'), ('clicks', 'Bài có nhiều lượt nhấp nhất', 'GSC')]:
        observed = [(number(article['values'].get(key)), article) for article in result['articles']]
        best = sorted(((value, article) for value, article in observed if value is not None and value > 0),
                      key=lambda entry: entry[0], reverse=True)[:3]
        if best:
            result['article_highlights'] = {'label': label, 'source': source, 'items': [
                {'title': article['title'], 'value': display(value, 'count'), 'width': float(value / best[0][0] * 100)}
                for value, article in best]}
            break
    items = [goal for goal in (report.get('project') or {}).get('items', []) if goal.get('target') is not None]
    if items:
        result['goal_statuses'] = [
            {'label': label, 'tone': tone, 'count': sum(item['status'] in states for item in items)}
            for label, tone, states in (
                ('Đạt cam kết', 'met', ('met',)), ('Chưa đạt', 'below_target', ('below_target',)),
                ('Đang thực hiện', 'open', ('in_progress', 'in_progress_met')),
                ('Chờ dữ liệu hoặc kỳ đo', 'pending', ('no_data', 'period_mismatch', 'not_started')),
            )
        ]
    return result
