# Admin → New: chuyển phiên và dữ liệu trên dashboard hiện có

Cập nhật 13/10/2026. Working tree: `D:\KDH-Report-All\KDH-Report-Admin` và
`D:\KDH-Report-All\KDH-Report-New`. Không phải hai đường dẫn cũ ở ổ D gốc.

## Hành vi

Trong `/marketing`, chọn chính xác Report ID/revision và bấm **Mở báo cáo**.
New khởi tạo giao dịch, Admin xác thực phiên đang có, New nhận phiên Viewer riêng
và mở thẳng `/reports/{report_id}?revision=N`. Không qua danh sách `/reports`
và không hỏi lại mật khẩu khi cùng trình duyệt còn phiên Admin hợp lệ.

Admin hết phiên: đăng nhập trên trang Admin rồi quay lại đúng giao dịch/báo cáo.
Giao dịch sống 10 phút; quá thời gian phải mở lại từ Admin. Không tự chọn revision mới nhất.
Draft không có nút mở published; giao diện giải thích điều kiện xuất bản còn thiếu.
**Xem trước nội bộ** đi qua `/internal-preview/{candidate_id}`, có nhãn chưa xuất bản,
chỉ quyền Admin, không tạo publication hay grant. `/login` và `/reports` vẫn phục vụ
người truy cập trực tiếp; quyền khách hàng do Admin kiểm tra.

Các trang `/reports/...` dùng lại `layouts/dashboard.html` và sáu template gốc:
Overview, SEO, Facebook Ads, Facebook Content, TikTok, YouTube. Giữ CSS/font/icon,
sidebar/menu con, header, grid KPI và vùng biểu đồ/bảng/phễu/nhận định của các trang đó.
Nhánh Bundle thay số và nội dung mẫu; script mock riêng của các trang không được nạp.
Các URL mock `/overview`, `/report/...`, `/api/reports/...`, video mock API bị chặn
ở production. GMB chưa có trang thiết kế hoàn chỉnh, dùng trạng thái dữ liệu thiếu
trong cùng dashboard shell.

## Bảo vệ phiên

1. New backend tạo state và verifier ngẫu nhiên; gửi challenge SHA-256 cho Admin
   bằng Internal API có Bearer service token. Callback/audience lấy từ cấu hình.
2. Cookie giao dịch HttpOnly, SameSite=Lax ràng buộc trình duyệt; HTTPS dùng
   `__Host-kdh_handoff`, Secure. Không chép cookie Admin qua JavaScript.
3. Admin kiểm tra phiên, user, client, report, revision, mode, ACL và Publishing Guard
   trước khi cấp mã ngẫu nhiên 48 byte, thời hạn **60 giây**. Chỉ lưu hash mã.
4. Mã trả về fragment của callback. Fragment không đi vào HTTP request/access log;
   script cục bộ xóa fragment bằng `replaceState` trước khi POST mã. Callback có
   no-referrer, no-store, CSP; không tải tài nguyên ngoài. URL cuối chỉ có report/revision.
5. Callback kiểm tra Origin, state và cookie binding; New backend đổi mã với Admin
   qua Bearer. Admin kiểm tra PKCE, state, hạn dùng và phạm vi lần nữa. Redeem nguyên tử
   bằng transaction SQLite/PostgreSQL; hai request đồng thời chỉ một request thành công.
6. Admin cấp token Viewer riêng, chỉ lưu hash, gắn phiên gốc và đúng target/revision/mode.
   Token này không đăng nhập được vào Admin. New đổi cookie Viewer và CSRF khi thành công.
   Cookie Viewer tối đa 8 giờ; phía server không cho phép vượt hạn phiên gốc.
7. Mỗi lần đọc báo cáo/preview đều kiểm tra lại phiên gốc, trạng thái tài khoản,
   role, grant và guard. Khóa user, thu hồi phiên/grant hoặc mất quyền chặn lần đọc kế tiếp.
   Đây không phải cơ chế đẩy để xóa nội dung đã tải trong tab đang mở.

New đang có tài khoản khác: trả **409**, giữ nguyên tài khoản đó, hướng dẫn đăng xuất
New rồi mở lại từ Admin. Cùng tài khoản: đổi phiên được ủy quyền cũ sang phiên mới.
Đăng xuất New với token được ủy quyền chỉ thu hồi token đó; đăng xuất Admin làm token
được ủy quyền mất hiệu lực. Token bị pin phạm vi nên mở report/revision khác cần một
giao dịch mới; danh sách của token này chỉ chứa phạm vi đó.

Không nhận `next` URL tùy ý; không đưa mật khẩu, service token, provider token,
Admin session hoặc hash phiên vào URL/frontend. Migration **8** thêm hai bảng
`viewer_handoffs`, `delegated_viewer_sessions`; không thay migration cũ, Dataset hay Bundle.

## Cấu hình URL

| Repo / biến | Local mặc định | Mục đích |
| --- | --- | --- |
| Admin `APP_URL` | `http://localhost:8090` | Origin public Admin; Origin validation và nơi trình duyệt có cookie Admin |
| Admin `REPORT_NEW_BASE_URL` | `http://localhost:8080` | Allowlist audience và callback New |
| New `REPORT_ADMIN_PUBLIC_URL` | `http://localhost:8090` | Trình duyệt đi đến Admin |
| New `REPORT_NEW_PUBLIC_URL` | `http://localhost:8080` | Origin New, cookie giao dịch và callback |
| New `REPORT_ADMIN_BASE_URL` | `http://admin:8090` trong Compose | Backend New gọi Admin qua network Docker |
| Hai repo `REPORT_SERVICE_TOKEN` | Giá trị server hiện có, giống nhau | Xác thực Internal API; không đưa xuống frontend |

Hai cặp public URL phải trùng khớp tuyệt đối, không path/query/fragment. Bên ngoài
loopback yêu cầu HTTPS; đặt `COOKIE_SECURE=1` cho Admin HTTPS. Cấu hình proxy phải
truyền đúng scheme/host để ứng dụng nhận biết origin public. Không đặt Docker hostname
`admin` vào URL public. Điểm bắt đầu chuẩn hóa sang origin cấu hình trước khi tạo
giao dịch/đọc cookie. Phiên đã đăng nhập trên host khác không tự trở thành cookie của
host cấu hình; nên đăng nhập và sử dụng cùng URL canonical. `.env` thật chưa bị chỉnh.

## Bảng ánh xạ component

Luồng: `AdminViewerRepository → BundleService → BundleViewMapper → dashboard_context`
→ partial gốc. `W(id)` bên dưới là `sections[section].data.widgets[]` có `metric_id=id`
đã được Admin phát hành. Snapshot thông thường có thể dùng
`data.sources[source].kpis[]` hoặc `totals[key]` với source/key tương ứng.
Mapper yêu cầu đúng source, không chọn metric trùng/không rõ nguồn. Các mã chưa có
trong Catalog chỉ là vị trí nhận giá trị tường minh trong tương lai, không được tính bù.

| Component hiện có | Bundle field / ID | Đơn vị | Thiếu dữ liệu |
| --- | --- | --- | --- |
| Header/kỳ/nhãn trạng thái | `report`, `period`, `comparison`, `freshness` | Ngày; revision | Ghi chưa có thời điểm/kỳ so sánh; preview không mang nhãn final |
| Sidebar/menu con | `navigation.sections`, `default_section` | Section key | Giữ menu, vô hiệu hóa kênh không được phép; URL trực tiếp trả 404 |
| Overview: 5 KPI | W(`marketing.reach`, `traffic`, `engagement`, `leads`, `spend`) | Đơn vị được chốt; tiền tệ phải có mã nếu muốn hiển thị mã | Không cộng số liệu các kênh thành tổng Marketing |
| Overview: hai badge | W(`marketing.conversion_rate`, `marketing.kpi_completion`) | Ratio/percent theo snapshot | Không giữ tỷ lệ 1,82% / đạt 114,2% mẫu |
| Overview: card từng kênh | KPI tương ứng của section được Bundle cho phép | Theo từng metric | Card vẫn có trạng thái thiếu; không suy diễn tăng trưởng |
| SEO: 6 KPI đúng vị trí | W(`gsc.impressions`, `gsc.clicks`, `ga4.organic_users`, `keywords.top10`, `seo.leads`, `seo.conversion_rate`) | Lượt/người/từ khóa/Leads/ratio | `active_users` không thay `organic_users`; không tự suy ra Leads/CR |
| Facebook Ads: 6 KPI đúng vị trí | W(`facebook_ads.spend`, `reach`, `link_clicks`, `leads`, `cpl`, `lead_conversion_rate`) | Tiền/lượt/Leads/ratio | `clicks` không thay `link_clicks`; CR không được chia lại từ Leads/Clicks |
| Facebook Content: 6 KPI | W(`facebook_content.posts_published`, `reach`, `engagements`, `engagement_rate`, `followers_gained`, `link_clicks`) | Bài/lượt/ratio/người | `post_clicks` không thay nhấp liên kết |
| TikTok: 6 KPI đúng vị trí | W(`tiktok_ads.spend`, `reach`, `clicks`, `video_views`, `leads`, `cost_per_lead`) | Tiền/lượt/Leads/tiền | `conversions` không thay Leads; `cost_per_conversion` không thay CPA/Lead |
| YouTube: 6 KPI | W(`youtube.views`, `watch_time_minutes`, `subscribers_gained`, `impressions`, `impressions_ctr`, `average_view_duration`) | Lượt/phút/người/lượt/ratio/giây | Giữ đơn vị snapshot, không mặc định phút là giờ |
| Giá trị kỳ trước dưới KPI | `widgets[].comparison.previous_value` hoặc source `previous` | Cùng đơn vị KPI | Dấu —; không tự tính % tăng/giảm hay gắn đánh giá tốt/xấu |
| Biểu đồ tại vùng chart cũ | Source `daily[]`, `channels[]`, `charts[]`; so sánh widget đã chốt | Mỗi lựa chọn một unit/thang đo | Null tạo khoảng trống; ngày trùng/sai bị loại khỏi chart và có cảnh báo; không thêm 0 |
| SEO: bảng từ khóa | Bảng nguồn có `keyword`; các cột `url`, `previous_position`, `position`, `change`, `clicks`, `impressions`, `ctr` | Vị trí/lượt/ratio theo cột | Giữ cột, ô thiếu không suy ra từ traffic |
| SEO: bảng landing page | Bảng có `pagePath`/`landingPage`; `activeUsers`, `clicks`, `leads`, `cr` | Người/lượt/Leads/ratio | Không join/cộng nguồn để lấp ô |
| Facebook Ads: bảng chiến dịch | `campaigns`/bảng có `campaign_name` hoặc `name`; objective/spend/reach/clicks/leads/cpl/assessment | Unit của cột nếu có | Số hàng thực; không giữ ngân sách/CPL/cảm nhận mẫu |
| Facebook Content: bảng bài viết | `posts`/bảng có title/post_id; date/format/reach/engagement/engagement_rate/comments/shares/clicks | Theo cột | Cột/row thiếu hiển thị phù hợp; không giữ “48 bài” mẫu |
| TikTok: bảng chiến dịch | `rows`/`campaigns` có campaign_name/campaign_id; spend/reach/views/clicks/leads/cpa/status | Theo cột | Không gắn nhãn hiệu quả nếu snapshot không có |
| YouTube: bảng video | `videos`/`rows` có title/video_id; date/views/average_view_duration/ctr/subscribers_gained | Theo cột | Không giữ thumbnail hoặc “4 video” mẫu |
| SEO: sáu bước phễu | W(gsc.impressions/clicks, ga4.organic_users, seo.service_page_views/leads/appointments) | Từng chỉ số | Giữ sáu ô; chưa xác lập hành trình hay tỷ lệ giữa nguồn |
| Facebook Ads: phễu/chi phí | W(impressions/link_clicks/landing_page_views/leads/appointments; cpc/cpl/appointment_cpa) | Lượt/tiền | Giữ các bước và ô chi phí; không mặc định conversions là lịch hẹn |
| TikTok/YouTube: phễu | Metric tường minh của từng bước thuộc đúng source | Lượt | Giữ vùng/bước; không vẽ % ước tính khi không có tỷ lệ được chốt |
| Evidence/nhận định | `evidence` hoặc release `evidence_cards`, `review_status=approved`; release yêu cầu provider_origin_confirmed | Nội dung được duyệt | Không đưa câu nhận định mẫu; không suy ra Top từ traffic |
| Opportunity/kế hoạch | `opportunities` đã duyệt trong release | Nội dung/hành động/điều kiện | Giữ khối cũ với thông báo chưa có đề xuất |
| Creative, audience, topic, phân bổ, tiến độ, retention chưa có contract phù hợp | Không có dữ liệu đủ nghĩa trong snapshot | — | Giữ vùng thiết kế, hiển thị unavailable; không tự gọi provider |

`0` vẫn hiển thị 0, `null` là chưa có dữ liệu. Ratio 0–1 chỉ nhân 100 để định dạng
phần trăm, không tính KPI kinh doanh. Tiền thiếu mã có nhãn “tiền tệ (chưa có mã)”;
không giả định VND. Reach/Users/Position không được cộng. Các bảng của từng nguồn
không được dùng để tự tạo tổng; các dòng giữ nguyên phạm vi snapshot.

## Tương tác

- Chuyển section/menu con giữ report/revision. Không gọi lại API mock.
- Tìm kiếm, sắp xếp, phân trang và popup hàng đọc dữ liệu snapshot đang có.
  Popup ghi Report ID/revision; số hàng phản ánh đúng phạm vi đang hiển thị.
- Bộ ngày chỉ lọc điểm/hàng có ngày trong kỳ snapshot. KPI tổng giữ nguyên toàn kỳ.
  Nút kỳ nhanh giải thích giới hạn, không nhân số mẫu theo số ngày.
- PDF dùng trình in của trình duyệt. Excel trong menu xuất file CSV tương thích
  bảng tính, chỉ gồm các hàng đang thấy, có Report ID/revision/kỳ; chống formula injection.
- Các nút tạo chiến lược/báo cáo mới/thư viện chưa có dữ liệu hiển thị giới hạn trong
  dialog cũ, không phát sinh báo cáo, publication hoặc grant.

## Kiểm thử và ảnh

Chạy với SQLite tạm, PostgreSQL `kdh-handoff-qa-postgres` riêng ở 5434 dùng tmpfs,
HTTP fixture Admin 8093/New 8084 và Chrome headless profile riêng. Không ghi fixture
vào DB/volume KinderHealth, không sử dụng cookie trình duyệt của người dùng.

- New: `212 passed`, không skip; bốn deprecation warning từ thư viện/API template cũ.
  Log `.work/handoff-tests-final.txt`.
- Admin: lượt đầy đủ mới nhất chạy **328 tests**, **326 PASS / 2 FAIL / 0 SKIP**.
  Hai lỗi OAuth fixture bị ảnh hưởng bởi cấu hình Meta sandbox local; đã cố định
  môi trường của fixture, giữ nguyên `.env`. Chạy lại toàn nhóm Meta trên cả SQLite
  và PostgreSQL: **34 PASS / 0 FAIL / 0 SKIP**, bao gồm hai case từng lỗi.
  Không tuyên bố đã chạy lại toàn bộ 328 sau sửa fixture. Log:
  `test-results/handoff-full-python-current.txt`, `handoff-meta-fixture-final.txt`.
  Trước các thay đổi Meta bổ sung, toàn bộ 317 tests đạt, không skip. Trong lượt 328,
  cả 22 case handoff (11 × hai database) đều đạt.
- Frontend Admin: **69 PASS / 0 FAIL / 0 SKIP**, log `test-results/handoff-ui-final.txt`.
  Harness được bổ sung module Meta mới và endpoint đọc tài sản tương ứng để giữ
  kiểm thử đúng working tree hiện tại. Syntax JS và `git diff --check` hai repo đạt.
- Browser: `test-results/dashboard-binding/e2e-result.json` và `paired-result.json`
  trong Admin. Bao gồm click đúng revision, không login New, preview riêng, logout,
  thu hồi phiên gốc, hết phiên rồi login quay lại, hình chart đổi khi series đổi,
  filter/export không gọi mock, responsive 1440/768/390.

Fixture đối chiếu `scripts/qa_dashboard_fixture.py` dùng cùng bộ số đã lưu của thiết kế
gốc cho cả hai nhánh, cùng tập section và viewport. Chỉ script QA import mock; production
không dùng nó. Hai cách biểu diễn vẫn khác nhau có chủ đích ở nhãn trạng thái, số
thiếu, nhận định chưa duyệt và chart từ series thay cho đường SVG mẫu; không tuyên bố
pixel-identical. Bảng keyword đổi tên cột bằng ánh xạ, không tính lại số.

Ảnh trong `../../KDH-Report-Admin/test-results/dashboard-binding/`:

- `paired-original-{channel}-{width}.png` ↔ `paired-bound-{channel}-{width}.png`:
  sáu kênh × ba viewport, thêm ảnh bảng SEO.
- `e2e-report-{width}.png`, `e2e-details-{width}.png`, `e2e-source-popup.png`.
- `after-published-{width}.png`: no-data; `e2e-preview.png`: nhãn preview;
  `e2e-revoked-session.png`, `e2e-expired-admin-login.png`: phiên hết hiệu lực;
  `e2e-forbidden-section.png`: section không được Bundle cho phép.

## File và giới hạn

Admin: `kdh/viewer_handoff.py`, `viewer_access.py`, migration 8, đăng ký router trong
`app.py`, `static/marketing.js`, `templates/marketing.html`, login handoff và tests.
New: router `handoff.py`/`viewer.py`/`published.py`, mapper `dashboard.py`/`bundle.py`,
`MetricView.source_key`, các partial gốc, `snapshot.js`/`snapshot.css`, callback script,
cấu hình public URL, tests và script QA. Các file local đã có trước và thay đổi Meta
bổ sung bên Admin được giữ nguyên; không reset/clean, commit/push hay sửa `.env`.

Đã kiểm chứng luồng và bảo mật bằng fixture, không nghiệm thu dữ liệu/permission
provider thật. Các nguồn/metric chưa có release phù hợp vẫn unavailable. Việc có
template hoặc adapter Meta riêng không có nghĩa đã đồng bộ/duyệt số liệu thật.
Mở tab cũ của một revision vẫn đọc snapshot bất biến; không sync provider tại New.

## Build và đưa vào runtime

Đợt này chỉ build image kiểm thử `kdh-report-admin:handoff-qa` và
`kdh-report-new:handoff-qa`; không thay container/volume đang dùng. Trước khi nâng cấp
runtime: xác nhận backup DB đọc được, giữ các file local, kiểm tra các cặp URL và
service token server, giữ nguyên ENCRYPTION_KEY. Không `down -v`.

Lệnh đúng service hiện có, chạy khi đã sẵn sàng nâng cấp:

```powershell
Set-Location D:\KDH-Report-All\KDH-Report-Admin
docker compose up -d --build admin
Set-Location D:\KDH-Report-All\KDH-Report-New
docker compose up -d --build app
```

Sau build kiểm tra module/router trong image/container, migration 8 và đường
`/auth/handoff/start`, `/auth/handoff/callback`, `/viewer/authorize`. Sau đó thử click
thực từ phiên Admin hợp lệ với report đã được phép xuất bản. Healthy đơn thuần không
thay cho kiểm tra auth, quyền, guard, dashboard và request mạng trên trình duyệt.

Để lặp lại QA local: chạy `scripts/serve_handoff_qa.py` mỗi repo, rồi trong Admin chạy
`node scripts/handoff-browser.mjs`. Ảnh đối chiếu: chạy New `scripts/serve_dashboard_qa.py`,
sau đó Admin `node scripts/dashboard-browser.mjs paired`. Các server chỉ bind loopback.
