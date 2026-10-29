# Trang 08–09 — Thành viên và Cài đặt

Thiết kế theo hai bản Stitch `(4)` và `(5)` do người dùng cung cấp, dùng chung
header, sidebar cố định, font Inter/Jakarta và theme của Tổng quan/Dashboard.
URL có xác thực: `/workspace/members`, `/workspace/settings` tại cổng 8084.
Phân tích kênh và Báo cáo customer tiếp tục là phần triển khai sau.

## Thành viên

Danh sách, số thành viên được cấp quyền, lời mời, thời hạn và hoạt động đọc từ DB.
Không dựng người dùng, gói 10 chỗ, chứng nhận HIPAA, trạng thái online hoặc nhật ký
thiết bị/IP giả. Tìm tên/email không dấu, lọc vai trò/trạng thái, sắp xếp, tabs bàn
phím, ma trận quyền và bảng cuộn riêng trên mobile.

- Tất cả thành viên đang có quyền có thể xem đội ngũ đang hoạt động. Chỉ Owner/Admin
  xem lời mời, hoạt động Workspace và thành viên bị thu hồi.
- Owner/Admin đã xác minh email tạo mã mời theo email chính xác. Owner mời Admin,
  Member, Viewer; Admin chỉ mời Member/Viewer. Không tự gửi email mời. Mã chỉ xuất
  hiện một lần trong dialog, xóa khỏi DOM khi đóng, không lưu browser storage.
- Người nhận xác minh email rồi dùng mã trên trang onboarding. Giữ hạn 7 ngày,
  đúng email, một lần sử dụng. Chặn lời mời trùng đang chờ hoặc thành viên hiện có.
  Mất response cần kiểm tra danh sách trước khi tạo lại; không tự retry tạo mã.
- Thu hồi mã chưa sử dụng; không lấy lại mã cũ từ hash. Mã tham chiếu công khai
  khác credential được dùng để tham gia Workspace.
- Đổi vai trò và thu hồi quyền dùng version để chặn ghi đè đồng thời. Không đổi
  quyền bản thân/Owner; Admin không quản lý Admin khác hoặc cấp vai trò Admin.
  Thu hồi membership không xóa account/Workspace khác, xóa selection của Workspace
  đó và vô hiệu scope đang chọn trong các session liên quan.
- Chưa có khôi phục membership đã bị thu hồi hoặc chuyển chủ sở hữu trên UI.
  Không nới quy tắc join cũ để cho mã mới tự phục hồi membership bị revoke.
- Hoạt động là 100 event Workspace gần nhất có actor/time/action, không phải toàn
  bộ nhật ký đăng nhập của account. Không lộ hash phiên, password, code hay provider token.

## Cài đặt

Owner/Admin sửa tên Workspace, website, quốc gia, múi giờ, tiền tệ, tên doanh nghiệp,
default period (7/30/90 ngày, tháng này/tháng trước), so sánh kỳ trước, ngày bắt đầu
tuần và thông tin thương hiệu. Member/Viewer đọc; backend kiểm tra lại quyền.
Workspace ID bất biến, tên Workspace không bị giả là unique ID.

Cài đặt lưu thật ở Admin/PostgreSQL, không localStorage/sessionStorage. Nút lưu chỉ
bật khi khác baseline; có Ctrl+S, hủy, thanh nhắc lưu, xác nhận rời trang/switch
Workspace và conflict version 409 giữ biểu mẫu để đối chiếu. Thay tiền tệ/múi giờ
có xác nhận, không chuyển đổi lịch sử hoặc sửa published report/dataset.

Default period/comparison được áp dụng khi mở lại Tổng quan/Dashboard. Bộ lọc URL
Dashboard hợp lệ ưu tiên hơn mặc định. Múi giờ/tiền tệ được lấy từ Workspace hiện tại.
Week-start được lưu cho reader/report hỗ trợ trong tương lai, không giả thay đổi
aggregation khi chưa có analytics API. Không bật ngôn ngữ chưa được dịch.

Thương hiệu lưu text và HEX color; preview dùng `textContent`, chỉ có placeholder
“—”, không có KPI mẫu. Đây là bố cục minh họa, chưa đưa vào báo cáo legacy/published.
Logo upload, chuyển Owner và xóa Workspace chưa mở; không có nút lưu giả hoặc SVG
upload chưa kiểm tra. Không nhúng URL ảnh Stitch/ảnh đại diện từ dịch vụ ngoài.

## API, schema và ranh giới

Web BFF chỉ thêm GET `workspaces/{id}/members|settings`, POST `.../settings`,
`.../members/{account}/role|remove`, `.../invitations/{ref}/revoke`. Invite dùng
endpoint cũ. POST cần Origin/CSRF và cookie identity; ID/đường dẫn allowlist chính
xác, không thêm proxy tổng quát. Private Admin tương ứng kiểm tra service/session,
account, membership, Workspace active, Workspace đang chọn trong transaction.

`kdh/customer_workspace.py` sở hữu policy/read/write, dùng CustomerIdentity sẵn có.
Migration **12** chỉ thêm `customer_workspace_profiles`, `customer_membership_versions`,
`customer_invitation_refs` và index scoped. Không thay migration 1–11 hoặc các bảng
legacy. Ref cũ được backfill từ digest, ngày tạo chưa biết giữ null; raw code không
được khôi phục. New ref là UID. Workspace/member version mặc định 1, write tăng version.
Không ghi vào grants, data sources, datasets, bundles hoặc các revision báo cáo.

Trước rollout có dump private trong `.work/customer-workspace-admin-qa/`, hash image
cũ và rehearsal migration trên DB khôi phục độc lập: 47 bảng cũ giữ nguyên count/hash,
startup lặp PASS. Không rollback bằng cách xóa schema/data; image cũ vẫn tương thích
với các bảng thêm mới nhưng không hiểu version/settings mới, cần đối chiếu trước khi
quay về. File dump có dữ liệu riêng, được Git/Docker ignore; không đưa lên GitHub.

## Kiểm thử

- Web `tests/test_customer_auth.py`: auth/page gate, BFF allowlist, CSRF/cookie identity,
  không mở Channels/Reports/legacy API. Các test cũ giữ nguyên mục đích; Settings nay
  là trang thật nên smoke/tour kiểm tra điều hướng thay dialog placeholder.
- Admin `tests/test_customer_workspace.py`: scope, role, version, validation, lời mời,
  revoke, session/account/membership, no legacy write; SQLite và PostgreSQL disposable.
  Test identity cũ giữ expiry/replay và thêm denial lời mời vào member đã tham gia.
- Browser `scripts/check_customer_workspace_admin_ui.py`: hai account QA `.invalid`,
  invite/join/role/revoke/readonly/CSRF, settings persist/defaults, preview XSS literal,
  dirty navigation, concurrent version, 1440/1024/390 và logout. Email xác minh chỉ
  fixture DB cho đúng QA ID/email trong script, không thêm endpoint bỏ qua xác minh,
  không gửi email/provider thật. Không lưu cookies hoặc mật khẩu vào artifact.

Log, backup và screenshot nằm trong `.work/customer-workspace-admin-qa/` của mỗi repo.

Kết quả 28/10/2026 trên bản Docker đã cập nhật:

| Kiểm tra | Kết quả |
|---|---|
| Web pytest | 376 PASS, 6 deprecation warnings có sẵn |
| Admin đầy đủ, image sạch/không network | 626 test: 451 PASS / 175 SKIP có điều kiện |
| Customer team/settings SQLite + PostgreSQL disposable | 14 PASS / 0 SKIP |
| Platform/migration SQLite + PostgreSQL disposable | 12 PASS / 0 SKIP |
| Admin frontend | 102 PASS |
| Browser Thành viên/Cài đặt, 1440/1024/390 | 6 PASS, không JS error/external request |
| Tour tám bước, 1440/390 | 2 PASS |
| Migration restore 11→12, 47 bảng cũ, startup lặp | PASS, count/hash không đổi |
| Runtime/source | 19 file Web + 4 file Admin trùng hash |
| Python/JS syntax, CSS build, Git whitespace | PASS |

Lượt full PostgreSQL trước đó chạy 626 test có 2 failure do test inventory vẫn
liệt kê migration đến 11. Đã cập nhật danh sách đến 12, giữ toàn bộ kiểm tra
snapshot/data và chạy lại cả nhóm platform trên hai DB đạt 12 PASS; full image
không network sau sửa đạt như bảng trên. Không giảm policy hoặc xóa test.
Những SKIP của full suite cần DB/cờ runtime tương ứng; nhóm có DB test riêng
ở trên đã chạy không skip. Không dùng DB thật cho bộ unit test.

DB customer runtime hiện migration 12, ba service healthy; PostgreSQL dùng cho
rehearsal/test đã được dọn riêng. Không sửa/xóa account thật, không gửi email,
không gọi provider/sync, không commit/push.
