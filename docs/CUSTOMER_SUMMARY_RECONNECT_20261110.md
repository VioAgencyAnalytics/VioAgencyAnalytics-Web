# Customer: kết nối lại và Tổng quan/Dashboard từ báo cáo đã lưu

Cập nhật 10/11/2026. Phạm vi là Web Customer, BFF và phần trình bày từ operational snapshot; không thay đổi Admin backend, schema 18 hoặc Published Bundle.

## Đã thực hiện

- Thẻ tài khoản tại **Kết nối nền tảng** có nút **Kết nối lại** cho Owner/Admin khi app nguồn đã cấu hình, kể cả kết nối chưa chọn tài sản, lỗi, hết quyền hoặc đang đồng bộ. Hộp kết nối của cả Facebook Content và tám nguồn còn lại có cùng lối phục hồi.
- Nhấn nút mở lại bước đăng nhập/cấp quyền, không tự ngắt kết nối, xóa token, chọn tài sản hoặc đồng bộ. Khách tự nhấn tiếp tục trên nền tảng. Cấp quyền thất bại không được ghi nhận là thành công.
- Khi tải danh sách tài sản bị treo, người dùng có thể chọn kết nối lại ngay. Kết quả trả về muộn của lần tải cũ bị loại bỏ bằng generation/scope guard; không kéo người dùng về bước chọn tài khoản cũ. Trong các mutation đang gửi, nút được khóa để tránh hai thao tác chồng nhau.
- Viewer vẫn chỉ xem; UI ẩn nút và backend tiếp tục bảo vệ session, role, client, tenant, CSRF và OAuth state như trước. Không thêm bước xác minh email vào luồng nền tảng.
- **Tổng quan** và **Dashboard Marketing** tự đọc báo cáo đã lưu mới nhất của khách hàng/thương hiệu đang chọn. Tên, đơn vị, giá trị KPI và biểu đồ theo nguồn thực tế. Ví dụ Facebook Content hiển thị bài đăng, cảm xúc, bình luận, chia sẻ; GA4 hiển thị người dùng, phiên, lượt xem và tỷ lệ tương tác.
- Chọn nguồn/kỳ để xem đúng báo cáo. Kỳ mới chưa có bản lưu không mượn số liệu kỳ khác. Tháng này giữ toàn bộ cửa sổ mục tiêu tháng; preset 7/30/90 ngày dùng ngày đã kết thúc theo lịch của nguồn. Bộ lọc “Kỳ của báo cáo mới nhất” giữ đúng chế độ khi thay nguồn hoặc tải lại URL.
- Thông tin nguồn, tài khoản, ngày bắt đầu/kết thúc và mã bản lưu hiện ngay trên màn hình. Liên kết mới nhất ghim snapshot; kỳ tùy chỉnh giữ cửa sổ kế hoạch KPI. Mục tiêu được hiển thị tóm tắt cạnh KPI và có đường tới báo cáo đầy đủ.
- **Báo cáo gần đây**, trạng thái nguồn và bảng hiệu suất nền tảng dùng cùng snapshot đã kiểm tra. Từng nguồn có kỳ/tiền tệ riêng. Thẻ dữ liệu phụ được gom vào phần mở rộng để tránh lặp lại toàn bộ trang.
- Trang tự đọc lại dữ liệu khi quay lại tab, định kỳ 60 giây hoặc 6 giây khi có tác vụ đồng bộ; không chạy sync/provider request từ quá trình đọc này. Chuyển client/source hủy request cũ và dọn số liệu trước khi tải phạm vi mới.

## Quy tắc số liệu

Bốn vị trí KPI theo **một nguồn đang xem**, không phải tổng chung của những nền tảng khác cách đo. Chế độ tự chọn ưu tiên nguồn có bản lưu mới nhất; có thể chọn từng nguồn bằng dropdown. Bảng nền tảng và danh sách báo cáo vẫn hiển thị các nguồn đã có dữ liệu.

Giữ `null` khác 0, decimal tiền tệ chính xác và đơn vị nguồn. Không quy đổi tiền tệ, cộng số người duy nhất qua ngày, trung bình CTR hoặc gọi tương tác lifetime là phát sinh riêng trong kỳ. Nhóm biểu đồ theo tuần/tháng chỉ cộng các metric có aggregation cộng hợp lệ; bucket thiếu ngày/quan sát giữ trống. Chỉ số unique/rate không được suy diễn thành tổng tuần/tháng từ chuỗi ngày. So sánh kỳ trước cần có đúng snapshot kỳ trước; stock/lifetime và tháng chưa kết thúc không gắn nhãn tăng trưởng sai.

Bảng chiến dịch giữ từng hàng theo ngày của nguồn. Ngân sách, trạng thái chạy, CTR/CPA hoặc kết quả không có trong snapshot giữ thiếu dữ liệu. Meta Lead được ghi đúng tên, không tự đổi thành khách hàng/doanh thu. Bảng nguồn giới hạn hàng được ghi rõ.

## BFF và kiểm thử

GET `/api/customer/workspaces/{workspace_id}/analytics` chỉ gọi các GET nội bộ đã có: danh mục snapshot, integrations, báo cáo nguồn, tùy chọn kỳ trước, và kiểm tra lại phạm vi đang chọn. Web không đọc database hoặc nhận credential. Tham số allowlist gồm `source`, `start/end`, `comparison`, `granularity`; không nhận tenant/client giả từ query. Các mapper nguồn vẫn kiểm tra asset/consent version, hash và adapter receipt ở backend.

- Web: **565 pytest PASS** trên máy và candidate Docker; **14 Node PASS** cho định dạng, kỳ/KPI và tiện ích summary.
- Browser fixture: 9 nguồn summary và 9 đường kết nối lại; KPI/chart, báo cáo gần đây, kỳ không có dữ liệu, lỗi discovery, discovery bị treo/kết quả muộn, Viewer và desktop/mobile đạt; không gọi provider hoặc dùng database khách hàng.
- CSS build, Python/JavaScript syntax, `git diff --check` đạt. Artifact QA riêng tư ở `VioAgencyAnalytics-Admin/.work/kpi-readiness-20261110/`.
- Nghiệm thu Docker và trạng thái runtime được ghi trong `summary-deployment-result.json` và `live-dashboard-result.json` tại cùng thư mục sau triển khai. Không dùng ảnh fixture làm bằng chứng dữ liệu thật.

## Chuyển công việc sang Admin

Customer hiện có luồng: tự cấp quyền → chọn tài sản → đồng bộ → snapshot → KPI/report → mục tiêu theo kỳ → Tổng quan/Dashboard. Các cấu hình API và nghiệm thu tài khoản thật của từng nền tảng vẫn là điều kiện riêng. 8/9 ứng dụng được cấu hình ở lần kiểm tra trước; TikTok còn thiếu app. Không tuyên bố tất cả nguồn đã có dữ liệu thật hoặc toàn bộ SaaS production-ready.

Phần Admin cần nối/kiểm tra tiếp theo:

1. Theo dõi kết nối và tác vụ theo Workspace/client/platform, mã lỗi có hướng xử lý; Admin không consent thay khách hàng.
2. Theo dõi kỳ dữ liệu, độ phủ, receipt/lineage, tác vụ thất bại và trạng thái cần cấp lại quyền; không công khai token hoặc dữ liệu ngoài phạm vi.
3. Nối snapshot đủ điều kiện vào Dataset/Report Revision, review/publish và Web Viewer bằng contract sẵn có. Không sửa payload/revision đã phát hành.
4. Khóa phạm vi mục tiêu KPI vào revision khi thiết kế báo cáo phát hành; bản operational hiện dùng mục tiêu đang lưu của kỳ, chưa phải kế hoạch đã đóng băng.
5. Nghiệm thu từng provider bằng tài khoản có quyền thật, rồi xử lý các regression Admin legacy đã ghi nhận trước đó. Không xem việc Web/adapter tests đạt là bằng chứng toàn bộ Admin đã đạt.
