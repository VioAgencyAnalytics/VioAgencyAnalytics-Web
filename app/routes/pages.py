from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.services.reports import ReportService
from app.customer_platform_brands import PLATFORM_BRANDS
from app.display_time import vietnam_time


router = APIRouter(tags=["pages"])

templates = Jinja2Templates(
    directory=str(
        Path(__file__).resolve().parents[2]
        / "templates"
    )
)
templates.env.globals['customer_platform_brands'] = PLATFORM_BRANDS
templates.env.filters['vietnam_time'] = vietnam_time


# =========================================================
# OVERVIEW
# =========================================================

@router.get("/overview")
async def overview_page(
    request: Request,
):
    return templates.TemplateResponse(
        "pages/overview/index.html",
        {
            "request": request,
            "title": "Tổng quan toàn bộ dự án",
            "overview":
                ReportService()
                .get_overview(),
        },
    )


# =========================================================
# SEO
# =========================================================

@router.get("/report/seo")
async def seo_page(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="pages/seo/index.html",
        context={
            "title":
                "SEO & Lưu lượng Website",

            "seo":
                ReportService()
                .get_seo(),

            "active_report":
                "seo",
        },
    )


# =========================================================
# FACEBOOK ADS
# =========================================================

@router.get("/report/facebook-ads")
@router.get("/report/ads")
@router.get("/facebook-ads")
async def facebook_ads_page(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="pages/facebook_ads/index.html",
        context={
            "title": (
                "Facebook Ads & Chi phí - "
                "Hiệu quả chiến dịch & "
                "Tối ưu CPL"
            ),

            "active_report":
                "facebook-ads",

            "ads":
                ReportService()
                .get_facebook_ads(),
        },
    )


# =========================================================
# FACEBOOK CONTENT
# =========================================================

@router.get("/report/facebook-content")
@router.get("/report/social")
async def facebook_content_page(
    request: Request,
):
    fb_content = (
        ReportService()
        .get_facebook_content()
    )

    return templates.TemplateResponse(
        request=request,

        name=(
            "pages/"
            "facebook_content/"
            "index.html"
        ),

        context={
            "title": (
                "Facebook Content - "
                "Hiệu quả bài đăng & tương tác"
            ),

            "active_report":
                "facebook-content",

            "fb_content":
                fb_content,
        },
    )


# =========================================================
# GENERIC REPORT
# PHẢI ĐỂ CUỐI FILE
# =========================================================

@router.get("/report/{report_name}")
async def report_page(
    request: Request,
    report_name: str,
):
    return templates.TemplateResponse(
        "pages/report/index.html",
        {
            "request":
                request,

            "title":
                report_name
                .replace("-", " ")
                .title(),

            "report_name":
                report_name,
        },
    )
