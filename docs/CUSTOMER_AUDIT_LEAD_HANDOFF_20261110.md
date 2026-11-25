# Rà soát Web Customer và bàn giao nghiệm thu — 10/11/2026

**Cập nhật liên dịch vụ sau audit:** Docker hiện dùng `vio-bridge-web:20261110`
cùng Customer/Primary Admin tương thích danh mục chín nguồn, transport/scope
được siết và monitor đã triển khai. URL public/callback và dữ liệu giữ nguyên.
Các image/kết quả ở các mục lịch sử bên dưới phản ánh lượt audit trước đó.
Xem [Web ↔ Admin Customer](CUSTOMER_ADMIN_BRIDGE_20261110.md).

**Cập nhật chia sẻ sau audit:** người dùng đã xác nhận lưu callback Google/Meta và profile Customer public đã bật tại **https://preview-1.example.test**. Lead dùng URL public trong đợt thử; localhost 8444 tạm ngừng bind khi chạy profile này. Các mục localhost bên dưới ghi lại lần audit trước chuyển profile. Tài khoản/dữ liệu/grant/snapshot/KPI giữ nguyên; grant Facebook Content/GSC từ origin localhost cần cấp quyền lại để thao tác provider ở origin public. File cấu hình local được giữ để phục hồi. URL Quick Tunnel phụ thuộc máy/Docker/cloudflared đang chạy; kiểm tra public lưu riêng ở Admin `.work/lead-preview-20261110/`.

## Kết luận và phạm vi

Web Customer đã được rà theo 12 màn hình/URL, các trạng thái có dữ liệu, chưa có dữ liệu, tải lỗi, đổi phạm vi, quyền chỉ xem và thiết bị nhỏ. Đã chỉnh sửa mã nguồn, kiểm thử và cập nhật Docker tại **https://localhost:8444**. Admin console vẫn tại **http://localhost:8090**.

**Có thể nghiệm thu luồng Customer trên máy hiện tại. Chưa coi là hoàn tất nghiệm thu SaaS production hoặc kết nối dữ liệu thật của mọi nền tảng.** Lead ở máy khác cần public HTTPS và callback đã xác nhận; gửi localhost sẽ không truy cập máy đang chạy Vio.

Đợt này tập trung Customer; không đổi schema, cấu hình OAuth, quyền tài khoản, bộ đồng bộ hoặc dữ liệu kinh doanh. Backend Customer hiện ở schema 18. Admin tiếp tục giữ OAuth, token, tài sản, đồng bộ, dữ liệu, quyền và phát hành. Customer Web giữ giao diện tự phục vụ và BFF có kiểm tra phạm vi.

## Những vấn đề đã sửa

| Vấn đề | Cách xử lý | Xác nhận |
|---|---|---|
| Hành động chính còn giống chữ mô tả | Bộ kiểu nút chung: khung viền, nền, hover, focus bàn phím, vùng bấm tối thiểu 44px cho nút; áp dụng cả nội dung sinh bằng JavaScript | Kiểm tra DOM, bàn phím và ảnh desktop/mobile |
| Phân tích kênh báo chưa có dữ liệu dù Fanpage có bản lưu | Đọc hợp đồng `/data` và báo cáo đã lưu; mặc định kỳ gần nhất của từng nguồn | Fixture đa nguồn và Fanpage thật |
| Thẻ kênh dùng chỉ số của sườn, chưa khớp nguồn | Dùng nhãn, đơn vị, tiền tệ và giá trị từ DTO; ghi rõ chỉ số tích lũy; giữ null và số 0 khác nhau | Các ca 0/null/USD, nhãn gốc và KPI Fanpage |
| Đổi kỳ có thể khiến người dùng hiểu số cũ thuộc kỳ mới | Đọc đúng cửa sổ ngày đã chọn; khi không có bản lưu đúng kỳ thì xóa số cũ; không tự đồng bộ | Kỳ tùy chỉnh không có dữ liệu, ngày không hợp lệ, tối đa 90 ngày |
| Đổi khách hàng trong lúc tải | Hủy request cũ, tăng generation, kiểm tra Workspace/client/request trước khi nhận kết quả | Response trễ và dữ liệu phạm vi khác bị loại |
| Lỗi đọc dữ liệu dễ khiến khách hàng đi cấp quyền lại không cần thiết | Hiện “Thử tải lại” khi đọc lỗi, không tự mở OAuth | Lỗi 503, scope sai và retry |
| SEO mở bản bố cục giống phân tích hoàn chỉnh | Nút “Chọn nguồn SEO” dẫn tới GA4/Search Console riêng; không tạo số thứ hạng hoặc cộng hai nguồn | Điều hướng có source, snapshot hoặc ngày tương ứng |
| Trang Báo cáo còn ưu tiên công cụ thử bố cục | Báo cáo từ dữ liệu đã đồng bộ nằm trước; mẫu và phần phát hành/lịch gửi được gom riêng, ghi rõ trạng thái | Kiểm tra trạng thái mặc định và xem mẫu |
| Khoảng ngày đã lưu ở Cài đặt bị bỏ qua | Tổng quan/Dashboard dùng tùy chọn đã lưu; Workspace chưa lưu tùy chọn ưu tiên bản báo cáo mới nhất | Test hồi quy và thử lưu/mở lại hai trang |
| Chọn lại khoảng ngày mặc định ban đầu không thể lưu | Cho phép chủ Workspace chủ động chọn rồi lưu ngay cả khi chọn lại giá trị ban đầu | Kiểm thử lần lưu đầu tiên |
| Esc trong ô tìm kiếm chỉ xóa từ khóa | Esc đóng hộp tìm kiếm và trả focus về nút mở | Kiểm thử bàn phím |
| Biểu đồ rỗng có nhóm chọn chỉ số tràn trên điện thoại | Nhóm nút xuống dòng trong vùng biểu đồ | Kiểm thử Workspace mới ở 390px |
| Trường không hợp lệ nằm trong nhóm cài đặt đang gập | Tự mở đúng nhóm và đưa focus tới trường cần sửa; không gửi form sai | Invalid-field test, không có request ghi |
| Skip link chưa nhắm chính xác phần nội dung | Thêm đích main có thể nhận focus, dùng hành vi mở section dùng chung | Kiểm thử bằng bàn phím |
| Ma trận quyền còn ghi kết nối cần xác minh email | Cập nhật mô tả đúng với chính sách hiện tại; việc mời thành viên vẫn giữ yêu cầu riêng | So sánh UI với chính sách backend |
| Thông báo thiếu số liệu ở KPI Facebook quá lớn | Giảm cỡ chữ trạng thái thiếu dữ liệu, chỉnh dòng trên màn hình và bản in | Xem ảnh và bản A4 |
| Kiểu nút mới chồng màu với CTA báo cáo cũ | Giữ màu riêng cho nút “Xem báo cáo”, thêm khung các thao tác trên thẻ kết nối; xếp chú thích tích lũy thành dòng riêng | Kiểm tra ảnh sau deploy, CTA có tỷ lệ tương phản ít nhất 4,5:1 trong fixture |

Mục tiêu “hiểu trong 5 giây” là tiêu chí nghiệm thu với người dùng. Đợt này kiểm tra khả năng nhận biết và thao tác; chưa có nghiên cứu người dùng để bảo đảm mốc thời gian đó.

## Duyệt từng trang và chức năng

| Trang / nhóm | Chức năng đã kiểm tra | Kết quả và giới hạn |
|---|---|---|
| Đăng nhập | Email/mật khẩu, mật khẩu sai, hiện/ẩn, đăng xuất, đăng nhập lại, trạng thái Google sẵn sàng/chưa sẵn sàng | PASS trong kiểm thử; không tự đăng nhập tài khoản Google thật hoặc cấp quyền provider trong đợt audit |
| Khôi phục / xác minh | Cookie, CSRF, token một lần, lỗi/hết hạn và ranh giới bảo mật qua suite identity | PASS kiểm thử backend; không gửi email thật trong audit |
| Onboarding | Agency/Doanh nghiệp, tên/website, preview logo/fallback, khách hàng đầu tiên, xem lại, tạo, mở Workspace đã có | PASS luồng đăng ký đến mở lại, desktop/mobile; website bên ngoài không bảo đảm luôn có logo lấy được |
| Hướng dẫn ban đầu | Tour 8 bước được giữ lại, bỏ qua/hoàn tất và quay lại hướng dẫn | Không xóa luồng hiện có; các shortcut chính được giữ |
| Khung dùng chung | Menu, header, đổi Workspace, tìm kiếm, trợ giúp, đăng xuất, skip link, section anchors | PASS; sidebar/header có kiểm tra khi cuộn; chữ 200% được kiểm tra ở Cài đặt |
| Tổng quan | Chọn khách hàng/nguồn/kỳ, KPI theo nguồn, biểu đồ, báo cáo gần đây, nguồn dữ liệu, quản lý khách hàng | PASS; số liệu chỉ từ bản lưu; không cộng chi phí khác tiền tệ hoặc cộng người dùng duy nhất |
| Dashboard Marketing | Lọc nguồn/kỳ/so sánh, chi tiết ngày/tuần/tháng phù hợp cách tổng hợp, bảng nền tảng, CSV, campaign khi có nguồn Ads | PASS fixture đa nguồn; KPI/biểu đồ Fanpage đối chiếu bản lưu thật |
| Kết nối nền tảng | Danh mục, lọc/tìm, context, quyền quản lý, cấp quyền, chọn tài sản, đồng bộ, kết nối lại | PASS các nhánh UI giả lập cho 9 nguồn; consent live từng nguồn cần chủ tài khoản thao tác |
| Khôi phục kết nối | Lỗi discovery, không có tài sản, discovery treo, response trễ, grant hết hạn/lỗi, quay lại bước cấp quyền | PASS; mở nút kết nối lại chưa gửi OAuth/sync; không xóa bản lưu cũ trước |
| Phân tích kênh | Tìm không dấu, nhóm/trạng thái, kỳ gần nhất/tùy chỉnh, metric gốc, đường dẫn báo cáo, chọn GA4/GSC cho SEO | PASS; không bịa metric keyword/ROAS chưa được cung cấp |
| Facebook Content | Kỳ/snapshot, KPI, biểu đồ, lọc/tìm bài, link riêng từng bài, quyền truy cập | PASS kiểm tra hiện có; `null` không bị chuyển thành 0; không đọc nguồn mới khi xem |
| Báo cáo Facebook | Bìa, KPI, cách tính/phạm vi, mục tiêu, biểu đồ, bài viết, bản in | PASS native HTTPS và QA bản in; dữ liệu tích lũy được ghi rõ |
| Báo cáo chung | GA4, GSC, YouTube, Google Ads, Facebook Ads, TikTok Ads, Instagram, Business Profile | PASS renderer, kỳ, mục tiêu và quyền với fixture; chưa chứng nhận live-data acceptance cho cả 8 nguồn |
| Chọn kỳ báo cáo | 7/30/90 ngày, tháng, ngày tùy chỉnh, kỳ đang mở/tương lai, bản lưu cụ thể | PASS; cửa sổ tối đa 90 ngày; mục tiêu theo cả kỳ, không chia theo ngày; đồng bộ chỉ ngày nguồn đã kết thúc |
| KPI mục tiêu | Tối thiểu/tối đa, số 0, phần lẻ, tỷ lệ %, tiền tệ, bỏ mục tiêu, CAS version, cập nhật nguyên tử, revision | PASS backend SQLite/PostgreSQL và UI; không sửa actual/snapshot; không tự quy đổi tiền tệ |
| Trung tâm Báo cáo | Chọn khách hàng, mở bản dữ liệu gần nhất, chọn kỳ/đặt KPI, in PDF, xem mẫu | PASS; các mẫu là bố cục thử, không được ghi là báo cáo đã phát hành |
| Thành viên | Mời bằng mã, sao chép/ẩn mã sau đóng, tham gia đúng email, lọc/sắp xếp, đổi vai trò, thu hồi, lịch sử và ma trận quyền | PASS với DB tách biệt; chưa có email mời tự động |
| Cài đặt | Thông tin, website/logo, vùng/ngôn ngữ/tiền tệ, ngày mặc định, so sánh, thương hiệu, copy mã, lưu/hủy, Ctrl+S, chống ghi đè | PASS; xác nhận khi rời trang có thay đổi; input không hợp lệ được mở đúng nhóm |
| Quyền chỉ xem | Không sửa cài đặt, mời/cấp quyền, kết nối lại hoặc mục tiêu | PASS cả chính sách backend và UI; ẩn nút không thay cho kiểm tra server |
| Tenant và bảo mật | Workspace/client/asset/source/snapshot/period, session, Host/Origin/CSRF, phạm vi nội bộ, receipt | PASS suite Customer; không mở API Customer nội bộ ra public, không chuyển credential provider sang Web |
| Responsive và khả năng thao tác | Desktop/tablet/mobile, vùng cuộn bảng, nút/focus, phóng chữ, không có JS exception | PASS các cỡ đã nêu; chưa phải đánh giá WCAG đầy đủ hoặc kiểm thử mọi trình duyệt/thiết bị |

## Kết quả kiểm thử

| Kiểm tra | Kết quả |
|---|---|
| Toàn bộ Web pytest trên máy | **565 PASS**, 6 cảnh báo deprecation đã có |
| Toàn bộ Web pytest trên image ứng viên, không có network | **565 PASS**, 6 cảnh báo deprecation đã có |
| JavaScript định dạng, kỳ, mục tiêu, saved analytics, mặc định đã lưu | **15 PASS** |
| 16 module Customer backend: identity, workspace, server/migration, overview, integrations, providers, Meta, data, connectors, KPI, lỗi provider, logo | **233 PASS + 96 subtests PASS**, SQLite và PostgreSQL thử riêng |
| Đăng ký/đăng nhập/tạo/mở Workspace | **PASS**, desktop và mobile; DB tách biệt |
| Thành viên/Cài đặt/Viewer/concurrency/persistence | **PASS**, desktop/tablet/mobile; DB tách biệt |
| Nút, section, form sai, bàn phím, Esc, skip link, chữ 200% | **PASS** |
| Thẻ kênh, null/0/tiền tệ, custom period, scope sai, request trễ, retry, SEO, mẫu/báo cáo | **PASS**, fixture loopback, không dùng DB thật |
| Dashboard và kết nối lại 9 nguồn | **PASS**, gồm error/hang/late response/Viewer |
| Report controls/KPI 9 nguồn, lỗi version, kỳ tương lai, bản in | **PASS**, không có provider hay dữ liệu thử trong DB thật |
| Native HTTPS sau deploy | **PASS** trên 12 màn hình; đối chiếu Fanpage thật và continuity báo cáo/KPI; GET không gọi provider |
| Python/JavaScript syntax, CSS build, Git diff whitespace | **PASS** |
| Scan credential thật trong nội dung Git-visible | **PASS**, không phát hiện giá trị bí mật được kiểm tra; `.work` được Git ignore |

Các số liệu QA đa nguồn là fixture trong bộ nhớ/cơ sở dữ liệu dùng một lần. Không nhập số mẫu, tài khoản mẫu hay mục tiêu thử vào cơ sở dữ liệu khách hàng đang chạy. Audit live chỉ tạo phiên đăng nhập QA, chọn phạm vi để đọc rồi đăng xuất; không consent, sync, đổi grant hoặc lưu KPI thử.

Không cộng kết quả backend Customer vào một tuyên bố “toàn bộ Admin đã PASS”. Regression Admin legacy toàn bộ không nằm trong đợt này; các lỗi baseline đã ghi ở tài liệu trước còn cần xử lý trước production.

## Triển khai và bảo toàn dữ liệu

- Web Docker dùng image `vio-customer-audit-web:20261110` qua alias local hiện có, tại `https://localhost:8444`.
- Đã kiểm tra hash file trong image và container đối chiếu source.
- Có PostgreSQL dump kiểm tra được danh mục archive và image phục hồi riêng trước khi cập nhật.
- Origin, biến môi trường, port, mount, network, schema 18 giữ nguyên. Container backend Customer, Admin console và các container khác không bị thay thế.
- Hash tài khoản, identity, Workspace, membership, client, grant, asset, job, snapshot, mục tiêu và revision không đổi qua triển khai.
- Không commit/push. Không prune/xóa project Docker hoặc volume dữ liệu.

## Kịch bản Lead nghiệm thu

1. Trên máy chạy Vio, mở Web, đăng nhập và chọn đúng Workspace/thương hiệu. Xác nhận tên, logo và phạm vi trước khi nối tài khoản.
2. Thử tìm “kết nối”, “thành viên”, “cài đặt” bằng Ctrl+K; dùng bàn phím và Esc. Quan sát có biết ngay nút nào là hành động chính không.
3. Vào Kết nối nền tảng → chọn nguồn → Tiếp tục trên nền tảng → chọn tài sản → đồng bộ. Khách hàng dùng app của Vio; không phải tạo app riêng.
4. Với tài sản chưa xuất hiện hoặc lỗi cấp quyền, thử quay lại và Kết nối lại. Không gửi token, secret hoặc callback có code vào chat.
5. Mở Phân tích kênh, kiểm tra số và kỳ trên thẻ; vào báo cáo cùng nguồn, cùng snapshot/kỳ. So sánh với tài khoản nền tảng có cùng múi giờ và định nghĩa metric.
6. Chọn tháng và khoảng ngày tùy chỉnh, thử một kỳ chưa có bản lưu. Số cũ phải được xóa khỏi kỳ mới. Việc mở/xem/in không được tự đồng bộ.
7. Đặt KPI thử trong Workspace dành cho UAT, kiểm tra tối thiểu/tối đa, 0, phần lẻ, % và tiền tệ. Mở lại để xác nhận mục tiêu; thử hai tab để kiểm tra chống ghi đè.
8. Xem Tổng quan/Dashboard cùng nguồn/kỳ. Nếu chọn kỳ đã lưu mới nhất, số phải khớp báo cáo; không so sánh hai cửa sổ khác ngày.
9. In/lưu PDF: kiểm tra nhãn, biểu đồ, bảng nhiều trang, link bài Facebook và giá trị thiếu. Mẫu bố cục không được nhầm là báo cáo đã phát hành.
10. Dùng hai tài khoản trong Workspace UAT: mời thành viên, đổi sang Viewer, thử sửa mục tiêu/cài đặt/kết nối. Server phải từ chối thao tác ghi của Viewer.
11. Lưu mặc định 7 ngày/không so sánh trong Cài đặt rồi mở lại Tổng quan/Dashboard. Thử Hủy và rời trang khi còn thay đổi.
12. Lặp lại các thao tác quan trọng trên điện thoại. Ghi lỗi bằng tên trang, bước thao tác, kỳ/nguồn và ảnh đã che thông tin nhạy cảm.

Đo nhanh tiêu chí “5 giây” bằng ba nhiệm vụ không hướng dẫn: tìm nút nối tài khoản, mở báo cáo của nguồn có dữ liệu, đổi kỳ/đặt KPI. Ghi thời gian tới cú bấm đầu tiên đúng và số lần phải hỏi. Chỉ chốt tiêu chí này sau khi Lead/client thực hiện.

## Những việc chưa hoàn tất và điều kiện bàn giao Admin

| Ưu tiên | Việc cần làm | Tiêu chí hoàn tất |
|---|---|---|
| P0 trước khi Lead thử từ Internet | Chọn public HTTPS ổn định, xác nhận callback Google Sign-in/Google Data/Meta tương ứng, rồi chuyển cấu hình có kiểm soát | Đăng nhập, OAuth quay về đúng host, session/CSRF hoạt động từ máy Lead; không bỏ kiểm tra origin/grant |
| P0 trước khi công bố mọi connector hoạt động live | Nghiệm thu tài khoản/tài sản thật GA4, GSC, YouTube, Ads, Instagram, Business Profile, TikTok | Cấp quyền, chọn tài sản, đồng bộ, dữ liệu đúng và tái kết nối từng nguồn; lưu bằng chứng theo nguồn |
| P0 cho TikTok | Hoàn tất ứng dụng/cấu hình/quyền phía Vio và kiểm tra consent thật | Khách hàng bấm kết nối bằng tài khoản của họ; không tự tạo app |
| P0 trước production | Xác nhận điều kiện public/quyền/API/quota ở mỗi provider; giải quyết regression legacy và chạy kiểm tra an toàn toàn stack | Có kết quả nghiệm thu, không suy từ fixture hoặc một Fanpage sang mọi nguồn |
| P1 Admin — bắt đầu tiếp theo | Màn hình giám sát kết nối và sync, error code an toàn, độ phủ/kỳ/thời gian mới nhất, xử lý grant cần khách hàng cấp lại | Admin xem và vận hành dữ liệu; consent và chọn tài sản khách hàng vẫn tại Web Customer |
| P1 Admin — chuỗi báo cáo | Snapshot/Dataset → kiểm tra chất lượng → review → revision → publish/Bundle/Viewer theo ACL | Bản đã phát hành bất biến, đúng tenant; xem/preview không đọc provider |
| P1 sau publish | Lịch gửi, quản lý lần xuất, link chia sẻ/thu hồi, audit, hạn quyền | UI Customer và Admin dựa trên trạng thái thật; không dùng nút/bảng demo làm tính năng đã mở |
| P2 | Email mời tự động, upload logo, chuyển chủ/xóa Workspace, tracking keyword chuyên biệt, đánh giá a11y/trình duyệt sâu hơn | Có hợp đồng, quyền, test và UX riêng trước khi bật |

Ưu tiên triển khai Admin **giám sát kết nối → sync/job → chất lượng Dataset → duyệt/phát hành**. Lead có thể nghiệm thu Customer local song song. Không cần chờ thêm chỉnh trang trí mới bắt đầu phần vận hành Admin; vẫn phải giữ các gate live và public nêu trên.

## Mã nguồn thay đổi trong đợt audit

- Dùng chung: `templates/customer/base.html`, `static/css/customer/actions.css`, `static/js/customer/interactions.js`, `static/js/customer/shell.js`.
- Danh mục/báo cáo: `static/js/customer/library.js`, `static/js/customer/channels.js`, `templates/customer/live/channels.html`, `templates/customer/live/reports.html`, `templates/customer/live/components/library-filters.html`.
- Mặc định hiển thị: `static/js/customer/saved-analytics.js`, `static/js/customer/overview-dashboard.js`, `static/js/customer/marketing.js`, `static/js/customer/settings.js`, `templates/customer/live/settings.html`, test hồi quy `tests/customer_saved_analytics.test.cjs`.
- Đích nội dung chính/mô tả quyền: `templates/customer/live/overview.html`, `integrations.html`, `dashboard.html`, `members.html`, `data-report.html`, `facebook-content.html`, `facebook-content-report.html`.
- Tài liệu: báo cáo này và cập nhật `VioAgencyAnalytics-Admin/docs/SYSTEM_CONTEXT.md`. Các thay đổi cũ trong working tree được giữ nguyên.

## Bằng chứng riêng tư

Tại Admin `.work/customer-audit-20261110/`: `before-audit.json`, `after-audit.json`, ảnh các màn hình, `identity/result.json`, `workspace_admin/result.json`, `actions-result.json`, `library-result.json`, `postgres-result.json`/log, `audit-image-tests.log`, `audit-deployment-result.json`, hash và backup phục hồi.

Kiểm thử 9 nguồn Dashboard/reconnect/report controls và bản in ở `.work/kpi-readiness-20261110/`; native saved-summary sau audit ở `.work/customer-audit-20261110/live-dashboard-result.json`; scan secret ở `.work/all-connectors-20261109/secret-scan.json`. Toàn bộ các thư mục này được ignore. Không đưa credential, dump, ảnh chứa tài khoản hoặc fixture riêng tư vào GitHub public.
