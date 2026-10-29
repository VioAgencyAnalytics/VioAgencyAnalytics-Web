# Trang 03 — Tổng quan Workspace

## Tổng quan Marketing theo mẫu Stitch — 28/10/2026

Trang chính đã chuyển sang bố cục Tổng quan Marketing theo HTML/ảnh người dùng
cung cấp: Inter cho nội dung, Plus Jakarta Sans cho tiêu đề; nền `#F8FAFC`,
chữ slate, thẻ trắng viền `#E2E8F0`, nhấn `#D9232E`. Header/menu sticky và tìm
kiếm giữ nguyên. Khu vực chính có chọn kỳ, khách hàng, xuất CSV, banner kết nối,
bốn KPI, xu hướng, trạng thái chín nền tảng, sáu lối tắt phân tích và báo cáo gần
đây. Nguồn ưu tiên GA4/Meta/GSC; danh sách desktop tự cuộn để giữ thẻ gọn.
Quản lý khách hàng, lưu trữ/khôi phục, checklist và tour được giữ ở phần dưới.

Đây là **khung có binding dữ liệu**, chưa phải API Marketing customer đã hoàn
thiện. `app/mappers/customer_overview.py` xây model an toàn từ Workspace và danh
mục private hiện có của Admin. Không đọc connection/report legacy hoặc gọi
provider. Không thêm schema/migration. KPI ban đầu là `null`, trends/reports/
connections rỗng; không dùng tài khoản, số liệu hoặc chứng nhận trong ảnh mẫu.

### Điểm nối dữ liệu cho giai đoạn sau

`overview-analytics-data` là JSON ban đầu; `static/js/customer/overview-dashboard.js`
chịu trách nhiệm format/render. Bên gọi sau khi có Customer analytics API hợp lệ:

```javascript
const context = window.VioOverview.getContext();
// Lấy dữ liệu từ BFF/Customer API đã kiểm tra quyền tại Admin.
// Chỉ gọi applySnapshot với DTO của đúng context này.
const accepted = window.VioOverview.applySnapshot(dto);
```

Contract DTO:

- `schema_version: 1`, `scope: {workspace_id, client_id}`, `period: {start, end}`
  (ISO date), `currency`, `timezone` phải khớp context. Đây là guard chống render
  response cũ, **không thay thế authorization tại Admin**.
- `metrics`: khóa `spend`, `impressions`, `clicks`, `conversions`; mỗi item có
  `value: number|null`, `previous: number|null`, `status` (`empty`, `ready`,
  `partial`, `error`), `source_label`. `0` là dữ liệu; null/string/boolean không
  được biến thành 0. Không tự cộng nguồn khác currency, timezone hoặc định nghĩa
  chuyển đổi. Nếu `metrics.spend.currency` có thì phải khớp currency context.
- `trends`: `spend`, `clicks`, `conversions`, mỗi item có `status` và `points`
  `{date, value:number|null}`. Tối đa 366 điểm/kỳ; null cắt đường biểu đồ. Có bảng
  dữ liệu tương đương cho khả năng truy cập. Không tạo đường xu hướng mẫu.
- `connections`: `{platform_id, state}` với state `connected`, `syncing`,
  `error`, `expired`; chỉ ID có trong catalogue. `last_updated_at` có thể null.
- `reports`: danh sách gần đây có `name`, `period_label`, `status`, `href`.
  Chỉ link nội bộ dạng `/reports/rpt_<32hex>?revision=<positive integer>` được
  dựng; Viewer hiện có vẫn kiểm tra quyền/revision ở server. Không tạo grant.

`customer:overview-context` phát khi đổi kỳ hoặc xác nhận khách hàng mới. Dữ liệu
cũ được xóa khi bắt đầu đổi khách; response trong lúc đổi, sai scope/kỳ/currency/
timezone bị từ chối. Lỗi chọn khách khôi phục lựa chọn trước, giữ KPI trống và
hiển thị lỗi. Bộ chọn kỳ dùng ngày theo timezone Workspace, không hardcode T4/2025.
CSV có BOM UTF-8; giá trị null để trống, zero giữ `0`; chống công thức CSV trong
tên Workspace/khách hàng. Export chỉ gồm dữ liệu đang hiển thị, không lấy provider.

Kiểm thử khung: Web **367 PASS**, CSS/JS/Python syntax/diff check PASS; browser
1440/1280/390 kiểm tra empty state, 0/null, chart gaps, dữ liệu sai scope/kỳ/
currency/timezone, failed selection/late response, CSV/XSS, bàn phím và sticky.
Tour và CRUD trang 3 cũ đã chạy lại desktop/mobile. Analytics synthetic chỉ được
gắn trong browser QA để thử renderer rồi xóa, không lưu vào DB hoặc production.
Artifacts `.work/customer-overview-design/`; source trước deploy ở
`web-before-stitch.tgz` (không có env/DB/secrets). Không commit/push.

Lưu ý QA local: chạy nhiều suite browser liên tiếp đã chạm quota POST theo IP
100/15 phút, gây một lượt tour timeout sau phản hồi 429. Đã xác minh đúng bucket
IP browser QA bằng fingerprint/HMAC, dọn quota test đó và chạy lại tour đạt cả
hai viewport. Không tăng giới hạn, tắt throttle hoặc sửa quyền customer.

## Thanh điều hướng dùng chung — 28/10/2026

Tổng quan và Kết nối dùng chung `customer/live/components/topbar.html`,
`static/css/customer/shell.css`, `static/js/customer/shell.js`. Sidebar desktop
sticky, cao bằng viewport, tự cuộn nếu màn hình thấp; header sticky trong cột
nội dung. Mobile giữ thanh đầu trang gọn với tìm kiếm, hướng dẫn và đăng xuất;
menu ngang không chiếm cố định phần lớn màn hình. Anchor nội dung có scroll margin.

Header hiển thị breadcrumb, Workspace, tên/vai trò, tìm kiếm nhanh và hướng dẫn
thật của từng trang; không gắn số thông báo hoặc trạng thái realtime giả.
Ctrl/Cmd+K mở dialog, phím mũi tên chọn, Enter mở, Escape đóng và trả focus.
Tìm kiếm không dấu hỗ trợ trang, khách hàng active và chín nền tảng (cả alias
GA4/GSC). Kết quả khách hàng gọi API select có CSRF rồi mở Tổng quan; kết quả
nền tảng mở danh mục với bộ lọc tương ứng. Mỗi lần mở tải lại session và dữ liệu
theo Workspace, không dùng localStorage hoặc tìm chéo tenant. Lỗi metadata vẫn
cho dùng lối tắt và thông báo thiếu dữ liệu. Không thêm API hoặc migration.

Nghiệm thu: Web 365 PASS; CSS build/JS syntax/diff check PASS; browser tại
1440×960, 390×844 và 1440×600 kiểm tra cuộn, menu/header, tìm không dấu, GA4,
chọn khách, cách ly Workspace, XSS text, bàn phím/focus và hướng dẫn. Tour 8
bước vẫn đạt desktop/mobile. Artifact riêng trong `.work/customer-shell-qa/`.

Triển khai ngày 28/10/2026 tại `/workspace`, yêu cầu đăng nhập và Workspace đã chọn.
Web trình bày; Admin xác minh session/membership, quản lý dữ liệu và tiến độ.

## Chức năng đã có

- Chuyển giữa các Workspace được cấp quyền ngay trên sidebar; liên kết tạo/tham gia
  vẫn dẫn về onboarding. Không dùng tên hoặc ID Workspace làm quyền truy cập.
- Thêm khách hàng/thương hiệu, chỉnh tên và website, tìm kiếm theo tên/website,
  lọc đang hoạt động/đã lưu trữ, tải lại danh sách.
- Lưu trữ có hộp xác nhận, giữ bản ghi và báo cáo; khôi phục không tự chọn lại.
  Không có API xóa cứng. Tối đa 100 khách hàng hoạt động trong một Workspace.
- Chọn khách hàng đang làm việc; tạo mới là thao tác “Tạo và chọn”. Khách hàng
  đầu tiên khai báo trong onboarding được chọn ngay khi tạo Workspace mới.
- Đếm khách hàng hoạt động/lưu trữ và thành viên bằng DB thật. Marketing vẫn hiện
  “Chưa có dữ liệu” vì chưa triển khai nguồn customer; không lấy KPI mẫu thay thế.
- Giữ tour spotlight 8 bước và tiến độ riêng theo tài khoản/Workspace.

“Khách hàng / thương hiệu” hiện là một đối tượng `customer_clients`. Chưa triển
khai nhiều Brand lồng trong một Client; chưa ánh xạ sang `clients`/asset/provider
legacy và không cấp quyền xem dữ liệu của khách hàng cũ.

## Quyền và trạng thái

| Thao tác | Owner/Admin | Member/Viewer |
|---|---|---|
| Xem khách hàng thuộc Workspace đang có membership | Có | Có |
| Chọn khách hàng đang hoạt động | Có | Có |
| Thêm/sửa/lưu trữ/khôi phục | Có | Không |

Backend kiểm tra account/session/membership/Workspace active trong transaction,
và yêu cầu Workspace trên mutation khớp Workspace của session. Scope đổi ở tab
khác trả `409 workspace_changed`; client khác Workspace trả 404. Biết client ID
không cấp quyền. Member/Viewer hiện xem metadata tất cả khách hàng thuộc Workspace;
quyền đọc dữ liệu Marketing theo Client phải được kiểm tra riêng trước trang 04–06.

Lựa chọn lưu theo **session + Workspace**, sống qua reload/restart container trong
hạn session, không lưu localStorage/sessionStorage. Chuyển Workspace rồi quay lại
giữ lựa chọn của phiên đó. Đăng xuất/hết phiên xóa lựa chọn qua FK cascade.
Lưu trữ xóa lựa chọn client đó khỏi mọi session trong Workspace; khôi phục không
tự phục hồi lựa chọn cũ. Các phiên hoặc Workspace khác không dùng chung lựa chọn.

## Checklist thiết lập

Tiến độ được Admin tính từ dữ liệu hiện có, không cho trình duyệt đánh dấu tùy ý:

1. Workspace tồn tại: hoàn thành.
2. Có khách hàng đang hoạt động: hoàn thành khi có bản ghi.
3. Có khách hàng đang được chọn và còn hoạt động: hoàn thành khi chọn.
4. Kết nối nền tảng: `planned`, ghi rõ trang 04 đang phát triển.

Xem xong tour không biến checklist thành 4/4 hoặc cấp quyền nguồn. Nút trạng thái
kết nối mở giải thích, không thực hiện OAuth giả. Dashboard mở trang 05 có xác thực
và khung dữ liệu trống; Phân tích/Báo cáo vẫn giải thích phạm vi đang phát triển.
Xem [Dashboard Marketing](CUSTOMER_MARKETING.md).

## API

Qua Web BFF `/api/customer`, giữ cookie HttpOnly, Origin, CSRF và POST allowlist.
Admin chỉ nhận các endpoint tương ứng dưới `/api/internal/customer` với service auth:

| Method | Đường dẫn sau prefix | Nội dung |
|---|---|---|
| GET | `/workspaces/{workspace_id}` | clients, archived_clients, selected_client, permissions, setup, member_count, tour |
| POST | `/workspaces/{workspace_id}/clients` | `name`, `website`, `request_key` |
| POST | `/workspaces/{workspace_id}/clients/{client_id}/update` | `name`, `website`, `version` |
| POST | `/workspaces/{workspace_id}/clients/{client_id}/archive` | `version` |
| POST | `/workspaces/{workspace_id}/clients/{client_id}/restore` | `version` |
| POST | `/workspaces/{workspace_id}/clients/{client_id}/select` | `{}` |

Tên tối đa 100 ký tự; website không bắt buộc, tối đa 500 ký tự, chỉ http/https,
không chứa user/password. Không gọi HTTP đến website do khách nhập.
Create dùng request key theo actor + Workspace; retry cùng nội dung trả bản ghi
cũ, khác nội dung trả 409. Retry không khôi phục client đã lưu trữ.
Sửa/lưu trữ/khôi phục yêu cầu version mới nhất; stale trả `409 client_conflict`,
giữ form để người dùng chủ động tải bản mới. Mọi thao tác có audit không chứa secret.

## Migration và vận hành

Migration **11 `customer_overview_clients`** chỉ bổ sung:

- Unique index `(id, workspace_id)` trên customer_clients.
- `customer_client_profiles`: website, active, version, updated_at; composite FK
  giữ client thuộc đúng Workspace. Client cũ không có profile đọc như active/version 1.
- `customer_client_selections`: lựa chọn session/Workspace, FK session cascade và
  composite FK client/Workspace.
- `customer_client_requests`: idempotency theo account/Workspace/request key.

Không sửa migration 1–10, không backfill metadata vào payload Dataset/Bundle.
Đã rehearsal trên bản restore riêng, kiểm tra lại startup và xác nhận bảng cũ không
đổi hash/count. Trên DB customer đang dùng, toàn bộ bảng dữ liệu cũ giữ hash/count
trước/sau migration; schema_migrations chỉ thêm version 11. Sau đó QA tạo dữ liệu
có tên rõ để nghiệm thu, không dùng fixture làm dữ liệu Marketing thật.

Backup riêng (Git ignored): `.work/customer-dev/customer-before-overview-20261028.dump`;
source trước triển khai ở các file `customer-*-before-overview-20261028.tgz`.
Không drop bảng mới hoặc restore đè DB đang có thay đổi mới để rollback. Bản Admin
cũ không hiểu trạng thái archived/version nên cần kế hoạch tương thích trước khi
quay lại source cũ. Lệnh build/chạy stack: [CUSTOMER_DOCKER.md](CUSTOMER_DOCKER.md).

## Kiểm thử

- Admin: `tests/test_customer_overview.py`: CRUD, retry/concurrent retry, stale
  version, capacity/restore, session isolation, revoke, các role và forged scope,
  validation; chạy cả SQLite và PostgreSQL disposable.
- Web: `tests/test_customer_auth.py`: BFF allowlist, CSRF, cookie identity và từ chối delete.
- `scripts/check_customer_overview_ui.py`: viewport 1440/390, CRUD, XSS literal,
  response-loss retry, concurrent edit, reload, chuyển Workspace và checklist.
- `scripts/check_customer_tour_ui.py`: tour 8 bước vẫn hoạt động; hoàn tất tour
  không tự hoàn tất bước kết nối nền tảng.

Ảnh/kết quả riêng nằm trong `.work/customer-overview-qa/`, log regression trong
Admin `test-results/customer-overview-*.log`; không commit các artifact riêng này.

Kết quả 28/10/2026:

| Kiểm tra | Kết quả |
|---|---|
| Web pytest | 364 PASS |
| Admin toàn bộ trên image sạch | 606 test: 441 PASS / 165 SKIP cần PostgreSQL riêng |
| Customer trên SQLite + PostgreSQL disposable | 41 PASS, không SKIP |
| Admin frontend | 102 PASS |
| Browser trang 03, 1440/390 | 2 PASS, không lỗi JavaScript |
| Tour 8 bước, 1440/390 | 2 PASS, không lỗi JavaScript |
| Migration 10 → 11 trên bản restore và lặp startup | PASS, giữ hash/count bảng cũ |
| Migration 1–10 so với source backup | PASS, không thay đổi |
| Runtime/source (6 file trọng yếu) | PASS |
| Python/JS syntax, CSS build, Git whitespace | PASS |

Ba container Customer đều healthy; đã dọn container PostgreSQL dùng riêng cho
test/rehearsal. Không gửi email, gọi Google consent/Meta hoặc đồng bộ dữ liệu
Marketing thật trong lượt này. Chưa commit/push.

Trang Tổng quan và Kết nối nền tảng dùng chung partial sidebar
`templates/customer/live/components/sidebar.html` cùng theme
`static/css/customer/workspace-theme.css`. Header, tìm kiếm Ctrl+K, đổi Workspace,
font/màu và menu responsive được giữ thống nhất. Việc thu gọn cây kênh trên điện
thoại nằm trong `shell.js`, dùng cho cả hai trang; các ID của tour không đổi.
