# NEW-1 — Bundle Renderer Foundation

## Cập nhật 13/10/2026

Luồng chính `/reports/{id}?revision=N` đã dùng dashboard gốc với binding Bundle và
chuyển phiên Admin. Xem [ADMIN_HANDOFF_DASHBOARD.md](ADMIN_HANDOFF_DASHBOARD.md).
Các mô tả renderer tổng quát/phase cũ phía dưới là lịch sử triển khai.

Triển khai ngày 08/10/2026 trong `D:\KDH-Report-New`, nhánh `feat/admin-bundle-repository`.

## Audit trước khi sửa

- Có sẵn FastAPI, Jinja2, layout dashboard, font/icon/CSS tại máy chủ, chart helpers và sáu trang demo độc lập.
- Có sẵn `AdminBundleRepository`: gọi Internal API bằng service token, kiểm tra schema/status/ID và phân loại lỗi cơ bản. Bộ test repository ban đầu: **10 PASS**.
- Chưa có service, mapper, view model, route có viewer protection và renderer cho snapshot đã xuất bản.
- Working tree ban đầu chỉ thay đổi `tests/test_admin_bundle_repository.py`. File này được giữ nguyên trong NEW-1, đối chiếu SHA256 trước/sau.
- Đã đọc các file được yêu cầu ở New; đối chiếu **chỉ đọc** `D:\KDH-Report-Admin\docs\report-bundles.md`, `kdh/report_bundles.py`, `kdh/report_bundle_routes.py`, mã dataset Google và các test bundle phía Admin. Không thay đổi Admin, không truy cập DB, không gọi tài khoản/provider thật.
- Không reset, đổi nhánh, commit, push hoặc merge.

## Luồng và trách nhiệm

```text
GET /published/{report_id}?revision=N
  → Preview access: environment + credentials riêng + report allowlist
  → BundleService
  → AdminBundleRepository (đã có)
  → GET Admin /api/internal/v1/report-bundles/{report_id}?revision=N
  → Kiểm tra snapshot/credential contamination
  → BundleViewMapper → BundleView
  → Jinja2 + generic components + shared chart helper
```

`BundleService` chỉ điều phối repository và mapper. Renderer không gọi provider, không truy cập database, không lấy mock thay thế khi lỗi. Các route `/overview`, `/report/seo`, `/report/facebook-ads`, `/report/facebook-content`, `/report/tiktok`, `/report/youtube` vẫn sử dụng luồng demo cũ.

Repository hiện có được bổ sung phân biệt timeout, xác nhận revision trả về đúng revision yêu cầu, chặn redirect và kiểm tra cấu hình URL. Không tạo repository trùng chức năng. Không tự retry hay bỏ qua lỗi contract.

## Contract Admin đã đối chiếu

Schema `1.0` có `report`, `client`, `period`, `comparison`, `freshness`, `quality`, `navigation`, `branding`, `sections`.

- Chỉ nhận `provisional` hoặc `final`. Revision là số nguyên dương; ID và revision phải khớp yêu cầu.
- `navigation.sections` thực tế là **danh sách section key dạng chuỗi có thứ tự**. Mapper giữ thứ tự này; nếu `position` lệch thì cảnh báo. Không tự sắp xếp lại theo `position`.
- Chỉ hiển thị giao của navigation và section có snapshot. Section ngoài navigation không render. Navigation trỏ đến snapshot thiếu thì ẩn mục đó và cảnh báo. `default_section` không khả dụng thì chọn mục đầu tiên và cảnh báo; không có mục thì hiển thị trạng thái rỗng.
- Mỗi section có metadata `dataset_id`, `report_type`, `created_at`, `valid`, `position`, `quality` và `data`. `data` là dataset snapshot, thường gồm `params` và `sources`.
- Dataset Google hiện có các nguồn `ga4`, `gsc`, `keywords`, `gmb`; các trường như `totals`, `previous`, `daily`, `channels`, `pages`, `queries`, `entries`, `latest_available_date`, `fetched_at`, `warnings`, `status`.
- Không giả định các nền tảng khác đã có dataset hoặc có 211 KPI. Việc nhận diện loại báo cáo trong New chỉ cho phép dùng component chung khi snapshot thật sự cung cấp các trường hỗ trợ.
- Kỳ báo cáo dùng ISO date từ bundle. Dataset khai báo kỳ khác thì nội dung bị khóa và có cảnh báo. Chỉ hiển thị số kỳ trước/delta khi kỳ so sánh dataset khớp kỳ so sánh bundle. Dataset khai báo client khác bị từ chối.
- `freshness.generated_at`/`published_at` được hiển thị theo chuỗi thời điểm có trong snapshot. Không thay bằng giờ hiện tại hoặc ngày demo.

### Ánh xạ dữ liệu

| Dữ liệu nguồn | View/hiển thị | Giới hạn |
| --- | --- | --- |
| `totals` | KPI theo đúng key/value đã lưu | Không cộng daily, không suy ra Leads/ROAS/doanh thu |
| `previous`, `deltas` | Giá trị kỳ trước/thay đổi được cung cấp | Không tự trừ/chia để tạo delta |
| Giá trị `null` hoặc thiếu | “Chưa có dữ liệu” | Số `0` thật vẫn hiển thị `0` |
| GA4 `engagementRate`, GSC `ctr` | Giữ tỷ lệ 0–1 và ghi đơn vị | Không đổi định nghĩa hoặc tự tính tỷ lệ |
| `daily` | Line chart cho trường số + bảng nguồn | Giữ thứ tự; điểm thiếu tạo khoảng đứt, không nối thành số 0 |
| GA4 `channels` | Bar chart theo sessions + bảng | Không suy ra các nhóm kênh khác |
| Các danh sách chi tiết được hỗ trợ | Bảng cột từ trường scalar thực có | Bản ghi/cột trống có empty state; cấu trúc sai có cảnh báo |
| `quality` | Complete / Partial / Failed / Unknown, warnings | Không tự nâng chất lượng lên complete |
| Source metadata | Nguồn, trạng thái, ngày mới nhất, thời điểm lấy dữ liệu, lỗi | Không che lỗi nguồn; URL chỉ cho HTTP(S) hợp lệ |

Các danh sách chi tiết hỗ trợ: `daily`, `channels`, `pages`, `queries`, `entries`, `rows`, `campaigns`, `posts`, `videos`. Trường lồng nhau chưa có adapter không được đoán thành KPI. Section/report type chưa hỗ trợ có trạng thái “Chưa hỗ trợ”.

Chart helper chung ở `static/js/shared/charts.js` được mở rộng với `renderBundleChart`; các helper ECharts cũ giữ nguyên. Phần mới dùng SVG tại máy chủ, không cần CDN/SDK ngoài. Có line/bar/donut, legend, tooltip chuột/bàn phím, nhãn nguồn/ngày/đơn vị, trạng thái lỗi/rỗng. Tổng các lát donut chỉ dùng để vẽ cung tròn, không xuất thành KPI mới. Donut không vẽ khi giá trị âm/null/toàn 0.

### View contract mở rộng, không phải thay đổi API Admin

Model chung nằm ở `app/schemas/bundle_view.py`. Renderer nhận các model này, không nhận toàn bộ payload hoặc Settings. Các adapter trình bày tùy chọn chỉ map khi dataset **đã cung cấp** đúng dạng:

- `kpis`: danh sách `{key, label, value, unit, previous, delta, source, data_date}`.
- `charts`: danh sách `{title, type: line|bar|donut, labels, values, unit}`.
- `tables`: danh sách `{title, columns: [{key, label, unit}], rows: [object]}`.
- `evidence`: danh sách trường tương ứng EvidenceCard.
- `opportunities`: danh sách trường tương ứng OpportunityCard.

Đây là khả năng trình bày của New, **không yêu cầu Admin contract 1.0 phải có các trường trên**. Snapshot hiện tại vẫn được map từ `totals`, `daily` và danh sách chi tiết. Admin chưa có Evidence/Opportunity hoàn chỉnh nên báo cáo hiện empty state.

`EvidenceCard`: claim, metric, before, after, period, source, URL kiểm chứng, data_date, quality. `OpportunityCard`: title, reason, supporting_data, priority, action, conditions. Không tạo claim, Opportunity Score, AI nhận định hoặc câu khẳng định về hiệu quả kinh doanh.

## Nguồn demo và xác minh

Mapper nhận các marker demo/mock có trong snapshot, kể cả `params.demo` và cảnh báo DEMO của Admin. Nếu có, toàn báo cáo gắn nhãn **DEMO**, section cũng có nhãn tương ứng.

Snapshot không có marker demo vẫn ghi **“Chưa xác minh đầy đủ nguồn gốc”**. `demo=false` hoặc status `final` riêng lẻ không được coi là chứng minh đã đối soát mọi provider. NEW-1 chưa có cơ chế chứng thực provenance độc lập.

## Phân quyền và xử lý lỗi

Internal service token chỉ dùng backend → Admin. Browser không nhận token qua HTML/JS/URL. New chặn redirect và từ chối payload có trường credential, chuỗi token đang sử dụng, token URL hoặc dữ liệu số không hợp lệ. Template autoescape; chart dựng DOM bằng text; URL nguồn chặn scheme thực thi và URL chứa thông tin xác thực.

Chưa có đăng nhập khách hàng/ACL theo tenant trong dự án, do đó:

1. Preview mặc định tắt.
2. `APP_ENV=production` luôn trả 404 cho route published, kể cả bật preview bằng biến khác.
3. Preview chỉ hoạt động ở development/test khi được bật rõ ràng.
4. Yêu cầu HTTP Basic bằng username/password riêng; password tối thiểu 24 ký tự và phải khác service token.
5. Chỉ report ID có trong allowlist mới được đọc. Các bước kiểm tra này chạy trước lời gọi Admin.
6. Nội dung báo cáo có `Cache-Control: no-store, private`, CSP cùng origin, noindex, no-referrer và chống nhúng iframe.

Preview là công cụ cục bộ cho người vận hành, **chưa phải viewer authentication để public cho khách hàng**. Docker chỉ bind cổng vào localhost. Không dùng overlay preview khi triển khai production; NEW-2 cần đăng nhập và phân quyền thực sự trước khi mở báo cáo.

| Tình huống | Mã UI | HTTP tại New |
| --- | --- | --- |
| Preview tắt/production hoặc report ngoài allowlist | Truy cập chưa được mở/không có trong phạm vi | 404 |
| Thiếu/sai credentials người xem | Yêu cầu đăng nhập preview | 401 |
| Thiếu cấu hình preview/backend | `configuration` hoặc thông báo cấu hình an toàn | 503 |
| Admin trả 401 | `admin_unauthorized` | 502 |
| Admin trả 404 | `not_found` | 404 |
| Admin trả 409 | `snapshot_required` | 409 |
| Admin timeout | `timeout` | 504 |
| Không kết nối được Admin | `unavailable` | 503 |
| Lỗi HTTP khác/redirect | `upstream` | 502 |
| Sai schema/status/ID/revision hoặc payload không an toàn | `contract` | 502 |
| Query revision không hợp lệ | FastAPI validation | 422 |

401 giữa backend được biểu diễn bằng 502 để không nhầm với yêu cầu xác thực của người xem. Không đưa body lỗi Admin hoặc exception chứa thông tin nhạy cảm vào trang lỗi/log ứng dụng.

## Chạy Docker và URL

Trong **`D:\KDH-Report-New`**, giữ nguyên Compose project `kdh-report-new`, độc lập với KDH-Report và Admin:

```powershell
docker compose up --build -d
docker compose ps
```

Demo: `http://127.0.0.1:8080/overview` và các URL demo cũ. Báo cáo published **bị khóa trong chế độ này**; đây là hành vi chủ đích của NEW-1.

Để người vận hành thử snapshot đã xuất bản: cấu hình các biến dưới đây trong môi trường riêng hoặc `.env` đang được gitignore, rồi dùng overlay local:

```powershell
docker compose -f compose.yaml -f compose.preview.yaml up --build -d
```

`http://127.0.0.1:8080/published/{report_id}?revision=2` — thay report ID/revision bằng snapshot đã xuất bản thực có trong allowlist. Trình duyệt hỏi tài khoản preview riêng. Bỏ query revision để đọc bản đã xuất bản mới nhất; link sidebar sau đó giữ revision đã nhận, tránh đổi snapshot trong lúc điều hướng.

Các biến cần cấu hình (không ghi giá trị bí mật vào README, lệnh, ảnh chụp hoặc Git):

| Tên biến | Vai trò |
| --- | --- |
| `REPORT_ADMIN_BASE_URL` | Địa chỉ backend Admin mà container New truy cập được |
| `REPORT_SERVICE_TOKEN` | Credential nội bộ của backend, khớp cấu hình Admin |
| `REPORT_REQUEST_TIMEOUT_SECONDS` | Giới hạn thời gian request |
| `REPORT_PREVIEW_ENABLED` | Công tắc preview; overlay local bật rõ ràng |
| `REPORT_PREVIEW_USERNAME` | Người vận hành preview |
| `REPORT_PREVIEW_PASSWORD` | Mật khẩu preview riêng |
| `REPORT_PREVIEW_ALLOWED_IDS` | JSON array chứa chính xác các report ID được cho phép |
| `APP_ENV` | Production khóa published; overlay local đặt development |
| `DEBUG` | Giữ debug tắt |
| `KDH_PORT` | Tùy chọn đổi cổng host của riêng New |

Với Docker Desktop và Admin trên máy host, dùng hostname `host.docker.internal` cùng cổng Admin thực tế trong `REPORT_ADMIN_BASE_URL`. `127.0.0.1` bên trong container trỏ về chính New. Compose mặc định dùng cổng Admin 8090 khi không cấu hình; nếu `.env` có giá trị thì giá trị đó được ưu tiên. Không đổi cấu hình/network/DB của Admin để ghép hai dự án.

Tắt preview, quay về cấu hình production:

```powershell
docker compose -f compose.yaml up -d --force-recreate
```

Không dùng `docker compose config` hoặc dump môi trường đầy đủ để chia sẻ chẩn đoán vì chúng có thể in credential đã nội suy.

## Kiểm thử

```powershell
$env:DEBUG = 'false'
.venv\Scripts\python.exe -m pytest tests/test_admin_bundle_repository.py -q
.venv\Scripts\python.exe -m pytest tests/test_bundle_mapper.py tests/test_bundle_service.py tests/test_published_reports.py -q
.venv\Scripts\python.exe -m pytest -q
```

`DEBUG` được đặt trong shell kiểm thử vì máy hiện tại có biến môi trường cùng tên không phải boolean; không sửa `.env` của người dùng.

- **152 test PASS**, 0 FAIL sau thay đổi NEW-1, gồm 10 test repository hiện có. Có 4 cảnh báo deprecation từ Starlette/AnyIO và cách gọi template cũ.
- Test dùng fixture vô hại và `httpx.MockTransport`. Bao phủ revision cụ thể, provisional/final/draft, schema/ID/revision lệch, navigation/default/section chưa publish, null khác 0, không cộng daily thành KPI, warnings/empty state, error mapping, credential contamination, preview protection và các route demo cũ.
- Kiểm tra trình duyệt Edge headless trên fixture server localhost: desktop 1440px/mobile 390px, line/bar/donut, tooltip, chuyển section giữ revision, Back, menu/Escape; không tràn ngang, không có lỗi JS/CSP. Đã xem ảnh full-page ở cả hai kích thước.
- `docker compose up --build -d`: PASS, container `kdh-report-new-app-1` healthy. Kiểm tra HTTP trực tiếp tại cổng 8080: healthcheck, cả sáu trang demo và assets mới trả 200; published trong production trả 404 kèm `no-store`. Overlay preview qua `config --quiet` với fixture: PASS, không mở preview thật.
- Fixture QA và ảnh nằm trong `.work/`, được gitignore và không đưa vào Docker image. Đây là dữ liệu kiểm thử, không phải kết quả khách hàng.
- Chưa gọi live Internal API với báo cáo khách hàng; không thể coi mock transport PASS là đã nghiệm thu dữ liệu thật.

## File tạo và sửa

Tạo:

```text
app/bundle_safety.py
app/mappers/__init__.py
app/mappers/bundle.py
app/routes/published.py
app/schemas/bundle_view.py
app/services/bundle.py
compose.preview.yaml
static/css/pages/published.css
static/js/pages/published.js
templates/pages/published/base.html
templates/pages/published/index.html
templates/pages/published/error.html
templates/pages/published/components/quality.html
templates/pages/published/components/kpi.html
templates/pages/published/components/chart.html
templates/pages/published/components/table.html
templates/pages/published/components/evidence.html
templates/pages/published/components/opportunity.html
tests/bundle_fixtures.py
tests/test_bundle_mapper.py
tests/test_bundle_service.py
tests/test_published_reports.py
docs/NEW-1-bundle-renderer.md
```

Sửa:

```text
.env.example
app/config.py
app/repositories/admin_bundle.py
compose.yaml
main.py
README.md
static/js/shared/charts.js
templates/layouts/dashboard.html
```

`tests/test_admin_bundle_repository.py` vẫn là thay đổi của người dùng trước NEW-1, không nằm trong danh sách file do NEW-1 sửa. Layout chỉ thêm block để published tùy biến sidebar/header/controls; mặc định các trang demo giữ include cũ. Không thêm thư viện runtime hoặc migration.

## Phần còn thiếu và NEW-2

1. Đăng nhập người xem thật, session, quyền theo client/report/revision, thu hồi quyền và kiểm thử ngăn đọc chéo tenant. Giữ production đóng đến khi hoàn thành.
2. Nghiệm thu bằng snapshot đã xuất bản được cấp quyền từ Admin: đối chiếu số, kỳ, revision và freshness, vẫn giữ credential ở backend.
3. Thống nhất metadata chứng minh provenance giữa Admin và New; chỉ xác nhận nguồn thực khi đủ bằng chứng.
4. Mở rộng adapter theo dataset thật từng nền tảng khi Admin đã hỗ trợ; dùng chung các view model/component hiện tại. Không kéo provider vào New.
5. Khi Admin thực sự xuất bản Evidence/Opportunity, chốt contract, provenance và fixture cho chúng rồi mở hiển thị. Chưa xây AI hoặc Opportunity Score trong NEW-1.
