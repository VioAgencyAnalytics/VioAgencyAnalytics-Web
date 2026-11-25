"""Prepare focused sections and the accompanying notes from the same report snapshot."""

from app.customer_report_layouts import ranked_rows
from app.customer_data import display
from app.report_commentary import (daily_trend, detail_sections, distribution, facebook_content,
                                   ranking, section, summaries, trend)


def focus_report(preset, report, layout, content_view=None, *, example=False):
    if report['state'] != 'ready':
        return {}, summaries(report, layout)

    metrics = {item['key']: item for item in (content_view['cards'] if content_view else layout['metrics'])}
    keys = preset.metrics or tuple(metrics)[:4]
    selected = [metrics[key] for key in keys if key in metrics]
    chart_label = layout['by_key'].get(preset.chart, {}).get('label', '')
    focused_layout = {**layout, 'metrics': selected, 'order': keys,
                      'lead': selected[0]['key'] if selected else layout['lead'],
                      'chart': preset.chart or layout['chart'], 'trend': chart_label or layout['trend']}
    tables = [(index, table) for index, table in enumerate(report.get('tables', ()))
              if not preset.table or table['id'] == preset.table]
    rank = ranked_rows(report, preset.table, *preset.ranking) if preset.ranking else None
    if example and rank:
        for row in rank['rows']:
            row['url'] = None

    summary_layout = {**focused_layout, 'by_key': {item['key']: item for item in selected}} if not content_view else focused_layout
    notes = summaries(report, summary_layout)
    applicable = {'summary': 'metrics', 'comparison': 'comparison', 'kpi': 'kpi'}
    notes = {key: value for key, value in notes.items() if applicable[key] in preset.blocks}
    focus = {'layout': focused_layout, 'rank': rank, 'tables': tables}
    if content_view:
        content_notes = facebook_content(report, content_view, layout)
        if 'metrics' in preset.blocks:
            readings = [f"{card['label']} {display(card['value'], 'count')}" for card in selected if card['value'] is not None]
            notes['summary'] = section('Kết quả chính', ' · '.join(readings) + '.' if readings else 'Chưa có số liệu cho chỉ số của mẫu này.')
        for block, key in (('ranking', 'rank_posts'), ('distribution', 'distribution'), ('details', 'detail_posts')):
            if block in preset.blocks:
                notes[key] = content_notes[key]
        charts = [chart for chart in content_view['charts'] if not preset.chart or chart['key'] == preset.chart]
        focus['content'] = {**content_view, 'cards': selected, 'charts': charts}
        if 'trend' in preset.blocks:
            chart = charts[0] if charts else None
            notes['trend'] = section(chart['title'], trend({'label': chart['title'], 'unit': 'count'}, chart['points'], chart['expected'])) if chart else section('Xu hướng', 'Bản lưu chưa có quan sát cho chỉ số này.')
        return focus, notes

    if 'trend' in preset.blocks:
        notes['trend'] = section(focused_layout['trend'], daily_trend(report, focused_layout, prefer_position=False))
    if rank:
        notes['focus_rank'] = section(preset.name, ranking(rank))
    if 'distribution' in preset.blocks and layout['distribution']:
        chart = layout['distribution']
        notes['distribution'] = section(chart['title'], distribution(chart))
    if 'details' in preset.blocks:
        detail_notes = detail_sections(report)
        notes.update({f'detail_{index}': detail_notes[f'detail_{index}'] for index, _ in tables} if tables else {
            'details_empty': section('Dữ liệu chi tiết', 'Chưa có bảng phù hợp trong bản dữ liệu đã lưu.')})
    return focus, notes
