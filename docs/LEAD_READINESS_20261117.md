# Bàn giao Lead kiểm thử — 17/11/2026

## Kết luận

Đủ để Lead xem giao diện và kiểm thử nghiệp vụ có hướng dẫn. Chưa thể coi là hoàn tất nghiệm thu mọi connector hoặc sẵn sàng vận hành thương mại. Những kết nối hết hạn cần chủ tài khoản cấp quyền lại; dữ liệu thật cần được đối chiếu với nguồn.

## Đã kiểm tra trên bản đang chạy

- Customer: 19 trang, ba kích thước 1440/390/320 px; 57 kiểm tra bố cục đạt, không có lỗi JavaScript. Các trang kết nối, dashboard, kênh, SEO, báo cáo, thành viên và cài đặt đều mở được.
- Admin: 11 trang, 33 kiểm tra bố cục đạt sau khi sửa phần nút thao tác của Tổng quan tràn ngang trên điện thoại. Bộ lọc 30 ngày hoạt động. Logo chưa có trả trạng thái thiếu và dùng biểu tượng dự phòng.
- Đăng nhập bằng hai tài khoản Lead đã có qua HTTPS Cloudflare, đăng xuất và truy cập API được phân quyền: đạt. Cookie Secure/HttpOnly, CSRF và chặn truy cập khi chưa đăng nhập được kiểm tra.
- Google Sign-in và khởi tạo OAuth GSC, GA4, YouTube, Facebook dùng callback public mới đúng cấu trúc. Chủ ứng dụng xác nhận lưu Google/Meta ngày 17/11. Chưa thay thế việc Lead tự hoàn tất consent và nghiệm thu số liệu nguồn.
- Web Python: 710 đạt, 1 bỏ qua trên bản phát hành hiện tại. JavaScript Customer: 61 đạt. JavaScript Admin: 136 đạt. Build CSS và kiểm tra whitespace đạt.
- Báo cáo SEO mẫu bốn trang dùng dữ liệu kiểm thử riêng, có đủ 76 từ khóa, 16 URL bài viết và chín KPI dự án. Bảng có đường kẻ đen, phân biệt dữ liệu thiếu với 0 và so kế hoạch/thực hiện từng tháng.

Một lần mở màn hình nguồn trả 409 khi tự lấy danh sách tài sản của kết nối cần kiểm tra lại. Đây là đầu việc cấp quyền/chọn tài sản cần xử lý khi thử nguồn thật; không coi toàn bộ kết nối đã hoạt động chỉ vì trang mở được.

## Connector còn cần nghiệm thu

Các quan sát sau lấy từ Operations API của toàn hệ thống, không đồng nghĩa tất cả đều thuộc khách hàng Lead đang chọn:

| Nguồn | Quan sát hiện tại | Việc tiếp theo |
| --- | --- | --- |
| Facebook Content | Có 15 bản đồng bộ trong 30 ngày; có kết nối yêu cầu cấp quyền lại và chỉ số chưa được nguồn trả đủ | Kết nối lại, chọn Fanpage, đồng bộ kỳ cần xem và đối chiếu chỉ số |
| GA4 | Có một bản đồng bộ; kết nối cần cấp quyền lại; kỳ lưu có ngày thiếu | Chọn đúng property, đồng bộ đủ kỳ hiện tại và đối chiếu |
| GSC | Có một bản đồng bộ; có kết nối chưa chọn tài sản và kết nối cần cấp quyền lại | Chọn website đúng khách hàng rồi đồng bộ hai kỳ |
| YouTube | Có một bản đồng bộ; cần cấp quyền lại, độ phủ ngày chưa đầy đủ | Chọn đúng kênh, kiểm tra ngày và số liệu với YouTube Analytics |
| Facebook Ads | Có cấu hình ứng dụng; năm tác vụ gần đây lỗi `provider_unavailable`, chưa có bản đồng bộ thành công | Kiểm tra quyền/ad account và lỗi nguồn, thử lại sau khi cấp quyền |
| Instagram, Google Ads, Business Profile | Có cấu hình; chưa có bản đồng bộ thành công để nghiệm thu | Lead kết nối tài sản có quyền; kiểm tra yêu cầu API/quyền ứng dụng khi phát sinh lỗi |
| TikTok Ads | Chưa có cấu hình ứng dụng Vio | Hoàn tất cấu hình và quyền API trước khi thử |

## Trình tự Lead nên thử

1. Đăng nhập Web bằng tài khoản Vio được cấp, chọn đúng Workspace và khách hàng/thương hiệu.
2. Mở Kết nối nền tảng. Với nguồn hết hạn, chọn Kết nối lại rồi tự cấp quyền trên Google/Meta. Tài khoản nguồn phải có quyền đối với website, property, Fanpage hoặc kênh cần xem.
3. Chọn khoảng ngày đã kết thúc; đồng bộ kỳ đang xem và kỳ đối chiếu. Kiểm tra trạng thái công việc hoàn thành trước khi đối chiếu.
4. Mở trang nền tảng, Tổng quan và Dashboard. So cùng tài sản, ngày, múi giờ và định nghĩa chỉ số với nguồn; giữ dấu — cho dữ liệu chưa có.
5. SEO: nhập file Spineditor có ngày đo; dùng GSC cho truy vấn và GA4/GSC cho hiệu quả bài viết. Bài tự lấy từ website cần duyệt và xác nhận nghiệm thu.
6. KPI: nhập cam kết từng tháng theo hợp đồng, kiểm tra nguồn thực tế và trạng thái đánh giá. Mục “lưu lượng tăng thêm” cần thống nhất chỉ số và mốc gốc; hiện hệ thống đo tổng trong kỳ.
7. Tạo báo cáo mới, kiểm tra bảng và biểu đồ rồi chọn In / Lưu PDF. Bản lưu cũ giữ dữ liệu tại thời điểm tạo.
8. Admin: chọn 30 ngày để xem lịch sử nếu 24 giờ gần nhất không có tác vụ. Kiểm tra nguồn, trạng thái kết nối, lỗi tại bước nào và chất lượng snapshot.

## Phạm vi và giới hạn

Chưa thử thao tác xóa dữ liệu, đổi quyền hoặc sửa cam kết trên dự án thật trong lượt rà soát này. Các bài kiểm thử nghiệp vụ dùng dữ liệu riêng; Lead cần xác nhận kết quả trên dữ liệu thật. Phiên Cloudflare là link tạm, cần máy, Docker và tiến trình tunnel tiếp tục chạy. Link và thông tin đăng nhập được quản lý trong thư mục `.work` riêng, không commit/push.
