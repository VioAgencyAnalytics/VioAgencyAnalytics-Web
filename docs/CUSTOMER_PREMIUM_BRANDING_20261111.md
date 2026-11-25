# Customer UI — nhận diện nền tảng và giao diện SaaS

## Phạm vi

Theo lựa chọn đã chốt: SaaS cao cấp, tinh gọn; chuyển động nhẹ và chiều sâu 3D có chọn lọc. Áp dụng vào Customer Web, không thay đổi Primary Admin hay quyền kết nối nguồn.

- Nền Workspace có sắc xanh/xám và các lớp màu nhẹ, thay nền trắng phẳng. Tổng quan và Dashboard có vùng tiêu đề xanh đậm; thẻ dữ liệu dùng nền sáng, chữ rõ và số tabular.
- Kết nối và Phân tích kênh có thẻ theo màu thương hiệu. Trang nguồn và bìa báo cáo dùng màu riêng của Facebook, Meta Ads, Google Ads, GA4, Search Console, YouTube, Instagram, Business Profile và TikTok.
- Màu lỗi, cảnh báo và trạng thái KPI giữ ý nghĩa riêng; không dùng màu thương hiệu để biểu thị tăng trưởng hay hoàn thành mục tiêu.
- Nút thu gọn menu trên desktop tạo một dải biểu tượng có tên truy cập và tooltip. Tùy chọn chỉ lưu trên trình duyệt, có thể mở rộng lại. Menu và tìm kiếm nhanh giữ cấu trúc quen thuộc.
- Desktop giữ sidebar và topbar tại vị trí riêng khi cuộn. Ở màn hình nhỏ, menu chuyển về bố cục dành cho thiết bị di động; không ép một thanh biểu tượng desktop lên điện thoại.

## Logo thật, lưu tại ứng dụng

`app/customer_platform_brands.py` là danh mục nhận diện dùng chung cho Jinja và JavaScript. Logo gốc từ nguồn Google, Meta và TikTok nằm trong `static/customer/platforms/`; nguồn, bản gốc và SHA-256 nằm trong `sources.json`, cùng `NOTICE.md`.

Không dùng ký tự “f”, biểu tượng Material hay ảnh tạo sinh để thay logo nền tảng. Instagram dùng glyph đen chính thức dung lượng nhỏ, cùng nền hồng/tím của giao diện. Meta Ads dùng lockup Meta gốc. SEO & Keywords là nhóm phân tích nội bộ, dùng biểu tượng phân tích chung thay vì giả làm một nền tảng bên ngoài.

Logo giữ tỉ lệ và màu gốc; không gắn filter đổi màu. Khi ảnh không tải được, hiển thị tên rút gọn bên cạnh tiêu đề nguồn. Không gọi dịch vụ logo bên ngoài trong phiên người dùng và không đưa thông tin tài khoản vào URL ảnh.

## Chuyển động, 3D và khả năng sử dụng

Hiệu ứng chiều sâu chỉ nằm ở khối giới thiệu kết nối, với bóng đổ và perspective CSS. Chuyển động vào trang/hộp thoại ngắn, không lặp; hover nâng thẻ nhẹ trên thiết bị hỗ trợ chuột. Không cài thư viện WebGL, không thêm nền chuyển động liên tục.

`prefers-reduced-motion` tắt chuyển động và perspective trang trí. Form, phím Tab, tên truy cập, nút đóng và focus outline vẫn có. Nội dung chính và số liệu không bị animation che hoặc trì hoãn. Bản in bỏ bóng/nền trang trí; nhận diện nguồn vẫn hiện trên bìa báo cáo.

Typography giữ Plus Jakarta Sans cho tiêu đề và Inter cho nội dung; cỡ chữ theo rem, không ép thu nhỏ toàn trang. Header dùng grid bốn cột khi có nút thu menu; trở về ba/hai cột khi nút không hiển thị.

## Kiểm chứng

- Candidate Docker: **653 pytest PASS, 1 SKIP**, cùng các cảnh báo deprecation đã có.
- JavaScript/JSDOM: **21 PASS**, gồm chọn kỳ, số thập phân, null/0, form đối chiếu, đổi logo, fallback ảnh và thu/mở menu khi trình duyệt chặn storage.
- Build CSS, parse CSS và cú pháp Python: PASS. `git diff --check`: PASS; chỉ có thông báo LF/CRLF của Git.
- PostgreSQL cách ly: **30 kiểm thử báo cáo/KPI PASS**; backend không thay đổi trong đợt giao diện này.
- Clone dữ liệu thật trên mạng Docker không Internet: **13 trang PASS**, so sánh kỳ và tương tác Tổng quan/Dashboard PASS. GET không gọi provider, không tự sync hoặc ghi KPI.
- Kết quả rollout và kiểm tra **16 trang qua HTTPS** được lưu trong Admin `.work/report-periods-20261111/deployment-result.json`. Chỉ Web được recreate; origin, env, cổng, mount, schema và hash dữ liệu nghiệp vụ giữ nguyên. Không commit/push.

Công cụ Computer Use bị timeout nên chưa hoàn tất kiểm tra hình ảnh/pixel trên trình duyệt người dùng. Kiểm tra HTML, CSS, DOM và HTTP không được coi là nghiệm thu hình ảnh trên mọi kích thước màn hình.

Các nguồn chưa có bản lưu đúng kỳ vẫn hiển thị trạng thái thiếu dữ liệu. Thiếu kỳ đối chiếu không được thay bằng số 0 hoặc một kỳ khác. Việc Lead cấp quyền nguồn thật, Meta App Review/Tester và callback Meta của domain chia sẻ vẫn cần nghiệm thu riêng; đổi giao diện không thay thế các bước này.

Phần lịch, đối chiếu và mục tiêu KPI: xem `CUSTOMER_PERIOD_COMPARISON_AUDIT_20261111.md`.
