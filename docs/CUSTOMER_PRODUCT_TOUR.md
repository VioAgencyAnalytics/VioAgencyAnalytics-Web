# Tổng quan Workspace và hướng dẫn 8 bước

Ngày triển khai: 27/10/2026.

## Tham khảo AgencyAnalytics

Đã đọc trang chủ, [Getting Started Guide](https://help.agencyanalytics.com/en/articles/13890222-getting-started-guide)
và Knowledge Base qua connector AgencyAnalytics. Tài liệu mô tả quản lý khách hàng,
kết nối nguồn, dashboards, báo cáo, branding và quyền người dùng.

Công cụ trình duyệt trong phiên này không có browser/native connection, nên chưa
quan sát trực tiếp tour sau đăng ký trong tài khoản AgencyAnalytics. Không khẳng định
đây là bản sao chính xác tám bước của họ. Tour VIO áp dụng mô tả người dùng về
spotlight + tooltip, với nội dung phù hợp chín trang đã thiết kế.

## Hành vi đã triển khai

- Tạo/chọn/tham gia Workspace thành công đưa đến `/workspace`.
- `/workspace` yêu cầu đăng nhập và Workspace đang chọn; nếu thiếu sẽ chuyển về
  login/onboarding. Trang Tổng quan hiển thị khách hàng, số thành viên, thông tin
  Workspace từ Admin DB. Không dùng dữ liệu Marketing mẫu.
- Tour tự mở cho mỗi tài khoản/Workspace chưa xem, hoặc tiếp tục tour đang dở.
  Có 8 bước: Workspace, khách hàng, kết nối nền tảng, Dashboard, Phân tích kênh,
  Báo cáo, Thành viên, Cài đặt. Bấm vùng nổi bật hoặc Tiếp tục để sang bước kế.
- Có Quay lại, Để sau, Escape, hoàn tất và xem lại. Dialog modal giữ focus; vùng
  nổi bật theo viewport/scroll; trên mobile menu cuộn ngang, tooltip ở dưới.
- Tiến độ chỉ được thay đổi sau khi backend lưu thành công. Lỗi lưu giữ nguyên
  bước hiện tại và hiển thị thông báo; không tự đánh dấu hoàn tất.
- “Hoàn tất hướng dẫn” chỉ là đã xem tour, không đồng nghĩa đã kết nối nguồn hay
  tạo báo cáo. Menu chức năng chưa triển khai mở giải thích trạng thái, không đi
  vào bản preview hoặc dữ liệu báo cáo của khách hàng cũ.
- Thành viên dẫn về màn hình thiết lập và mã mời hiện có. Cài đặt hiện chỉ xem
  thông tin, chưa sửa. Tour không tự cấp quyền, gửi lời mời hoặc kết nối OAuth.

## Backend và DB

Migration 10 `customer_workspace_product_tour` thêm `customer_product_tours`:
khóa `(workspace_id, account_id, version)`, `step` 0–7,
`status` active/dismissed/completed, `updated_at`.

GET workspace detail trả `tour` và `member_count`; mặc định tour là new, step 0.
POST `/api/customer/workspaces/{id}/tour` qua BFF, CSRF/Origin và service auth
hiện có. Admin xác minh session và membership đang hoạt động trong transaction;
không nhận account ID tùy ý từ trình duyệt. Bản tour hiện tại là version 1.

Trước khi nâng cấp local đã tạo pg_dump ở
`.work/customer-dev/vio-before-tour-20261027.dump` (Git ignored).
Không thay đổi DB báo cáo cũ hoặc volume khác.

## Kiểm tra

- `tests/test_customer_auth.py`: bảo vệ route, selected Workspace, CSRF, allowlist.
- Admin `test_customer_identity.py`: lưu/đọc lại, isolation giữa tài khoản và
  Workspace, validation, membership/session bị thu hồi, chạy SQLite và PG riêng.
- `scripts/check_customer_tour_ui.py`: đăng ký, tạo Workspace, 8 bước, bỏ qua,
  reload, quay lại, hoàn tất, replay, logout/login, chọn Workspace, layout 1440/390.
  Script tạo tài khoản QA có tên rõ trong DB local, không gửi email.
- `scripts/check_customer_identity_ui.py` đã cập nhật theo điều hướng mới.

Trang 4–9 chưa triển khai đầy đủ; các nút tương ứng chưa thực hiện kết nối, đồng bộ,
phân tích hoặc tạo báo cáo cho customer.

Kết quả 27/10/2026: Web 345 PASS (đặt DEBUG=false cho môi trường test);
Admin Python 588 bài, 538 PASS / 50 SKIP có điều kiện môi trường;
Admin frontend 102 PASS. Các test customer gồm schema PostgreSQL dùng riêng.
Browser acceptance 1440px và 390px đều PASS, không lỗi JavaScript; đã xem ảnh
spotlight desktop/mobile. Chạy trực tiếp FE → BFF → Admin → PostgreSQL local,
gồm tạo Workspace, tour 8 bước, lưu/reload, bỏ qua, replay và đăng nhập lại.
Ảnh và kết quả trong `.work/customer-tour-qa/` (Git ignored).
