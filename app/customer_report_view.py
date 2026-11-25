"""Pure presentation facts derived from the authenticated saved-data DTO."""
from datetime import date
from app.customer_report_layouts import build_layout
from app.customer_metric_semantics import trend


DESCRIPTIONS = {
    'ga4': 'Người dùng, lượt truy cập và tương tác trên website hoặc ứng dụng.',
    'gsc': 'Hiệu suất xuất hiện và lượt nhấp từ tìm kiếm tự nhiên Google.',
    'google_ads': 'Chi phí, lượt nhấp và chuyển đổi của tài khoản Google Ads.',
    'facebook_ads': 'Hiệu quả quảng cáo Facebook và Instagram theo tài khoản đã chọn.',
    'tiktok_ads': 'Hiệu quả tài khoản quảng cáo TikTok theo kỳ đã đồng bộ.',
    'youtube': 'Lượt xem, thời gian xem và lượt đăng ký kênh trong kỳ.',
    'business_profile': 'Tương tác của khách hàng với hồ sơ doanh nghiệp trên Google.',
    'instagram': 'Nhịp đăng bài, tương tác tích lũy và tài khoản Instagram chuyên nghiệp.',
    'facebook_content': 'Nội dung và tương tác Fanpage từ lần đồng bộ được lưu.',
}

SYNC_MESSAGES = {
    'provider_setup_required': 'Vio cần hoàn tất cấu hình API cho nền tảng này. Vui lòng liên hệ hỗ trợ; bạn không cần đăng nhập lại.',
    'provider_account_required': 'Tài khoản chưa có nguồn dữ liệu phù hợp. Hãy chọn tài khoản quản lý nguồn tại Kết nối nền tảng.',
    'provider_scopes': 'Tài khoản chưa có đủ quyền đọc nguồn dữ liệu. Kiểm tra quyền hoặc đăng nhập tài khoản khác tại Kết nối nền tảng.',
    'provider_rate_limit': 'Nền tảng đang giới hạn lượt đọc. Hãy thử lại sau; kết nối vẫn được giữ nguyên.',
    'provider_reauth': 'Quyền truy cập đã hết hiệu lực. Hãy cấp quyền lại tại Kết nối nền tảng.',
}

MEANINGS = {
    'provider_period': 'Lấy tổng kỳ do nền tảng trả về. Không cộng số người duy nhất hoặc trung bình các tỷ lệ theo ngày.',
    'sum': 'Cộng các quan sát hợp lệ trong kỳ. Ngày không có quan sát được giữ trống.',
    'decimal_sum': 'Cộng chi phí bằng số thập phân, giữ nguyên tiền tệ tài khoản.',
    'sum_complete_days': 'Chỉ hiển thị tổng kỳ khi chỉ số có quan sát đủ các ngày.',
    'clicks/impressions': 'Tổng lượt nhấp ÷ tổng lượt hiển thị × 100%. Không lấy trung bình CTR của các ngày.',
    'spend/clicks': 'Tổng chi phí ÷ tổng lượt nhấp. Không tính khi thiếu dữ liệu hoặc mẫu số bằng 0.',
    'spend/lead': 'Tổng chi phí ÷ tổng Lead được ghi nhận. Không tính khi thiếu dữ liệu hoặc chưa có Lead.',
    'sum_posts_at_fetch': 'Bộ đếm tích lũy của các bài đăng trong kỳ, đo tại lúc đồng bộ. Không phải tương tác phát sinh riêng trong kỳ.',
    'latest_observation': 'Số hiện tại tại lúc đồng bộ. Không phải số tăng mới trong kỳ.',
}

SPECIFIC_MEANINGS = {
    ('ga4', 'active_users'): 'Người dùng hoạt động duy nhất do GA4 tính cho cả kỳ. Một người xuất hiện nhiều ngày không được cộng lặp.',
    ('ga4', 'page_views'): 'screenPageViews của GA4 gồm lượt xem trang web và màn hình ứng dụng trong property đã chọn.',
    ('ga4', 'engagement_rate'): 'Phiên có tương tác ÷ tổng phiên, lấy từ kết quả toàn kỳ của GA4.',
    ('gsc', 'position'): 'Vị trí trung bình do Search Console tính cho kỳ. Số nhỏ hơn thể hiện vị trí gần đầu kết quả hơn.',
    ('youtube', 'average_view_seconds'): 'Thời lượng xem trung bình của toàn kỳ, tính bằng giây; không cộng hoặc trung bình đơn giản các ngày.',
    ('youtube', 'subscribers_gained'): 'Số lượt đăng ký mới trong kỳ; không phải tổng số người đăng ký hiện tại của kênh.',
    ('business_profile', 'call_clicks'): 'Số lần nhấp nút gọi trên hồ sơ. Không đồng nghĩa số cuộc gọi đã kết nối hoặc hoàn tất.',
    ('facebook_ads', 'leads'): 'Lead có action_type=lead theo số liệu Meta trả về. Đối chiếu với cài đặt phân bổ và ngày ghi nhận ở Ads Manager.',
    ('facebook_ads', 'ctr'): 'Tất cả lượt nhấp ÷ lượt hiển thị × 100%. Dùng tổng hai chỉ số trong kỳ.',
    ('facebook_ads', 'cpc'): 'Chi phí ÷ tất cả lượt nhấp trong kỳ.',
    ('google_ads', 'conversions'): 'Chuyển đổi theo cài đặt ghi nhận của tài khoản. Có thể có phần thập phân do mô hình phân bổ.',
    ('tiktok_ads', 'conversions'): 'Chuyển đổi theo cài đặt ghi nhận TikTok của advertiser; không tự quy đổi thành doanh thu hoặc ROAS.',
}


def build(report):
    snapshot = report.get('snapshot') or {}
    first, last = snapshot.get('start_date'), snapshot.get('end_date')
    requested = report.get('period') or {}
    requested_first, requested_last = requested.get('start', first), requested.get('end', last)
    days = (date.fromisoformat(last)-date.fromisoformat(first)).days+1 if first and last else 0
    metrics = report.get('metrics', [])
    job = report.get('latest_sync') or {}
    observed_rows = [item for item in report.get('daily', []) if any(value is not None for value in item['values'].values())]
    definitions = []
    for metric in metrics:
        aggregation = metric.get('aggregation')
        definitions.append({'key': metric['key'], 'label': metric['label'],
            'description': SPECIFIC_MEANINGS.get((report['source'], metric['key']), MEANINGS.get(aggregation, 'Theo định nghĩa của nguồn dữ liệu đã chọn.')),
            'available': metric['value'] is not None,
            'unit': {'count':'Số đếm', 'percent':'Tỷ lệ (%)', 'currency':metric.get('currency') or 'Tiền tệ tài khoản'}.get(metric.get('unit'),
                'Vị trí' if metric['key']=='position' else 'Phút' if metric['key']=='watch_minutes' else 'Giây' if metric['key']=='average_view_seconds' else 'Giá trị'),
            'trend': trend(metric['key'])})
    latest = max((item['date'] for item in observed_rows), default=None)
    return {'description': DESCRIPTIONS.get(report['source'], ''), 'days': days, 'layout': build_layout(report),
            'sync_message': SYNC_MESSAGES.get(job.get('error_code'), 'Lần đồng bộ chưa thành công. Hãy thử lại tại Kết nối nền tảng.') if job.get('status') == 'failed' else '',
            'period': date.fromisoformat(requested_first).strftime('%d/%m/%Y')+' – '+date.fromisoformat(requested_last).strftime('%d/%m/%Y') if requested_first and requested_last else '',
            'available': sum(item['value'] is not None for item in metrics), 'total': len(metrics),
            'observed_days': len(observed_rows), 'latest_observation': date.fromisoformat(latest).strftime('%d/%m/%Y') if latest else '',
            'definitions': definitions, 'loaded_rows': sum(len(table['rows']) for table in report.get('tables', [])),
            'missing': [item['label'] for item in metrics if item['value'] is None],
            'table_rows': sum(table['total_rows'] for table in report.get('tables', []))}
