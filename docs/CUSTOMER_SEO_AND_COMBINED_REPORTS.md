# SEO & Từ khóa và báo cáo tổng hợp

Cập nhật ngày 16/11/2026.

## Luồng nguồn và báo cáo SEO thống nhất — 16/11/2026

| Mục trên trang SEO | Nguồn đầu vào | Thao tác tại mục đó |
| --- | --- | --- |
| Thứ hạng và tăng/giảm | Excel/CSV Spineditor có ngày đo | Mở Spineditor, nhập file cho kỳ hiện tại và kỳ đối chiếu |
| Từ khóa chính, phụ và ngách | Truy vấn GSC và phân loại của Lead | Kết nối GSC, đồng bộ truy vấn, duyệt vai trò và phạm vi cam kết |
| Bài viết đã đăng | WordPress REST API, feed hoặc sitemap/metadata | Đồng bộ từ website, kiểm tra ngày đăng và duyệt nghiệm thu |
| Hiệu quả từng bài | GA4 theo pageLocation và GSC theo page | Kết nối GA4/GSC, chọn đúng tài sản và đồng bộ kỳ đang xem |
| KPI dự án | Cam kết theo tháng, phép đo thứ hạng, GA4/GSC và bằng chứng công việc | Chốt định nghĩa lưu lượng, đặt mục tiêu từng tháng và xác nhận kết quả |
| Báo cáo tổng SEO | Các đầu vào đã lưu theo kỳ | Kiểm tra bảng đầu vào, chọn SEO + GA4 + GSC và tạo bản báo cáo |

Các thẻ nguồn có logo, tài sản đang chọn, ngày dữ liệu, nút kết nối/quản lý
và đồng bộ ngay tại phần Bài viết, KPI và Báo cáo. Nút đồng bộ dùng queue,
quyền và phiên bản kết nối hiện có. Khi làm mới bản đã lưu, giao diện tiếp
tục theo dõi tác vụ và tự đọc lại SEO sau khi hoàn tất.

GA4 bổ sung bảng URL đầy đủ và số phiên theo thiết bị. GSC bổ sung bảng
trang riêng và quốc gia. Các snapshot cũ cần đồng bộ lại để có chi tiết này.
Chi tiết bài viết ghép đúng host và URL chuẩn hóa. Một bài có cả công việc
viết mới/cập nhật được trình bày một dòng hiệu quả theo URL. Lượt xem GA4,
lượt nhấp, hiển thị, CTR và vị trí trung bình GSC có cột kỳ trước khi đủ dữ
liệu. Nghiệm thu tiếp tục được theo dõi trong sổ công việc.

Báo cáo có các nội dung tương ứng mẫu PDF của Lead cùng phần mở rộng

- GA4 có KPI, xu hướng hai kỳ, phân bổ phiên theo kênh và thiết bị.
- GSC có nhấp, hiển thị, CTR, vị trí trung bình, truy vấn, trang và quốc gia.
- Từ khóa có nhóm cam kết, ngách mở rộng và theo dõi chính/phụ. Truy vấn GSC
  chưa có phép đo Spineditor dùng bảng quan sát GSC riêng với tên chỉ số rõ ràng.
- Bài viết có ngày đăng, trạng thái duyệt/nghiệm thu, liên kết và hiệu quả URL.
- KPI có kế hoạch–thực tế theo từng tháng trong thời hạn cam kết 1–24 tháng.
  Tháng tương lai để trống thực tế. Bộ từ khóa cam kết giữ theo phiên bản.
- Biểu đồ có hai chuỗi cùng thang đo, khoảng trống cho ngày thiếu và đơn vị.
  Biểu đồ vị trí tìm kiếm đưa vị trí thấp hơn lên cao hơn. Bảng in có tiêu đề
  lặp khi sang trang, cột số căn thẳng và tên bài xuống dòng.

Báo cáo đã lưu giữ bản dữ liệu tại thời điểm tạo. Khi đồng bộ thêm, tạo bản
mới để nhận dữ liệu mới. Đọc trang hoặc tạo báo cáo chỉ sử dụng quan sát đã
lưu. Quyền truy cập nguồn và hash dữ liệu được kiểm tra lại khi mở báo cáo,
kể cả phép đo thứ hạng lịch sử dùng trong bảng nhiều tháng.

Số liệu thiếu giữ dấu —. GSC có thể ẩn truy vấn hoặc giới hạn dòng, GA4 có
thể áp dụng ngưỡng/lấy mẫu. Bảng URL giới hạn 5.000 dòng mỗi lượt đọc,
bảng chi tiết Google trên báo cáo tối đa 200 dòng và ghi số dòng thực có.
Kiểm thử dữ liệu dùng kho riêng, Lead cần đồng bộ các nguồn thật cùng kỳ
để nghiệm thu số liệu khách hàng. Đợt này tiếp tục dùng schema 21.


Đã triển khai hai image `seo-flow-20261116` lên Docker local. Đối chiếu
24 file source/image và count/hash 75 bảng đạt. Web, Customer Backend và
Admin Console healthy. Kiểm thử Web đạt 704, JavaScript Web 59, JavaScript
Admin 136. Toàn bộ Admin chạy 1.007 ca, 321 ca cần PostgreSQL riêng được
skip. Nhóm SEO chạy 86 ca trên PostgreSQL tạm, nhóm mới chạy thêm 12 ca.
QA nghiệp vụ/giao diện đạt 35 kiểm tra cùng bốn kích thước bản báo cáo.
Đăng nhập Customer thật và 15 kiểm tra tab/responsive trên Docker đạt,
TLS và yêu cầu đăng nhập được xác nhận. Kết quả này kiểm tra triển khai và
logic bằng dữ liệu QA. Số liệu provider của từng khách hàng cần Lead đồng bộ
và đối chiếu trong tài khoản nguồn để nghiệm thu.

## Tự lấy bài viết và từ khóa — 16/11/2026

Trong tab **Bài viết**, nút **Đồng bộ từ website** tạo tác vụ riêng theo
Workspace, khách hàng và kỳ đang áp dụng. Worker Customer Backend đọc website
công khai: ưu tiên WordPress REST API, tiếp đến RSS/Atom và sitemap kết hợp
thông tin Article/BlogPosting hoặc metadata ngày đăng. Người dùng không phải
cung cấp tài khoản quản trị website. Nút chọn nguồn cho phép thử lại bằng
sitemap hoặc feed khi nguồn ưu tiên chưa phù hợp.

Tên bài, URL, ngày đăng và nguồn được lưu có hash, lịch sử và kiểm tra trùng.
Ngày đăng có giờ được đổi sang múi giờ Workspace. Ngày cập nhật, sitemap
lastmod và timestamp thiếu múi giờ không được dùng để tự suy ra ngày đăng.
Bài thiếu ngày nằm ở mục cần kiểm tra, không tăng số bài đã đăng/nghiệm thu.
Bài có ngày rõ ràng vào sổ ở trạng thái chờ duyệt; chỉ người có quyền mới
xác nhận nghiệm thu. Đồng bộ lại giữ nguyên chỉnh sửa và nghiệm thu cũ.

Mỗi lượt đọc giới hạn thời gian, số request, kích thước và phạm vi cùng
website. Sitemap đọc tối đa 50 trang mỗi tác vụ và có **Lấy tiếp** cho danh
sách còn lại. WordPress tối đa 1.000 bài/lượt; sổ nội dung tối đa 2.000 dòng.
Feed chỉ có thể chứa bài gần đây, được đánh dấu phạm vi giới hạn. Website
chặn đọc, yêu cầu đăng nhập hoặc không công khai ngày đăng vẫn cần bổ sung
bằng file/duyệt tay. Không đăng nhập hộ CMS, chạy JavaScript website hoặc
coi danh sách lấy được là bằng chứng đã hoàn thành hợp đồng SEO.

Trong tab **Từ khóa**, mục **Từ khóa tự lấy từ Google** nằm trước bộ theo dõi.
Kết nối Search Console đúng website, chọn kỳ rồi nhấn **Đồng bộ từ khóa GSC**.
Adapter bổ sung cặp query/page với lượt nhấp, hiển thị, CTR và vị trí trung
bình. Chọn bản đã lưu có các cặp này sẽ nhập ngay; bản cũ được đồng bộ lại qua
queue có kiểm tra quyền và cấu hình nguồn. Các lần đồng bộ GSC thành công
sau khi bật luồng này tiếp tục bổ sung từ mới, chống trùng theo tên chuẩn hóa.

Gợi ý từ chính là truy vấn nổi bật theo lượt nhấp, hiển thị rồi vị trí cho
từng URL; các truy vấn hỗ trợ là gợi ý từ phụ. Đây là cách sắp xếp dữ liệu,
không xác nhận ý định tìm kiếm hay thay thế nghiên cứu từ khóa. Vai trò có
nhãn chờ duyệt; Lead có thể sửa chính/phụ, chủ đề và ngách riêng. Từ đã phân
loại thủ công không bị ghi đè. Từ mới chưa nằm trong cam kết và chưa được gán
thứ hạng Spineditor. GSC chỉ trả truy vấn đã ghi nhận, có thể ẩn một số truy
vấn và không cung cấp toàn bộ bộ từ khóa tiềm năng. Luồng này đọc tối đa
5.000 cặp query/page và quản lý tối đa 2.000 từ duy nhất cho mỗi website.

Lượt xem/phiên Organic Search và KPI lưu lượng tiếp tục đọc từ snapshot
GA4/GSC đã có đúng kỳ. Spineditor vẫn dùng Excel/CSV có ngày đo; mục tiêu
hợp đồng, bản thảo, công việc thủ công và nghiệm thu do Lead xác nhận. Chọn
bộ lọc hoặc mở báo cáo không phát sinh provider request. Chưa có lịch chạy
định kỳ website; người dùng chủ động nhấn đồng bộ. Snapshot và báo cáo đã
chốt vẫn bất biến khi các tác vụ sau bổ sung dữ liệu mới.

Luồng mới sử dụng migration 21, session, CSRF, quyền owner/admin, kiểm tra
website hiện tại và phiên bản grant/tài sản. Website transport chặn IP nội
bộ/DNS rebinding, chuyển hướng khác website và HTTPS xuống HTTP, có TLS
verification và giới hạn đọc; không chuyển cookie hoặc thông tin OAuth tới
website. Bộ đọc feed/sitemap không xử lý XML external entity.

Thử đọc công khai Hoa Phong Pack tháng 10/2026 lấy được 10 bài WordPress có
ngày đăng; phép thử không ghi vào dữ liệu khách hàng. QA giao diện và nghiệp
vụ dùng SQLite riêng; PostgreSQL dùng container tạm và dữ liệu phục hồi để
kiểm tra migration. Lead cần chạy đồng bộ cho website thực tế và duyệt dữ
liệu đầu vào trước khi nghiệm thu KPI.

## SEO phục vụ Lead kiểm tra ngày 13/11/2026

Trang `/workspace/seo` có năm tab Tổng quan, Từ khóa, Bài viết,
KPI & Công việc và Báo cáo SEO. Thiết lập website sử dụng API khách hàng
hiện có và kiểm tra phiên bản chỉnh sửa. Hai nguồn GSC/GA4 dùng bản đồng bộ
đã lưu để trình bày hiệu quả trong kỳ. Phiên Organic Search chỉ đọc đúng
nhóm kênh đó khi có quan sát.

Bộ từ khóa có thêm thuộc tính ngách độc lập với vai trò chính/phụ và cam kết.
Nút Mở Spineditor truy cập công cụ thứ hạng của nhà cung cấp. Truy vấn GSC
được đọc từ snapshot có quyền, cho chọn đưa vào danh sách theo dõi. Khi thêm
truy vấn, thứ hạng Spineditor tiếp tục chờ phép đo. Biểu đồ hai kỳ trình bày
các khoảng thứ hạng cùng nhóm chưa xác định.

Bài viết hỗ trợ thêm từng dòng hoặc nhập Excel/CSV tối đa 2 MB, 2.000 dòng,
sheet đầu tiên. Nút tải mẫu sinh CSV UTF-8 gồm mười cột tên bài, loại công
việc, tháng kế hoạch, trạng thái đăng, ngày đăng, trạng thái duyệt, ngày
nghiệm thu, URL bài viết, link bản thảo và nhóm nội dung. Dialog có hướng dẫn,
xem trước và xác nhận. Dòng đã có được bỏ qua khi nhập tiếp. Người dùng cập
nhật trực tiếp dòng hiện có khi cần sửa dữ liệu.

Bài mới tính theo ngày đăng và URL website. Nghiệm thu tính theo ngày xác
nhận với bài đã đăng, đã duyệt. Cập nhật bài cũ có loại công việc riêng.
Đếm trùng URL được kiểm tra qua các tháng đối với bài mới. Bài lưu trữ được
giữ trong lịch sử. Thay đổi có phiên bản và bản ghi nội dung trước/sau.
Kết nối tự động CMS đang chờ triển khai. Các trang có quan sát GA4 tương ứng
hiển thị lượt xem trong kỳ từ bảng trang đã đồng bộ.

Cam kết dự án hỗ trợ 1–24 tháng, chỉ tiêu riêng từng tháng và thao tác sao
chép mục tiêu sang các tháng phía sau. Các chỉ tiêu gồm tỷ lệ Top 10, lưu
lượng, bài mới nghiệm thu, bài cập nhật nghiệm thu, checklist kỹ thuật,
tối ưu nội dung/liên kết, entity, trang mạng xã hội và lượt chia sẻ có bằng
chứng. Lưu lượng chọn một định nghĩa GSC clicks, GA4 Organic Search sessions,
GA4 sessions hoặc GA4 page views. Bộ từ khóa và điều kiện đo được chốt theo
phiên bản cam kết. Giá trị trống và mục tiêu 0 được giữ nghĩa riêng.

Công việc chỉ đi vào KPI dự án sau xác nhận nghiệm thu, có bằng chứng và ngày
nghiệm thu trong tháng. Checklist kỹ thuật tính từ khối lượng đã nghiệm thu
trên khối lượng kế hoạch. Mỗi chỉ tiêu hiển thị thực tế, mục tiêu, chênh lệch,
mức hoàn thành và trạng thái kỳ. Chênh lệch tỷ lệ hiển thị bằng điểm phần
trăm. Chỉ tiêu chưa có nguồn quan sát hiển thị trạng thái cần bổ sung.

Tab Báo cáo SEO mở trình tạo báo cáo với nguồn, kỳ và điều kiện đang xem,
đồng thời liệt kê báo cáo của khách hàng đang chọn. Bản đã chốt lưu cả danh
sách bài, nghiệm thu, phiên bản dự án và kết quả KPI. Lưu lại cam kết hoặc
sửa bài về sau vẫn cho mở đúng nội dung bản báo cáo trước. PDF có thêm phần
KPI dự án, biểu đồ đối chiếu và danh sách nội dung kèm liên kết.

Migration 20 thêm thuộc tính từ khóa/công việc và bốn bảng sổ nội dung,
lịch sử nội dung, bản xem trước nhập file và phiên bản dự án. Dry-run trên
bản phục hồi PostgreSQL chạy hai lần thành công, đối chiếu 68 bảng cũ bằng
count/hash theo cột gốc. Rollout Web và Customer Backend sử dụng image
`seo-delivery-20261113`, đối chiếu 22 file source/image và kiểm tra dịch vụ
healthy. Đăng nhập Customer tại HTTPS localhost và 15 kiểm tra tab/responsive
đạt. Luồng nghiệp vụ QA có 35 kiểm tra, xuất PDF bảy trang đã render kiểm tra.
PostgreSQL SEO đạt 50 ca. Node Web 43 ca và Node Admin 136 ca đạt.

Toàn bộ dữ liệu minh họa nằm trong SQLite/PostgreSQL QA riêng. Lead cần nhập
danh sách của khách hàng, chọn nguồn Google và chốt cam kết để nghiệm thu
báo cáo thực tế. Bằng chứng kỹ thuật riêng nằm ở `.work/seo-delivery-20261113`.

## Vị trí trong Customer Web

- Phân tích kênh → SEO & Từ khóa, đường dẫn `/workspace/seo`.
- Báo cáo → Báo cáo tổng hợp, đường dẫn `/workspace/reports/combined`.
- Nút Tạo báo cáo SEO mang khách hàng, điều kiện đo và kỳ đang xem sang trình tạo báo cáo.

Giao diện dùng chung sidebar, tìm kiếm, typography và thành phần nút của Customer. SEO dùng màu xanh ngọc, trình tạo báo cáo dùng màu chàm. Mobile có menu đóng/mở và bảng cuộn ngang.

## Nhập bộ từ khóa

Chọn đúng Workspace và khách hàng/thương hiệu, nhập website cùng điều kiện đo, tải Excel `.xlsx` hoặc CSV rồi xem trước và xác nhận. Bộ đọc nhận năm cột Từ khóa, Vị trí, Vị trí cũ, Ngày cập nhật, Liên kết hiển thị. File mẫu tải ở cửa sổ nhập.

File tối đa 2 MB và 2.000 dòng dữ liệu. Mỗi website quản lý tối đa 2.000 từ khóa. Dòng tên nhóm được dùng làm chủ đề. Ngày đo của từng dòng phải có trong file. Dữ liệu chưa xác định hiển thị dấu gạch và được tính riêng. URL phải thuộc website đã chọn. Các điều kiện thiết bị, vị trí và ngôn ngữ được lưu riêng để đối chiếu đúng phạm vi.

Spineditor hiện dùng file xuất do người dùng tải lên. Kết nối GA4 và Search Console tiếp tục qua OAuth hiện có. Thứ hạng từ file và vị trí trung bình Search Console có định nghĩa khác nhau và được trình bày theo nguồn.

Các bản nhập đã xác nhận và quan sát thứ hạng được lưu bất biến. Nhập lại cùng file, cùng điều kiện đo có cơ chế chống trùng. File nhị phân chỉ tồn tại trong quá trình xử lý. Bản xem trước hết hạn sau một ngày.

## Từ khóa và cam kết KPI

Mỗi từ khóa có chủ đề, vai trò chính/phụ/chưa phân loại và tùy chọn đưa vào bộ cam kết. Vai trò và cam kết được chỉnh độc lập. Thao tác chọn cam kết hàng loạt áp dụng cho trang đang hiển thị.

KPI theo tháng lưu danh sách từ khóa đã chốt, tỷ lệ Top 10, điều kiện đo và phiên bản. Số từ cần đạt được làm tròn lên từ tỷ lệ nhân số từ đã chốt. Thay đổi danh sách đang quản lý không thay mẫu số của phiên bản đã lưu. Thiếu phép đo, sai điều kiện hoặc sai kỳ được hiển thị thành trạng thái riêng. Tháng còn mở dùng trạng thái đang thực hiện khi chưa đạt mục tiêu.

Công việc SEO có tháng, nhóm, tên việc, số lượng kế hoạch, số lượng đã làm và liên kết bằng chứng. Cập nhật kiểm tra phiên bản để phát hiện sửa đồng thời.

## Kỳ và báo cáo tổng hợp

Chọn tháng hoặc khoảng ngày tối đa 90 ngày. Kỳ liền trước lấy cùng số ngày ngay trước ngày bắt đầu. Cùng kỳ tháng trước dịch mốc ngày lùi một tháng, giới hạn theo độ dài tháng, và dùng toàn tháng trước khi kỳ đang xem là toàn tháng đã kết thúc. Kỳ tùy chỉnh nhận hai mốc riêng, tối đa 90 ngày. Không so sánh tắt phần đối chiếu.

Từ 16/11/2026, trang SEO hiển thị mốc đối chiếu trước khi áp dụng, trạng thái hai kỳ riêng cho thứ hạng, GSC và GA4. GSC/GA4 dùng ngày nguồn đã hoàn tất và múi giờ nguồn. Chọn bộ lọc chỉ đọc snapshot. Nút Lấy dữ liệu Google còn thiếu gửi yêu cầu đồng bộ có CSRF, client, phiên bản kết nối và request key qua API sync hiện có. Nguồn có quyền quản lý được đồng bộ từng kỳ hoặc các kỳ còn thiếu, theo dõi tác vụ và tự cập nhật. Sửa bộ lọc chưa áp dụng sẽ khóa nút đồng bộ của dữ liệu cũ.

Thứ hạng của mỗi kỳ lấy lần đo gần nhất trong chính kỳ đó, cùng điều kiện đo. Hai phía hiện số từ có phép đo và ngày đo. Nhập file để bổ sung kỳ đối chiếu giữ bộ lọc và điều kiện đang xem. Cột Vị trí cũ thiếu ngày đo riêng tiếp tục được giữ làm thông tin nguồn. Bản xuất giữ rõ ngày quan sát của từng từ khóa.

GSC so lượt nhấp, hiển thị, CTR và vị trí trung bình. GA4 bổ sung so Phiên Organic Search từ chính dòng Organic Search của bảng kênh. Thiếu dòng này giữ trạng thái chưa có dữ liệu. Chênh lệch tỷ lệ dùng điểm phần trăm, mốc trước bằng 0 giữ chênh lệch tuyệt đối, và vị trí thấp hơn có chiều cải thiện. Phiên Organic Search cũng có trong đối chiếu bản báo cáo đã chốt khi hai snapshot có dữ liệu phù hợp.

Người dùng chọn SEO, GA4, GSC và các nguồn Marketing hiện có. Các phần có thể chọn gồm tổng quan, đối chiếu, mục tiêu KPI, biểu đồ, chi tiết và công việc SEO. GA4/GSC/thứ hạng nằm trong nhóm SEO & Website. Nguồn chưa có bản đồng bộ đúng kỳ được ghi rõ. Các chỉ số giữ đơn vị, múi giờ và định nghĩa của nguồn. Chỉ tiêu tích lũy có chú thích riêng.

Tạo báo cáo lưu một bản dữ liệu cố định, có hash kiểm tra toàn vẹn và khóa chống tạo trùng. Báo cáo đọc các snapshot đã được kiểm định. Quyền hiện tại vẫn được kiểm tra khi mở lại. Bản này được xem riêng tư trong Workspace và xuất bằng In / Lưu PDF của trình duyệt. Luồng phát hành Published Bundle hiện có tiếp tục vận hành riêng.

## Quyền và kiến trúc

Admin Customer Backend lưu dữ liệu và thực thi quyền Workspace/client. Web dùng BFF, session, CSRF và projection hiện có. Owner/Admin nhập từ khóa, sửa KPI/công việc. Owner/Admin/Member tạo báo cáo. Viewer xem theo phạm vi được cấp.

Migration 19 bổ sung sáu bảng `customer_seo_imports`, `customer_seo_keywords`, `customer_seo_measurements`, `customer_seo_plans`, `customer_seo_work`, `customer_compiled_reports`. Các migration trước được giữ nguyên.

## Nghiệm thu

Đã kiểm thử parser bằng file Excel người dùng cung cấp theo chế độ chỉ đọc. Luồng nhập/xác nhận/phân loại/KPI/công việc/tạo báo cáo/PDF được chạy trên cơ sở dữ liệu QA riêng. Cần Lead nhập file đúng website và xác nhận bộ từ khóa cam kết để nghiệm thu bằng số liệu nghiệp vụ thực tế.
