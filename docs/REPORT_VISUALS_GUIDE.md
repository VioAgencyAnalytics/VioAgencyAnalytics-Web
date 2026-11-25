# Thiết kế biểu đồ và báo cáo VIO

## Công cụ hỗ trợ

- `frontend-design`: skill thiết kế từ [Anthropic Skills](https://github.com/anthropics/skills/tree/main/skills/frontend-design), đã cài trong môi trường Codex của người phát triển.
- `vio-report-visuals`: skill riêng cho cách trình bày dữ liệu VIO, bảng KPI, đối chiếu kỳ và kiểm tra bản in. Skill được lưu trong thư mục skills của Codex; không phải thư viện chạy trên server.
- tldraw: plugin đã kết nối, dùng cho sơ đồ có thể chỉnh sửa khi cần thiết kế luồng. Plugin không tự nhúng vào Web và không nhận dữ liệu khách hàng từ báo cáo.

Biểu đồ trong sản phẩm tiếp tục dùng SVG và bộ dựng hiện có tại `static/js/customer/report-charts.js`. Màu nền tảng lấy từ `static/css/customer/platform-brands.css`; không cần dịch vụ thiết kế bên ngoài để khách hàng xem hoặc in báo cáo.

## Hướng trình bày

Giữ Plus Jakarta Sans / Inter hiện có và chữ tiếng Việt. Chữ chỉ số dùng số có cùng độ rộng; cột số căn phải. Nền bảng nhẹ, phần tiêu đề rõ cấp bậc. Màu SEO xanh teal, GA4 cam và GSC xanh dương; trạng thái đạt/chưa đạt luôn kèm chữ, không dựa riêng vào màu.

Biểu đồ xu hướng có một màu nguồn cho kỳ đang xem và đường nét đứt trung tính cho kỳ trước. Đối chiếu theo thứ tự ngày phải ghi rõ hai khoảng ngày và số ngày thực tế. Dữ liệu chưa có là khoảng trống; giá trị 0 vẫn là quan sát hợp lệ.

Biểu đồ cột dùng đường gốc 0. Biểu đồ donut dành cho tỷ trọng có mẫu số xác định và đi kèm số thực tế, tỷ lệ, chú giải. Không dùng góc nhìn 3D làm méo tỷ lệ của cột hoặc lát cắt. Hiệu ứng chiều sâu chỉ dành cho phần minh họa không mang giá trị đo lường.

## Báo cáo SEO gọn

Phần trình bày gọn được dựng từ bản dữ liệu đã chốt, không gọi thêm API nền tảng và không sửa số liệu gốc:

1. Hiệu quả website: bảng GA4/GSC, đối chiếu kỳ, bốn biểu đồ xu hướng và phân bổ phiên.
2. Từ khóa: tách bộ cam kết, ngách và mở rộng; bảng hai cột trên desktop/PDF, lặp tiêu đề khi sang trang. Không cắt bớt dòng để giảm số trang.
3. Bài viết: một URL có một dòng số liệu truy cập. Bài mới và lần cập nhật giữ từng mốc nghiệm thu riêng. Bản thảo vẫn được ghi nhận.
4. KPI: mục tiêu, thực tế, mức hoàn thành và đánh giá; ma trận tiến độ sáu tháng mỗi nhóm cột, mở rộng theo thời hạn dự án. Tháng tương lai giữ dấu —.

Bảng đầy đủ từ từng nguồn và hiệu quả chi tiết của bài viết vẫn có thể mở trên Web. PDF dùng phần tổng hợp gọn. Các nguồn khác ngoài SEO/GA4/GSC giữ phần báo cáo nền tảng của chúng.

GSC average position không được thay thành thứ hạng Spineditor. Lượt xem GA4, phiên Organic Search và lượt nhấp GSC giữ định nghĩa riêng. KPI nghiệm thu dùng ngày xác nhận và phiên bản cam kết, không mặc định bài đã đăng là đã nghiệm thu.

## Kiểm tra trước khi bàn giao

Kiểm tra 1440, 768, 390 và 320 px, tương tác bàn phím, tooltip và chế độ giảm chuyển động. Xuất PDF A4 rồi xem từng trang để phát hiện cắt chữ, mất dòng, chú giải quá nhỏ, ngắt bảng hoặc khoảng trắng thừa. Bộ dữ liệu thử phải tách khỏi dữ liệu khách hàng. Số trang phụ thuộc số từ khóa, bài viết, nguồn và thời hạn dự án; không đặt số trang cố định bằng cách bỏ dữ liệu.
