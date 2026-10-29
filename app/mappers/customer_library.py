"""Presentation scaffolds only; Admin owns datasets, revisions and publication.

The nine analysis areas include SEO as a composite, not an OAuth provider.
Instagram stays in the integration catalogue; it is not a tenth analysis area.
"""
from copy import deepcopy

GROUPS = (
    ('all', 'Tất cả'), ('ads', 'Quảng cáo'), ('social', 'Mạng xã hội'),
    ('search', 'SEO & Website'), ('video', 'Video'), ('local', 'Doanh nghiệp địa phương'),
)

# key, name, group, icon, color, sources, description, topics, metric definitions
CHANNELS = (
    ('facebook_ads', 'Facebook Ads', 'ads', 'campaign', 'blue', ('facebook_ads',),
     'Đọc hiệu quả chiến dịch Facebook và Instagram từ chi phí đến kết quả quảng cáo.',
     ('Chi phí & ROAS', 'Lượt nhấp & CTR', 'Kết quả chiến dịch'),
     (('spend', 'Chi tiêu', 'currency'), ('clicks', 'Lượt nhấp', 'number'), ('roas', 'ROAS', 'ratio'))),
    ('tiktok_ads', 'TikTok Ads', 'ads', 'play_circle', 'dark', ('tiktok_ads',),
     'Theo dõi phân phối video, chi phí và chuyển đổi của chiến dịch TikTok.',
     ('Video & lượt xem', 'Chi tiêu & CPC', 'Lượt chuyển đổi'),
     (('spend', 'Chi tiêu', 'currency'), ('video_views', 'Lượt xem', 'number'), ('conversions', 'Chuyển đổi', 'number'))),
    ('google_ads', 'Google Ads', 'ads', 'ads_click', 'amber', ('google_ads',),
     'Đánh giá quảng cáo Search, Display và Performance Max theo từng tài khoản.',
     ('Từ khóa & chiến dịch', 'Lượt nhấp & CTR', 'Chi phí / chuyển đổi'),
     (('spend', 'Chi tiêu', 'currency'), ('ctr', 'CTR', 'percent'), ('conversions', 'Chuyển đổi', 'number'))),
    ('facebook_content', 'Facebook Content', 'social', 'feed', 'blue', ('facebook_content',),
     'Khám phá nội dung Fanpage, bài đăng, mức tiếp cận và tương tác được ghi nhận.',
     ('Hiệu quả bài đăng', 'Tương tác & chia sẻ', 'Tăng trưởng theo dõi'),
     (('posts', 'Bài viết', 'number'), ('interactions', 'Tương tác', 'number'), ('reach', 'Tiếp cận', 'number'))),
    ('seo', 'SEO & Keywords', 'search', 'troubleshoot', 'orange', ('ga4', 'gsc'),
     'Theo dõi thứ hạng từ khóa, trang đích và hiệu quả tìm kiếm trong cùng một góc nhìn.',
     ('Thứ hạng từ khóa', 'Biến động vị trí', 'Hiệu suất trang đích'),
     (('top10', 'Top 10', 'number'), ('visibility', 'Hiển thị SEO', 'percent'), ('tracked_keywords', 'Từ khóa', 'number'))),
    ('ga4', 'Google Analytics 4', 'search', 'monitoring', 'amber', ('ga4',),
     'Hiểu người dùng, phiên truy cập và hành vi trên website hoặc ứng dụng.',
     ('Người dùng & phiên', 'Nguồn truy cập', 'Sự kiện quan trọng'),
     (('users', 'Người dùng', 'number'), ('sessions', 'Phiên', 'number'), ('engagement_rate', 'Tỷ lệ tương tác', 'percent'))),
    ('gsc', 'Google Search Console', 'search', 'search_insights', 'teal', ('gsc',),
     'Phân tích truy vấn, lượt nhấp và mức hiển thị tự nhiên trên Google Search.',
     ('Truy vấn & trang đích', 'Lượt nhấp & hiển thị', 'Vị trí tìm kiếm'),
     (('clicks', 'Lượt nhấp', 'number'), ('impressions', 'Hiển thị', 'number'), ('position', 'Vị trí TB', 'number'))),
    ('youtube', 'YouTube', 'video', 'smart_display', 'red', ('youtube',),
     'Đánh giá video và kênh qua lượt xem, thời gian xem và lượt đăng ký mới.',
     ('Hiệu suất video', 'Thời gian xem', 'Tăng trưởng kênh'),
     (('views', 'Lượt xem', 'number'), ('watch_hours', 'Giờ xem', 'number'), ('subscribers', 'Đăng ký mới', 'number'))),
    ('business_profile', 'Google Business Profile', 'local', 'storefront', 'green', ('business_profile',),
     'Theo dõi sự hiện diện địa phương trên Google Search và Maps.',
     ('Cuộc gọi', 'Yêu cầu chỉ đường', 'Đánh giá & phản hồi'),
     (('calls', 'Cuộc gọi', 'number'), ('directions', 'Chỉ đường', 'number'), ('rating', 'Điểm đánh giá', 'number'))),
)


def build_library(details, catalogue):
    workspace = details['workspace']
    client = details.get('selected_client')
    scope = {'workspace_id': workspace['id'], 'client_id': client['id'] if client else None}
    catalogue_client = catalogue.get('selected_client')
    if catalogue.get('workspace', {}).get('id') != workspace['id'] or (
        catalogue_client.get('id') if catalogue_client else None
    ) != scope['client_id']:
        raise ValueError('Library scope mismatch')
    groups = dict(GROUPS)
    platforms = {p['id']: p for p in catalogue.get('platforms', [])}
    connections = [c for c in catalogue.get('connections', [])
                   if client and c.get('workspace_id') == workspace['id']
                   and c.get('client_id') == client['id'] and c.get('platform_id') in platforms]
    channels = []
    for key, name, group, icon, color, sources, description, topics, metrics in CHANNELS:
        states = [c.get('state') for c in connections if c.get('platform_id') in sources]
        state = ('attention' if any(s in ('expired', 'error', 'disconnected') for s in states)
                 else 'syncing' if 'syncing' in states
                 else 'empty' if 'connected' in states else 'not_connected')
        channels.append({'id': key, 'name': name, 'group': group, 'group_label': groups[group],
                         'icon': icon, 'color': color, 'source_ids': list(sources),
                         'description': description, 'topics': list(topics), 'state': state,
                         'metrics': [{'key': k, 'label': label, 'unit': unit, 'value': None}
                                     for k, label, unit in metrics]})
    templates = [{'id': 'overview', 'name': 'Marketing tổng hợp', 'group': 'multi',
                  'group_label': 'Đa kênh', 'icon': 'stacked_bar_chart', 'color': 'red',
                  'description': 'Tóm tắt hiệu suất các nguồn Marketing trong một báo cáo nhất quán theo khách hàng và kỳ đã chọn.',
                  'source_ids': list(platforms), 'topics': ['KPI tổng quan', 'Xu hướng đa kênh', 'So sánh nguồn dữ liệu'],
                  'state': 'empty', 'metrics': [
                      {'key': k, 'label': label, 'unit': unit, 'value': None}
                      for k, label, unit in (('spend', 'Chi tiêu', 'currency'), ('clicks', 'Lượt nhấp', 'number'),
                                             ('conversions', 'Chuyển đổi', 'number'), ('roas', 'ROAS', 'ratio'))]}]
    templates.extend(deepcopy(channels))
    return {'schema_version': 1, 'scope': scope, 'currency': workspace.get('currency', 'VND'),
            'timezone': workspace.get('timezone', 'Asia/Ho_Chi_Minh'), 'period': None,
            'groups': [{'id': k, 'label': v} for k, v in GROUPS], 'channels': channels,
            'templates': templates, 'reports': [], 'exports': [], 'reports_loaded': False,
            'capabilities': {'save_report': False, 'export_report': False, 'share_report': False},
            'sources': [{'id': p['id'], 'name': p['name']} for p in platforms.values()]}
