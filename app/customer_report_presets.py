"""Curated report layouts over the sources and metrics already collected by Vio."""

from dataclasses import dataclass
from urllib.parse import urlencode

from app.customer_auth import CustomerError


@dataclass(frozen=True)
class Preset:
    key: str
    name: str
    description: str
    blocks: tuple[str, ...]
    metrics: tuple[str, ...] = ()
    chart: str = ''
    table: str = ''
    ranking: tuple[str, str] = ()
    sources: tuple[str, ...] = ()
    sections: tuple[str, ...] = ()

    @property
    def style(self):
        return self.blocks[0]


PRESETS = {
    'ga4': (
        Preset('traffic', 'Nguồn truy cập', 'Xem kênh nào mang lại nhiều phiên và kênh nào có tỷ trọng nhỏ.',
               ('distribution', 'ranking', 'metrics', 'details'), ('sessions', 'active_users'), table='channels', ranking=('sessionDefaultChannelGroup', 'sessions')),
        Preset('pages', 'Hiệu suất trang', 'Tìm những trang được xem nhiều để rà lại nội dung và điều hướng.',
               ('ranking', 'details', 'metrics'), ('page_views', 'sessions', 'engagement_rate'), table='pages', ranking=('pagePath', 'screenPageViews')),
        Preset('engagement', 'Mức độ tương tác', 'Theo dõi tỷ lệ tương tác theo thời gian cùng số phiên và lượt xem trang.',
               ('trend', 'metrics', 'comparison'), ('engagement_rate', 'sessions', 'page_views'), chart='engagement_rate'),
    ),
    'gsc': (
        Preset('queries', 'Truy vấn tìm kiếm', 'Đọc truy vấn mang lại lượt nhấp, cùng mức hiển thị và CTR của từng truy vấn.',
               ('ranking', 'details', 'distribution'), ('clicks', 'impressions', 'ctr'), table='queries', ranking=('query', 'clicks')),
        Preset('pages', 'Trang đích từ Google', 'Xem trang nào nhận nhiều lượt nhấp tìm kiếm và đối chiếu CTR giữa các trang.',
               ('details', 'ranking', 'metrics'), ('clicks', 'impressions', 'ctr'), table='seo_pages', ranking=('page', 'clicks')),
        Preset('position', 'Biến động vị trí', 'Theo dõi vị trí trung bình, cách vị trí thay đổi và độ phủ dữ liệu.',
               ('trend', 'metrics', 'comparison'), ('position', 'impressions', 'ctr'), chart='position'),
    ),
    'google_ads': (
        Preset('campaigns', 'Hiệu suất chiến dịch', 'Đọc chi phí, lượt nhấp và chuyển đổi trong bảng chiến dịch theo ngày.',
               ('details', 'distribution', 'metrics'), ('conversions', 'spend', 'clicks'), table='campaigns'),
        Preset('spend', 'Chi phí & CPC', 'Theo dõi nhịp sử dụng ngân sách cùng chi phí mỗi lượt nhấp.',
               ('trend', 'metrics', 'distribution'), ('spend', 'cpc', 'clicks'), chart='spend'),
        Preset('conversions', 'Hiệu quả chuyển đổi', 'Đặt số chuyển đổi cạnh chi phí và đối chiếu kết quả giữa các kỳ.',
               ('metrics', 'trend', 'comparison', 'details'), ('conversions', 'spend', 'clicks'), chart='conversions', table='campaigns'),
    ),
    'facebook_ads': (
        Preset('campaigns', 'Hiệu suất chiến dịch', 'Xem dữ liệu chiến dịch theo ngày và phân bổ chi phí giữa các chiến dịch đã tải.',
               ('details', 'distribution', 'metrics'), ('spend', 'leads', 'clicks'), table='campaigns'),
        Preset('spend', 'Ngân sách & lượt nhấp', 'Đọc nhịp chi tiêu, CPC và khả năng thu hút lượt nhấp.',
               ('trend', 'metrics', 'distribution'), ('spend', 'cpc', 'clicks', 'ctr'), chart='spend'),
        Preset('leads', 'Khách hàng tiềm năng', 'Đọc số lead và chi phí mỗi lead cùng kết quả theo ngày.',
               ('metrics', 'trend', 'details', 'comparison'), ('leads', 'cost_per_result', 'spend'), chart='leads', table='campaigns'),
    ),
    'tiktok_ads': (
        Preset('spend', 'Nhịp chi tiêu', 'Xem chi phí theo ngày và cơ cấu chi tiêu theo tuần.',
               ('trend', 'distribution', 'metrics'), ('spend', 'cpc', 'clicks'), chart='spend'),
        Preset('delivery', 'Phân phối & lượt nhấp', 'Đọc lượt hiển thị và CTR cùng số liệu phân phối từng ngày.',
               ('details', 'metrics', 'trend'), ('impressions', 'clicks', 'ctr'), chart='impressions', table='daily'),
        Preset('conversions', 'Hiệu quả chuyển đổi', 'Kiểm tra ngày có chuyển đổi và đọc kết quả cạnh chi phí trong cùng kỳ.',
               ('metrics', 'trend', 'comparison', 'details'), ('conversions', 'spend', 'clicks'), chart='conversions', table='daily'),
    ),
    'youtube': (
        Preset('videos', 'Video nổi bật', 'Xếp video theo lượt xem và rà thời gian xem ở bảng chi tiết.',
               ('ranking', 'distribution', 'details'), ('views', 'watch_minutes'), table='videos', ranking=('video', 'views')),
        Preset('watch-time', 'Thời gian xem', 'Đọc tổng phút xem và thời lượng xem trung bình qua từng ngày.',
               ('trend', 'metrics', 'ranking'), ('watch_minutes', 'average_view_seconds', 'views'), chart='watch_minutes', table='videos', ranking=('video', 'watch_minutes')),
        Preset('subscribers', 'Lượt đăng ký mới', 'Theo dõi số lượt đăng ký mới và mức thay đổi so với kỳ đối chiếu.',
               ('metrics', 'trend', 'comparison'), ('subscribers_gained', 'views', 'watch_minutes'), chart='subscribers_gained'),
    ),
    'business_profile': (
        Preset('visibility', 'Hiện diện trên Search & Maps', 'Đọc lượt hiển thị trên Google Search và Maps từ thiết bị di động.',
               ('trend', 'metrics', 'details'), ('search_mobile', 'maps_mobile'), chart='search_mobile', table='daily'),
        Preset('local-actions', 'Cuộc gọi & chỉ đường', 'Xem thao tác gọi và yêu cầu chỉ đường, với tỷ trọng từng loại hành động.',
               ('distribution', 'metrics', 'trend'), ('call_clicks', 'directions'), chart='directions'),
        Preset('website', 'Lượt nhấp vào website', 'Theo dõi lượt nhấp website từ hồ sơ doanh nghiệp theo ngày.',
               ('metrics', 'trend', 'details', 'comparison'), ('website_clicks',), chart='website_clicks', table='daily'),
    ),
    'facebook_content': (
        Preset('publishing', 'Nhịp đăng bài', 'Xem ngày có bài đăng và định dạng nội dung đã xuất bản trong kỳ.',
               ('trend', 'distribution', 'metrics'), ('posts_published', 'post_views_lifetime'), chart='publishing'),
        Preset('top-posts', 'Bài viết nổi bật', 'Đọc bài có nhiều lượt xem tích lũy và rà số liệu từng bài.',
               ('ranking', 'details', 'metrics'), ('post_views_lifetime', 'reactions_lifetime', 'comments_lifetime')),
        Preset('engagement', 'Tương tác nội dung', 'Đọc cảm xúc, bình luận và số liệu tương tác Fanpage khi có quan sát.',
               ('metrics', 'trend', 'details'), ('reactions_lifetime', 'comments_lifetime', 'post_views_lifetime'), chart='page_post_engagements'),
    ),
    'instagram': (
        Preset('publishing', 'Lịch xuất bản', 'Xem nhịp đăng và đối chiếu với danh sách bài thực tế trong kỳ.',
               ('trend', 'metrics', 'details'), ('posts_published', 'followers'), chart='posts_published', table='posts'),
        Preset('formats', 'Cơ cấu định dạng', 'Đọc tỷ trọng ảnh, video và album trong các bài đã tải.',
               ('distribution', 'details', 'metrics'), ('posts_published', 'likes_lifetime', 'comments_lifetime'), table='posts'),
        Preset('engagement', 'Bài đăng tạo tương tác', 'Xếp bài theo lượt thích tích lũy và đọc bình luận ở từng bài.',
               ('ranking', 'metrics', 'details'), ('likes_lifetime', 'comments_lifetime', 'posts_published'), table='posts', ranking=('caption', 'likes_lifetime')),
    ),
    'seo': (
        Preset('website', 'Hiệu quả SEO & website', 'Đọc phiên truy cập, hiệu suất tìm kiếm và xu hướng website trong kỳ.', ('trend',),
               sources=('seo', 'ga4', 'gsc'), sections=('summary', 'charts', 'comparison')),
        Preset('rankings', 'Thứ hạng từ khóa', 'Đọc vị trí và biến động của từ khóa theo dõi, có nhóm riêng cho bộ cam kết.', ('ranking',),
               sources=('seo',), sections=('details', 'charts', 'comparison')),
        Preset('long-tail', 'Từ khóa phụ & ngách', 'Rà các từ khóa mở rộng, vai trò từng từ và quan sát có trong kỳ.', ('details',),
               sources=('seo',), sections=('details', 'comparison')),
        Preset('content', 'Bài viết & nghiệm thu', 'Tổng hợp bài đăng, bài nghiệm thu và hiệu quả truy cập theo URL.', ('details',),
               sources=('seo', 'ga4', 'gsc'), sections=('details', 'charts')),
        Preset('commitments', 'Cam kết KPI dự án', 'Xem ma trận kế hoạch 12 tháng, kết quả thực hiện và bằng chứng nghiệm thu.', ('kpi',),
               sources=('seo', 'ga4', 'gsc'), sections=('kpi', 'seo_work')),
    ),
    'combined': (
        Preset('executive', 'Tóm tắt điều hành', 'Điểm qua kết quả chính và nguồn dữ liệu đã sẵn sàng để gửi quản lý.', ('metrics',), sections=('summary',)),
        Preset('comparison', 'Đối chiếu đa nền tảng', 'Đọc kết quả kỳ này và kỳ đối chiếu riêng cho từng nền tảng.', ('comparison',), sections=('comparison',)),
        Preset('goals', 'KPI đa nền tảng', 'Đặt mục tiêu cạnh số thực tế cho từng nguồn, với trạng thái đạt và chưa đạt.', ('kpi',), sections=('kpi',)),
        Preset('trends', 'Xu hướng theo nguồn', 'Dùng chuỗi theo ngày và biểu đồ phân bổ để rà nhịp thay đổi ở từng nguồn.', ('trend',), sections=('charts', 'comparison')),
        Preset('details', 'Phụ lục dữ liệu', 'Gom bảng truy vấn, bài viết, video hoặc chiến dịch theo từng nguồn để đối soát.', ('details',), sections=('details',)),
    ),
}


PLATFORM_FOCUS = (
    Preset('comparison', 'Đối chiếu hai kỳ', 'So sánh cùng nguồn và tài khoản để thấy chỉ số nào thay đổi.', ('comparison', 'metrics', 'trend')),
    Preset('goals', 'Theo dõi KPI', 'Xem mục tiêu, kết quả thực tế và mức chênh lệch của từng chỉ số.', ('kpi', 'metrics')),
)


def for_source(source):
    return PRESETS.get(source, ()) + (PLATFORM_FOCUS if source in PRESETS and source not in ('seo', 'combined') else ())


def get_preset(source, key):
    if key is None:
        return None
    preset = next((preset for preset in for_source(source) if preset.key == key), None)
    if preset is None:
        raise CustomerError(404, 'Mẫu báo cáo không thuộc nền tảng này.', 'report_template')
    return preset


def compiled_id(source, preset):
    return f'{source}:{preset.key}'


def compiled_preset(value):
    if value is None:
        return None, None
    source, _, key = str(value).partition(':')
    if source not in ('seo', 'combined'):
        raise CustomerError(404, 'Không tìm thấy mẫu báo cáo tổng hợp.', 'report_template')
    return source, get_preset(source, key)


def preset_url(url, source, preset):
    if source in ('seo', 'combined'):
        return '/workspace/reports/combined?' + urlencode({'template': compiled_id(source, preset)})
    query = {'template': preset.key}
    if 'comparison' in preset.blocks:
        query['comparison'] = 'previous'
    return url + ('&' if '?' in url else '?') + urlencode(query)


SEO_MODULES = {'website': ('performance',), 'rankings': ('keywords',), 'long-tail': ('extended',),
               'content': ('articles',), 'commitments': ('matrix', 'kpi', 'work')}


def seo_modules(source, preset):
    return SEO_MODULES[preset.key] if source == 'seo' and preset else None
