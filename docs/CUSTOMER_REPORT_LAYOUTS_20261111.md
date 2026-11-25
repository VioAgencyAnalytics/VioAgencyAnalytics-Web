# Mẫu báo cáo theo nền tảng — 11/11/2026

Web Customer dùng chín bố cục báo cáo từ dữ liệu đã đồng bộ. Đã cập nhật Web
Docker bằng `vio-web-report-layouts:20261111-v3`; Admin, Customer backend,
origin/callback, cấu hình môi trường, cổng, network và volume không đổi.
Không thêm migration, gọi API nhà cung cấp hoặc sửa dữ liệu/KPI khách hàng.

## Bố cục

| Nguồn | Trọng tâm trình bày |
|---|---|
| Facebook Content | Bìa editorial, KPI nội dung, định dạng, bài nổi bật, nhịp đăng, chi tiết và liên kết bài |
| Facebook Ads | Lead / chi phí mỗi Lead / ngân sách, chỉ số hỗ trợ, biểu đồ chi phí, chiến dịch theo ngày |
| Google Ads | Chuyển đổi / chi phí / CPC, dải hiển thị–nhấp–CTR độc lập, xu hướng và chi tiết chiến dịch |
| TikTok Ads | Khối chuyển đổi nổi bật, dải chỉ số, nhịp chuyển đổi và tài khoản theo ngày |
| GA4 | Người dùng / phiên / lượt xem / tương tác, xếp hạng kênh và trang, xu hướng truy cập |
| GSC | Lượt nhấp / hiển thị / CTR / vị trí, biểu đồ và bảng truy vấn |
| YouTube | Phút xem / lượt xem / đăng ký mới / thời lượng TB, thẻ video và liên kết từ ID hợp lệ |
| Instagram | Nhóm chỉ số tích lũy, nội dung nổi bật theo lượt thích, nhịp xuất bản |
| Business Profile | Ba hành động gọi / website / chỉ đường, hiển thị di động Search/Maps, tương tác theo ngày |

Giữ nhận diện Vio, logo nguồn gốc đã có, bìa theo màu nền tảng và các lớp trang
trí có chiều sâu. Không dùng phối cảnh 3D cho dữ liệu biểu đồ. Không tạo ảnh,
tiêu đề video, ảnh bài đăng, doanh thu hoặc nhận xét chưa có trong DTO.
Các chỉ số hiện hữu đều được giữ. Xếp hạng chỉ trong những hàng đã tải,
ghi số hàng/giới hạn, không cộng các chiều dữ liệu thành KPI toàn tài khoản.

## So sánh và KPI

- Giữ bộ chọn ngày, tháng bất kỳ, 7/30/90 ngày, kỳ trước cùng số ngày,
  cùng kỳ tháng trước và kỳ đối chiếu tùy chỉnh. Các giới hạn cũ giữ nguyên.
- Hiển thị rõ ngày và số ngày của hai kỳ. Cảnh báo khi hai kỳ dài khác nhau.
  Thẻ so sánh có thực tế, đối chiếu, thanh song song, chênh lệch tương đối
  hoặc điểm phần trăm; mốc so sánh bằng 0 không tạo phần trăm vô hạn.
- Chuỗi ngày của kỳ đối chiếu chỉ được chuyển từ DTO đã kiểm tra scope,
  asset, connection/version, đơn vị và tiền tệ. Biểu đồ chung ghép theo thứ
  tự ngày của mỗi kỳ, dùng nét đứt cho kỳ cũ, không nối qua ngày thiếu.
- Không so sánh tăng trưởng với bộ đếm lifetime/stock. Không quy đổi tiền
  tệ, trung bình tỷ lệ, cộng người duy nhất hoặc lấp null bằng 0.
- Mục tiêu có thực tế, mức tối thiểu/giới hạn tối đa, trạng thái và bullet
  chart có vạch mục tiêu. Vượt chi phí không mang màu đạt chỉ tiêu.
  Kỳ chưa kết thúc vẫn so với mục tiêu đầy đủ, không tự chia theo ngày.
- Các thao tác sync và lưu mục tiêu giữ endpoint, quyền, CSRF và kiểm tra
  version hiện hữu. GET báo cáo/preview không gọi provider.

## In/PDF và kiểm chứng

Vẫn sử dụng chức năng In/PDF của trình duyệt. Bản in A4 có bìa gọn, màu nguồn,
biểu đồ SVG, ngắt trang, lặp đầu bảng và nội dung phương pháp được mở.
Trước in, bảng được dựng lại bằng toàn bộ hàng đã tải, không theo bộ lọc/trang
đang xem. Giới hạn snapshot tối đa 200 hàng không bị diễn giải thành dữ liệu
đầy đủ của nhà cung cấp.

- Full Web pytest: **666 PASS, 1 SKIP**. Sau chỉnh bố cục cuối, nhóm báo cáo,
  so sánh, KPI và Content: **71 PASS**.
- Toàn bộ Node `.test.cjs`: **24 PASS**; Python/JS syntax, CSS build và
  `git diff --check`: PASS. Build có cảnh báo cơ sở Browserslist cũ.
- Native browser kiểm tra responsive chín nguồn tại 390px: không tràn toàn
  trang; bảng/biểu đồ cuộn trong vùng riêng. Có kiểm tra bìa, KPI, chart và
  không có lỗi console trong các lần kiểm tra chính.
- Chín PDF minh họa được dựng qua dịch vụ PDF hiện hữu, render Poppler và
  kiểm tra text bounds. Đây là kiểm tra trình bày với fixture được gắn nhãn,
  không phải nghiệm thu số liệu thật đồng loạt của chín nhà cung cấp.
- Candidate và runtime: health/login, guest report denial, asset hashes PASS.
  Các container khác và cấu hình Web được đối chiếu trước/sau.

Bằng chứng, preview, PDF và ảnh riêng tư nằm trong
`.work/report-layouts-20261111/` (đã ignore). Không đưa fixture, cấu hình riêng,
credential hoặc ảnh minh họa vào image dịch vụ. Không commit/push.

## Tham chiếu thiết kế

Chọn cách phân cấp báo cáo, bố trí chỉ số, biểu đồ và so sánh; không sao chép
nguyên mẫu hoặc áp thêm chỉ số ngoài dữ liệu Vio có.

- [AgencyAnalytics Facebook](https://agencyanalytics.com/templates/reports/facebook)
- [AgencyAnalytics GA4](https://agencyanalytics.com/templates/reports/google-analytics)
- [AgencyAnalytics YouTube](https://agencyanalytics.com/templates/reports/youtube)
- [AgencyAnalytics Business Profile](https://agencyanalytics.com/templates/reports/google-business-profile)
- [Whatagraph Facebook Ads](https://whatagraph.com/templates/facebook-ads-report)
- [DashThis Google Ads](https://dashthis.com/adwords-report-template/)
- [DashThis TikTok Ads](https://dashthis.com/tiktok-ads-report-template/)
- [DashThis Instagram](https://dashthis.com/instagram-report-template/)
- [Databox GSC](https://databox.com/dashboard-examples/google-organic-search-performance)
- [AgencyAnalytics date comparisons](https://help.agencyanalytics.com/en/articles/4603849-create-and-manage-custom-dashboards)
- [Whatagraph goal widgets](https://help.whatagraph.com/en/articles/6215833-how-to-create-a-goal-widget)
