"""Presentation contract for the customer overview; never invent Marketing data.

Admin remains the authority for scopes, connections and future analytics reads.
This builds an empty, data-bindable view from the existing customer endpoints.
"""

METRICS = (
    ('spend', 'Tổng chi tiêu quảng cáo', 'currency', 'Kết nối nền tảng để xem chỉ số', 'Meta & Google Ads'),
    ('impressions', 'Lượt hiển thị (Impressions)', 'number', 'Theo dõi độ phủ của các kênh', 'Quảng cáo & tìm kiếm'),
    ('clicks', 'Lượt nhấp (Clicks)', 'number', 'Theo dõi tương tác truy cập', 'Search & Ads'),
    ('conversions', 'Lượt chuyển đổi (Conversions)', 'number', 'Theo dõi mục tiêu kinh doanh', 'Sự kiện đã cấu hình'),
)

CHANNELS = (
    ('facebook_ads', 'Facebook Ads', 'Chi phí, kết quả & chiến dịch', 'campaign', 'blue'),
    ('google_ads', 'Google Ads', 'Từ khóa, Search & Performance Max', 'ads_click', 'amber'),
    ('seo', 'SEO & Keywords', 'Thứ hạng & hiệu suất tìm kiếm', 'tag', 'green'),
    ('ga4', 'Analytics (GA4)', 'Phiên, hành vi & sự kiện', 'bar_chart', 'orange'),
    ('tiktok_ads', 'TikTok Ads', 'Chiến dịch & hiệu quả video', 'music_note', 'dark'),
    ('business_profile', 'Google Maps', 'Hồ sơ, tương tác & chỉ đường', 'location_on', 'purple'),
)


def build_overview(details, catalogue):
    workspace = details['workspace']
    client = details.get('selected_client')
    source_order = ('ga4', 'facebook_ads', 'gsc', 'tiktok_ads', 'business_profile', 'facebook_content', 'youtube', 'google_ads', 'instagram')
    platforms = sorted(catalogue.get('platforms', []), key=lambda item: source_order.index(item['id']) if item['id'] in source_order else len(source_order))
    return {
        'schema_version': 1,
        'scope': {'workspace_id': workspace['id'], 'client_id': client['id'] if client else None},
        'currency': workspace.get('currency', 'VND'), 'timezone': workspace.get('timezone', 'Asia/Ho_Chi_Minh'),
        'period': None, 'last_updated_at': None,
        'metrics': {key: {'label': label, 'unit': unit, 'value': None, 'previous': None,
                           'status': 'empty', 'hint': hint, 'source_label': source}
                    for key, label, unit, hint, source in METRICS},
        'trends': {key: {'status': 'empty', 'points': []} for key in ('spend', 'clicks', 'conversions')},
        'platforms': platforms, 'connections': [], 'reports': [],
        'channels': [{'id': key, 'name': label, 'description': description, 'icon': icon, 'color': color}
                     for key, label, description, icon, color in CHANNELS],
    }
