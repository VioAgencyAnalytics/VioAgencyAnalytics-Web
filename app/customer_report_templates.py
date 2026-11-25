"""The Workspace catalogue and read-only previews of Vio report layouts."""

from dataclasses import dataclass
import json
from pathlib import Path
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Request

from app.compiled_commentary import compiled_sections
from app.customer_auth import BINDING, HEADERS, CustomerError, browser_binding, set_cookie
from app.customer_content_view import amount, build_view, day
from app.customer_data import display
from app.customer_report_layouts import build_layout
from app.customer_report_focus import focus_report
from app.customer_report_presets import compiled_id, get_preset, preset_url, seo_modules
from app.customer_report_styles import PALETTES, STYLES, get_style, style_context, style_url
from app.customer_report_view import build
from app.customer_seo import page_context, page_error
from app.customer_seo_reports import prepare
from app.report_commentary import facebook_content, platform
from app.routes.pages import templates


router = APIRouter(tags=['customer report templates'])
LIBRARY = '/workspace/reports/templates'
SAMPLES = Path(__file__).with_name('report_samples')
GROUPS = (
    ('all', 'Tất cả'), ('search', 'SEO & Website'), ('ads', 'Quảng cáo'),
    ('social', 'Mạng xã hội'), ('video', 'Video'), ('local', 'Địa phương'), ('multi', 'Tổng hợp'),
)


@dataclass(frozen=True)
class ReportTemplate:
    key: str
    name: str
    group: str
    description: str
    topics: tuple[str, ...]
    search: str = ''

    @property
    def slug(self):
        return self.key.replace('_', '-')

    @property
    def preview_url(self):
        return LIBRARY + '/' + self.slug

    @property
    def use_url(self):
        if self.key == 'seo':
            return '/workspace/reports/combined?sources=seo,ga4,gsc'
        if self.key == 'combined':
            return '/workspace/reports/combined'
        if self.key == 'facebook_content':
            return '/workspace/reports/facebook-content'
        return '/workspace/reports/data?source=' + self.key


CATALOGUE = (
    ReportTemplate('seo', 'SEO & Từ khóa', 'search',
                   'Nối kết quả tìm kiếm với thứ hạng, bài viết và cam kết dự án.',
                   ('Thứ hạng Spineditor', 'Tiến độ bài viết', 'KPI 12 tháng'), 'SEO từ khóa phụ chính ngách GA4 GSC'),
    ReportTemplate('gsc', 'Google Search Console', 'search',
                   'Xem website xuất hiện và thu hút lượt nhấp thế nào trên Google.',
                   ('Lượt nhấp & hiển thị', 'Vị trí trung bình', 'Truy vấn tìm kiếm'), 'GSC truy vấn thứ hạng CTR'),
    ReportTemplate('ga4', 'Google Analytics 4', 'search',
                   'Xem khách truy cập đến từ đâu và tương tác ra sao trên website.',
                   ('Người dùng & phiên', 'Nguồn truy cập', 'Trang được xem'), 'GA4 analytics lưu lượng traffic'),
    ReportTemplate('google_ads', 'Google Ads', 'ads',
                   'Đọc chi phí, lượt nhấp và chuyển đổi theo từng chiến dịch.',
                   ('Chi phí & CPC', 'Chuyển đổi', 'Bảng chiến dịch'), 'quảng cáo Google tìm kiếm PPC'),
    ReportTemplate('youtube', 'YouTube', 'video',
                   'Đánh giá video nổi bật và mức độ giữ chân người xem.',
                   ('Lượt xem', 'Thời gian xem', 'Lượt đăng ký'), 'YT video kênh YouTube'),
    ReportTemplate('business_profile', 'Google Business Profile', 'local',
                   'Đo mức hiển thị trên Search và Maps cùng hành động của khách hàng.',
                   ('Lượt gọi', 'Yêu cầu chỉ đường', 'Nhấp vào website'), 'GBP GMB Google Maps địa phương'),
    ReportTemplate('facebook_content', 'Facebook Content', 'social',
                   'Tổng hợp nhịp đăng bài, tương tác và các nội dung nổi bật của Fanpage.',
                   ('Bài đăng', 'Định dạng nội dung', 'Hiệu suất từng bài'), 'Meta FB fanpage Facebook organic'),
    ReportTemplate('facebook_ads', 'Facebook Ads', 'ads',
                   'Theo dõi chi phí và hiệu quả thu hút khách hàng tiềm năng từ Meta.',
                   ('Chi phí & CPC', 'Khách hàng tiềm năng', 'Bảng chiến dịch'), 'Meta Ads FB quảng cáo'),
    ReportTemplate('instagram', 'Instagram', 'social',
                   'Đọc hiệu suất nội dung theo định dạng và tương tác từng bài.',
                   ('Bài đăng', 'Lượt thích & bình luận', 'Người theo dõi'), 'IG Meta Instagram organic'),
    ReportTemplate('tiktok_ads', 'TikTok Ads', 'ads',
                   'Theo dõi phân phối, chi phí và chuyển đổi của quảng cáo TikTok.',
                   ('Chi phí & lượt nhấp', 'Lượt hiển thị', 'Chuyển đổi'), 'TikTok Tik Tok quảng cáo video'),
    ReportTemplate('combined', 'Báo cáo tổng hợp', 'multi',
                   'Chọn nhiều nguồn và đưa kết quả từng nền tảng vào cùng một báo cáo.',
                   ('Tóm tắt theo nguồn', 'Đối chiếu hai kỳ', 'Mục tiêu KPI'), 'Marketing tổng hợp đa kênh báo cáo tháng'),
)
TEMPLATE_BY_SLUG = {item.slug: item for item in CATALOGUE}
FILTER_GROUPS = {key for key, _ in GROUPS if key != 'all'}


def catalogue_filters(params):
    filters = {}
    category = params.get('category')
    if category in FILTER_GROUPS:
        filters['category'] = category
    if params.get('platform') in TEMPLATE_BY_SLUG:
        filters['platform'] = params['platform']
    if params.get('palette') in PALETTES and params['palette'] != 'brand':
        filters['palette'] = params['palette']
    search = params.get('q', '').strip()[:120]
    if search:
        filters['q'] = search
    return '?' + urlencode(filters) if filters else ''


def preview_content(item, preset=None, style=None, palette=None, order=None, hidden=None):
    # These built-in fixtures only contain illustrative records. Each render gets a fresh copy.
    data = json.loads((SAMPLES / (item.key + '.json')).read_text(encoding='utf-8'))
    styling = style_context(style.key if style else None, palette, preset, order, hidden)
    context = {'display': display, 'report_preset': preset, **styling,
               'example_use_url': preset_url(item.use_url, item.key, preset) if preset
                                  else style_url(item.use_url, item.key, style or STYLES[0], styling['report_palette'],
                                                 styling['report_order'], styling['report_hidden'])
                                      if style or palette or order or hidden else item.use_url}
    if item.key in ('seo', 'combined'):
        if preset:
            data['name'] = preset.name
            data['sections'] = preset.sections
            if preset.sources:
                data['sources'] = [source for source in data['sources'] if source['id'] in preset.sources]
        modules = seo_modules(item.key, preset)
        for source in data['sources']:
            if source['id'] != 'seo':
                source['view'] = build(source['data'])
        compiled = prepare(data)
        sections = compiled_sections(compiled, modules)
        context.update(customer_compiled_live=True, compiled=compiled, seo_modules=modules,
                       presentation=compiled_id(item.key, preset) if preset else None)
        name = 'compiled-report'
    elif item.key == 'facebook_content':
        view = build_view(data, {'workspace': {'name': 'VIO Agency'}})
        layout = build_layout(data)
        if preset:
            focus, sections = focus_report(preset, data, layout, view, example=True)
            context['report_focus'] = focus
        else:
            sections = facebook_content(data, view, layout)
        context.update(customer_meta_live=True, content=data, view=view, fc_amount=amount, fc_day=day)
        name = 'facebook-content-report'
    else:
        view = build(data)
        if preset:
            focus, sections = focus_report(preset, data, view['layout'], example=True)
            context['report_focus'] = focus
        else:
            sections = platform(data, view['layout'])
        context.update(customer_data_live=True, report=data, view=view)
        name = 'data-report'
    context['report_review'] = {'sections': {key: {**section, 'finalized': True} for key, section in sections.items()}}
    return name, context


@router.get(LIBRARY)
@router.get(LIBRARY + '/{slug}')
@router.get(LIBRARY + '/{slug}/{variant}')
@router.get(LIBRARY + '/{slug}/design/{style_key}')
async def report_templates_page(request: Request):
    try:
        slug = request.path_params.get('slug')
        variant = request.path_params.get('variant')
        style_key = request.path_params.get('style_key')
        settings, account, details = await page_context(request)
        context = {'customer_page': 'reports', 'customer_live': True, 'account': account, 'details': details}
        if slug is None:
            name = 'report-template-library'
            context.update(title='Kho mẫu báo cáo', report_library=True, report_catalogue=CATALOGUE,
                           report_groups=GROUPS, report_group_labels=dict(GROUPS), report_styles=STYLES, report_palettes=PALETTES,
                           style_url=style_url, report_count=len(STYLES) * len(CATALOGUE))
        else:
            item = TEMPLATE_BY_SLUG.get(slug)
            if item is None:
                raise CustomerError(404, 'Không tìm thấy mẫu báo cáo.')
            preset = get_preset(item.key, variant)
            style = get_style(style_key) if not preset else None
            palette = request.query_params.get('palette') if not preset else None
            order = request.query_params.get('order') if not preset else None
            hidden = request.query_params.get('hidden') if not preset else None
            name, preview = preview_content(item, preset, style if style_key else None, palette, order, hidden)
            filters = dict(request.query_params)
            if (variant or style_key) and not filters.get('platform'):
                filters['platform'] = item.slug
            context.update(preview, title=f'{item.name} · {preset.name if preset else style.name}', report_example=item,
                           report_library_url=LIBRARY + catalogue_filters(filters))
        response = templates.TemplateResponse(request=request, name=f'customer/live/{name}.html',
                                              context=context, headers=HEADERS)
        if not browser_binding(request):
            set_cookie(response, BINDING, secrets.token_urlsafe(48), settings)
        return response
    except CustomerError as error:
        return await page_error(request, error)
