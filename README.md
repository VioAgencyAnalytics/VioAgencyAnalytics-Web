# VioAgencyAnalytics-Web

**Cập nhật 09/11/2026:** Customer Web đã có luồng ba bước và khung báo cáo cho
chín nguồn dữ liệu, chạy Docker HTTPS local. Cấu hình ứng dụng là việc một lần
của Vio; khách hàng chỉ đăng nhập/cấp quyền tại nhà cung cấp. Xem
[hướng dẫn cấu hình chín connector](docs/CUSTOMER_CONNECTORS_SETUP_VI.md) và
[kết quả kiểm tra, phần còn lại](docs/CUSTOMER_CONNECTORS_VALIDATION_20261109.md).

Customer stack local: [Web + Customer Admin + PostgreSQL trên Docker](docs/CUSTOMER_DOCKER.md),
điểm vào `http://127.0.0.1:8084/workspace/login`.
Kết nối Meta cần HTTPS: [thiết lập HTTPS localhost và callback Google/Meta](docs/CUSTOMER_LOCAL_HTTPS.md),
điểm vào sau khi bật là `https://localhost:8444/workspace/login`.
Trang 03: [Tổng quan, quản lý khách hàng và checklist thật](docs/CUSTOMER_OVERVIEW.md).

Trang 04: [Danh mục 9 nền tảng, phạm vi khách hàng và trạng thái tích hợp](docs/CUSTOMER_INTEGRATIONS.md).

Trang 05: [Dashboard Marketing, bộ lọc, biểu đồ và bảng hiệu suất](docs/CUSTOMER_MARKETING.md).

Trang 06–07: [Phân tích 9 kênh, thư viện 10 bố cục và khung báo cáo tùy chỉnh](docs/CUSTOMER_CHANNELS_REPORTS.md).
Facebook Content đã kết nối: [KPI, biểu đồ, bài viết và bản báo cáo riêng tư](docs/CUSTOMER_FACEBOOK_CONTENT_UX.md).

Trang 08–09: [Thành viên, lời mời, phân quyền và cài đặt Workspace](docs/CUSTOMER_MEMBERS_SETTINGS.md).

**VioAgencyAnalytics do VIO Agency phát triển, sở hữu và vận hành**, hướng tới
Self-service Multi-platform Marketing Analytics & Reporting SaaS. Sản phẩm được
phát triển độc lập; tham khảo mô hình AgencyAnalytics không hàm ý sở hữu/hợp tác.

Web dùng FastAPI + Jinja2 + Vanilla JS. Giao diện khách hàng đã được tổ chức thành
9 trang theo bộ thiết kế người dùng cung cấp, có thể chạy bằng `app.design_preview:app`.
Các báo cáo cũ được mở trong **Phân tích kênh**. Trang 01–02 đã có tài khoản và
Workspace trên DB thật khi bật `CUSTOMER_AUTH_ENABLED`; xem hướng dẫn bên dưới.
Google/SMTP cần cấu hình để bật. Luồng Viewer của Published Bundle từ Admin được
giữ tương thích. Dashboard customer đã có giao diện thật, bộ lọc và khung dữ liệu
scoped; OAuth/sync, analytics API và Report Builder customer chưa được triển khai.
Google Sign-in xác thực người dùng; provider OAuth cấp quyền dữ liệu riêng biệt.
Web không gọi provider API hoặc nhận provider secrets từ Admin.

- [Giao diện 9 trang, cách chạy và phạm vi đã triển khai](docs/CUSTOMER_UI_IMPLEMENTATION.md)
- [Trang 01–02: FE, backend, DB và cách chạy bản thật cổng 8084](docs/CUSTOMER_IDENTITY_IMPLEMENTATION.md)
- [Customer Workspace UX và permission flow](docs/CUSTOMER_WORKSPACE_UX.md)
- [Product Vision](../VioAgencyAnalytics-Admin/docs/VIOAGENCYANALYTICS_PRODUCT_VISION.md)
- [Kiến trúc và trạng thái tích hợp](../VioAgencyAnalytics-Admin/docs/VIOAGENCYANALYTICS_ARCHITECTURE.md)
- [Roadmap](../VioAgencyAnalytics-Admin/docs/SAAS_MIGRATION_ROADMAP.md)
- [Audit và file map](../VioAgencyAnalytics-Admin/docs/REBRAND_FILE_MAP.md)

Các liên kết chéo repository giả định hai checkout nằm cạnh nhau như workspace
hiện tại. Tên package, header/cookie, service và client ID cũ được giữ tương thích.

**Ghi nhận lịch sử ngày 20/10/2026:** các module Viewer, handoff, Bundle mapper và giao diện
Facebook Content đã được đưa vào working tree này từ bản VIO đã kiểm thử. HEAD
không đổi; thay đổi chưa commit. Compose dùng image bất biến đã build từ source
này. VIO sandbox giữ riêng, không chuyển database, báo cáo hoặc quyền Viewer.

## Stack

- FastAPI
- SQLAlchemy / PostgreSQL-ready data layer
- Jinja2 templates
- Vanilla JS + ECharts
- Pytest for smoke tests

## Giao diện khách hàng mới — 9 trang

```sh
python -m uvicorn app.design_preview:app --host 127.0.0.1 --port 8083
```

Mở **http://127.0.0.1:8083/**: Đăng nhập → Thiết lập Workspace → Tổng quan →
Kết nối nền tảng → Dashboard Marketing → Phân tích kênh → Báo cáo → Thành viên →
Cài đặt. Nút **Khám phá giao diện mới** mở luồng xem thử, không tạo phiên đăng nhập.
Các tùy chọn và bản nháp xem thử chỉ lưu trong phiên tab trình duyệt.
Trang 04 có nội dung **Kết nối nền tảng**, dù tên thư mục ZIP là Agency Overview.

Tại **Phân tích kênh**, báo cáo Tổng quan, SEO, Facebook Ads, Facebook Content,
TikTok và YouTube giữ các bộ lọc và chức năng xuất file hiện có. Trang báo cáo được
nhúng cùng nguồn vào khung điều hướng mới. Kênh chưa có báo cáo hiện trạng thái trống.
CSS, logo và font được phục vụ tại máy chủ, không phụ thuộc Tailwind CDN.

`/workspace*` có hai chế độ: giao diện mẫu chỉ mở trong development/test hoặc
ứng dụng preview riêng; production chỉ bật Customer BFF khi cấu hình
`CUSTOMER_AUTH_ENABLED=true`. Backend Admin xác thực phiên và quyền Workspace.
Các báo cáo Viewer tiếp tục dùng handoff và grant hiện hành.

## Viewer hiện hành và cấu hình triển khai

Đối chiếu source ngày 23/10/2026: `compose.yaml` include `compose.shared.yaml`,
project `kdh-report-admin`, service `new`, container `kdh-report-new-app-1` tại
cổng 8080. Cấu hình có hai backend qua relay riêng: primary và VIO, lựa chọn theo
origin được cấu hình. `client_id` trên URL không chọn backend và không cấp quyền.
Cookies host-only, service credentials và grants hiện có phải được giữ nguyên.

Web production chuyển luồng đăng nhập/chọn báo cáo về Admin, sau đó nhận handoff
và chỉ hiển thị Published Bundle theo revision được cấp quyền. `/overview` và
các route dữ liệu mẫu bị chặn trong production. Preview nội bộ yêu cầu quyền
riêng; không phải dashboard live cho khách hàng.

Đây là trạng thái **source**, không phải kết quả kiểm tra container ngày 23/10.
Các bản ghi triển khai mới nhất nằm trong
[System Context của Admin](../VioAgencyAnalytics-Admin/docs/SYSTEM_CONTEXT.md).
Hướng dẫn cũ tạo service `app`, image `unified-20261020` và nối trực tiếp
`kdh-report-admin_default` không mô tả Compose shared hiện hành. Không dùng chúng
để recreate hệ thống. Task rebrand không đổi image, network, IP, callback hoặc mount.

Cấu hình shared giữ các network `kdh-vio-host-phase9-20261019`,
`kdh-shared-viewer-primary-20261021`, `kdh-vio-handoff-phase9-recovery-20261019`.
Không đổi tên network `kdh-report-admin_default` của Admin. Mount
`.work/layout-preview` chỉ dành cho HTML bố cục công khai, không chứa dữ liệu khách hàng.
Trang layout preview có KPI rỗng, không gọi provider hoặc thay thế báo cáo đã phát hành.

Bản mock riêng dùng `compose.mock.yaml`, cổng 8082; không phải production tenant.
Các mô tả dashboard mẫu bên dưới chỉ áp dụng development/design preview.
`client_kinderhealth` và `client_meta_sandbox` là phạm vi hiện có; rebrand không
chuyển dữ liệu hoặc grant giữa các database và không biến sandbox thành tenant SaaS.

## Viewer mẫu — container `KDH-Report-New-MockDb`

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

Các route mẫu TikTok/YouTube ở trên chỉ hoạt động ngoài production.
Không chạy Compose production để mở route demo. Repository local hiện tại là
`D:\VioAgencyAnalytics\VioAgencyAnalytics-Web`; các tên Docker cũ vẫn là contract vận hành.

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


## Viewer độc lập và preview Bundle

Luồng Viewer được giữ: **Admin → chọn báo cáo/revision → handoff → Viewer**.
`/reports` quay về Admin; `/` và `/login` mở Customer Login khi bật Customer BFF
(hoặc trong development), và quay về Admin khi production tắt Customer BFF.
Xem [Admin handoff và Dashboard](docs/ADMIN_HANDOFF_DASHBOARD.md) và
[Bundle renderer, ACL và contract](docs/NEW-1-bundle-renderer.md).
Renderer chỉ đọc Internal API của Admin, không tính lại KPI và không có mock fallback.

Cấu hình một backend trước đây được giữ tại `compose.standalone.yaml`, build từ
source hiện tại, service `app`, project `kdh-report-new`, port mặc định 8080.
Khởi động Admin trước và cung cấp riêng `REPORT_SERVICE_TOKEN`; dùng
`docker compose -f compose.standalone.yaml up -d --build` khi triển khai chế độ này.
Không chạy cùng shared Viewer trên cổng 8080. `KDH_PORT` đổi cổng host; đồng thời
cập nhật public origin/callback tương ứng ở cả Web và Admin. Xem trạng thái/log
bằng `docker compose -f compose.standalone.yaml ps` và `logs -f app`.
Không thay đổi container đang hoạt động chỉ để kiểm thử merge.

Preview Bundle riêng vẫn dùng
`docker compose -f compose.design-preview.yaml up -d --build`, cổng 8081,
`/qa/overview`, với fixture có nhãn DEMO, không phải dữ liệu khách hàng.
Preview không nhận service token, không nối DB/network Admin; scripts và tests
chỉ mount read-only trong preview và không nằm trong image production.
Không ghép compose preview với compose production. Các file `.env`, `.work`,
virtualenv và `node_modules` không được đưa vào image runtime.

# Kết nối nguồn dữ liệu Customer (30/10/2026)

GA4, Google Search Console, Facebook Content và Facebook Ads có luồng Customer
OAuth, chọn tài sản, đồng bộ khởi tạo/thủ công và ngắt tại Vio. Cấu hình app ở
Customer Admin bằng `scripts/configure_customer_providers.py google` hoặc `meta`;
không dùng secret đăng nhập Google thay cho consent đọc dữ liệu. Helper nhập ẩn,
lưu env private và in callback đúng `CUSTOMER_WEB_ORIGIN`. Web không nhận provider
secret/token. Khi app chưa cấu hình, catalogue báo **Chờ cấu hình ứng dụng**.

Xem contract và hướng dẫn đầy đủ trong
`../VioAgencyAnalytics-Admin/docs/CUSTOMER_PROVIDER_CONNECTIONS.md`. Chỉ Owner/Admin
đã xác minh email được quản lý nguồn; Member/Viewer chỉ đọc trạng thái. Snapshot
nguồn chưa tự trở thành báo cáo phát hành; không có scheduler định kỳ ở bước này.

## Facebook Content Customer (05/11/2026)

Sau khi cấp quyền Meta và **chọn Fanpage tại Vio**, worker đồng bộ kỳ khởi tạo.
Trang `/workspace/channels/facebook-content` đọc các snapshot đã lưu đúng
Workspace/khách hàng/tài sản/phiên bản kết nối. Có KPI nội dung, nhịp đăng bài,
Page Insights khi nguồn đủ quyền, tìm kiếm và phân trang bài đăng; thiếu dữ liệu
giữ `—`, số 0 thực có giữ nguyên. GET không gọi Meta hoặc phát hành báo cáo.

Tổng quan và Dashboard có thẻ Facebook Content với kỳ snapshot riêng; không trộn
organic vào chỉ số quảng cáo và xóa dữ liệu cũ khi chuyển khách hàng. Đây là dữ
liệu vận hành riêng tư, chưa phải revision đã phát hành.

Để chỉ cấu hình Content, dùng
`scripts/configure_customer_providers.py meta --meta-source content`; Ads cần
cấu hình và nghiệm thu riêng. Contract, quyền và giới hạn tại
[Customer Meta Content](../VioAgencyAnalytics-Admin/docs/CUSTOMER_META_CONTENT.md).

## Customer UX gọn hơn (05/11/2026)

Menu chỉ mở danh sách kênh khi ở Phân tích kênh. Tổng quan gom quản lý khách hàng
và thiết lập vào mục mở rộng; Cài đặt chia nhóm; Báo cáo ưu tiên danh sách đã lưu,
mẫu báo cáo có thể mở riêng. Hướng dẫn và định nghĩa chỉ số vẫn truy cập được khi cần.
Cỡ chữ và các kiểm tra quyền giữ nguyên; không thay dữ liệu thiếu bằng số 0.

`clarity.css` chứa bố cục bổ sung. `shell.js` mở đúng nhóm khi đi theo liên kết
hoặc gặp trường nhập không hợp lệ. Hướng dẫn 8 bước tự mở rồi khôi phục nhóm đã thu gọn.

## Kết nối Fanpage theo từng bước (05/11/2026)

Mở `/workspace/integrations?platform=facebook_content`. Luồng Facebook riêng gồm
**Kết nối → Chọn Fanpage → Hoàn tất**. Sau consent từ chính nút kết nối, Web mở
ngay danh sách Fanpage; khách hàng bấm **Kết nối Fanpage** để xác nhận. Có tìm kiếm
không dấu, phân trang, trạng thái danh sách trống và thử lại. Nhiều Page không tự
chọn; một Page có thể được điền sẵn nhưng vẫn cần khách hàng xác nhận.

Email chưa xác minh có nút gửi thư và kiểm tra lại ngay tại đây; chỉ gửi khi
khách hàng bấm, không tự xác minh tài khoản. Trạng thái hoàn tất phân biệt đã
kết nối, đang đồng bộ, đã có dữ liệu và đồng bộ lỗi. Đổi Fanpage, đồng bộ theo
khoảng ngày và ngắt kết nối nằm trong **Tùy chọn kết nối**.

`facebook-connect.js` chỉ gọi BFF hiện có, không gọi Graph trực tiếp. Phản hồi
khác người dùng/Workspace/khách hàng/phiên bản kết nối bị bỏ. Dấu nhớ điều hướng
trong sessionStorage chỉ có phạm vi và thời hạn, không chứa token, state OAuth
hoặc URL cấp quyền; query callback giả không tự tải danh sách Page. Backend vẫn
kiểm tra quyền, email, grant, version và tài sản trước mọi thao tác. Không đổi DB,
chỉ số hoặc đường phát hành báo cáo. Callback Meta phải khớp origin đang dùng;
hostname Quick Tunnel mới không tự được đăng ký tại Meta.

Nút **Kết nối Facebook** trên danh mục mở thẳng consent nếu người dùng đã đủ
quyền/xác minh và chưa có grant hợp lệ, giảm một lần xác nhận trung gian. Mở URL
có `platform=facebook_content` chỉ mở giao diện, không tự khởi tạo OAuth. Callback
hủy cũng không tự chuyển lại Facebook. Email chưa xác minh hiển thị riêng là tài
khoản Vio; khi quay lại tab sau khi xác minh, Web tự đọc lại trạng thái, vẫn có
nút kiểm tra thủ công. Không tự gửi thư hoặc đổi cờ xác minh trong DB.

Mọi khách hàng dùng Meta App do VIO cấu hình ở backend; Customer không tạo App,
nhập App ID/Secret hoặc chỉnh callback. VIO cần chuẩn bị origin/callback ổn định
và hoàn tất yêu cầu phát hành/quyền của Meta cho khách hàng ngoài nhóm thử nghiệm.
Có credential ứng dụng không đồng nghĩa đã đủ điều kiện phục vụ khách hàng bất kỳ.

## Connector và trình xem dữ liệu chung (06/11/2026)

**Báo cáo → Dữ liệu đã đồng bộ** và các thẻ nguồn ở Tổng quan/Dashboard dùng
chung hợp đồng dữ liệu với Customer backend. Mở
`/workspace/reports/data?source=ga4`, đổi nền tảng/khách hàng và chọn snapshot
đã lưu để xem KPI, biểu đồ, bảng tìm kiếm/phân trang và cách tính chỉ số.

Kho có chín connector; mapping hiện đọc được bốn adapter đã có: Facebook
Content, Facebook Ads, GA4 và GSC. Năm nền tảng khác vẫn `planned`, không tự
bật OAuth chỉ vì có tên trong danh mục. Ứng dụng VIO được cấu hình chung ở
backend; khách hàng không nhập token, secret hoặc URL API tùy ý.

Trình xem chỉ đọc dữ liệu bất biến đúng Workspace/client/tài sản/phiên bản
kết nối. Null khác 0; không cộng unique, tỷ lệ hoặc các nguồn khác kỳ/tiền tệ.
Giá trị tiền decimal được định dạng chính xác. Mỗi thẻ nguồn ghi kỳ đã lưu
riêng; không lấy kỳ của khung thử bố cục để giả định đã có dữ liệu trong kỳ đó.
Trang Facebook Content chuyên sâu và luồng Published Bundle/ACL giữ nguyên.

Đây là báo cáo vận hành riêng, chưa duyệt/phát hành. Các thao tác lưu Report
Builder, xuất file, lịch gửi và chia sẻ vẫn cần luồng Dataset/Bundle riêng.
Xem [hợp đồng connector và mở rộng adapter](../VioAgencyAnalytics-Admin/docs/CUSTOMER_CONNECTOR_DATA.md).

Kiểm tra formatter tiền tệ bằng `node --test tests/customer_data_format.test.cjs`;
kiểm tra BFF bằng `python -m pytest tests/test_customer_data.py`.

Đã triển khai lên Docker Customer backend và Web ngày 06/11/2026, giữ nguyên
schema 16 và dữ liệu cũ. **407 pytest Web PASS**, **3 test formatter PASS** và
**27 nhóm browser PASS** trên provider/SMTP giả lập. Smoke bản Docker sau triển
khai: đăng nhập, **14 trang và 6 API dữ liệu PASS**, kèm tenant/CSRF/cookie và hash
asset. Kiểm tra loopback dùng Host/Origin đang cấu hình, không thay chế độ chia
sẻ hiện tại; chưa nghiệm thu lại HTTPS public hoặc tài khoản provider thật.
