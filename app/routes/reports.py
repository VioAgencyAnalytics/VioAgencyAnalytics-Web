from typing import Any, Dict, Literal
import csv
from datetime import date
from io import StringIO

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import Response

from app.presentation import facebook_content_fragments
from app.services.reports import ReportService


router = APIRouter(
    prefix="/api/v1",
    tags=["reports"],
)

service = ReportService()


# =========================================================
# OVERVIEW
# =========================================================

@router.get("/reports/overview")
def get_overview(
    start: date | None = None,
    end: date | None = None,
):
    try:
        return service.get_overview(
            start,
            end,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


@router.get("/reports/overview/export")
def export_overview(
    start: date | None = None,
    end: date | None = None,
):
    data = get_overview(
        start,
        end,
    )

    output = StringIO(newline="")
    writer = csv.writer(output)

    writer.writerow([
        "KDH Traffic Report",
        "Dữ liệu mẫu KinderHealth",
    ])

    writer.writerow([
        "Từ ngày",
        data["period"]["start"],
        "Đến ngày",
        data["period"]["end"],
    ])

    writer.writerow([])

    writer.writerow([
        "Chỉ số",
        "Giá trị",
        "Đơn vị",
        "Thay đổi (%)",
    ])

    for metric in data["metrics"]:
        writer.writerow([
            metric["label"],
            metric["value"],
            metric["unit"],
            metric["delta"],
        ])

    writer.writerow([])

    writer.writerow([
        "Kênh",
        "Leads đóng góp",
    ])

    mix = data["charts"]["channel_mix"]

    writer.writerows(
        zip(
            mix["labels"],
            mix["values"],
        )
    )

    writer.writerow([])

    writer.writerow([
        "Ngày",
        "Lưu lượng",
        "Lưu lượng kỳ trước",
    ])

    trend = data["charts"]["trends"]["traffic"]

    writer.writerows(
        zip(
            trend["dates"],
            trend["values"],
            trend["previous"],
        )
    )

    filename = (
        f"KDH-Tong-quan-"
        f"{data['period']['start']}-"
        f"{data['period']['end']}.csv"
    )

    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        },
    )


# =========================================================
# SEO & WEBSITE TRAFFIC
# =========================================================

@router.get("/reports/seo")
def get_seo(
    start: date | None = None,
    end: date | None = None,
    period: str | None = None,
    channel: str | None = None,
):
    filters = {
        key: value
        for key, value in {
            "period": period,
            "channel": channel,
        }.items()
        if value
    }

    try:
        return service.get_seo(
            start,
            end,
            filters,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


@router.get("/reports/seo/export")
def export_seo(
    start: date | None = None,
    end: date | None = None,

    rank: Literal[
        "all",
        "top3",
        "top5",
        "top10",
        "top20",
        "top30",
        "top50",
        "top100",
        "new",
        "risers",
    ] = "all",

    query: str = "",
):
    from app.integrations.mock.seo import filter_keywords

    data = get_seo(
        start,
        end,
    )

    output = StringIO(newline="")
    writer = csv.writer(output)

    writer.writerow([
        "KDH Traffic Report",
        "SEO & Lưu lượng Website",
        "Dữ liệu mẫu",
    ])

    writer.writerow([
        "Từ ngày",
        data["period"]["start"],
        "Đến ngày",
        data["period"]["end"],
    ])

    writer.writerow([])

    writer.writerow([
        "Chỉ số",
        "Giá trị",
        "Đơn vị",
    ])

    for metric in data["metrics"]:
        writer.writerow([
            metric["label"],
            metric["value"],
            metric["unit"],
        ])

    writer.writerow([])

    writer.writerow([
        "Từ khóa",
        "Trang đích",
        "Vị trí cũ",
        "Vị trí mới",
        "Thay đổi",
        "Clicks",
        "Hiển thị",
        "CTR",
    ])

    for row in filter_keywords(
        data["keywords"],
        rank,
        query,
    ):
        writer.writerow([
            row["keyword"],
            row["landing"],
            row["previous"],
            row["position"],
            row["previous"] - row["position"],
            row["clicks"],
            row["impressions"],
            row["ctr"],
        ])

    writer.writerow([])

    writer.writerow([
        "Trang đích",
        "Users",
        "Clicks",
        "Leads",
        "CR",
    ])

    for row in data["landings"]:
        writer.writerow([
            row["url"],
            row["users"],
            row["clicks"],
            row["leads"],
            row["cr"],
        ])

    filename = (
        f"KDH-SEO-"
        f"{data['period']['start']}-"
        f"{data['period']['end']}.csv"
    )

    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        },
    )


# =========================================================
# FACEBOOK ADS
# =========================================================

@router.get("/reports/facebook-ads")
@router.get("/reports/ads")
def get_facebook_ads(
    start: date | None = None,
    end: date | None = None,

    query: str = Query(
        default="",
        max_length=200,
    ),

    status: Literal[
        "all",
        "active",
        "attention",
    ] = "all",

    campaign: str = "all",

    sort: Literal[
        "cpl_asc",
        "cpl_desc",
        "spend_desc",
        "leads_desc",
    ] = "cpl_asc",
):
    from app.presentation import facebook_ads_fragments

    try:
        data = service.get_facebook_ads(
            start=start,
            end=end,
            query=query,
            status=status,
            campaign=campaign,
            sort=sort,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    return {
        **data,
        "fragments":
            facebook_ads_fragments(data),
    }


@router.get("/reports/facebook-ads/export")
def export_facebook_ads(
    start: date | None = None,
    end: date | None = None,

    query: str = Query(
        default="",
        max_length=200,
    ),

    status: Literal[
        "all",
        "active",
        "attention",
    ] = "all",

    campaign: str = "all",

    sort: Literal[
        "cpl_asc",
        "cpl_desc",
        "spend_desc",
        "leads_desc",
    ] = "cpl_asc",

    compare: bool = True,
):
    data = get_facebook_ads(
        start,
        end,
        query,
        status,
        campaign,
        sort,
    )

    output = StringIO(newline="")
    writer = csv.writer(output)

    # Ngăn Excel hiểu text tìm kiếm
    # bắt đầu bằng = + - @ thành công thức.
    safe_query = (
        "'" + query
        if query.lstrip().startswith(
            (
                "=",
                "+",
                "-",
                "@",
                "\t",
                "\r",
                "\n",
            )
        )
        else query
    )

    writer.writerow([
        "KDH Traffic Report",
        "Facebook Ads",
        "Dữ liệu mẫu — chưa kết nối Meta",
    ])

    writer.writerow([
        "Từ ngày",
        data["period"]["start"],
        "Đến ngày",
        data["period"]["end"],
    ])

    writer.writerow([
        "Chiến dịch",
        campaign,
        "Trạng thái",
        status,
        "Tìm kiếm",
        safe_query,
        "Sắp xếp",
        sort,
    ])

    writer.writerow([])

    metric_header = [
        "Chỉ số",
        "Giá trị",
    ]

    if compare:
        metric_header.extend([
            "Kỳ trước",
            "Thay đổi (%)",
        ])

    writer.writerow(metric_header)

    for metric in data["metrics"]:
        row = [
            metric["label"],
            metric["value"],
        ]

        if compare:
            row.extend([
                data["previous"][
                    metric["key"]
                ],
                metric["delta"],
            ])

        writer.writerow(row)

    writer.writerow([])

    writer.writerow([
        "CTR = Clicks / Impressions",
        data["totals"]["ctr"],
        "%",
    ])

    writer.writerow([
        "CPC = Chi tiêu / Clicks",
        data["totals"]["cpc"],
        "VND",
    ])

    writer.writerow([
        "CPA = Chi tiêu / Lịch hẹn",
        data["totals"]["cpa"],
        "VND",
    ])

    writer.writerow([])

    writer.writerow([
        "Chiến dịch",
        "ID",
        "Trạng thái",
        "Chi tiêu (VND)",
        "Ngân sách (VND)",
        "Reach",
        "Impressions",
        "Clicks",
        "CTR (%)",
        "Leads",
        "CPL (VND)",
        "Lịch hẹn",
    ])

    for row in data["campaigns"]:
        writer.writerow([
            row["name"],
            row["id"],
            row["status_label"],
            row["spend"],
            row["budget"],
            row["reach"],
            row["impressions"],
            row["clicks"],
            row["ctr"],
            row["leads"],
            row["cpl"],
            row["appointments"],
        ])

    writer.writerow([])

    writer.writerow([
        (
            "Mẫu quảng cáo nổi bật "
            "(không phải toàn bộ quảng cáo)"
        ),
        "Chiến dịch",
        "Chi tiêu (VND)",
        "Impressions",
        "Clicks",
        "Leads",
        "CTR (%)",
        "CPL (VND)",
    ])

    for row in data["creatives"]:
        writer.writerow([
            row["name"],
            row["campaign_id"],
            row["spend"],
            row["impressions"],
            row["clicks"],
            row["leads"],
            row["ctr"],
            row["cpl"],
        ])

    writer.writerow([])

    writer.writerow([
        "Vị trí hiển thị",
        "Chi tiêu (VND)",
        "Tỷ trọng (%)",
    ])

    for row in data["placements"]:
        writer.writerow([
            row["name"],
            row["spend"],
            row["percent"],
        ])

    filename = (
        f"KDH-Facebook-Ads-"
        f"{data['period']['start']}-"
        f"{data['period']['end']}.csv"
    )

    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        },
    )


# =========================================================
# FACEBOOK CONTENT
# =========================================================

@router.get("/reports/facebook-content")
def get_facebook_content(
    start: date | None = None,
    end: date | None = None,

    query: str = Query(
        default="",
        max_length=200,
    ),

    content_format: Literal[
        "all",
        "reels",
        "long_video",
        "carousel",
        "photo",
        "livestream",
    ] = Query(
        default="all",
        alias="format",
    ),

    topic: Literal[
        "all",
        "pediatric",
        "nutrition",
        "vaccination",
        "review",
    ] = "all",

    sort: Literal[
        "all",
        "reach_desc",
        "engagement_desc",
        "shares_desc",
        "clicks_desc",
    ] = "all",
):
    try:
        data = (
            service
            .get_facebook_content(
                start=start,
                end=end,
                query=query,
                content_format=
                    content_format,
                topic=topic,
                sort=sort,
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    return {
        **data,

        "fragments":
            facebook_content_fragments(
                data
            ),
    }


# =========================================================
@router.get("/reports/facebook-content/export")
def export_facebook_content(data: dict = Depends(get_facebook_content), compare: bool = True):
    output = StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['KDH Traffic Report', 'Facebook Content', 'Dữ liệu mẫu — chưa kết nối Meta'])
    writer.writerow(['Từ ngày', data['period']['start'], 'Đến ngày', data['period']['end']])
    writer.writerow([data['notice']])
    query = data['filters']['query']
    if query.lstrip().startswith(('=', '+', '-', '@')) or query.startswith(('\t', '\r', '\n')):
        query = "'" + query
    writer.writerow(['Tìm kiếm', query, 'Định dạng', data['filters']['format'], 'Chủ đề', data['filters']['topic'], 'Sắp xếp', data['filters']['sort']])
    writer.writerow([])
    writer.writerow(['Chỉ số', 'Giá trị'] + (['Kỳ trước', 'Thay đổi (%)'] if compare else []))
    for key, label in [('total_posts', 'Tổng bài đăng'), ('reach', 'Reach'), ('engagement', 'Tương tác'), ('engagement_rate', 'ER (%)'), ('followers_new', 'Followers mới'), ('link_clicks', 'Click liên kết')]:
        writer.writerow([label, data['metrics'][key]] + ([data['previous'][key], data['deltas'][key]] if compare else []))
    writer.writerow([])
    writer.writerow(['Bài mẫu theo bộ lọc — không phải toàn bộ 48 bài'])
    writer.writerow(['ID', 'Tiêu đề', 'Ngày đăng', 'Định dạng', 'Chủ đề', 'Reach', 'Engagement', 'ER (%)', 'Comments', 'Shares', 'Clicks'])
    for row in data['posts']:
        writer.writerow([row[k] for k in ['id', 'title', 'date', 'format', 'topic', 'reach', 'engagement', 'er', 'comments', 'shares', 'clicks']])
    writer.writerow([])
    writer.writerow(['Cấu trúc tương tác', 'Số lượt', 'Tỷ trọng (%)'])
    writer.writerows([r['label'], r['value'], r['percent']] for r in data['engagement_breakdown'])
    writer.writerow([])
    writer.writerow(['Nguồn tiếp cận', 'Reach'])
    writer.writerow(['Organic', data['reach_mix']['organic']])
    writer.writerow(['Paid', data['reach_mix']['paid']])
    filename = f"KDH-Facebook-Content-{data['period']['start']}-{data['period']['end']}.csv"
    return Response(content='\ufeff' + output.getvalue(), media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})


# GENERIC REPORT
#
# Route tổng quát này phải nằm dưới
# Overview / SEO / Facebook Ads / Facebook Content.
# =========================================================

@router.get("/reports/{report_type}")
def get_report(
    report_type: str,

    period: str | None = Query(
        default=None
    ),

    channel: str | None = Query(
        default=None
    ),
):
    filters: Dict[str, Any] = {}

    if period:
        filters["period"] = period

    if channel:
        filters["channel"] = channel

    return service.get_report(
        report_type,
        filters,
    )
