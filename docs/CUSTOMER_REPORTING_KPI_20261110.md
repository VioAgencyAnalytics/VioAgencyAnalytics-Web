# Nghiệm thu kỳ báo cáo và mục tiêu KPI — 10/11/2026

Đã cập nhật Docker Customer Web và Customer backend tại `https://localhost:8444`. Admin console và các container dự án khác giữ nguyên. Chưa commit hoặc push.

## Người dùng thao tác

1. Chọn Workspace và khách hàng/thương hiệu có tài khoản nguồn.
2. Vào **Báo cáo**, mở nền tảng. Với nguồn đã chọn tài khoản nhưng chưa có dữ liệu, dùng **Chọn kỳ & đặt KPI**.
3. Chọn 7/30/90 ngày đã kết thúc, tháng này, tháng trước, một tháng bất kỳ hoặc khoảng ngày tùy chỉnh (tối đa 90 ngày).
4. Nếu chưa có bản dữ liệu đúng kỳ, Owner/Admin nhấn **Đồng bộ kỳ này**. Xem, chuyển kỳ hoặc in không tự gọi nền tảng.
5. Nhấn **Đặt mục tiêu KPI** / **Sửa mục tiêu**: nhập chỉ tiêu tối thiểu hoặc giới hạn tối đa, rồi lưu. Giá trị phần trăm nhập từ 0 đến 100; hỗ trợ dấu phẩy thập phân. Để trống để bỏ mục tiêu.
6. Xem thực tế, mục tiêu, chênh lệch, tỷ lệ và trạng thái ở **So sánh KPI**; cùng bảng xuất hiện trong bản In/PDF. Viewer chỉ xem.

Mục tiêu thuộc đúng Workspace, khách hàng, nền tảng, tài khoản và khoảng ngày. Không tự mang mục tiêu từ tháng/kỳ khác sang. Tháng đang diễn ra dùng dữ liệu đến ngày đã kết thúc của nguồn và giữ nguyên toàn bộ mục tiêu tháng; kỳ tương lai cho phép nhập kế hoạch trước. Không chia mục tiêu theo số ngày hoặc tự thay `null` thành 0.

Ngân sách/CPC/vị trí trung bình mặc định là giới hạn tối đa. Tỷ lệ sử dụng giới hạn không gọi là phần trăm hoàn thành. Mục tiêu bằng 0 không tính tỷ lệ chia cho 0; khác tiền tệ không tự quy đổi hoặc so sánh. Tương tác tích lũy/follower tại mốc quan sát giữ đúng nghĩa.

Áp dụng chung cho 9 connector hiện có: Facebook Content, Facebook Ads, Instagram, GA4, Search Console, Google Ads, YouTube, Business Profile và TikTok Ads. Mỗi nguồn cho đặt các metric đã đăng ký trong mapping của nguồn, không nhận biểu thức hoặc metric tùy ý từ trình duyệt.

## Bằng chứng kiểm thử

| Kiểm tra | Kết quả |
| --- | --- |
| Toàn bộ pytest Web, trên máy và trong image mới | 554 PASS, 6 cảnh báo deprecation hiện có |
| Backend tập trung trên SQLite và PostgreSQL dùng riêng | 88 PASS / 55 subtest; thêm 4 PASS cho rollback batch và bản lưu cũ ngoài giới hạn lịch sử |
| Backend trong image, unittest mục tiêu | 30 ca, 15 PASS / 15 PostgreSQL skip; PostgreSQL đã chạy riêng ở hàng trên |
| Node định dạng số, chọn kỳ và chuẩn hóa mục tiêu | 9 PASS |
| Trình duyệt với fixture | 9 nguồn; lưu/mở lại mục tiêu, ngày/tháng/kỳ tương lai, xung đột phiên bản, quyền Viewer, sync đúng ngày đã kết thúc, chuyển giữa phân tích Facebook và báo cáo: PASS |
| Responsive và PDF | 1440/1280/768/390px, không lỗi JS; hai báo cáo PDF được render và kiểm tra bố cục |
| Docker thật | HTTPS tin cậy gốc, 16 bài Fanpage đã lưu, chọn đúng kỳ giữ cùng snapshot và giá trị KPI; mở form trên mobile: PASS |
| Build / cú pháp / diff | CSS build, Python compile, JS syntax, `git diff --check`: PASS |
| Quét secret | Không tìm thấy giá trị secret thật trong 892 file text Git nhìn thấy tại lần quét; `.work` được ignore |

Kiểm tra thật chỉ đọc snapshot: không consent, không gọi provider để đồng bộ thêm, không lưu mục tiêu thử vào dữ liệu khách hàng. Fixture và database thử không dùng dữ liệu vận hành. Đây là kiểm thử có phạm vi cho Customer/KPI, không phải tuyên bố toàn bộ Admin legacy regression đã đạt; xem các tồn tại trước đợt này trong `CUSTOMER_CONNECTORS_VALIDATION_20261109.md`.

## Nâng cấp và phần còn cần nghiệm thu

- Migration 18 thêm hai bảng mục tiêu/revision. PostgreSQL đã được sao lưu và kiểm tra archive trước nâng cấp. Hash các tài khoản, Workspace, khách hàng, grant, asset, job và payload snapshot cũ không đổi; binding Content và cấu hình runtime giữ nguyên.
- Sau triển khai cả hai container Customer healthy, source trong image khớp working tree. Có image khôi phục và archive riêng tư trong `.work`; không reset database/volume.
- Fanpage thật đã có dữ liệu để xác nhận giao diện. Những nền tảng còn lại vẫn cần Lead tự consent/chọn đúng tài sản và nghiệm thu số liệu thật. 8/9 cấu hình ứng dụng có sẵn ở lúc kiểm tra; TikTok còn thiếu cấu hình ứng dụng Vio. Google Ads/Business Profile còn cần xác nhận quyền API của project/tài khoản thật.
- Runtime hiện giữ localhost. Phiên chia sẻ Lead qua Internet cần xác nhận đủ callback HTTPS của Vio trước khi đổi origin; không đưa link tunnel tạm chưa sẵn sàng cho khách.
- Mục tiêu là kế hoạch có thể cập nhật. In lại báo cáo vận hành của một snapshot dùng mục tiêu hiện tại của kỳ. Khóa mục tiêu vào một revision đã phát hành thuộc luồng publication riêng, chưa được quảng bá là hoàn tất trong đợt này.

Contract backend: `VioAgencyAnalytics-Admin/docs/CUSTOMER_REPORTING_PERIODS_KPI.md`. Artifact QA, backup và thông tin đăng nhập chỉ nằm trong `.work`, không đưa vào Git hoặc image.
