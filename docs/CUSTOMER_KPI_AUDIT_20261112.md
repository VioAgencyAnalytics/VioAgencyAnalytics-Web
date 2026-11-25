# Kiểm định kho KPI Customer — 12/11/2026

Phạm vi lần này là 44 KPI đang khai báo trong chín connector. Đã thống nhất cách
tính, cách đọc biến động và so với mục tiêu giữa trang nguồn, Tổng quan,
Dashboard và báo cáo tổng hợp. Phần nghiệp vụ SEO chuyên sâu sẽ triển khai sau.

## Phạm vi từng nền tảng

| Nền tảng | KPI hiện có | Nguyên tắc quan trọng |
| --- | --- | --- |
| Facebook Content — 4 | Bài đăng, cảm xúc, bình luận, chia sẻ | Bài đăng thuộc kỳ; tương tác là bộ đếm tích lũy của nhóm bài tại lúc đồng bộ. Không diễn giải thành tương tác phát sinh trong kỳ. |
| Facebook Ads — 7 | Chi phí, hiển thị, tất cả lượt nhấp, Lead, CTR, CPC, chi phí/Lead | CTR = tổng nhấp / tổng hiển thị; CPC = tổng chi phí / tổng nhấp; chi phí/Lead = tổng chi phí / tổng Lead. Lead theo định nghĩa và cửa sổ ghi nhận đã lưu. |
| Google Ads — 6 | Chi phí, hiển thị, nhấp, chuyển đổi, CTR, CPC | Đổi costMicros bằng số thập phân chính xác; tính tỷ lệ từ tổng kỳ. Chuyển đổi có thể có phần lẻ theo mô hình phân bổ. |
| TikTok Ads — 6 | Chi phí, hiển thị, nhấp đến đích, chuyển đổi, CTR, CPC | Không trộn nhấp đến đích với mọi tương tác. Tỷ lệ dựa trên tổng; chuyển đổi theo cài đặt nguồn. |
| GA4 — 4 | Người dùng hoạt động, phiên, lượt xem trang/màn hình, tỷ lệ tương tác | Dùng kết quả toàn kỳ của GA4. Không cộng người dùng duy nhất hoặc trung bình tỷ lệ hằng ngày để thay tổng kỳ. |
| Google Search Console — 4 | Nhấp tự nhiên, hiển thị, CTR, vị trí trung bình | Tổng kỳ do nguồn tính; không cộng bảng truy vấn để thay tổng. Vị trí là trung bình, số thấp hơn là chiều cải thiện. |
| YouTube — 4 | Lượt xem, phút xem, đăng ký mới, thời lượng xem trung bình (giây) | Trung bình toàn kỳ do nguồn trả; đăng ký mới khác tổng subscriber hiện tại. |
| Business Profile — 5 | Nhấp website, nhấp nút gọi, chỉ đường, hiển thị Search di động, hiển thị Maps di động | Chỉ cộng chỉ số có đủ quan sát ngày. Nhấp nút gọi không đồng nghĩa cuộc gọi thành công. |
| Instagram — 4 | Bài đăng, thích và bình luận nhóm bài, follower hiện tại | Tương tác/follower tại thời điểm đồng bộ không được tính thành tăng trưởng phát sinh trong kỳ. |

Đây là danh mục KPI đang hỗ trợ, không phải toàn bộ chỉ số mà mỗi nhà cung cấp
có thể cung cấp. Không tự tạo doanh thu, ROAS, reach hoặc conversion khi chưa có
định nghĩa và dữ liệu nguồn phù hợp.

## Quy tắc tính và trình bày

- Chi phí và giá dẫn xuất giữ Decimal; không ép qua float để tính CPC/chi phí
  trên Lead. Đã sửa mất chữ số khi cộng số tiền lớn và khi chiếu snapshot cũ.
  Không ghi lại payload hoặc hash của snapshot đã lưu.
- Không lấy trung bình CTR/CPC theo ngày. Ví dụ hai ngày có 3/10 và 7/990 lượt
  nhấp/hiển thị: CTR cả kỳ là 10/1.000 = 1%, không phải trung bình hai tỷ lệ.
- Thiếu dữ liệu giữ `null`; 0 là số 0 đã được quan sát. Mẫu số bằng 0 không sinh
  Infinity, NaN hoặc tỷ lệ giả. Số dương nhỏ hơn độ chính xác hiển thị có ký hiệu
  `<0,01` hoặc `<1`.
- Biến động tương đối = (thực tế − kỳ trước) / kỳ trước. Kỳ trước bằng 0 chỉ nêu
  chênh lệch tuyệt đối. Từ 20% lên 25% ghi **+5 điểm phần trăm**.
- CPC, chi phí/Lead và vị trí giảm là chiều cải thiện; chi tiêu có nhãn trung
  tính để đọc cùng kết quả. Mũi tên vẫn biểu thị tăng/giảm số học. Màu và nhãn
  không thay cho kết luận về chất lượng kinh doanh.
- Chỉ đối chiếu cùng Workspace, client, nguồn, tài khoản, phiên bản kết nối,
  múi giờ và định nghĩa KPI. Không quy đổi tiền tệ ngầm.

## Kỳ báo cáo và mục tiêu

Có 7/30/90 ngày đã kết thúc, chọn tháng, ngày tùy chỉnh và đối chiếu kỳ trước,
cùng kỳ tháng trước hoặc kỳ tùy chọn. Mỗi cửa sổ tối đa 90 ngày. Tháng lịch,
năm nhuận và chuyển năm được kiểm tra. Hai tháng khác số ngày được ghi rõ;
không tự chuẩn hóa tổng theo ngày.

Kỳ đang diễn ra so sánh phần thời gian nguồn đã kết thúc. Mục tiêu vẫn giữ
toàn bộ kỳ, không tự chia theo số ngày. Nhãn **Đang thực hiện**, **Đạt đến hiện
tại**, **Trong giới hạn hiện tại** tránh kết luận cuối kỳ quá sớm.

Mục tiêu hỗ trợ tối thiểu/tối đa, kể cả mục tiêu bằng 0, gắn đúng asset/KPI/kỳ
và có revision/version để chống ghi đè. Đạt mục tiêu và biến động theo kỳ là
hai phép so sánh riêng. Actual không bị thay bằng mục tiêu; báo cáo tổng hợp
đã chốt giữ payload và mục tiêu tại lần tạo.

GET báo cáo và đổi bộ lọc chỉ đọc bản lưu. Thiếu kỳ có nút đồng bộ theo quyền;
không gọi API provider từ luồng xem hoặc in báo cáo. Thời gian lịch sử và độ trễ
dữ liệu vẫn phụ thuộc từng API và quyền đã cấp.

## Các sửa lỗi liên quan SEO đã giữ lại

Đã sửa làm tròn số từ khóa cam kết bằng Decimal (250 × 64,4% cần 161 từ, không
phải 162), phân biệt chưa đo với ngoài Top 100, giữ đúng phiên bản danh sách
cam kết và không kết luận hoàn thành cho kỳ thiếu hoặc khác điều kiện đo.
Những sửa lỗi này được giữ; mở rộng nghiệp vụ SEO chưa thuộc đợt hiện tại.

## Kiểm chứng

- Web Python: **694 PASS, 1 SKIP**.
- Admin Python: **648 PASS, 307 SKIP**; chạy trong tiến trình kiểm thử tách biệt
  với mặc định client legacy, không lấy chế độ sandbox từ `.env` máy làm kết
  quả của các test legacy. Không thay cấu hình dịch vụ đang chạy.
- PostgreSQL dùng database QA riêng: **26 PASS** cho mục tiêu, phân quyền,
  revision, phép so sánh và các lỗi dữ liệu liên quan.
- JavaScript: **34 PASS** ở Web, **136 PASS** ở Admin.
- UI: **39 kiểm tra responsive / 13 trang**, gồm chín nền tảng, không có lỗi JS;
  kiểm tra chọn kỳ, tùy chỉnh đối chiếu, mục tiêu và tạo báo cáo qua fixture.
- Ba bản In/PDF QA: GA4, Facebook Ads và Facebook Content; kiểm tra phân trang,
  chú thích, màu và các khối so sánh. Dữ liệu minh họa chỉ nằm trong `.work`.

Các bài SKIP có điều kiện, chủ yếu cần môi trường PostgreSQL riêng; 26 bài trên
đã chạy bổ sung trên PostgreSQL. Những kiểm tra tự động không thay thế nghiệm
thu số liệu thật của từng tài khoản.

## Triển khai và kiểm tra lại — 13/11/2026

Web và Customer Backend đã chạy image `kpi-20261112` trên Docker, gắn tag
`local`. Đối chiếu 34 file source/image đạt khớp. Hai dịch vụ healthy; login,
session và tài nguyên mới trả 200. Trang riêng tư yêu cầu đăng nhập, Customer
API không có phiên trả 401. HTTP 8084 chuyển về `https://localhost:8444`.
Primary Admin vẫn chạy ở `http://localhost:8090`.

Giữ nguyên credential, mount, network và 18 snapshot trước/sau triển khai.
Kiểm định chỉ đọc các bản lưu có sẵn gồm Facebook Content (15), GA4 (1),
GSC (1), YouTube (1): hash, receipt và contract không có kiểm tra thất bại.
Vẫn ghi nhận cảnh báo về cấu hình kết nối đã đổi, quan sát ngày chưa đầy đủ,
một số KPI Facebook thiếu số liệu và hai bản lịch sử khác lựa chọn hiện tại.
Đó là các trạng thái cần trình bày rõ, không lấp bằng số 0 hoặc báo cáo giả.

Kết nối được tạo dưới origin/cấu hình trước có thể cần **Kết nối lại** trên
localhost trước khi đồng bộ thêm. Dữ liệu đã lưu vẫn được giữ nguyên. Cơ sở
dữ liệu QA đã dọn xong; không commit/push trong đợt này.

## Việc còn cần để nghiệm thu kết nối thật

Lead cần cấp quyền từng nguồn và đối chiếu một kỳ đã kết thúc với giao diện gốc,
giữ cùng tài khoản, múi giờ và định nghĩa KPI. Cần kiểm tra thêm kỳ không có
hoạt động, kỳ thiếu quyền, token hết hạn và dữ liệu cập nhật trễ. Không xem trạng
thái “đã cấu hình connector” là đã nghiệm thu dữ liệu thật.

Google Ads/TikTok/Meta/Business Profile vẫn phụ thuộc quyền và phê duyệt của
ứng dụng Vio. Không cam kết cả chín nguồn đã được cấp quyền hoặc có dữ liệu thật
chỉ từ kết quả test. HTTPS localhost hiện dùng cho phát triển; chia sẻ Internet
cần origin và callback OAuth khớp URL tại thời điểm chia sẻ.
