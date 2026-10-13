"""Local-only report preview; reads published DEMO bundle from Admin API."""
import os
import re
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["demo-bundle"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))
DISPLAY = {
    "overview": "Tổng quan", "seo": "SEO & Website Traffic",
    "facebook-ads": "Facebook Ads", "facebook-content": "Facebook Content",
    "tiktok": "TikTok Ads", "youtube": "YouTube", "gmb": "Google Business Profile",
}


def display_value(key, value):
    if value is None:
        return "Không khả dụng"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        if key.endswith("_vnd") or key.startswith(("cpl_", "cpc_")):
            return f"{value:,.0f} ₫"
        low = key.lower()
        if ("ctr" in low or "rate" in low or low == "engagementrate") and 0 <= value <= 1:
            return f"{value * 100:.2f}%"
        if isinstance(value, float) and not value.is_integer():
            return f"{value:,.2f}"
        return f"{value:,.0f}"
    return str(value)


def shape(section):
    items = []
    sources = section.get("data", {}).get("sources", {})
    for name, src in sources.items():
        totals = src.get("totals", {})
        metrics = [{"name": key, "value": display_value(key, val)}
                   for key, val in totals.items()
                   if isinstance(val, (int, float)) and not isinstance(val, bool)][:18]
        notes = [str(val) for key, val in totals.items() if isinstance(val, str)][:3]
        table = None
        for field in ("campaigns", "posts", "videos", "entries", "queries", "channels", "pages", "topics"):
            rows = src.get(field)
            if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                cols = [key for key, value in rows[0].items()
                        if isinstance(value, (int, float, str))][:7]
                table = {"title": field, "columns": cols,
                         "rows": [[display_value(key, r.get(key)) for key in cols]
                                  for r in rows[:12]]}
                break
        trend = None
        daily = src.get("daily")
        if isinstance(daily, list) and len(daily) > 1:
            key = next((name for name in ("sessions", "clicks", "spend_vnd", "views", "impressions", "leads")
                        if all(isinstance(r.get(name), (int, float)) for r in daily[:12])), None)
            if key:
                values = [r[key] for r in daily if isinstance(r.get(key), (int, float))]
                if len(values) >= 2:
                    lower, upper = min(values), max(values)
                    span = (upper - lower) or 1
                    coords = " ".join(
                        f"{12 + i * 676 / (len(values)-1):.1f},{172 - (v-lower)*142/span:.1f}"
                        for i, v in enumerate(values))
                    trend = {"key": key, "points": coords, "count": len(values)}
        items.append({"key": name, "label": src.get("label", name), "metrics": metrics,
                      "notes": notes, "status": src.get("status", "unknown"),
                      "table": table, "trend": trend})
    return items


@router.get("/demo-bundles/{report_id}")
@router.get("/demo-bundles/{report_id}/{section_key}")
def demo_bundle(request: Request, report_id: str, section_key: str = "overview", revision: int | None = None):
    if os.getenv("ENABLE_DEMO_PREVIEW") != "1":
        raise HTTPException(status_code=404, detail="DEMO preview is disabled")
    if not re.fullmatch(r"rpt_[0-9a-f]{32}", report_id):
        raise HTTPException(status_code=404, detail="Invalid report id")
    base = os.getenv("REPORT_ADMIN_BASE_URL", "").rstrip("/")
    token = os.getenv("REPORT_SERVICE_TOKEN", "")
    if not base or not token:
        raise HTTPException(status_code=503, detail="Admin API backend is not configured")
    url = f"{base}/api/internal/v1/report-bundles/{report_id}"
    try:
        response = httpx.get(url, params={"revision": revision} if revision else None,
                             headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
        response.raise_for_status()
        bundle = response.json()
    except httpx.HTTPStatusError as exc:
        status = 404 if exc.response.status_code == 404 else 502
        raise HTTPException(status_code=status, detail="Admin report not published or unavailable") from None
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status_code=502, detail="Admin report API unavailable or invalid") from None
    if (bundle.get("client", {}).get("id") != "client_kinderhealth_demo"
            or bundle.get("branding", {}).get("demo") is not True):
        raise HTTPException(status_code=403, detail="Only separately marked DEMO bundles are supported")
    allowed = bundle.get("navigation", {}).get("sections", [])
    if section_key not in allowed or section_key not in bundle.get("sections", {}):
        raise HTTPException(status_code=404, detail="Section not published")
    details = bundle["sections"][section_key]
    nav = [{"key": key, "label": DISPLAY.get(key, key)} for key in allowed]
    return templates.TemplateResponse(request=request, name="pages/demo_bundle.html", context={
        "title": DISPLAY.get(section_key, section_key),
        "report_id": report_id, "revision": bundle["report"]["revision"],
        "status": bundle["report"]["status"], "period": bundle["period"],
        "section_key": section_key, "sections": nav, "items": shape(details),
        "quality": details.get("quality", {}), "report_quality": bundle.get("quality", {}),
    })
