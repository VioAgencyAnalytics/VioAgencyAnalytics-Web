"""Customer workspace UI. Demo routes never issue identity or provider grants."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.config import get_runtime_mode
from app.routes.pages import templates

router = APIRouter(tags=['customer workspace'])
BASE = '/workspace'
PAGES = {
    'login': ('Đăng nhập', 'login', 1),
    'onboarding': ('Thiết lập Workspace', 'onboarding', 2),
    '': ('Tổng quan', 'overview', 3),
    'integrations': ('Kết nối nền tảng', 'integrations', 4),
    'dashboard': ('Dashboard Marketing', 'marketing', 5),
    'channels': ('Phân tích kênh', 'channels', 6),
    'reports': ('Báo cáo', 'reports', 7),
    'members': ('Thành viên', 'members', 8),
    'settings': ('Cài đặt', 'settings', 9),
}
CHANNELS = {
    'facebook-content': ('Facebook Content', '/report/facebook-content'),
    'facebook-ads': ('Facebook Ads', '/report/facebook-ads'),
    'tiktok': ('TikTok Ads', '/report/tiktok'),
    'google-ads': ('Google Ads', None),
    'seo': ('SEO & Keywords', '/report/seo'),
    'ga4': ('Google Analytics 4', None),
    'gsc': ('Google Search Console', None),
    'youtube': ('YouTube', '/report/youtube'),
    'business-profile': ('Google Business Profile', None),
    'overview': ('Báo cáo tổng quan', '/overview'),
}
NAV = [
    ('overview', '', 'dashboard', 'Tổng quan'),
    ('integrations', 'integrations', 'hub', 'Kết nối nền tảng'),
    ('marketing', 'dashboard', 'monitoring', 'Dashboard Marketing'),
    ('channels', 'channels', 'query_stats', 'Phân tích kênh'),
    ('reports', 'reports', 'description', 'Báo cáo'),
    ('members', 'members', 'group', 'Thành viên'),
    ('settings', 'settings', 'settings', 'Cài đặt'),
]
HEADERS = {'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex, nofollow'}


def check_preview(request: Request):
    # The separate preview app uses only mock data, even when .env is production.
    mode = getattr(request.state, 'runtime_env', None) or get_runtime_mode().app_env
    if not getattr(request.app.state, 'customer_preview', False) and mode == 'production':
        raise HTTPException(404, 'Not found')


def context(page, title, number):
    return {'title': title, 'customer_page': page, 'page_number': number,
            'customer_nav': NAV, 'customer_channels': CHANNELS}


@router.get('/workspace/channels/{channel}')
def channel_page(request: Request, channel: str):
    check_preview(request)
    if channel not in CHANNELS:
        raise HTTPException(404, 'Không tìm thấy kênh')
    title, legacy_url = CHANNELS[channel]
    return templates.TemplateResponse(request=request, name='customer/channel.html',
        context={**context('channels', title, 6), 'channel': channel, 'legacy_url': legacy_url}, headers=HEADERS)


@router.get('/workspace')
@router.get('/workspace/{page}')
async def workspace_page(request: Request, page: str = ''):
    from app.customer_auth import enabled, live_page
    if enabled(request) and page in ('login', 'onboarding', '', 'integrations', 'dashboard', 'channels', 'reports', 'members', 'settings'):
        return await live_page(request, page)
    check_preview(request)
    if page not in PAGES:
        raise HTTPException(404, 'Không tìm thấy trang')
    title, template, number = PAGES[page]
    return templates.TemplateResponse(request=request, name=f'customer/pages/{template}.html',
        context=context(template, title, number), headers=HEADERS)


@router.get('/workspace/')
def workspace_index(request: Request):
    from app.customer_auth import enabled
    if not enabled(request):
        check_preview(request)
    return RedirectResponse(BASE, status_code=303, headers=HEADERS)
