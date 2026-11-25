"""Compare exact saved windows without fetching providers or modifying actuals."""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, localcontext
from urllib.parse import urlencode

from app.customer_auth import CustomerError, backend
from app.customer_metric_semantics import effect, trend


MODES = {'none', 'previous', 'previous_month', 'custom'}
PARAMETERS = {'comparison', 'comparison_start', 'comparison_end'}
LABELS = {'none': 'Không so sánh', 'previous': 'Kỳ liền trước',
          'previous_month': 'Cùng kỳ tháng trước', 'custom': 'Kỳ tùy chỉnh'}


def invalid(message='Chọn kỳ đối chiếu hợp lệ, tối đa 90 ngày.'):
    raise CustomerError(422, message, 'report_comparison_input')


def dates(start, end):
    try:
        first, last = date.fromisoformat(start), date.fromisoformat(end)
        if first.isoformat() != start or last.isoformat() != end or first > last or (last-first).days > 89:
            raise ValueError()
        return first, last
    except (ValueError, TypeError):
        invalid()


def parameters(values, default='none'):
    mode = values.get('comparison', default)
    if mode not in MODES:
        invalid('Kiểu so sánh không hợp lệ.')
    start, end = values.get('comparison_start'), values.get('comparison_end')
    if mode == 'custom':
        dates(start, end)
        return mode, {'start': start, 'end': end}
    if start is not None or end is not None:
        invalid('Chỉ nhập ngày đối chiếu khi chọn kỳ tùy chỉnh.')
    return mode, None


def previous_month(value):
    year, month = (value.year-1, 12) if value.month == 1 else (value.year, value.month-1)
    if year < 1:
        invalid('Không có kỳ trước mốc ngày này.')
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def resolve(period, mode, custom=None):
    """Open periods compare elapsed closed days; goals retain the complete period."""
    if mode == 'none' or not period or not period.get('data_start'):
        return None
    first, last = dates(period['data_start'], period['data_end'])
    try:
        if mode == 'custom':
            dates(custom['start'], custom['end'])
            return dict(custom)
        if mode == 'previous':
            end = first-timedelta(days=1)
            start = end-timedelta(days=(last-first).days)
        else:
            start, end = previous_month(first), previous_month(last)
            full_month = first.day == 1 and first.year == last.year and first.month == last.month and last.day == monthrange(last.year, last.month)[1]
            if full_month and not period.get('is_open'):
                end = date(start.year, start.month, monthrange(start.year, start.month)[1])
        if (end-start).days > 89:
            raise CustomerError(422, 'Kỳ tháng trước vượt 90 ngày do độ dài tháng khác nhau. Chọn kỳ đối chiếu tùy chỉnh.', 'report_comparison_limit')
        dates(start.isoformat(), end.isoformat())
        return {'start': start.isoformat(), 'end': end.isoformat()}
    except (ValueError, OverflowError, TypeError):
        invalid('Không xác định được kỳ đối chiếu cho các ngày này.')


def assert_period(report, wanted):
    if not wanted:
        return
    current = report.get('period') or {}
    if any(current.get(key) != value for key, value in wanted.items()):
        raise CustomerError(502, 'Báo cáo trả về không đúng kỳ đang chọn.', 'snapshot_scope')


def assert_same_asset(current, earlier):
    for field, keys in (('scope', ('workspace_id', 'client_id')), ('asset', ('id',)),
                        ('connection', ('id', 'version'))):
        left, right = current.get(field) or {}, earlier.get(field) or {}
        if any(left.get(key) != right.get(key) for key in keys):
            raise CustomerError(409, 'Tài khoản nguồn hoặc phạm vi đã thay đổi. Vui lòng tải lại.', 'client_changed')
    if current['source'] != earlier['source']:
        raise CustomerError(409, 'Nguồn so sánh đã thay đổi. Vui lòng tải lại.', 'client_changed')
    if current.get('snapshot') and earlier.get('snapshot') and current['snapshot'].get('timezone') != earlier['snapshot'].get('timezone'):
        raise CustomerError(409, 'Hai bản lưu khác múi giờ. Vui lòng đồng bộ đúng tài khoản nguồn.', 'client_changed')


def metric_change(spec, current, earlier):
    from app.customer_data import display
    actual, prior = current.get('value'), earlier.get('value')
    item = {key: spec.get(key) for key in ('key', 'label', 'unit', 'grain')}
    item.update(actual=actual, previous=prior, currency=current.get('currency'),
                status='no_data', difference=None, relative=None, relation=None,
                summary='Chưa có đủ dữ liệu hai kỳ.', chart=None, difference_label=None,
                effect='unavailable', effect_label='', trend=trend(spec.get('key')))
    if spec.get('grain') == 'snapshot':
        item.update(status='not_comparable', previous=None,
                    summary='Số tích lũy / tại thời điểm đồng bộ; không tính tăng trưởng theo kỳ.')
        return item
    if earlier and any(earlier.get(key) != spec.get(key) for key in ('unit', 'grain', 'aggregation') if key in spec):
        item.update(status='not_comparable', previous=None, summary='Định nghĩa chỉ số hai kỳ khác nhau; không tính chênh lệch.')
        return item
    if spec.get('unit') == 'currency' and current.get('currency') != earlier.get('currency'):
        item.update(status='currency_mismatch', previous=None, summary='Hai kỳ khác tiền tệ; không tự quy đổi.')
        return item
    if actual is None or prior is None:
        return item
    # Projectors already reject booleans, non-finite numbers and negative actuals.
    with localcontext() as context:
        context.prec = 100
        left, right = Decimal(str(actual)), Decimal(str(prior))
        delta = left-right
        relation = 'above' if delta > 0 else 'below' if delta < 0 else 'equal'
        relative = abs(delta)/right if right else None
        item.update(status='ready', difference=format(abs(delta), 'f'),
                    relative=format(relative, 'f') if relative is not None else None, relation=relation)
        item.update(effect(spec.get('key'), relation))
        largest = max(left, right)
        item['chart'] = {'actual': float(left/largest*100) if largest else 0,
                         'previous': float(right/largest*100) if largest else 0}
        item['difference_label'] = display(abs(delta)*100, 'number')+' điểm phần trăm' if spec.get('unit') == 'percent' else display(abs(delta), spec.get('unit'), item['currency'])
        sign = '+' if delta > 0 else '−' if delta < 0 else ''
        if not delta:
            item['summary'] = 'Không thay đổi'
        elif spec.get('key') == 'position':
            item['summary'] = sign + display(abs(delta), 'number') + ' vị trí'
        elif spec.get('unit') == 'percent':
            item['summary'] = sign + display(abs(delta)*100, 'number') + ' điểm phần trăm'
        elif not right:
            item['summary'] = 'Kỳ đối chiếu bằng 0; chênh lệch ' + sign + display(abs(delta), spec.get('unit'), item['currency'])
        else:
            item['summary'] = sign + display(relative, 'percent')
    return item


def organic_sessions_metric(report):
    """Keep an absent channel unknown, using only the attested GA4 channel row."""
    channels = next((table['rows'] for table in report.get('tables', []) if table['id'] == 'channels'), [])
    rows = [row for row in channels if row.get('sessionDefaultChannelGroup') == 'Organic Search']
    value = rows[0].get('sessions') if len(rows) == 1 and report.get('snapshot') else None
    return {'key': 'organic_sessions', 'label': 'Phiên Organic Search', 'unit': 'count',
            'grain': 'period', 'aggregation': 'provider_channel_total', 'value': value, 'currency': None}


def describe(report, mode, wanted=None):
    period = report.get('period') or {}
    current = {'start': period.get('data_start'), 'end': period.get('data_end')}
    days = lambda value: (date.fromisoformat(value['end'])-date.fromisoformat(value['start'])).days+1 if value and value.get('start') and value.get('end') else 0
    return {'mode': mode, 'label': LABELS[mode], 'status': 'disabled' if mode == 'none' else 'no_current_data',
            'period': wanted, 'current_period': current, 'current_days': days(current),
            'comparison_days': days(wanted), 'matched_elapsed': bool(period.get('is_open')) and mode != 'custom',
            'items': [], 'snapshot': None, 'message': '' if mode == 'none' else 'Chưa có bản lưu kỳ đang xem để đối chiếu.'}


async def attach(request, report, path, projector, *, mode=None, custom=None):
    if mode is None:
        mode, custom = parameters(request.query_params)
    try:
        wanted = resolve(report.get('period'), mode, custom)
    except CustomerError as error:
        if error.code != 'report_comparison_limit':
            raise
        report['comparison'] = describe(report, mode)
        report['comparison'].update(status='unavailable', message=error.message)
        return None
    comparison = describe(report, mode, wanted)
    report['comparison'] = comparison
    if mode == 'none' or not wanted:
        return None
    calendar = report.get('calendar') or {}
    if calendar.get('latest_closed_date') and wanted['end'] > calendar['latest_closed_date']:
        invalid('Kỳ đối chiếu phải kết thúc vào ngày nguồn đã kết thúc.')
    comparison.update(status='missing', message='Chưa có bản lưu đúng kỳ đối chiếu. Đồng bộ kỳ đối chiếu để xem chênh lệch.')
    if not report.get('asset'):
        comparison.update(status='no_current_data', message='Đồng bộ kỳ đang xem trước khi đối chiếu.')
        return None
    try:
        earlier = projector(await backend(request, 'GET', path+'?'+urlencode(wanted)), report['scope']['workspace_id'])
    except CustomerError as error:
        if error.status in (401, 403, 409):
            raise
        comparison.update(status='unavailable', message='Chưa tải được kỳ đối chiếu. Kỳ hiện tại vẫn được giữ nguyên.')
        return None
    assert_same_asset(report, earlier)
    assert_period(earlier, wanted)
    comparison['latest_sync'] = earlier.get('latest_sync')
    if not earlier.get('snapshot'):
        if (earlier.get('latest_sync') or {}).get('status') in ('queued', 'running'):
            comparison.update(status='syncing', message='Kỳ đối chiếu đang đồng bộ. Cập nhật kết quả sau khi tác vụ hoàn tất.')
        return None
    metrics = {item['key']: item for item in report['metrics']} if report.get('snapshot') else {}
    previous = {item['key']: item for item in earlier['metrics']}
    specs = (report.get('connector') or {}).get('metrics') or report['metrics']
    comparison['items'] = [metric_change(spec, metrics.get(spec['key'], {}), previous.get(spec['key'], {})) for spec in specs]
    if report['source'] == 'ga4':
        organic, old_organic = organic_sessions_metric(report), organic_sessions_metric(earlier)
        comparison['items'].append(metric_change(organic, organic, old_organic))
    comparable = {item['key'] for item in comparison['items'] if item['status'] == 'ready'}
    daily = earlier.get('daily', [])
    if earlier['source'] == 'facebook_content':
        daily = [{'date': row['date'], 'values': {'posts_published': row['posts_published']}} for row in earlier.get('daily_posts', [])]
    comparison['daily'] = [{'date': row['date'], 'values': {key: value for key, value in row['values'].items() if key in comparable}} for row in daily[:90]]
    comparison.update(status='ready' if report.get('snapshot') else 'no_current_data',
                      snapshot={key: earlier['snapshot'].get(key) for key in ('id', 'start_date', 'end_date', 'fetched_at')},
                      message='Đối chiếu các bản dữ liệu đã đồng bộ đúng ngày và cùng tài khoản nguồn.' if report.get('snapshot')
                      else 'Kỳ đối chiếu đã có dữ liệu. Đồng bộ kỳ đang xem để tính chênh lệch.')
    return earlier
