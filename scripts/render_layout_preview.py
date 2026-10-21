"""Render empty, static UI pages using the installed Viewer image.

Run inside that image with /app on PYTHONPATH. No repository/API is used.
The output is a layout preview, never a published Bundle or customer report.
"""
import sys
from pathlib import Path

from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, select_autoescape

from app.mappers.dashboard import dashboard_context
from app.schemas.bundle_view import BundleView, QualityView, SectionView


def render(output: Path) -> None:
    root = Path("/app/templates")
    header = (root / "components/dashboard/header.html").read_text(encoding="utf-8")
    header = header.replace('id="date-range"', 'id="date-range" disabled title="Chưa chọn báo cáo"')
    header = header.replace('id="export-report"', 'id="export-report" disabled title="Bản xem bố cục không có dữ liệu để xuất"')
    header = header.replace("{{ bundle.period.start ~ ' – ' ~ bundle.period.end if dashboard is defined else '01/09/2026 – 30/09/2026' }}", "Chưa chọn kỳ báo cáo")
    env = Environment(
        loader=ChoiceLoader([DictLoader({
            "components/dashboard/header.html": header,
            "pages/snapshot/status.html": """
<div class="snapshot-status" role="status">
  <strong class="snapshot-preview">XEM TRƯỚC GIAO DIỆN</strong>
  <span>Chưa kết nối báo cáo · Không có dữ liệu khách hàng</span>
</div>
<p class="snapshot-filter-status">Chọn các trang ở menu để xem bố cục.
KPI, biểu đồ và bảng sẽ hiển thị khi có báo cáo đã xuất bản.</p>
<p id="snapshot-filter-status" class="snapshot-filter-status" role="status" aria-live="polite"></p>
""",
        }), FileSystemLoader(root)]),
        autoescape=select_autoescape(["html"]),
    )
    names = [
        ("overview", "Tổng quan"), ("seo", "SEO & Website"),
        ("facebook_ads", "Facebook Ads"), ("facebook_content", "Facebook Content"),
        ("tiktok", "TikTok Ads"), ("youtube", "YouTube"),
    ]
    period = {"start": "", "end": ""}
    sections = [
        SectionView(key, key, label, key, period, None, "unavailable", QualityView("unavailable"))
        for key, label in names
    ]
    bundle = BundleView(
        report_id="layout-preview", revision=0, status="layout-preview",
        name="Xem trước giao diện", client_name="Bố cục chưa có dữ liệu",
        period=period, comparison=None, generated_at=None, published_at=None,
        quality=QualityView("unavailable"), sections=sections, default_section="overview",
    )
    links = {
        key.replace("_", "-"): f"/static/layout-preview/{key}.html?layout=1"
        for key, _ in names
    }
    output.mkdir(parents=True, exist_ok=True)
    for key, _ in names:
        context = dashboard_context(bundle, key, "/static/layout-preview/", preview=True)
        context.update(snapshot_links=links, snapshot_home=links["overview"], viewer_mode=False)
        context["dashboard"]["links"] = links
        html = env.get_template(context["snapshot_template"]).render(**context)
        html = html.replace("<head>", '<head>\n<meta name="robots" content="noindex,nofollow">', 1)
        (output / f"{key}.html").write_text(html, encoding="utf-8")
        print(f"Rendered {key}.html (empty data)")


if __name__ == "__main__":
    render(Path(sys.argv[1]))
