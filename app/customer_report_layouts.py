"""Source-specific presentation over the saved DTO. No metric or provider writes."""
from decimal import Decimal, InvalidOperation, localcontext
from datetime import date, timedelta
import re


PROFILES = {
    'ga4': {
        'id': 'acquisition', 'template': 'ga4', 'eyebrow': 'WEBSITE / AUDIENCE',
        'title': 'Từ lượt truy cập đến tương tác.', 'section': 'Nguồn truy cập',
        'trend': 'Nhịp truy cập', 'detail': 'Kênh & trang được xem',
        'lead': 'active_users', 'order': ('active_users', 'sessions', 'page_views', 'engagement_rate'),
        'chart': 'sessions', 'style': 'line',
    },
    'gsc': {
        'id': 'search', 'template': 'gsc', 'eyebrow': 'GOOGLE / ORGANIC SEARCH',
        'title': 'Hiện diện trên tìm kiếm.', 'section': 'Truy vấn nổi bật',
        'trend': 'Lượt nhấp & hiển thị', 'detail': 'Truy vấn tìm kiếm',
        'lead': 'clicks', 'order': ('clicks', 'impressions', 'ctr', 'position'),
        'chart': 'clicks', 'style': 'line',
    },
    'facebook_ads': {
        'id': 'paid-social', 'template': 'facebook-ads', 'eyebrow': 'META / PAID SOCIAL',
        'title': 'Ngân sách & kết quả.', 'section': 'Hiệu quả quảng cáo',
        'trend': 'Chi phí theo ngày', 'detail': 'Chiến dịch theo ngày',
        'lead': 'leads', 'order': ('leads', 'cost_per_result', 'spend', 'clicks', 'impressions', 'ctr', 'cpc'),
        'chart': 'spend', 'style': 'bar',
    },
    'google_ads': {
        'id': 'search-ads', 'template': 'google-ads', 'eyebrow': 'GOOGLE / PAID SEARCH',
        'title': 'Đầu tư cho chuyển đổi.', 'section': 'Hiệu quả đầu tư',
        'trend': 'Chuyển đổi theo ngày', 'detail': 'Chiến dịch theo ngày',
        'lead': 'conversions', 'order': ('conversions', 'spend', 'cpc', 'clicks', 'impressions', 'ctr'),
        'chart': 'conversions', 'style': 'line',
    },
    'tiktok_ads': {
        'id': 'short-video-ads', 'template': 'tiktok-ads', 'eyebrow': 'TIKTOK / ADS PERFORMANCE',
        'title': 'Hiệu quả trong từng nhịp.', 'section': 'Kết quả quảng cáo',
        'trend': 'Nhịp chuyển đổi', 'detail': 'Hiệu quả theo ngày',
        'lead': 'conversions', 'order': ('conversions', 'spend', 'clicks', 'ctr', 'cpc', 'impressions'),
        'chart': 'conversions', 'style': 'bar',
    },
    'youtube': {
        'id': 'video-editorial', 'template': 'youtube', 'eyebrow': 'YOUTUBE / VIDEO ANALYTICS',
        'title': 'Video. Người xem. Thời gian.', 'section': 'Video nổi bật',
        'trend': 'Thời gian xem', 'detail': 'Hiệu suất video',
        'lead': 'watch_minutes', 'order': ('watch_minutes', 'views', 'subscribers_gained', 'average_view_seconds'),
        'chart': 'watch_minutes', 'style': 'line',
    },
    'business_profile': {
        'id': 'local-actions', 'template': 'business-profile', 'eyebrow': 'GOOGLE / LOCAL BUSINESS',
        'title': 'Từ tìm kiếm đến hành động.', 'section': 'Hành động trên hồ sơ',
        'trend': 'Tương tác theo ngày', 'detail': 'Dữ liệu tại địa điểm',
        'lead': 'directions', 'order': ('call_clicks', 'website_clicks', 'directions', 'search_mobile', 'maps_mobile'),
        'chart': 'directions', 'style': 'bar',
    },
    'instagram': {
        'id': 'social-editorial', 'template': 'instagram', 'eyebrow': 'INSTAGRAM / CONTENT',
        'title': 'Dấu ấn của nội dung.', 'section': 'Bài đăng nổi bật',
        'trend': 'Nhịp xuất bản', 'detail': 'Hiệu suất bài đăng',
        'lead': 'likes_lifetime', 'order': ('likes_lifetime', 'comments_lifetime', 'posts_published', 'followers'),
        'chart': 'posts_published', 'style': 'bar',
    },
}


def _amount(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() and result >= 0 else None
    except (ValueError, InvalidOperation):
        return None


def ranked_rows(report, table_id, label, key):
    """Rank loaded rows only; do not aggregate dimensions into account totals."""
    table = next((item for item in report.get('tables', []) if item['id'] == table_id), None)
    if not table:
        return {'rows': [], 'loaded': 0, 'total': 0, 'missing': 0, 'key': key}
    columns = {column['key']: column for column in table['columns']}
    unit = columns.get(key, {}).get('unit', 'count')
    found = [row for row in table['rows'] if _amount(row.get(key)) is not None]
    ordered = sorted(found, key=lambda row: _amount(row[key]), reverse=True)[:5]
    maximum = max((_amount(row[key]) for row in ordered), default=Decimal(0))
    output = []
    for row in ordered:
        video = row.get('video')
        # No guessed captions, images, URLs or thumbnails absent from the DTO.
        url = 'https://www.youtube.com/watch?v='+video if report['source'] == 'youtube' and isinstance(video, str) and re.fullmatch(r'[A-Za-z0-9_-]{11}', video) else None
        output.append({'label': row.get(label) or 'Chưa có tên', 'value': row[key],
            'unit': unit, 'width': round(100 * _amount(row[key]) / maximum, 2) if maximum else 0,
            'url': url, 'row': dict(row)})
    return {'rows': output, 'loaded': len(table['rows']), 'total': table['total_rows'],
            'missing': len(table['rows'])-len(found), 'key': key}


def distribution(report):
    """Parts of one measured quantity, scoped to the rows actually loaded."""
    specs = {
        'ga4': ('channels', 'sessionDefaultChannelGroup', 'sessions', 'Phiên theo kênh', 'phiên đã tải'),
        'gsc': ('queries', 'query', 'clicks', 'Lượt nhấp theo truy vấn', 'nhấp đã tải'),
        'facebook_ads': ('campaigns', 'campaign_name', 'spend_decimal', 'Phân bổ chi tiêu', 'chi phí đã tải'),
        'google_ads': ('campaigns', 'campaign', 'spend', 'Phân bổ chi tiêu', 'chi phí đã tải'),
        'tiktok_ads': ('daily', 'date', 'spend', 'Chi tiêu theo tuần', 'chi phí đã tải'),
        'youtube': ('videos', 'video', 'views', 'Lượt xem theo video', 'lượt xem đã tải'),
        'instagram': ('posts', 'format', None, 'Định dạng nội dung', 'bài đã tải'),
        'facebook_content': ('posts', 'format', None, 'Định dạng nội dung', 'bài đã tải'),
    }
    if report['source'] == 'business_profile':
        keys = {'call_clicks': 'Nhấp nút gọi', 'website_clicks': 'Nhấp website', 'directions': 'Chỉ đường'}
        metrics = {item['key']: item for item in report.get('metrics', [])}
        return {'title': 'Các thao tác trên hồ sơ', 'label': 'thao tác', 'unit': 'count',
                'rows': [{'label': label, 'value': metrics.get(key, {}).get('value')} for key, label in keys.items()],
                'note': 'Tỷ trọng các loại thao tác đã ghi nhận. Một người có thể thực hiện nhiều thao tác.'}
    if report['source'] not in specs:
        return None
    table_id, group_key, value_key, title, label = specs[report['source']]
    table = next((item for item in report.get('tables', []) if item['id'] == table_id), None)
    output = {'title': title, 'label': label, 'unit': 'currency' if value_key in ('spend', 'spend_decimal') else 'count',
              'rows': [], 'note': 'Chưa có dữ liệu phân bổ trong bản lưu này.'}
    if not table or not table['rows']:
        return output
    groups = {}
    for row in table['rows']:
        group = row.get(group_key) or 'Chưa phân loại'
        if report['source'] == 'tiktok_ads':
            try:
                day = date.fromisoformat(group)
            except (TypeError, ValueError):
                return output
            group = 'Tuần từ ' + (day - timedelta(days=day.weekday())).strftime('%d/%m')
        value = Decimal(1) if value_key is None else _amount(row.get(value_key))
        if value is None:
            output['note'] = 'Một số hàng thiếu số liệu, chưa đủ để tính tỷ trọng.'
            return output
        with localcontext() as context:
            context.prec = 100
            groups[group] = groups.get(group, Decimal(0)) + value
    format_labels = {'photo': 'Ảnh', 'album': 'Album', 'video': 'Video', 'link': 'Liên kết',
                     'IMAGE': 'Ảnh', 'VIDEO': 'Video', 'CAROUSEL_ALBUM': 'Album'}
    output['rows'] = [{'label': format_labels.get(key, key),
                       'value': str(value) if output['unit'] == 'currency' else int(value) if value == value.to_integral_value() else float(value)}
                      for key, value in groups.items()]
    output['note'] = (f"Tỷ trọng trong {len(table['rows'])} hàng đã tải"
                      + (f" / {table['total_rows']} hàng nguồn" if table['total_rows'] > len(table['rows']) else '')
                      + '. Tổng giữa vòng chỉ tính các hàng này.')
    return output


def build_layout(report):
    profile = dict(PROFILES.get(report['source'], {
        'id': 'content', 'template': 'default', 'eyebrow': 'FACEBOOK / CONTENT',
        'title': 'Bức tranh nội dung.', 'section': 'Nội dung',
        'trend': 'Nhịp xuất bản', 'detail': 'Chi tiết bài đăng',
        'lead': 'posts_published', 'order': ('posts_published',),
        'chart': 'posts_published', 'style': 'bar',
    }))
    by_key = {metric['key']: metric for metric in report.get('metrics', [])}
    ordered = [by_key[key] for key in profile['order'] if key in by_key]
    ordered += [metric for metric in report.get('metrics', []) if metric['key'] not in profile['order']]
    # Keep the exact metric dictionaries, including precision, null and semantics.
    profile['metrics'] = ordered
    profile['lead_metric'] = by_key.get(profile['lead'])
    profile['by_key'] = by_key
    profile['rankings'] = {}
    profile['distribution'] = distribution(report)
    specs = {
        'ga4': (('channels', 'sessionDefaultChannelGroup', 'sessions'), ('pages', 'pagePath', 'screenPageViews')),
        'gsc': (('queries', 'query', 'clicks'),),
        'youtube': (('videos', 'video', 'views'),),
        'instagram': (('posts', 'caption', 'likes_lifetime'),),
    }
    for table, label, key in specs.get(report['source'], ()):
        profile['rankings'][table] = ranked_rows(report, table, label, key)
    return profile
