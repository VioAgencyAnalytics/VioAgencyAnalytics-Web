"""Presentation choices for complete reports. A style never selects data or sections."""

from dataclasses import dataclass
from urllib.parse import urlencode

from app.customer_auth import CustomerError


@dataclass(frozen=True)
class ReportStyle:
    key: str
    name: str
    description: str


STYLES = (
    ReportStyle('standard', 'Tiêu chuẩn', 'Trang bìa theo thương hiệu, các phần lớn và biểu đồ dễ đọc.'),
    ReportStyle('executive', 'Điều hành', 'Tiêu đề và thông tin kỳ đặt cạnh nhau, dưới đó là dải số liệu nổi bật.'),
    ReportStyle('editorial', 'Ấn phẩm', 'Bố cục theo chương, tiêu đề serif và phần nhận xét có lề màu riêng.'),
    ReportStyle('analytical', 'Lưới phân tích', 'Bố cục theo ô, khung biểu đồ rõ và bảng số căn thẳng.'),
    ReportStyle('contrast', 'Tương phản', 'Nền xanh đậm, khung số liệu sáng và màu nền tảng làm điểm nhấn.'),
    ReportStyle('ledger', 'Sổ báo cáo', 'Cột và hàng kẻ rõ, thông tin kỳ trình bày theo dạng hồ sơ.'),
)
STYLE_BY_KEY = {style.key: style for style in STYLES}
PALETTES = {
    'brand': 'Màu nền tảng', 'navy': 'Xanh navy', 'teal': 'Xanh ngọc',
    'plum': 'Tím mận', 'brick': 'Đỏ gạch', 'slate': 'Xám than',
}
ORDER_KEYS = frozenset((
    'summary', 'highlights', 'trend', 'comparison', 'kpi', 'distribution', 'details', 'method',
    'performance', 'keywords', 'articles', 'extended', 'ga4', 'gsc', 'google_ads', 'facebook_content',
    'facebook_ads', 'instagram', 'youtube', 'tiktok_ads', 'business_profile',
))


def get_style(key):
    style = STYLES[0] if key is None else STYLE_BY_KEY.get(key)
    if style is None:
        raise CustomerError(404, 'Không tìm thấy kiểu trình bày báo cáo.', 'report_template')
    return style


def section_order(value):
    if value is not None and (not isinstance(value, str) or len(value) > 240):
        raise CustomerError(422, 'Thứ tự mục báo cáo chưa hợp lệ.', 'report_template')
    keys = value.split(',') if value else []
    if len(keys) != len(set(keys)) or not set(keys) <= ORDER_KEYS:
        raise CustomerError(422, 'Thứ tự mục báo cáo chưa hợp lệ.', 'report_template')
    return keys


def style_context(key, palette=None, preset=None, order=None, hidden=None):
    if preset and any(value is not None for value in (key, palette, order, hidden)):
        raise CustomerError(422, 'Chỉ chọn một kiểu trình bày báo cáo.', 'report_template')
    palette = 'brand' if palette is None else palette
    if palette not in PALETTES:
        raise CustomerError(404, 'Không tìm thấy bảng màu báo cáo.', 'report_template')
    return {} if preset else {'report_style': get_style(key), 'report_styles': STYLES,
                              'report_palette': palette, 'report_palettes': PALETTES,
                              'report_order': section_order(order), 'report_hidden': section_order(hidden)}


def style_url(url, source, style, palette='brand', order=(), hidden=()):
    params = {'style': style.key}
    if palette != 'brand':
        params['palette'] = palette
    if order:
        params['order'] = ','.join(order)
    if hidden:
        params['hidden'] = ','.join(hidden)
    if source not in ('seo', 'combined'):
        params['comparison'] = 'previous'
    return url + ('&' if '?' in url else '?') + urlencode(params)
