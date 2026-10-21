# KDH Marketing Reporting Dashboard

KDH-Report-New chạy Viewer bằng FastAPI + Jinja2. Bản Docker hiện tại chỉ đọc
Published Report Bundle từ Admin.

**Source ngày 20/10/2026:** các module Viewer, handoff, Bundle mapper và giao diện
Facebook Content đã được đưa vào working tree này từ bản VIO đã kiểm thử. HEAD
không đổi; thay đổi chưa commit. Compose dùng image bất biến đã build từ source
này. VIO sandbox giữ riêng, không chuyển database, báo cáo hoặc quyền Viewer.

## Stack

- FastAPI
- SQLAlchemy / PostgreSQL-ready data layer
- Jinja2 templates
- Vanilla JS + ECharts
- Pytest for smoke tests

## Mở New — một container, một cổng

Trong Docker Desktop, mở nhóm **`kdh-report-new`**, bấm **Run/Start** ở container
**`kdh-report-new-app-1`**, rồi mở **http://localhost:8080**.

FE và BE cùng chạy trong container này. Không cần mở các cổng preview `8081` hoặc
`18085`. Các container VIO/Meta thuộc môi trường kiểm thử riêng, không dùng để mở
bản New này.

**Xem bố cục ngay, chưa cần chọn báo cáo:**
http://localhost:8080/static/layout-preview/overview.html

Các trang xem trước được render từ template trong image Viewer, với KPI rỗng;
không gọi Admin, không tạo báo cáo và không sử dụng số liệu mẫu. Menu cho phép xem
Tổng quan, SEO/Keywords, Facebook Ads, Facebook Content, TikTok Ads và YouTube.
Lọc kỳ và xuất báo cáo bị vô hiệu hóa vì chưa có dữ liệu.

Các HTML nằm trong `.work/layout-preview` (không commit) và được mount chỉ đọc.
Khi cần tạo lại, chạy các lệnh sau với container Viewer hiện có:

```powershell
docker cp scripts/render_layout_preview.py kdh-report-new-app-1:/tmp/render_layout_preview.py
docker exec -e PYTHONPATH=/app kdh-report-new-app-1 python /tmp/render_layout_preview.py /tmp/kdh-layout-preview
New-Item -ItemType Directory -Force .work/layout-preview
docker cp kdh-report-new-app-1:/tmp/kdh-layout-preview/. .work/layout-preview
```

Nếu tạo container lần đầu và chưa có thư mục này, tạo thư mục rỗng
`.work/layout-preview` trước, khởi động container, rồi render theo hướng dẫn trên.
Chỉ lưu HTML xem bố cục trong thư mục này vì các file ở đây mở được không cần đăng nhập.

Trang gốc chuyển sang Admin tại `http://localhost:8090/viewer/reports` để đăng nhập
và chọn báo cáo. Admin cùng database của Admin phải đang chạy; chúng vẫn là các
dịch vụ độc lập. Sau khi chọn báo cáo đã xuất bản, Admin chuyển về Viewer ở cổng
8080. Đường dẫn `/overview` trực tiếp bị chặn trong production.

Nếu cần tạo lại container, tại `D:\KDH-Report-All\KDH-Report-New` chạy:

```sh
docker compose up -d --no-build --pull never app
```

Yêu cầu có sẵn image local `kdh-new:unified-20261020-0d8c6b94bb93`, network
`kdh-report-admin_default` và cấu hình `REPORT_SERVICE_TOKEN` hợp lệ đã được cấp.
Image ID:
`sha256:87844f282565682fefffb3f1436a48b70099129a96704abb743b134df16256f9`.
Compose không tải image thay thế nếu thiếu image local.
Không đưa token vào source hoặc tài liệu.

```sh
docker compose ps              # Kiểm tra trạng thái / healthcheck
docker compose logs -f app     # Xem log (Ctrl+C chỉ thoát xem log)
docker compose stop app        # Dừng New, giữ container để bấm Run lần sau
docker compose start app       # Chạy lại New
```

Container tự khởi động lại khi Docker Engine chạy, trừ khi đã chủ động dừng.
Chỉ mở ứng dụng trên máy đang chạy Docker. New không gọi Google/Meta trực tiếp và
không có database riêng. Nếu không mở được link, kiểm tra trạng thái container và
`http://localhost:8080/api/v1/health`; sau đó kiểm tra Admin nếu lỗi xảy ra khi chuyển trang.

Các mô tả dashboard mẫu bên dưới chỉ áp dụng cho chế độ development.
Runtime production chặn các route demo; chỉ đọc Bundle đã phát hành từ Admin.
Admin chính hiện giữ `client_meta_sandbox`. Báo cáo và Viewer grant của VIO sandbox
không tự có ở database chính; chưa có Bundle/quyền phù hợp thì chưa mở được báo cáo.

## New có dữ liệu mẫu — KDH-Report-New-MockDb

Mở **http://localhost:8082** để xem dashboard có KPI, biểu đồ và bảng mẫu,
không cần đăng nhập/chọn báo cáo. Trong Docker Desktop, mở nhóm
`kdh-report-new-mockdb`, bật container **`KDH-Report-New-MockDb`** và bấm
**8082:8000**. Trang gốc tự mở Tổng quan.

```sh
docker compose -f compose.mock.yaml up -d --no-build --pull never
docker compose -f compose.mock.yaml stop
```

Bản này dùng entrypoint `app.design_preview:app` và dữ liệu mock sẵn có trong
image `kdh-new:unified-20261020-0d8c6b94bb93`. Tên MockDb dùng để nhận diện;
không tạo PostgreSQL hoặc database riêng. Container chỉ mount file CSS
`static/css/pages/executive.css` ở chế độ chỉ đọc để cập nhật giao diện;
không mount `.env` hay dữ liệu khách hàng, không có service token và chỉ tham gia network Docker
riêng, không kết nối Admin/Google/Meta. Các trang ghi rõ **Dữ liệu mẫu**.
Các số liệu và nhận định minh họa không phải kết quả hoặc cam kết kinh doanh.
Viewer thật vẫn chạy riêng trên cổng 8080 với cơ chế phân quyền hiện tại.

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
