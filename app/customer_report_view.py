"""Pure presentation facts derived from the authenticated saved-data DTO."""
from datetime import date


DESCRIPTIONS = {
    'ga4': 'Người dùng, lượt truy cập và mức độ tương tác trên website.',
    'gsc': 'Hiệu suất xuất hiện và lượt nhấp từ tìm kiếm tự nhiên Google.',
    'google_ads': 'Chi phí, lượt nhấp và chuyển đổi của tài khoản Google Ads.',
    'facebook_ads': 'Hiệu quả quảng cáo Facebook và Instagram theo tài khoản đã chọn.',
    'tiktok_ads': 'Hiệu quả tài khoản quảng cáo TikTok theo kỳ đã đồng bộ.',
    'youtube': 'Lượt xem, thời gian xem và lượt đăng ký kênh trong kỳ.',
    'business_profile': 'Tương tác của khách hàng với hồ sơ doanh nghiệp trên Google.',
    'instagram': 'Nhịp đăng bài, tương tác tích lũy và tài khoản Instagram chuyên nghiệp.',
    'facebook_content': 'Nội dung và tương tác Fanpage từ lần đồng bộ được lưu.',
}


def build(report):
    snapshot = report.get('snapshot') or {}
    first, last = snapshot.get('start_date'), snapshot.get('end_date')
    days = (date.fromisoformat(last)-date.fromisoformat(first)).days+1 if first and last else 0
    metrics = report.get('metrics', [])
    observed = sum(any(value is not None for value in item['values'].values()) for item in report.get('daily', []))
    return {'description': DESCRIPTIONS.get(report['source'], ''), 'days': days,
            'period': date.fromisoformat(first).strftime('%d/%m/%Y')+' – '+date.fromisoformat(last).strftime('%d/%m/%Y') if days else '',
            'available': sum(item['value'] is not None for item in metrics), 'total': len(metrics),
            'observed_days': observed, 'missing': [item['label'] for item in metrics if item['value'] is None],
            'table_rows': sum(table['total_rows'] for table in report.get('tables', []))}
