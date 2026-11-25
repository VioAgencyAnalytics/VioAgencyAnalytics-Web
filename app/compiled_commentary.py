"""Observations for the frozen SEO and multi-source report layouts."""
from datetime import date

from app.customer_data import display
from app.report_commentary import (change_sentence, comparison, detail_sections, distribution, label, number, observed,
                                   reading, section, summary, targets, trend)


def days(period):
    start, end = (period or {}).get('start'), (period or {}).get('end')
    return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1 if start and end else 0


def saved_comparison(item):
    return {'status': 'ready' if item['comparison_metrics'] else 'missing',
            'items': item['comparison_metrics'],
            'current_days': days(item.get('current_period')), 'comparison_days': days(item.get('previous_period'))}


def website_performance(compact, compare):
    sources = {item['id']: item for item in compact['google']}
    notes = []
    for source, source_label, keys in [('ga4', 'GA4', ('organic_sessions', 'sessions', 'page_views')),
                                       ('gsc', 'Search Console', ('clicks', 'position', 'impressions'))]:
        item = sources.get(source)
        if not item:
            notes.append(f'Báo cáo chưa gồm nguồn {source_label}.')
            continue
        if item['data'].get('state') != 'ready':
            notes.append(f'Chưa có dữ liệu {source_label} đúng kỳ trong báo cáo.')
            continue
        changes = saved_comparison(item) if compare else {}
        by_key = {row['key']: row for row in changes.get('items', [])
                  if row['status'] == 'ready' and observed(row, 'actual') and observed(row, 'previous')}
        selected = next((by_key[key] for key in keys if key in by_key), None)
        if selected and changes['current_days'] == changes['comparison_days']:
            notes.append(change_sentence(selected))
        elif selected and changes['current_days'] and changes['comparison_days']:
            notes.append(f'{label(selected["label"])} ghi nhận {reading(selected, "actual")} ở kỳ {changes["current_days"]} ngày '
                         f'và {reading(selected, "previous")} ở kỳ đối chiếu {changes["comparison_days"]} ngày.')
        else:
            metrics = {row['key']: row for row in item['data']['metrics'] if observed(row)}
            metric = next((metrics[key] for key in keys if key in metrics), None)
            if metric:
                tail = ' Chưa đủ dữ liệu phù hợp để đối chiếu.' if compare else ''
                notes.append(f'{label(metric["label"])} ghi nhận {reading(metric)} từ {source_label}.' + tail)
            else:
                notes.append(f'Chưa có chỉ số hiệu quả phù hợp từ {source_label} trong bản lưu.')
    return ' '.join(notes)


def keyword_ranks(blocks, compare):
    rows = [row for block in blocks if not block.get('search') for table in block['tables'] for row in table]
    if not rows:
        if any(block.get('search') for block in blocks):
            return 'Nhóm từ khóa đang có quan sát truy vấn Search Console. Chưa có phép đo thứ hạng Spineditor cho nhóm này.'
        return 'Chưa có bộ từ khóa để nhận xét trong mục này.'
    observed_rows = [row for row in rows if row.get('observed_date')
                     and (row.get('rank') is not None or row.get('state') == 'outside_top100')]
    if not observed_rows:
        return f'Chưa có phép đo thứ hạng trong kỳ cho {len(rows)} từ đang theo dõi ở mục này.'
    top10 = sum(row.get('rank') is not None and row['rank'] <= 10 for row in observed_rows)
    text = f'Có {top10}/{len(rows)} từ ở Top 10. Đã có phép đo cho {len(observed_rows)}/{len(rows)} từ.'
    if compare:
        paired = [row for row in observed_rows if row.get('previous_observed_date') and
                  (row.get('previous_period_rank') is not None or row.get('previous_period_state') == 'outside_top100')]
        if not paired:
            return text + ' Chưa có phép đo hợp lệ của kỳ đối chiếu trên cùng nhóm từ.'
        before = sum(row.get('previous_period_rank') is not None and row['previous_period_rank'] <= 10 for row in paired)
        after = sum(row.get('rank') is not None and row['rank'] <= 10 for row in paired)
        text += f' Trên {len(paired)} từ đo ở cả hai kỳ, Top 10 từ {before} lên {after}.' if before < after else (
            f' Trên {len(paired)} từ đo ở cả hai kỳ, Top 10 giảm từ {before} còn {after}.' if after < before else
            f' Trên {len(paired)} từ đo ở cả hai kỳ, số từ Top 10 giữ ở mức {after}.')
    return text


def article_progress(seo, compact):
    stats = (seo.get('content') or {}).get('summary') or {}
    if not compact['articles'] or 'published_new' not in stats:
        return 'Chưa có dữ liệu sổ nội dung của kỳ đang xem để đánh giá tiến độ bài viết.'
    text = (f'Kỳ này có {stats["published_new"]} bài mới đã đăng, {stats["accepted_new"]} bài mới '
            f'và {stats["accepted_updates"]} lượt cập nhật đã nghiệm thu.')
    if stats['awaiting_acceptance']:
        text += f' Còn {stats["awaiting_acceptance"]} bài đã đăng đang chờ nghiệm thu.'
    missing = [name for key, name in [('views', 'GA4'), ('clicks', 'Search Console')]
               if not any(row['values'].get(key) is not None for row in compact['articles'])]
    if missing:
        text += f' Chưa có số liệu {" và ".join(missing)} theo URL.'
    return text


def seo_commitments(seo):
    project = seo.get('project') or {}
    if not project.get('plan'):
        target = seo.get('plan') or {}
        if target.get('status') in ('met', 'below_target'):
            return f'Bộ cam kết có {target["top10"]} từ Top 10 trên {target["required"]} từ cần đạt.'
        return 'Chưa có đủ cam kết dự án và dữ liệu đúng kỳ để đánh giá KPI SEO.'
    items = [item for item in project.get('items', []) if item.get('target') is not None]
    if not items:
        return 'Kỳ đang xem chưa có chỉ tiêu SEO áp dụng.'
    met = sum(item['status'] == 'met' for item in items)
    pending = sum(item['status'] in ('in_progress', 'in_progress_met') for item in items)
    undecided = sum(item['status'] not in ('met', 'below_target', 'in_progress', 'in_progress_met') for item in items)
    text = f'{met}/{len(items)} chỉ tiêu đã đặt đạt cam kết.'
    if pending:
        text += f' {pending} chỉ tiêu đang thực hiện, kết quả là tạm tính.'
    if undecided:
        text += f' {undecided} chỉ tiêu chưa đủ dữ liệu đúng kỳ để nghiệm thu.'
    first = next((item for item in items if item['status'] == 'below_target'), None)
    if first:
        delta = number(abs(first['difference'])) if first.get('difference') is not None else None
        gap = display(delta, 'number') + (' điểm phần trăm' if first['unit'] == 'percent' else '') if delta is not None else None
        text += f' {label(first["label"])} còn thiếu {gap}.' if gap else f' {label(first["label"])} chưa đạt cam kết.'
    return text


def seo_sections(compact, selected):
    seo = compact['seo']['data']
    compare = 'comparison' in selected
    result = {}
    if {'summary', 'charts', 'comparison'} & selected:
        result['seo_performance'] = section('Hiệu quả SEO & Website', website_performance(compact, compare))
    if 'details' in selected:
        ranks = keyword_ranks(compact['keywords'], compare)
        if not compact['extended_keywords']:
            ranks += ' Bản lưu chưa có dữ liệu từ khóa phụ và ngách.'
        result['seo_keywords'] = section('Thứ hạng từ khóa', ranks)
        if compact['extended_keywords']:
            result['seo_extended'] = section('Từ khóa phụ & ngách', keyword_ranks(compact['extended_keywords'], compare))
    if {'details', 'seo_work'} & selected:
        result['seo_articles'] = section('Bài viết & hiệu quả', article_progress(seo, compact))
    if 'kpi' in selected:
        result['seo_kpi'] = section('Đối chiếu cam kết SEO', seo_commitments(seo))
        if compact['targets']:
            result['seo_google_kpi'] = section('Mục tiêu hiệu quả từ nguồn Google', targets(compact['targets']))
        timeline = (seo.get('project') or {}).get('timeline') or {}
        if timeline.get('months') and timeline.get('metrics'):
            months = timeline['months']
            observed_months = sum(any(item.get('actual') is not None for item in month['items']) for month in months)
            result['seo_matrix'] = section('Kế hoạch KPI dự án', (
                f'Ma trận có số thực hiện ở {observed_months}/{len(months)} tháng. '
                + ('Các tháng còn lại đang chờ số thực hiện.' if observed_months < len(months) else 'Có số thực hiện trong cả thời hạn theo dõi.')))
    if 'seo_work' in selected:
        work = seo.get('work') or []
        verified = sum(bool(item.get('verified') and item.get('accepted_date')) for item in work)
        result['seo_work'] = section('Công việc & bằng chứng', (
            f'Đã ghi nhận nghiệm thu ở {verified}/{len(work)} dòng công việc.'
            if work else 'Chưa có dòng công việc và bằng chứng trong kỳ đã chọn.'))
    return result


def compiled_sections(compiled, modules=None):
    selected = set(compiled['sections'])
    compact = compiled.get('compact_seo')
    result = seo_sections(compact, selected) if compact else {}
    if modules is not None:
        module_keys = {'performance': ('seo_performance',), 'keywords': ('seo_keywords',),
                       'extended': ('seo_extended',), 'articles': ('seo_articles',),
                       'matrix': ('seo_matrix',), 'kpi': ('seo_kpi', 'seo_google_kpi'), 'work': ('seo_work',)}
        included = {key for module in modules for key in module_keys[module]}
        result = {key: value for key, value in result.items() if key in included}
    if not compact and 'summary' in selected:
        ready = sum(item['data']['state'] == 'ready' for item in compiled['sources'])
        total = len(compiled['sources'])
        result['overview'] = section('Tổng quan báo cáo', f'{ready}/{total} nguồn đã có dữ liệu đúng kỳ trong báo cáo.')
    for item in compiled['sources']:
        source = item['id']
        if compact and source in ('seo', 'ga4', 'gsc'):
            continue
        report, layout = item['data'], item['view']['layout']
        notes = {'summary': section('Kết quả tổng quan', summary(report, layout))}
        if report['state'] == 'ready':
            if 'comparison' in selected:
                notes['comparison'] = section('Đối chiếu hai kỳ', comparison(source, layout, saved_comparison(item)))
            if 'kpi' in selected:
                notes['kpi'] = section('Đối chiếu mục tiêu KPI', targets((report.get('targets') or {}).get('items', []),
                                                                     (report.get('period') or {}).get('is_open', False)))
            if 'charts' in selected:
                for key, chart in [('distribution', layout['distribution']), ('devices', item.get('device_distribution'))]:
                    if chart:
                        notes[key] = section(chart['title'], distribution(chart))
                chart = item.get('chart') or {}
                notes['trend'] = section('Xu hướng theo ngày', trend(chart, chart.get('rows', []), chart.get('days', 0)))
            if 'details' in selected:
                notes.update(detail_sections(report))
        result.update({source + '_' + key: {**value, 'title': item['name'] + ' · ' + value['title']}
                       for key, value in notes.items()})
    return result
