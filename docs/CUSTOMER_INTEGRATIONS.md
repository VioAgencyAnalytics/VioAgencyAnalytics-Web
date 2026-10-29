# Trang 04 — Kết nối nền tảng

Ngày 28/10/2026. URL customer: `/workspace/integrations`.

## Phạm vi đã triển khai

Trang thật có xác thực trong Docker customer, tách khỏi bản thiết kế có mock.
Giữ bố cục mẫu: sidebar, breadcrumb, Workspace, khách hàng đang chọn, tài khoản
đã kết nối, danh mục thẻ nguồn, tìm kiếm, bộ lọc, hướng dẫn và khối bảo mật.
Desktop ba cột, tablet hai cột, điện thoại một cột. Không dùng tài khoản KinderHealth,
chứng nhận HIPAA/ISO, thời gian đồng bộ hay KPI mẫu trong giao diện thật.

Danh mục do **Admin** sở hữu tại `kdh/customer_integrations.py`, gồm chín nguồn:
Facebook Ads, TikTok Ads, Google Ads, Facebook Content, Instagram, Google Analytics 4,
Google Search Console, YouTube và Google Business Profile. Một nguồn có nhiều nhóm
(ví dụ TikTok Ads thuộc quảng cáo và video), không nhân đôi thẻ. Zalo trong phần
tài khoản mẫu không có adapter customer nên chưa được quảng bá là kết nối có sẵn.

Web dựng danh mục từ DTO Admin; thêm metadata nền tảng tại Admin không cần viết
lại từng thẻ HTML. ID nguồn, categories và catalogue_version là contract để mở
rộng. Khả năng đọc báo cáo/import CSV/adapter nội bộ **không** đồng nghĩa đã có
OAuth tự phục vụ. Cả chín hiện là `planned`, `can_connect=false`, nút **Tìm hiểu**
mở thông tin chuẩn bị, không giả chạy OAuth. Facebook Content/Ads và Google SEO
có bộ xử lý legacy; chưa tái sử dụng token, asset hoặc grant legacy cho Workspace.

## API và quyền

- Web GET `/api/customer/workspaces/{workspace_id}/integrations` chuyển đúng một
  đường dẫn allowlist sang Admin GET `/api/internal/customer/workspaces/{workspace_id}/integrations`.
- Bearer service và session customer bắt buộc tại Admin. Session/account,
  membership và Workspace active được kiểm tra lại trong transaction. Workspace
  URL phải trùng Workspace đang chọn của session; tab cũ nhận 409 `workspace_changed`.
- DTO: `catalogue_version`, `workspace`, `clients` active, `selected_client`,
  `permissions.manage_connections`, `categories`, `platforms`, `connections`, `summary`.
- Owner/Admin có capability quản lý tương lai. Member/Viewer chỉ xem, chọn khách
  hàng theo quyền đã có. Chọn khách dùng POST `/clients/{id}/select` có CSRF,
  Origin, membership và scope check; không cấp quyền nguồn dữ liệu.
- ID client không được lấy từ query string để truy cập legacy. Không đọc bảng
  `connections`/`source_assets` legacy hoặc gọi API provider khi mở/refresh trang.
- `connections=[]`, số tài khoản/nền tảng kết nối là 0 vì chưa có luồng tạo
  connection customer. `automatic_sync=false`; không gán lịch 30 phút hay realtime.
- HTTP không cache; cookie HttpOnly; token provider, secrets và địa chỉ nội bộ
  không có trong DTO/HTML/browser storage. Không nới quyền các trang customer còn lại.

## Hoàn thiện UX/UI cùng trang Tổng quan

Sidebar và bộ theme chung nằm trong `live/components/sidebar.html` và
`workspace-theme.css`: Inter cho nội dung, Plus Jakarta Sans cho tiêu đề, nền slate,
thẻ trắng và màu đỏ thương hiệu. Header và sidebar desktop cố định khi cuộn;
sidebar cuộn riêng khi màn hình thấp. Điện thoại dùng menu ngang, thu gọn cây kênh.
Giữ nguyên các điểm neo của tour tám bước trên Tổng quan.

Trang kết nối có chọn Workspace thực, chọn khách hàng, thông báo quyền xem/quản lý,
ba bước hướng dẫn, trạng thái đang tải/lỗi/thử lại, danh mục ba/hai/một cột và
khối giải thích quyền truy cập. Toolbar tìm kiếm/lọc bám dưới header trên desktop.
Tìm kiếm không phân biệt dấu, hỗ trợ nhiều từ và tên viết tắt GA4/GSC/Meta Ads.
Nhóm nền tảng có số lượng; bộ lọc trạng thái có thể kết hợp với tìm kiếm và nhóm.
Query `q`, `category`, `status` giữ bộ lọc sau reload/chia sẻ; `platform` vẫn nhận
deep link từ tìm kiếm chung. Không lưu dữ liệu tài khoản trong browser storage.

Khung tài khoản đã kết nối đã có renderer cho DTO tương lai; backend hiện vẫn
trả `connections=[]`. Mỗi record cần `id`, `workspace_id`, `client_id`,
`platform_id`, `state`; metadata tùy chọn `account_name`, `asset_name`,
`last_sync_at`. Chỉ nhận record đúng Workspace, khách hàng đã chọn và nền tảng
trong danh mục. Trạng thái gồm `connected`, `syncing`, `expired`, `error`,
`disconnected`, `pending`; timestamp thiếu hiển thị **Chưa đồng bộ**.
Đây là contract hiển thị dự kiến, chưa phải API tạo kết nối hoặc quyền gọi OAuth.
Thẻ mở thông tin tài khoản; chưa có endpoint quản lý/revoke/đồng bộ customer.
Khi đổi phạm vi hoặc tải lỗi, ẩn record cũ trước khi tải lại.

## Database và bước mở kết nối thật

Lượt này không đổi schema hay thêm migration: chỉ dùng Workspace, membership,
client metadata và selection migration 11. Không tạo bảng connection rỗng để
ngụ ý đã tích hợp. Trước khi bật `can_connect`, cần migration riêng cho connection,
OAuth transaction, encrypted secret, asset và job có ownership Workspace/Client;
kiểm thử chéo tenant, revoke, state/replay, asset và sync. Callback/worker thuộc
Admin; Web chỉ điều hướng consent và nhận DTO an toàn. Google Sign-in vẫn là
identity riêng. Ưu tiên nghiệm thu Facebook Content, sau đó Google SEO và Ads.

## Kiểm thử

`tests/test_customer_auth.py`: production gate, session/onboarding redirect,
allowlist GET, cookie identity không bị header browser giả mạo, không mở POST
hoặc trang mock. Admin `tests/test_customer_integrations.py`: danh mục đủ,
không rò token/config, không ghi provider data, service/session/tenant/stale
Workspace, role, revoked membership, archived client và disabled account;
có biến thể SQLite và PostgreSQL disposable.

`scripts/check_customer_integrations_ui.py`: tạo tài khoản QA `.invalid`, kiểm tra
1440/390, tạo khách hàng, chọn/đổi khách, reload, filter/search/reset, dialog,
empty state, refresh, CSRF và không tràn ngang/lỗi JavaScript. Artifact nằm trong
`.work/customer-integrations-qa/`, không đưa DB, cookie hay mật khẩu vào Git.
Script còn kiểm tra bố cục 1024, menu/header cố định, bộ lọc giữ qua reload,
trạng thái lỗi/thử lại và renderer kết nối bằng response giả lập **chỉ trong
trình duyệt**. Record sai Workspace/khách hàng bị bỏ qua, chuỗi HTML hiển thị như
văn bản, record thiếu ngày đồng bộ không biến thành ngày hay số giả. Không ghi
connection giả xuống DB hoặc gọi provider.

Kết quả 28/10/2026 sau khi cập nhật Docker:

- Web pytest: **365 PASS**, 6 deprecation warnings có sẵn. Chạy với `DEBUG=false`
  trong process test vì biến môi trường máy có giá trị không phải boolean;
  không sửa `.env` hoặc nới validation của ứng dụng.
- Admin full suite trên image sạch, không network và chỉ mount tests readonly:
  **612 test: 444 PASS / 168 SKIP**. Các SKIP cần PostgreSQL test riêng.
- API trang 4 trên SQLite và PostgreSQL disposable: **6 PASS / 0 SKIP**;
  gồm fixture có kết nối legacy nhưng không được gán sang customer.
- Admin frontend: **102 PASS**. Python/JS syntax, CSS build, diff check: PASS.
- Browser trang 4: **2 PASS** (1440/390), không JS error, không external request;
  tour trang 3: **2 PASS**, giữ nguyên tiến độ 8 bước.

Bộ Admin chạy trực tiếp trên máy trước đó có 107 failure / 22 error do cấu hình
sandbox được load từ môi trường local (ví dụ 403 `client_not_allowed`), không phải
kết quả của image sạch. Không gỡ sandbox scope hoặc sửa policy để ép test qua.
Lệnh nghiệm thu từ thư mục Admin dùng image đã build, không mount env/instance:

```powershell
$taskTestPath = (Resolve-Path tests).Path
docker run --rm --network none --mount "type=bind,source=$taskTestPath,target=/app/tests,readonly" --entrypoint python vioagencyanalytics-customer-admin:local -m unittest discover -s tests -v
```

Ba service customer healthy. Source trong container đã được đối chiếu hash với
source local. Không đổi schema, không nhập lại DB, không commit/push. Hai bản
source trước deploy nằm trong `.work/customer-integrations-qa/*-before-page4.tgz`
(không chứa env/DB/secrets); test PostgreSQL disposable đã được dừng/xóa. Browser
test chỉ thêm tài khoản/Workspace QA `.invalid`, không chỉnh hoặc xóa dữ liệu cũ.

Nghiệm thu sau lượt tối ưu UX/UI cùng ngày:

- Web: **367 pytest PASS**, 6 deprecation warnings có sẵn. JS syntax, Python
  syntax của script nghiệm thu, hai CSS build và Git whitespace: PASS.
- Browser Kết nối nền tảng: **2 PASS** ở 1440/390, thêm kiểm tra bố cục 1024;
  filter/reload/search nhiều từ, trạng thái lỗi/thử lại, CSRF, scope, literal HTML,
  trạng thái kết nối giả lập trong trình duyệt và menu/header cố định đều PASS.
  Không JavaScript error hoặc request ra dịch vụ ngoài.
- Tour tám bước: **2 PASS** ở 1440/390 sau khi chuyển sang sidebar/theme chung.
- Ba container healthy; hash **8 file** giao diện/runtime trùng source local.
  Log riêng `.work/customer-integrations-polish/`. Lượt UX/UI này không đổi Admin,
  schema DB hoặc cơ chế cấp quyền; kết quả Admin ở trên là nghiệm thu trước đó.
  Không commit/push.
