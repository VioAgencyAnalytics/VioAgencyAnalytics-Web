# KDH Marketing Reporting Dashboard

> Luồng hiện hành: **Đăng nhập Admin → Chọn báo cáo/revision → Mở báo cáo → Dashboard New**. New không có form hoặc API đăng nhập riêng. `/`, `/login` cũ và `/reports` chuyển về Admin. Xem [hướng dẫn hiện hành](docs/ADMIN_HANDOFF_DASHBOARD.md).

A FastAPI + Jinja2 marketing reporting dashboard with independent demo pages and a protected renderer for published Admin Report Bundles.

## Stack

- FastAPI
- SQLAlchemy / PostgreSQL-ready data layer
- Jinja2 templates
- Vanilla JS + ECharts
- Pytest for smoke tests

## Chạy bằng Docker — một lệnh

Cài và mở Docker Desktop (Linux containers). Tại thư mục dự án, chạy:

```sh
docker compose up --build -d
```

Mở **http://localhost:8080** (chuyển đến Admin để đăng nhập/chọn báo cáo). FE và BE của **KDH-Report-New**
chạy trong container `kdh-report-new-app-1`, nhóm Compose **`kdh-report-new`**.
New chạy riêng và tham gia network nội bộ của **KDH-Report-Admin** để đọc Bundle.
Khởi động Admin trước; chạy lệnh New trong `D:\KDH-Report-All\KDH-Report-New`.
Docker tự cài thư viện Python, build Tailwind CSS và khởi động FastAPI; máy host
không cần cài Python hoặc Node.js. Lần build đầu cần Internet để tải image và thư viện.
Cổng mặc định là 8080 để không trùng bản uvicorn đang chạy ở cổng 8000.

```sh
docker compose ps              # Kiểm tra trạng thái / healthcheck
docker compose logs -f app     # Xem log (Ctrl+C chỉ thoát xem log)
docker compose down            # Dừng và gỡ container của dự án
```

Sau khi sửa code, chạy lại `docker compose up --build -d` để cập nhật.
Container tự khởi động lại khi Docker Engine chạy, trừ khi đã chủ động dừng.
Muốn đổi cổng trên PowerShell, đặt `$env:KDH_PORT = '8090'` trước khi chạy Compose.
Ứng dụng mặc định chỉ được mở trên máy đang chạy Docker.

Bản Docker production chỉ phục vụ dashboard qua phiên được Admin cấp cho đúng
`/reports/{report_id}?revision=N`. Phiên hết hạn quay về đăng nhập tại Admin rồi mở
lại đúng báo cáo. Các trang mock và `/published/{report_id}` dành cho phát triển
bị khóa trong production. Preview nội bộ từ Admin đi qua handoff riêng.
Chưa thêm database; New chỉ đọc Internal API của Admin và không tự kết nối các provider.
Các file `.env`, môi trường ảo, `node_modules` và dữ liệu thử trong `.work` không được
đưa vào image. Node.js chỉ dùng ở bước build CSS; container chạy bằng user không phải root.

## Run locally without Docker

1. Create and activate a virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Start the app:
   `uvicorn main:app --reload`
4. Open http://localhost:8000/overview

## Features

- Vietnamese KinderHealth overview matching the supplied reference design
- Five KPI cards, six marketing channels, trend comparison and channel contributions
- Highlights, optimization alerts and next-period action plan
- Responsive navigation, date filters, chart metric switcher and comparison toggle
- Excel-compatible CSV export and browser print / Save as PDF (including plan-only print)
- JSON API endpoints for report data
- Repository/service layer separated from UI rendering
- SEO & website traffic dashboard at `/report/seo`, matching the supplied SEO HTML
- SEO ranking tabs, keyword search, landing-page details, weekly report and filtered CSV export
- Facebook Ads campaign filters, CPL sorting, campaign/creative details and an ad library
- Consistent Ads KPI, funnel and placement totals; filtered CSV and browser PDF export
- Rule-based Ads optimization report with text/PDF downloads (no AI service required)

The overview uses explicitly labeled mock data. September 2026 matches the reference;
other selectable periods (April–September 2026) are proportional demonstrations.
It is not connected to live customer or advertising accounts. Existing channel pages
remain available through the sidebar.

The SEO page preserves the reference's 148-keyword / 24-page summary counts. Its detailed
sample contains the six keywords and four landing pages provided in that reference.
Date filters scale sample counts; rankings, rates, and the illustrative trend shapes
are demonstration values. All reports share one sidebar. SEO and Facebook Ads use
the same inline accordion: the label opens the report, the arrow expands its sections.
Section links on the current report preserve filters and scroll to the selected section.

Facebook Ads at `/report/facebook-ads` uses three sample campaigns and three featured
creatives. Filters apply to the entire report, including exports and recommendations.
CTR, CPC, CPL, conversion and appointment rates are calculated from the same counts.
Demographic profiles and placement shares are illustrative. The optimization report
uses deterministic rules; Meta Marketing API, CRM and AI services are not connected.

## Dashboard styling

Facebook Content (`/report/facebook-content`, alias `/report/social`) follows the supplied
HTML reference: six KPIs, format/topic distribution, post table, engagement/reach breakdown
and executive insights. Date selection updates proportional demo totals. Search, format and
topic filters apply only to the five supplied post records, using their original publication
dates; the other 43 posts are not fabricated. Sorting, page size, post/topic details, CSV and
print/PDF work with the selected period and filters. Printed reports include all matching
sample rows, even when the screen table is paginated. ER and CTR derive from the raw counts.

The compiled stylesheet, fonts, icons and logo are served locally; no Tailwind CDN or
external chart library is needed by `/overview`, `/report/seo` or `/report/facebook-ads`. To rebuild styles after changing
templates or `static/css/shared/dashboard.source.css`:

```sh
npm ci
npm run build:css
```

Run backend checks with `python -m pytest -q`.

## TikTok Ads và YouTube

- `/report/tiktok` (alias `/report/tiktok-ads`): KPI, phễu chuyển đổi, biểu đồ chi tiêu/Leads, chiến dịch, video tiêu biểu và đề xuất theo HTML TikTok.
- `/report/youtube`: KPI, biểu đồ lượt xem/thời gian xem, video tiêu biểu, khán giả, nguồn truy cập, từ khóa, phễu và kế hoạch theo HTML YouTube.
- Hai trang dùng chung layout và menu con xổ xuống. Có bộ lọc kỳ báo cáo, tìm kiếm/sắp xếp bảng, popup chi tiết, so sánh, CSV và In/Lưu PDF. Các bộ lọc được giữ trong URL.
- API: `/api/v1/video-reports/tiktok` và `/api/v1/video-reports/youtube`; thêm `/export` để tải CSV. FE gọi backend qua các endpoint này.
- Dữ liệu vẫn là mẫu; lớp kiểm tra API thật trong `scripts/real_data_tests/` hoạt động độc lập. KPI kỳ khác được mô phỏng theo số ngày. TikTok tổng hợp từ ba chiến dịch mẫu; CTR trong thiết kế này là Clicks/Reach, tỷ lệ trên các thanh phễu tính theo Impressions. Không dùng các định nghĩa mẫu này để đối soát API quảng cáo thật.
- YouTube chỉ có bốn video tiêu biểu trong HTML, không tạo thêm 20 video để đủ nhãn 24. Bộ lọc ngày áp dụng theo ngày đăng của bốn video; KPI toàn kênh và các video tiêu biểu là các mẫu độc lập. Kế hoạch YouTube chỉ lưu lựa chọn trên trình duyệt, không gửi phê duyệt đến hệ thống bên ngoài.
- CSS, biểu đồ SVG, font và thumbnail phục vụ tại máy chủ; không cần CDN khi mở trang.

Chạy riêng dự án này từ `D:\KDH-Report-New`:

```powershell
docker compose up -d --build
```

Mở `http://127.0.0.1:8080/report/tiktok` hoặc `http://127.0.0.1:8080/report/youtube`.
Compose project là `kdh-report-new`, không gộp với dự án `KDH-Report` khác.

## Project structure

NEW-1 bổ sung `BundleService`, `BundleViewMapper`, các view model và template chung trong
`templates/pages/published/`. Xem [audit, danh sách file, contract, phân quyền preview và cách kiểm thử](docs/NEW-1-bundle-renderer.md).
Luồng này tái sử dụng `AdminBundleRepository`, không dùng mock fallback và không tính lại KPI.

The frontend is server-rendered Jinja2 HTML with local CSS and vanilla JavaScript.
`templates/` and `static/` together form the frontend; Python routes, services and
integrations remain in `app/`.

```text
templates/
  layouts/
    dashboard.html          # Shared dashboard document and shell
    basic.html              # Layout for generic channel reports
  components/dashboard/
    sidebar.html
    navigation.html         # Shared channel links and inline submenus
    header.html
    controls.html           # Shared date/source dialogs, export menu, toast
  pages/
    overview/
      index.html            # Page entry point: compose sections and load assets
      controls.html         # Page-specific dialogs
      partials/             # Summary, KPIs, channels, analytics, insights, plan
    seo/
      index.html
      controls.html
      partials/             # Summary, KPIs, trend, funnel, keywords, details
    facebook_ads/
      index.html
      controls.html
      partials/             # KPIs, campaigns, funnel, audience, creatives, insights
    tiktok/                 # TikTok entry point, campaign/video/insight partials
    youtube/                # YouTube entry point, videos/audience/insight partials
    video/                  # Shared video report base, KPI/funnel/chart partials
    report/
      index.html            # Generic channel report
static/
  css/
    shared/                 # Fonts, basic styles, dashboard.source.css
    pages/                  # seo.css and facebook-ads.css
    dist/dashboard.css      # Generated Tailwind output
  js/
    shared/                 # Shared sidebar, generic report bootstrap, chart helpers
    pages/                  # overview.js, seo.js, facebook-ads.js
  fonts/                    # Local fonts and icons with licenses
  img/                      # Logo and sample creative images
app/
  routes/                   # Page and JSON/CSV endpoints
  services/                 # Report orchestration
  repositories/             # Data access
  integrations/mock/        # Explicitly labeled sample data
  presentation.py           # Render the same Ads partials for AJAX updates
tests/                      # Endpoint, filtering and calculation checks
```

Edit page content in its `partials/`, and page behavior in `static/js/pages/`.
Change shared navigation once in `components/dashboard/`. `index.html` composes the
sections and declares that page's CSS/JS. Each page loads its own script explicitly.
Edit `static/css/shared/dashboard.source.css`, then run `npm run build:css`;
do not edit generated `static/css/dist/dashboard.css` directly. Public page URLs
are unchanged by this folder organization.
