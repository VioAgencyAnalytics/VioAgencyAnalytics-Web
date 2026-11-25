# Đăng nhập và Workspace — 13/11/2026

Hai trang sử dụng cùng bộ màu navy, nền xanh nhạt và hành động chính đỏ VIO.
Font nhập liệu giữ 16 px; phân cấp riêng tiêu đề, nhãn và phần hướng dẫn.

- Đăng nhập: một nhận diện thương hiệu ở đầu trang, phần giới thiệu và minh họa
  kết nối ở bên trái, form ở bên phải. Google và email có phân cách rõ. Trên
  màn hình nhỏ ưu tiên form, ẩn minh họa; không thu nhỏ cả bố cục desktop.
- Tạo tài khoản, quên/đặt lại mật khẩu, thông báo và tài khoản đã đăng nhập
  dùng chung bố cục. Nút hiện/ẩn mật khẩu giữ nhãn và trạng thái hỗ trợ đọc màn
  hình. Chuyển bước đưa focus đến nội dung đang thao tác.
- Người đã có Workspace thấy danh sách trước; mở Workspace bằng một lần bấm.
  Card hiển thị logo, loại hình, vai trò, website và các thương hiệu có sẵn.
  Có tìm kiếm khi có từ bốn Workspace, hỗ trợ tìm không dấu tiếng Việt.
- Tạo mới là luồng riêng, có quay lại và giữ dữ liệu đang nhập. Người chưa có
  Workspace được mở trực tiếp luồng tạo. Ba bước Thông tin → Khách hàng hoặc
  Thương hiệu → Xác nhận giữ cùng payload và request key của API cũ.
- Agency và Doanh nghiệp có hướng dẫn phù hợp; Doanh nghiệp có thể để trống
  thương hiệu đầu tiên để backend dùng tên Workspace. Website và logo dùng
  preview/cache đã có; không thêm dịch vụ ảnh bên ngoài hoặc thay đổi kiểm tra
  URL ở backend. Khu vực, tiền tệ và múi giờ được gom trong mục có thể mở rộng.
- Dùng mã mời mở dialog riêng. Lỗi và thao tác gửi xác minh hiển thị bên trong
  dialog; giữ kiểm tra xác minh/quyền của backend. Không thêm bước xác minh
  email cho đăng nhập Google hoặc kết nối nền tảng.

Không thay đổi OAuth, session cookie, CSRF, phân quyền, database hoặc logic
connector. Việc không tải được thông tin xem trước của Workspace đang chọn
không chặn danh sách và chức năng tạo mới. Tên người dùng/Workspace/khách hàng
vẫn được đưa vào DOM bằng text, không ghép HTML từ dữ liệu người dùng.

Chuyển động chỉ dùng cho minh họa và hover, tắt theo prefers-reduced-motion.
Logo/font phục vụ từ tài nguyên local. CSS mới chỉ nạp ở login/onboarding.

Kiểm chứng: Web pytest 694 PASS / 1 SKIP; chạy lại nhóm auth/Workspace đạt
84 PASS sau điều chỉnh cuối. Node 39 PASS, gồm năm ca hồi quy mới. UI có
28 kiểm tra responsive ở 320–1920 px và kiểm tra hành vi form, khôi phục,
lọc Workspace, chọn/tạo, logo, đổi tiền tệ/múi giờ và lỗi mã mời. Kiểm tra
chặn URL OAuth không hợp lệ và phục hồi nút Google. CSS build, JS syntax,
PostCSS parse và git diff --check đạt. Dữ liệu UI QA chỉ nằm trong `.work`,
không đưa tài khoản minh họa vào database ứng dụng.

Image Web: `vioagencyanalytics-web:entry-ux-20261113`. Cập nhật riêng Web qua
Compose HTTPS local; backend giữ nguyên. Không commit/push.
