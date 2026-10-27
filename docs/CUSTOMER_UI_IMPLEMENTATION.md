# Giao diện khách hàng 9 trang

**Cập nhật tiếp theo cùng ngày:** trang 01–02 đã có triển khai tài khoản/Workspace
thật, chạy cổng 8084 và bật bằng feature flag. Xem
[FE, BE, DB của trang 01–02](CUSTOMER_IDENTITY_IMPLEMENTATION.md).
Phần bên dưới mô tả **ứng dụng preview 9 trang cổng 8083**; trạng thái sessionStorage
và các nút mẫu của preview không áp dụng cho hai trang thật.

Ngày triển khai: 26/10/2026. Nguồn thiết kế là 9 file HTML trong ZIP
`stitch_legacy_mock_data_exporter (1).zip` người dùng cung cấp. Đây là phần triển khai
giao diện và điều hướng của kiến trúc self-service, chưa phải backend SaaS hoàn chỉnh.

| Trang | Nội dung | URL |
|---|---|---|
| 01 | Đăng nhập / Đăng ký | `/workspace/login` |
| 02 | Thiết lập Workspace | `/workspace/onboarding` |
| 03 | Tổng quan | `/workspace` |
| 04 | Kết nối nền tảng | `/workspace/integrations` |
| 05 | Dashboard Marketing | `/workspace/dashboard` |
| 06 | Phân tích kênh | `/workspace/channels` |
| 07 | Báo cáo | `/workspace/reports` |
| 08 | Thành viên | `/workspace/members` |
| 09 | Cài đặt | `/workspace/settings` |

Trang 04 được xác định từ nội dung HTML, không dùng tên thư mục Agency Overview.
Trang 05 được dựng từ HTML vì ảnh PNG trong ZIP không hợp lệ.

## Chạy và chỉnh sửa

```sh
python -m uvicorn app.design_preview:app --host 127.0.0.1 --port 8083
npm run build:css
python -m pytest -q
```

Trên Windows dùng `.venv\Scripts\python.exe` nếu chưa kích hoạt virtualenv.
Nếu biến môi trường máy `DEBUG` không phải boolean, đặt `DEBUG=false` cho tiến trình
kiểm thử; không cần sửa `.env` của hệ thống đang chạy.

- Route và danh mục màn hình: `app/routes/customer.py`.
- Layout, menu, nội dung: `templates/customer/`.
- Tương tác: `static/js/customer/workspace.js`.
- Kiểu dáng bổ sung: `static/css/customer/workspace.css`.
- Tailwind riêng: `tailwind.customer.config.cjs`, build bằng `npm run build:customer`.
- Logo từ bản thiết kế, font Plus Jakarta Sans và giấy phép: `static/customer/`.

## Chức năng hoạt động trong giao diện

Điều hướng đủ 9 trang; menu thu gọn trên điện thoại; tìm trang/báo cáo bằng Ctrl+K;
tìm kiếm và lọc thẻ kênh theo nhóm, từ khóa, trạng thái; lọc danh mục nền tảng và mẫu
báo cáo; tab thành viên và ma trận phân quyền; tạo/xem/xóa bản nháp báo cáo cục bộ;
lưu/khôi phục cài đặt và xem trước logo PNG/JPG/WebP tối đa 2 MB.

Tên Workspace, tùy chọn và bản nháp chỉ lưu trong `sessionStorage` với namespace
`vio.customer-preview.v1`. Reload giữ dữ liệu trong tab; đóng phiên tab sẽ mất dữ
liệu này. Các giá trị này không phải tài khoản, membership, role, token hay grant.
Form đăng nhập không nhận mật khẩu; thao tác mời thành viên không gửi email.

## Đưa báo cáo hiện có vào Phân tích kênh

`/workspace/channels/{channel}` là trang chi tiết trong menu mới. Báo cáo hiện có
được nhúng qua iframe cùng nguồn, với `workspace_embed=1` để ẩn menu cũ và căn lại
thanh lọc. Các URL cũ vẫn hoạt động để giữ tương thích và mở cửa sổ riêng.

| Kênh | Báo cáo hiện có |
|---|---|
| Tổng quan | `/overview` |
| SEO & Keywords | `/report/seo` |
| Facebook Ads | `/report/facebook-ads` |
| Facebook Content | `/report/facebook-content` |
| TikTok Ads | `/report/tiktok` |
| YouTube | `/report/youtube` |

Google Ads, GA4, GSC và Google Business Profile chưa có bộ báo cáo tương đương trong
source hiện tại nên trang chi tiết hiển thị trạng thái trống; không dùng dữ liệu
của một kênh khác để thay thế. Các báo cáo mẫu và số liệu thiết kế luôn có nhãn.

## Backend và production

Chưa tích hợp Google/email login mới, tạo Organization trên máy chủ, OAuth provider,
chọn tài sản, job đồng bộ, mời thành viên, cấp quyền, xuất/chia sẻ/lên lịch báo cáo
mới. Các nút tương ứng thông báo rõ trạng thái chưa hỗ trợ. Chức năng xuất file của
các báo cáo cũ vẫn được giữ nguyên.

Ứng dụng preview không có route handoff, đăng nhập backend hoặc xem Published Bundle.
Ứng dụng chính chặn các trang mẫu ở production. Khi customer auth bật, chỉ trang
01–02 và màn hình Workspace đã lưu được mở bằng backend thật. Nếu tắt cờ,
production tiếp tục chuyển tới Admin theo kiểm tra origin hiện có.
Không thay đổi session, cookie, token, grant, revision hoặc database production.
Chưa triển khai container production trong thay đổi này.

## Kiểm tra giao diện tự động

Kiểm thử HTTP nằm trong `tests/test_customer_workspace.py`, bao gồm đủ 9 trang,
đường dẫn giữa các trang, báo cáo nhúng, route không tồn tại và chặn mẫu ở production.
Kiểm tra trình duyệt bằng `scripts/check_customer_workspace_ui.py` yêu cầu Playwright
trong môi trường phát triển và Microsoft Edge có sẵn trên Windows:

```sh
python -m pip install playwright
python scripts/check_customer_workspace_ui.py
```

Chạy preview cổng 8083 trước. Script dùng phiên trình duyệt riêng, không gửi email
hoặc đăng nhập dịch vụ ngoài; lưu ảnh 1440 px / 390 px và kết quả tại
`.work/customer-qa/`. Có thể truyền `--base-url` và `--browser-path` nếu cần.
