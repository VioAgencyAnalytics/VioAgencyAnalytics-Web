# Facebook Content: phân tích và báo cáo riêng tư

Cập nhật 09/11/2026. Trang phân tích tại
`/workspace/channels/facebook-content`; nút **Xem báo cáo** mở
`/workspace/reports/facebook-content?snapshot=<id>` với đúng snapshot đang xem.
Thư viện Báo cáo cũng mở bản này khi nguồn Facebook Content có dữ liệu.

## Trình bày

- Bốn KPI: số bài xuất bản trong kỳ UTC; tổng lượt xem tích lũy của các bài khi
  có đủ số đếm từng bài; cảm xúc và bình luận tích lũy của nhóm bài đó. Không gọi
  tổng lượt xem bài là lượt xem phát sinh trong kỳ hoặc người xem duy nhất.
- Ba biểu đồ cột khi có số đo: số bài/ngày UTC, lượt xem toàn Page và tương tác
  toàn Page. Hai chuỗi Insights giữ đúng mốc kết thúc ngày Meta, không ép sang
  ngày đăng hoặc tổng kỳ UTC khi ranh giới không khớp.
- Quy mô Page hiển thị tổng followers và unique viewers từ mốc gần nhất **có
  số đo**, kèm ngày/mô tả. Không cộng unique/stock qua ngày hoặc suy ra follows mới.
- Phân bổ định dạng lấy từ attachment đã chuẩn hóa, không đoán Reels/chủ đề.
- Ba bài nổi bật xếp theo lượt xem tích lũy nếu có, nếu không thì theo cảm xúc
  tích lũy; không tạo nhận định tăng trưởng hoặc kỳ so sánh chưa có dữ liệu.
- Bảng có tìm kiếm không dấu, lọc định dạng, sắp xếp, phân trang, mở nội dung và
  liên kết **Xem bài trên Facebook** ở từng dòng. Chỉ tạo deep link từ cặp số
  Page/Post đã lưu, Page phải trùng tài sản snapshot; URL cố định host HTTPS,
  `target=_blank`, `noopener noreferrer`. Không đưa raw permalink bên ngoài vào
  DOM. Một số permalink vanity/pfbid đã bị normalizer cũ loại bỏ; đường dẫn
  `permalink.php?story_fbid=<post>&id=<page>` dùng đúng cặp ID đã có, không thay
  snapshot hoặc phỏng đoán vanity. Meta có thể yêu cầu đăng nhập/quyền xem bài.
- Doanh nghiệp một thương hiệu không hiện picker Khách hàng dư thừa. Agency/
  nhiều thương hiệu vẫn có phạm vi chọn rõ ràng, backend vẫn kiểm tra selection.

Số 0 giữ nguyên; chỉ số thiếu hiển thị **Chưa có**/**Chưa có số liệu**. Lý do được
gom trong phần Thông tin về số liệu; số chia sẻ chưa đủ coverage không cộng thành
tổng giả. API gốc vẫn giữ null/status/coverage và không biến unknown thành 0.

## Báo cáo và bản in

Bố cục gồm thông tin thương hiệu/kỳ, tổng quan KPI, ba chuỗi biểu đồ, nội dung
nổi bật, danh sách bài và nguồn/cách đọc. Nút **In báo cáo** gọi hộp thoại in của
trình duyệt, có thể lưu PDF tại máy; trước in dùng toàn bộ bài của snapshot,
không bỏ sót do tìm kiếm, phân trang hoặc lọc hiện tại. Sau in phục hồi bảng.
Đây là bản xem riêng tư, **không phải Published Bundle hoặc bản đã duyệt/phát hành**;
không tạo share link, file export phía backend, revision, scheduler hay token Viewer.

Route mới dùng cùng Customer session, workspace/client selection, whitelist query
snapshot và BFF projection đang có. Header no-store/noindex/no-referrer, output
escape, kiểm tra số hữu hạn và guard tenant không thay đổi. GET không gọi Graph,
không đồng bộ hoặc sửa số liệu; Web không nhận credential/provider secret.

Chế độ local hiện dùng `https://localhost:8444`, xem
[thiết lập HTTPS](CUSTOMER_LOCAL_HTTPS.md). Triển khai Web phải giữ **cả hai**
Compose file HTTPS, credential và volume Customer đang dùng.
