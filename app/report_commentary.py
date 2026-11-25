"""Short observations from the same saved numbers and assessments as the report."""
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext

from app.customer_data import display


MISSING_PERIOD = 'Chưa có bản dữ liệu đã đồng bộ cho kỳ đang xem.'


def number(value):
    try:
        result = Decimal(str(value))
    except (ValueError, InvalidOperation):
        return None
    return result if result.is_finite() and result >= 0 else None


def label(value):
    value = ' '.join(str(value).split())
    return value if len(value) <= 100 else value[:99].rstrip() + '…'


def section(title, text):
    return {'title': title, 'text': text}


def reading(metric, field='value'):
    return display(metric.get(field), metric['unit'], metric.get('currency'))


def observed(metric, field='value'):
    value = number(metric.get(field))
    return value is not None and (metric['key'] != 'position' or value >= 1)


def summary(report, layout):
    if report.get('state') != 'ready':
        return MISSING_PERIOD
    main = layout['lead']
    metrics = layout['by_key']
    # The lead metric and one supporting measure use the units shown above.
    keys = dict.fromkeys([main, *layout['order'], *metrics])
    present = [metrics[key] for key in keys if key in metrics and observed(metrics[key])]
    if not present:
        return 'Bản lưu kỳ này chưa có số liệu cho các chỉ số tổng quan.'
    if report['source'] == 'gsc' and all(key in metrics and observed(metrics[key]) for key in ('clicks', 'impressions', 'ctr')):
        clicks, impressions, ctr = (reading(metrics[key]) for key in ('clicks', 'impressions', 'ctr'))
        return f'Tìm kiếm ghi nhận {clicks} lượt nhấp trên {impressions} lượt hiển thị. Tỷ lệ nhấp là {ctr}.'
    missing = metrics.keys() - {metric['key'] for metric in present}
    output = []
    for metric in present[:1 if main in missing else 2]:
        timing = 'tại lần đồng bộ' if metric.get('grain') == 'snapshot' else 'trong kỳ'
        output.append(f"{label(metric['label'])} ghi nhận {reading(metric)} {timing}.")
    if main in missing:
        output.append(f"Chưa có số liệu cho {label(metrics[main]['label']).lower()} trong bản lưu.")
    elif missing:
        output.append(f'Còn {len(missing)} chỉ số tổng quan chưa có số liệu trong bản lưu.')
    return ' '.join(output)


def day(value):
    return date.fromisoformat(value[:10]).strftime('%d/%m')


def trend(metric, points, expected=0):
    if not metric:
        return 'Chưa có chỉ số theo ngày để nhận xét xu hướng.'
    title = label(metric['label'])
    minimum = 1 if metric.get('key') == 'position' or metric.get('reverse_y') else 0
    values = {}
    for point in points:
        stamp, value = point['date'], number(point.get('value'))
        if stamp and value is not None and value >= minimum:
            values[stamp] = value
    if not values:
        return f'Chưa có chuỗi theo ngày để nhận xét {title.lower()}.'
    ordered = sorted(values.items())
    unit, currency = metric['unit'], metric.get('currency')
    if minimum and len(ordered) > 1:
        first, last = ordered[0], ordered[-1]
        change = 'cải thiện' if last[1] < first[1] else 'lùi' if last[1] > first[1] else 'giữ nguyên'
        text = (f'{title} {change} từ {display(first[1], unit, currency)} ngày {day(first[0])} '
                f'đến {display(last[1], unit, currency)} ngày {day(last[0])}.')
    elif len(set(values.values())) == 1:
        text = f'{title} ghi nhận {display(ordered[0][1], unit, currency)} ở {len(ordered)} ngày có số liệu.'
    else:
        stamp, value = max(ordered, key=lambda pair: pair[1])
        text = f'{title} cao nhất ở mức {display(value, unit, currency)} vào {day(stamp)}.'
    if expected > len(values):
        text += f' Có dữ liệu cho {len(values)}/{expected} ngày.'
    return text


def daily_trend(report, layout, *, prefer_position=True):
    key = layout['chart']
    snap = report.get('snapshot') or {}
    start, end = snap.get('start_date'), snap.get('end_date')
    rows = [row for row in report.get('daily', []) if not start or start <= row['date'] <= end]
    expected = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1 if start and end else 0
    if prefer_position and report['source'] == 'gsc' and any((number(row['values'].get('position')) or 0) >= 1 for row in rows):
        key = 'position'
    metric = layout['by_key'].get(key)
    return trend(metric, [{'date': row['date'], 'value': row['values'].get(key)} for row in rows], expected)


def change_sentence(item):
    title = label(item['label'])
    relation = item['relation']
    if relation == 'equal':
        return f'{title} giữ ở mức {reading(item, "actual")}.'
    if item['key'] == 'position':
        direction = 'cải thiện xuống' if relation == 'below' else 'lùi lên'
        return f'{title} {direction} {reading(item, "actual")} từ {reading(item, "previous")}.'
    delta = item['summary'].lstrip('+−') if item.get('relative') is not None or item['unit'] == 'percent' else item['difference_label']
    change = 'tăng' if relation == 'above' else 'giảm'
    return f'{title} {change} {delta} so với kỳ đối chiếu.'


COMPARISON_ORDER = {
    'gsc': ('clicks', 'position', 'ctr', 'impressions'),
    'ga4': ('organic_sessions', 'sessions', 'engagement_rate', 'active_users', 'page_views'),
    'facebook_ads': ('leads', 'cost_per_result', 'spend'),
}


def comparison(source, layout, current):
    if current.get('status') != 'ready':
        return current.get('message') or 'Chưa có bản lưu kỳ đối chiếu tương thích để tính thay đổi.'
    order = COMPARISON_ORDER.get(source, (layout['lead'], *layout['order']))
    items = current.get('items', [])
    rows = {item['key']: item for item in items
            if item['status'] == 'ready' and observed(item, 'actual') and observed(item, 'previous')}
    if not rows:
        return 'Hai kỳ đã có bản lưu. Các chỉ số cần thêm dữ liệu tương thích để tính thay đổi.'
    unavailable = sum(item['grain'] != 'snapshot' and item['key'] not in rows for item in items)
    coverage = f' Có {unavailable} chỉ số thiếu số liệu tương thích giữa hai kỳ.' if unavailable else ''
    left, right = current.get('current_days'), current.get('comparison_days')
    if left and right and left != right:
        key = next((key for key in order if key in rows), next(iter(rows)))
        item = rows[key]
        return (f'{label(item["label"])} ghi nhận {reading(item, "actual")} ở kỳ {left} ngày '
                f'và {reading(item, "previous")} ở kỳ đối chiếu {right} ngày. Hai kỳ có độ dài khác nhau.' + coverage)
    first, impressions, ctr = (rows.get(key) for key in ('clicks', 'impressions', 'ctr'))
    if (source == 'gsc' and first and impressions and ctr and first.get('relative') is not None
            and first['relative'] == impressions.get('relative') and first['relation'] in ('above', 'below')
            and first['relation'] == impressions['relation']
            and ctr['relation'] == 'equal'):
        direction = 'tăng' if first['relation'] == 'above' else 'giảm'
        return f'Lượt nhấp và hiển thị cùng {direction} {first["summary"].lstrip("+−")}. CTR giữ ở {reading(ctr, "actual")}.' + coverage
    selected = [rows[key] for key in dict.fromkeys([*order, *rows]) if key in rows]
    return ' '.join(change_sentence(item) for item in selected[:2]) + coverage


def goal_difference(goal):
    diff = number(goal.get('difference'))
    if diff is None:
        return None
    if goal['unit'] == 'percent':
        return display(diff * 100, 'number') + ' điểm phần trăm'
    return display(diff, goal['unit'], goal.get('currency'))


def targets(goals, is_open=False):
    goals = [goal for goal in goals if goal.get('value') is not None]
    if not goals:
        return 'Chưa đặt mục tiêu KPI cho tài khoản và kỳ này.'
    misses = [goal for goal in goals if goal['status'] in ('over_limit', 'below_target')]
    met = [goal for goal in goals if goal['status'] in ('met', 'within_limit')]
    missing = [goal for goal in goals if goal['status'] not in ('over_limit', 'below_target', 'met', 'within_limit')]
    selected = next((goal for goal in misses if goal['status'] == 'over_limit'), misses[0] if misses else None)
    prefix = 'Tạm tính đến ngày dữ liệu cuối. ' if is_open else ''
    if selected:
        delta = goal_difference(selected)
        change = 'vượt giới hạn' if selected['status'] == 'over_limit' else 'còn thiếu'
        phrase = f'{label(selected["label"])} {change} {delta}' if delta else f'{label(selected["label"])} cần đối chiếu với mục tiêu'
        text = f'{phrase} (thực tế {reading(selected, "actual")}, mốc {reading(selected)}).'
    elif met:
        text = f'{len(met)}/{len(goals)} chỉ tiêu đã đặt đạt mục tiêu hoặc trong giới hạn.'
    else:
        text = 'Chưa có chỉ tiêu đủ dữ liệu để đánh giá mức đạt.'
    if len(missing) == 1:
        goal = missing[0]
        reason = 'khác tiền tệ với mục tiêu' if goal['status'] == 'currency_mismatch' else 'chưa có số liệu thực tế'
        text += f' {label(goal["label"])} {reason}.'
    elif missing:
        text += f' {len(missing)} chỉ tiêu chưa đủ dữ liệu tương thích để đánh giá.'
    elif misses and met:
        text += f' {len(met)}/{len(goals)} chỉ tiêu đạt mục tiêu hoặc trong giới hạn.'
    return prefix + text


def ranking(items, currency=None):
    rows = items.get('rows', [])
    if not rows:
        return 'Chưa có số liệu chi tiết để xếp hạng trong mục này.'
    best = rows[0]
    text = ('Các dòng có số liệu đều ghi nhận 0.'
            if number(best['value']) == 0 else
            f'“{label(best["label"])}” đứng đầu trong các dòng có số liệu với {display(best["value"], best["unit"], currency)}.')
    if items.get('missing'):
        text += f' Có {items["missing"]}/{items["loaded"]} dòng thiếu chỉ số xếp hạng.'
    return text


def distribution(chart):
    rows = chart.get('rows', []) if chart else []
    values = [(row['label'], number(row['value'])) for row in rows]
    if not values or any(value is None for _, value in values):
        return 'Chưa đủ dữ liệu của các nhóm để tính tỷ trọng.'
    with localcontext() as context:
        context.prec = 100
        total = sum(value for _, value in values)
        if total == 0:
            return 'Các nhóm đã tải đều ghi nhận 0. Chưa có tổng dương để tính tỷ trọng.'
        name, value = max(values, key=lambda entry: entry[1])
        tied = sum(amount == value for _, amount in values)
        leader = f'{tied} nhóm cùng' if tied > 1 else f'“{label(name)}”'
        return f'{leader} chiếm tỷ trọng cao nhất, {display(value / total, "percent")} trong phần dữ liệu của biểu đồ.'


def detail(table):
    rows = table['rows']
    if not rows:
        return 'Chưa có dòng chi tiết trong bản dữ liệu đã lưu.'
    expected = table['total_rows']
    coverage = f'Bảng có {len(rows)}/{expected} dòng được nguồn báo cáo.' if expected > len(rows) else f'Bảng có {len(rows)} dòng từ bản lưu.'
    columns = [column for column in table['columns'] if column['unit'] != 'text']
    for column in columns:
        missing = sum(row.get(column['key']) is None for row in rows)
        if missing:
            return f'{coverage} {missing} dòng thiếu {label(column["label"]).lower()}.'
    return coverage


def summaries(report, layout):
    result = {'summary': section('Kết quả tổng quan', summary(report, layout))}
    previous = report.get('comparison') or {}
    if previous and previous['mode'] != 'none':
        result['comparison'] = section('Đối chiếu hai kỳ', comparison(report['source'], layout, previous))
    if report.get('targets') and report.get('period'):
        result['kpi'] = section('So sánh KPI', targets(report['targets']['items'], report['period'].get('is_open')))
    return result


def detail_sections(report):
    return {f'detail_{index}': section(table['title'], detail(table)) for index, table in enumerate(report.get('tables', []))} or {
        'details_empty': section('Dữ liệu chi tiết', 'Chưa có bảng chi tiết trong bản dữ liệu đã lưu.')}


def platform(report, layout):
    result = summaries(report, layout)
    if report['state'] == 'ready':
        result['trend'] = section(layout['trend'], daily_trend(report, layout))
        result.update({f'rank_{key}': section(title, ranking(layout['rankings'][key]))
                       for key, title in [('channels','Kênh truy cập'), ('pages','Trang được xem'), ('queries','Truy vấn nổi bật'),
                                          ('videos','Video nổi bật'), ('posts','Bài đăng nổi bật')] if key in layout['rankings']})
        chart = layout['distribution']
        if chart:
            result['distribution'] = section(chart['title'], distribution(chart))
        result.update(detail_sections(report))
    return result


def facebook_content(report, view, layout):
    result = summaries(report, layout)
    if report['state'] != 'ready':
        return result
    published = next(card['value'] for card in view['cards'] if card['key'] == 'posts_published')
    total = len(view['posts'])
    result['summary']['text'] = (f'Có {display(published, "count")} bài đăng trong kỳ, xuất bản vào {view["active_days"]}/{view["days"]} ngày.'
                                 if published is not None else 'Chưa có số bài xuất bản cho kỳ này.')
    top = view['top']
    result['rank_posts'] = section('Nội dung nổi bật', (
        f'“{label(top[0]["heading"])}” đứng đầu trong {total} bài đã tải. Bài ghi nhận '
        f'{display(top[0][view["ranking"]], "count")} {view["ranking_label"]} tích lũy tại lần đồng bộ.'
        if top else 'Chưa đủ số liệu lượt xem hoặc cảm xúc tích lũy để xếp hạng bài viết.'))
    chart = view['charts'][0]
    result['trend'] = section('Hoạt động & xu hướng',
                              trend({'label': 'Số bài đăng theo ngày', 'unit': 'count'}, chart['points'], chart['expected']))
    result['distribution'] = section(view['distribution']['title'], distribution(view['distribution']))
    views = sum(row.get('post_media_view_lifetime') is not None for row in view['posts'])
    result['detail_posts'] = section('Chi tiết bài viết', (
        f'Cột lượt xem tích lũy có số liệu ở {views}/{total} bài đã tải.'
        if total else 'Chưa có dòng bài viết trong bản lưu của kỳ này.'))
    return result
