# Rà soát kỳ dữ liệu, đối chiếu và KPI — 11/11/2026

## Kết luận và phạm vi

Customer đã có chọn ngày/tháng và mục tiêu KPI. Trước lần rà soát này, Dashboard chỉ đối chiếu kỳ liền trước cùng độ dài và chỉ chạy với kỳ đã kết thúc; báo cáo nguồn chưa có bộ chọn kỳ đối chiếu. Vì vậy chọn “Tháng trước” để xem dữ liệu trước đây chưa đồng nghĩa với đối chiếu hai tháng.

Đã bổ sung cùng một bộ quy tắc cho Tổng quan, Dashboard và báo cáo nguồn, gồm Facebook Content chuyên biệt và tám nguồn còn lại qua báo cáo chung. Web chỉ hợp thành DTO đã kiểm tra từ Customer backend; không gọi provider khi mở hoặc đổi kỳ. Không thay schema, worker, OAuth, Published Bundle hay revision đã phát hành.

## Các khả năng

| Thao tác | Quy tắc |
| --- | --- |
| 7/30/90 ngày | Đếm cả ngày đầu và cuối, theo ngày nguồn đã kết thúc |
| Tháng này/trước/chọn tháng | Giữ đúng ranh giới tháng; xử lý năm nhuận và chuyển năm |
| Ngày tùy chỉnh | Tối đa 90 ngày cho mỗi kỳ; nhận cả hai ngày, chặn ngày không tồn tại/đảo ngược |
| Kỳ liền trước | Cùng số ngày dữ liệu đã kết thúc, kết thúc ngay trước ngày bắt đầu kỳ hiện tại |
| Cùng kỳ tháng trước | Dời về tháng trước; kỳ trọn tháng đã kết thúc đối chiếu đúng tháng lịch trước |
| Kỳ đối chiếu tùy chỉnh | Tối đa 90 ngày, chỉ gồm ngày nguồn đã kết thúc; có thể chọn một kỳ lịch sử xa hơn |
| KPI kế hoạch | Theo đúng Workspace/client/platform/asset/kỳ/metric; tối thiểu hoặc tối đa |

Mỗi kỳ tối đa 90 ngày; hai kỳ có thể nằm xa nhau. Khả năng đồng bộ lịch sử còn phụ thuộc API, quyền và thời gian lưu dữ liệu của nền tảng. 90 ngày là giới hạn một lần xem/đồng bộ của Vio, không phải cam kết mọi API đều có đủ dữ liệu lịch sử.

Preset được đối chiếu lại theo calendar backend của nguồn đang chọn. Không lấy ngày của trình duyệt hoặc múi giờ Workspace để thay thế lịch nguồn GSC/YouTube hay múi giờ tài khoản quảng cáo/GA4. “Ngày đã kết thúc” không bảo đảm dữ liệu API đã được chốt đầy đủ; thiếu dữ liệu vẫn giữ thiếu.

## Các ví dụ quan trọng

- Chọn 01–30/11 và nguồn mới có dữ liệu đến 10/11: “Cùng kỳ tháng trước” dùng 01–10/10. Mục tiêu KPI vẫn của 01–30/11, không tự chia thành mục tiêu 10 ngày.
- Chọn cả tháng 11 đã kết thúc: đối chiếu cả tháng 10. Giao diện ghi rõ 30 ngày đang xem và 31 ngày đối chiếu; không âm thầm chia trung bình theo ngày.
- Chọn 05–11/11 (7 ngày): kỳ liền trước là 29/10–04/11; cùng kỳ tháng trước là 05–11/10.
- Tháng 3/2024 đối chiếu tháng 2 có 29 ngày; tháng 3/2026 đối chiếu tháng 2 có 28 ngày.
- Dời một cửa sổ 90 ngày về tháng trước có thể thành 91 ngày. Khi đó giữ báo cáo hiện tại, thông báo giới hạn và yêu cầu chọn kỳ đối chiếu tùy chỉnh; không gọi backend với cửa sổ quá giới hạn.

## Cách đọc kết quả

- So sánh kỳ và so sánh KPI là hai khối riêng, có thể xem cùng lúc.
- Chỉ đối chiếu cùng nguồn, Workspace, khách hàng, asset, connection/version và múi giờ. Thay phạm vi giữa các request bị từ chối.
- Tiền tệ khác nhau không được tự chuyển đổi hoặc tính chênh lệch. Số tiền giữ decimal chính xác; không ép qua số thực JavaScript để tính tăng trưởng.
- Tỷ lệ từ 20% lên 25% hiển thị **+5 điểm phần trăm**. Các KPI chỉ tiêu/tỷ lệ hoàn thành vẫn dùng định nghĩa mục tiêu riêng.
- Kỳ trước bằng 0: nêu rõ không có mẫu số để tính tăng trưởng; không trả Infinity/NaN. Không quan sát được giữ `null`, không đổi thành 0.
- Chỉ số tích lũy hoặc tại thời điểm thu thập, như phản ứng trọn đời của bài và follower, không bị diễn giải thành tăng trưởng phát sinh riêng trong kỳ.
- Không cộng người dùng duy nhất qua các ngày, không lấy trung bình CTR/CPC hằng ngày để giả lập tổng kỳ, không cộng tiền khác đơn vị hoặc số liệu các nguồn có định nghĩa khác nhau.

## Thiếu dữ liệu và quyền thao tác

Đối chiếu chỉ dùng bản lưu đúng cửa sổ. Không lấy bản mới nhất thuộc kỳ khác để lấp. Kỳ đối chiếu thiếu/lỗi không xóa số liệu hiện tại và không tạo số 0 giả. Owner/Admin có nút **Đồng bộ kỳ đối chiếu**; Viewer chỉ đọc. Nếu tác vụ đang chạy, hiện trạng thái và nút cập nhật kết quả. Ghi KPI vẫn dùng cơ chế version/CAS và revision đã có; thao tác đổi kỳ không ghi lại actual hoặc snapshot.

Nút đồng bộ là thao tác rõ ràng của người dùng, đi qua API hiện có cùng Origin/Host/CSRF và kiểm tra quyền phía backend. GET báo cáo không tự sync. Báo cáo vận hành dùng kế hoạch KPI hiện tại; đây không phải một revision phát hành đã khóa.

## Kiểm chứng và triển khai

Kiểm tra bao gồm biên tháng/năm nhuận, khoảng tối đa 90 ngày, tháng đang diễn ra, tiền lớn, giá trị 0/null, điểm phần trăm, nguồn/asset/version/timezone lệch, baseline thiếu/lỗi, Viewer và form chọn kỳ. Có kiểm tra schema PostgreSQL tách biệt và candidate Web trên mạng Docker nội bộ không Internet; không cấp quyền hoặc đồng bộ provider thật thay Lead.

Kết quả chạy, manifest, image, clone và trạng thái rollout được lưu riêng trong Admin `.work/report-periods-20261111/`. Trạng thái triển khai hiện tại được ghi tại `Admin/docs/SYSTEM_CONTEXT.md`; không suy ra đã rollout chỉ từ sự tồn tại của mã nguồn hoặc tài liệu này. Chưa nghiệm thu consent, giới hạn API và số liệu thật đồng loạt ở mọi nền tảng. Không commit/push.
