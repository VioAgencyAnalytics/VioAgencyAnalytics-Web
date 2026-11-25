# Kiểm tra khung connector và báo cáo — 09/11/2026

**Xác nhận bổ sung 10/11:** người dùng đã bật API GA4 và YouTube theo hướng dẫn.
App settings/callback hai nguồn đã có trên Docker; đang chờ customer tự cấp quyền,
chọn property/kênh và đồng bộ thật. Xác nhận Enable chưa phải nghiệm thu dữ liệu.

**Mốc mới 10/11:** Meta Ads và Instagram đã được cấu hình bằng hai Config ID riêng
người dùng tạo. Runtime có App settings 8/9 nguồn; TikTok còn đăng ký ứng dụng.
Web **507 PASS** Windows và Docker, focused backend **45 PASS / 38 PG skip**,
transport/error candidate bốn tests PASS. Browser fixture kiểm tra hướng dẫn
từng nguồn và lỗi setup trên desktop/mobile; không có lỗi JS. Lỗi API disabled
và quota không chuyển grant sang expired, không làm phát sinh snapshot. GSC đã
có connection `connected` nhưng chưa chọn website/chưa có snapshot Google;
Facebook Content vẫn giữ 16 bài. Consent/sync Ads và Instagram chưa nghiệm thu.
Hướng dẫn mới: [Thao tác tiếp theo](CUSTOMER_CONNECTORS_NEXT_STEPS_20261110.md).
Các đoạn ngày 09/11 bên dưới là lịch sử trước thay đổi này.

**Cập nhật sau lượt triển khai ban đầu:** đã kích hoạt Google Data dùng chung App
với Sign-in nhưng grant/transaction riêng. Người dùng đã Save callback Data và
xác nhận bật Search Console API; browser live đã thấy nút Tiếp tục với Google.
Chưa nghiệm thu consent/sync Google thật. Runtime hiện có App settings cho năm
nguồn Google; Google Ads API còn cần access level của Cloud project, các API
khác cần bật/duyệt theo nguồn. Không còn yêu cầu Developer Token đã sunset.
Chỉ Customer backend được cập nhật sang `vio-google-data-admin:20261109`; giữ
Web, Primary Admin, dữ liệu, Facebook grant và snapshot. Các mốc bên dưới ghi lại
lượt triển khai khung trước khi kích hoạt Google Data.

## Kết quả triển khai

Customer Web và Customer Admin đã chạy image mới trên Docker tại
[https://localhost:8444](https://localhost:8444/workspace/integrations).
Backend schema **17**, hai container healthy. Giữ nguyên TLS/origin, secrets,
port, mount, network và mọi row nghiệp vụ/snapshot có trước deployment. Kết nối
Facebook Content và app binding cũ không đổi. Primary Admin không được recreate.
Có backup database xác minh bằng pg_restore list và hai image khôi phục riêng.
Không commit/push hoặc xóa volume, không đụng các dự án Docker cũ.

## Phần đã làm

- Giữ Facebook Content đã có dữ liệu thật, bổ sung transport Customer cho Google
  Ads, YouTube, Business Profile, Instagram, TikTok Ads; tái sử dụng GA4/GSC và Ads.
- Tất cả nguồn dùng chung quản lý trạng thái OAuth, scope, token mã hóa, chọn
  asset, initial sync và immutable snapshot. App settings Vio ở backend; không
  đưa token/secret vào Web hoặc yêu cầu client tạo app.
- Modal ba bước cho tám nguồn ngoài Content, có tìm kiếm tài khoản, chọn rõ ràng,
  đổi tài khoản đăng nhập, thông báo thiếu tài khoản/lỗi, thử lại và tiến độ sync.
  Không có email-verification Vio chen vào known connector; không thay trạng thái
  email_verified của người dùng. Session/role/CSRF/tenant/consent vẫn bắt buộc.
- Report có cover, KPI, SVG charts, mốc cập nhật, bảng chi tiết tìm kiếm/phân trang,
  ghi chú cách đọc, responsive và In/PDF. In toàn bộ hàng trong projection đã tải,
  không chỉ hàng đang lọc/trang hiện tại; projection lớn có nhãn giới hạn 200 hàng.
- Null không biến thành 0; tiền tệ giữ Decimal; không gộp tỷ lệ/unique/stock sai kỳ.
  Các chỉ số chưa thu thập không được quảng bá thành số liệu sẵn có.
- Công cụ nhập ẩn cấu hình ứng dụng và kiểm tra readiness an toàn, hướng dẫn một
  lần cho Google Data, quyền Ads theo Cloud project, Meta configurations, TikTok Business.

## Kết quả kiểm tra

| Nhóm | Kết quả |
|---|---|
| Toàn bộ pytest Web trên Windows | **492 PASS**, 6 deprecation warnings |
| Pytest Web trong image Docker candidate | **492 PASS**, 6 warnings |
| Backend connector/data/OAuth/migration 16→17 trên SQLite + PostgreSQL disposable | **74 PASS**, 6 subtests PASS |
| Catalogue Customer và bounded transport bổ sung | **6 PASS**, 3 PostgreSQL skip, 4 subtests PASS |
| Connector tests trong backend image Docker | **13 PASS**, 10 PostgreSQL skip |
| JavaScript Admin | **116 PASS** |
| Formatter tiền tệ Web | **3 PASS** |
| Python compile, JS syntax, CSS build, git diff --check | **PASS**; Browserslist database có thông báo cũ |
| Browser fixture tám nguồn còn lại | **PASS**, 1440/1280/768/390 px, không lỗi JS hoặc tràn trang |
| Empty/error/retry, tìm tên không dấu, chọn/đổi account | **PASS** |
| Print từ bảng đang lọc | **PASS**, đủ 45 hàng fixture và phục hồi bộ lọc; PDF A4 bốn trang đã render/xem |
| Browser live sau deploy | **PASS**: Facebook 16 bài, 3 chart, link bài, 5 mục báo cáo; tám modal chuẩn bị và index 9 nguồn |
| Primary Admin sau deploy | **PASS**, login/logout và bốn API đọc |
| Quét giá trị secret thực trong Git-visible text | **PASS**, 873 file; không phát hiện match; artifact private Git-ignore |

Các bài test transport dùng phản hồi giả lập và database dùng một lần. Browser
fixture chỉ ở loopback, không ghi database thật và chặn điều hướng provider.
Browser live đọc snapshot Facebook hiện có, không consent/sync/gửi email. Kết quả
này không chứng minh Google/TikTok/Instagram hoặc Ads đã kết nối tài khoản thật.

## Bộ test Admin rộng còn lỗi

Lượt `python -m unittest discover -s tests -v` chạy **816 test**, ghi nhận
**110 failures, 22 errors, 258 skips**. Một failure là assertion catalogue cũ chỉ
coi bốn nguồn đã có adapter; đã sửa theo chín nguồn và test catalogue chạy lại PASS.

Các failure/error còn lại thuộc các nhóm App, demo, Marketing release/review/
dataset/publication/verification, Platform Data, Report Bundle, runtime, SEO
composite, Viewer/hand-off. Đã chạy một test đại diện mỗi nhóm trên **migration
<=16**: 14/14 vẫn lỗi (10 failures + 4 errors), có bằng chứng guard yêu cầu client
sandbox và quy trình/route legacy. Không bỏ kiểm tra quyền hoặc sửa chức năng
phát hành để ép các fixture này xanh. Chưa kiểm chứng riêng nguyên nhân của từng
failure/error còn lại và chưa có lượt full Admin suite sạch; đây là việc còn cần
rà soát riêng, không được ghi thành toàn bộ test PASS.

Private evidence: Admin `.work/all-connectors-20261109/backend-full.log`,
`legacy-baseline.log`, `baseline-sandbox.log`, `backend-focused-final.log`,
`backend-additional.log`, `backend-container-tests.log`, `deployment-result.json`,
`browser-result.json`, `live-browser.log`, `secret-scan.json`; Web có
`.work/all-connectors-20261109/web-tests-final.log`, `container-tests.log`.

## Cần gì để thử dữ liệu thật

**Hiện chỉ Facebook Content có app settings đủ và đã có dữ liệu thật.** Tám nguồn
khác đã có code, nhưng chưa đủ App settings/permission/approval của Vio, nên UI
ghi Đang chuẩn bị. Cần một lần cấu hình cho nền tảng:

1. Google: thêm callback Data vào OAuth client và bật các API cần thiết. Có thể
   dùng cùng App với Sign-in qua helper, không dùng lại token đăng nhập.
2. Google Ads: bật API và xin access level phù hợp trong Cloud project sở hữu
   OAuth client; Developer Token đã sunset ngày 09/09/2026 và không còn là gate.
3. Meta Ads/Instagram: đúng Business Login Config ID/scopes, app roles/Live/
   Advanced Access theo điều kiện Meta. Không thay Content Config đang chạy.
4. TikTok: app Marketing API, quyền advertiser/reporting, App Secret và app-generated
   authorization URL; xác nhận callback được portal chấp nhận và approval cần thiết.
5. Chủ tài khoản tự consent/chọn asset tại Web; đối chiếu KPI với provider,
   pagination, timezone, revoke/reauth và cách ly Workspace trước khi nghiệm thu.

Hướng dẫn từng bước và lệnh PowerShell:
[CUSTOMER_CONNECTORS_SETUP_VI.md](CUSTOMER_CONNECTORS_SETUP_VI.md).

Instagram bản này chưa thu thập Insights reach/views; TikTok bản đầu là báo cáo
advertiser theo ngày; YouTube top 25 video; GBP là các tương tác đã liệt kê, chưa
thu thập Reviews. Chưa có scheduler đồng bộ định kỳ, customer report builder/
publication/share, billing, white-label hoặc production SLA. Khung báo cáo riêng
tư không thay thế luồng Published Bundle/ACL/revision hiện có.
