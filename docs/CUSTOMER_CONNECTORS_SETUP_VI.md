# Kết nối chín nền tảng của Vio

Cập nhật 09/11/2026. Đây là hướng dẫn cho **người vận hành Vio**. Khách hàng không
phải tạo ứng dụng, xin Developer Token hoặc nhập API key. Họ chỉ chọn nền tảng,
đăng nhập tại nhà cung cấp, cấp quyền, chọn tài khoản và xem kết quả đồng bộ.

## Khung chức năng

| Nguồn | Đăng nhập / chọn tài khoản | Nội dung báo cáo đã có mapping |
|---|---|---|
| Facebook Content | Facebook → Fanpage | Bài đăng, bộ đếm lifetime, Page Insights; báo cáo Content riêng |
| Facebook Ads | Facebook → Ad Account | Chi phí, hiển thị, nhấp, lead, CTR/CPC, chiến dịch |
| Instagram | Facebook → tài khoản chuyên nghiệp liên kết Page | Bài trong kỳ, lượt thích/bình luận lifetime, follower stock; không suy ra reach hoặc views |
| Google Analytics 4 | Google → GA4 Property | Người dùng, phiên, lượt xem, tương tác, kênh và trang |
| Search Console | Google → website được cấp quyền | Clicks, impressions, CTR, vị trí trung bình, truy vấn |
| Google Ads | Google → tài khoản trực tiếp hoặc trong MCC được cấp quyền | Chi phí chính xác từ micros, impressions, clicks, conversions, CTR/CPC, chiến dịch |
| YouTube | Google → kênh quản lý | Views, phút xem, đăng ký mới, thời lượng xem TB, 25 video nổi bật |
| Google Business Profile | Google → địa điểm | Nhấp website, nhấp nút gọi, chỉ đường, hiển thị Search/Maps trên di động |
| TikTok Ads | TikTok for Business → advertiser | Chi phí, hiển thị, nhấp đến đích, chuyển đổi, CTR/CPC theo ngày |

Có transport không đồng nghĩa nhà cung cấp đã duyệt ứng dụng hoặc đã thử dữ liệu
thật. Mỗi nguồn chỉ hiện nút kết nối khi có cấu hình ứng dụng phù hợp. Facebook
Content là nguồn đã được người dùng thử thật trước lượt mở rộng này. Các nguồn
khác cần nghiệm thu consent, tài khoản, đối chiếu KPI và pagination riêng.

Không dùng tài khoản đăng nhập Google của Vio làm quyền Marketing. Có thể dùng
cùng OAuth **application** nhưng transaction và token dữ liệu vẫn riêng. Không
sao chép token Admin legacy hoặc consent của khách hàng này sang khách hàng khác.

## 1. Google dùng chung cho GA4, GSC, YouTube, Business Profile và Google Ads

Trong Google Cloud project của Vio:

1. Bật Analytics Admin API, Google Analytics Data API, Search Console API,
   YouTube Data API v3 và YouTube Analytics API. Với Business Profile, cần quyền
   truy cập project/API phù hợp và bật Account Management, Business Information,
   Business Profile Performance. Bật Google Ads API khi triển khai Ads.
2. Google Auth Platform → Clients → Web OAuth client. Thêm callback dữ liệu:
   `https://localhost:8444/auth/customer/providers/google/callback`.
   Giữ callback đăng nhập hiện tại
   `https://localhost:8444/auth/customer/google/callback`.
3. Audience → thêm tài khoản kiểm thử trong giai đoạn Testing. Chuẩn bị thông tin
   thương hiệu, privacy policy và verification cho các scope cần duyệt trước khi
   cho khách hàng ngoài nhóm thử nghiệm sử dụng.
4. Nhập Client ID/Secret của ứng dụng Vio qua công cụ local. Secret nhập ẩn:

```powershell
Set-Location 'D:\VioAgencyAnalytics'
& '.\VioAgencyAnalytics-Admin\.venv\Scripts\python.exe' '.\VioAgencyAnalytics-Web\scripts\configure_customer_providers.py' google
```

Nếu chủ động chọn dùng cùng ứng dụng đang đăng nhập Google, không phải nhập lại
secret hoặc tạo client mới:

```powershell
& '.\VioAgencyAnalytics-Admin\.venv\Scripts\python.exe' '.\VioAgencyAnalytics-Web\scripts\configure_customer_providers.py' google --reuse-signin-google-app
```

Lệnh chỉ sao chép application settings vào cấu hình backend; không đọc hoặc sao
chép session/token Sign-in. Chạy sau khi đã thêm callback dữ liệu và bật các API.

Scope được xin riêng theo nguồn, không xin toàn bộ cùng lúc:
`analytics.readonly`, `webmasters.readonly`, `youtube.readonly` +
`yt-analytics.readonly`, `business.manage`, `adwords`.
Business Profile và Google Ads không có scope chỉ đọc tương đương cho toàn bộ
chức năng này; code Vio chỉ gọi các endpoint đọc đã khai báo, không tạo/sửa quảng
cáo hoặc hồ sơ doanh nghiệp.

Tài liệu chính thức: [Google OAuth web flow](https://developers.google.com/identity/protocols/oauth2/web-server),
[YouTube Analytics reports](https://developers.google.com/youtube/analytics/reference/reports/query),
[Business Profile prerequisites](https://developers.google.com/my-business/content/prereqs).

## 2. Google Ads — quyền API thuộc Google Cloud project

Google đã sunset Developer Token ngày **09/09/2026**. Với Google Ads API, quyền
truy cập hiện gắn với Cloud project sở hữu OAuth client. Hướng dẫn đăng ký token
ở MCC/API Center trước đây không còn áp dụng cho connector này.

1. Dùng Cloud project chứa Google Data OAuth client của Vio, bật **Google Ads API**.
2. Mở [Google Ads API Overview](https://console.cloud.google.com/google-ads-api/overview).
   Project mới bật API có Test access; cần mức phù hợp cho tài khoản thật.
3. Trong Upgrade access level, yêu cầu **Explorer access** nếu được Google cung
   cấp. Nếu nhu cầu vượt quyền/hạn mức này, thực hiện quy trình nâng cấp của Google.
   Quyền truy cập API không thay thế quyền của người dùng trên tài khoản Ads.
4. Sau khi đã cấu hình Google Data ở mục 1, đặt phiên bản connector (không hỏi token):

```powershell
& '.\VioAgencyAnalytics-Admin\.venv\Scripts\python.exe' '.\VioAgencyAnalytics-Web\scripts\configure_customer_providers.py' google-ads
```

Khách hàng vẫn tự đăng nhập Google và cấp quyền tài khoản của họ. MCC routing
được backend khám phá từ đúng grant; trình duyệt không gửi `login-customer-id`
tùy ý. Connector không yêu cầu hoặc gửi header developer-token. Token cũ còn
trong cấu hình local không được dùng làm gate hoặc tính vào binding consent.

Tài liệu: [Thông báo sunset Developer Token](https://developers.google.com/google-ads/api/docs/api-policy/developer-token),
[Access levels theo Cloud project](https://developers.google.com/google-ads/api/docs/api-policy/access-levels).

## 3. Facebook Ads và Instagram — giữ ứng dụng Facebook Content hiện có

Trong ứng dụng Meta của Vio, chuẩn bị Facebook Login for Business configuration
phù hợp cho từng nguồn. Giữ nguyên Content Config ID đang dùng, không thay scope
của nguồn Content chỉ để thêm Ads/Instagram.

- Callback: `https://localhost:8444/auth/customer/providers/meta/callback`.
- Facebook Ads: cấu hình USER token với `ads_read`; nghiệm thu asset Ad Account.
- Instagram: cấu hình USER token với `pages_show_list`, `pages_read_engagement`,
  `instagram_basic`; tài khoản Instagram Professional phải liên kết Page được
  người đăng nhập quản lý. Connector hiện đọc media và follower stock; không
  quảng bá Instagram Insights reach/views nếu chưa có collector tương ứng.
- Kiểm tra App Review, Advanced Access, chế độ Live và điều kiện Business theo
  yêu cầu của Meta trước khi khách hàng ngoài app roles sử dụng.

Nhập App settings và đúng Config ID; để trống trường đã có để giữ nguyên:

```powershell
& '.\VioAgencyAnalytics-Admin\.venv\Scripts\python.exe' '.\VioAgencyAnalytics-Web\scripts\configure_customer_providers.py' meta --meta-source ads
& '.\VioAgencyAnalytics-Admin\.venv\Scripts\python.exe' '.\VioAgencyAnalytics-Web\scripts\configure_customer_providers.py' meta --meta-source instagram
```

Nếu dùng app khác với Content đang chạy, cần chủ động đánh giá ảnh hưởng
reconnect. Không dùng tùy chọn reuse Primary để đoán Instagram Config ID.

Tài liệu: [Instagram API với Facebook Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/),
[Meta App Review](https://developers.facebook.com/docs/app-review/).

## 4. TikTok Ads — ứng dụng Marketing API của Vio

1. Đăng ký TikTok for Business và developer tại
   [TikTok API for Business](https://business-api.tiktok.com/portal/).
2. My Apps → tạo developer app cho **Marketing API**; cung cấp thông tin doanh
   nghiệp, website/privacy policy và mô tả chỉ dùng đọc báo cáo cho tài khoản đã
   cấp quyền. Xin quyền đọc advertiser và Reporting/Consolidated Report cần thiết.
3. Đăng ký callback Vio:
   `https://localhost:8444/auth/customer/providers/tiktok/callback`.
   Tài liệu Authorization hiện có mô tả localhost, trong khi FAQ cũ nêu yêu cầu
   địa chỉ công khai. Xác nhận ngay tại portal app của bạn. Nếu portal từ chối
   localhost, dùng domain HTTPS ổn định cho môi trường thử, cập nhật origin/callback
   đồng bộ theo quy trình triển khai; không đổi sang HTTP hoặc tắt bảo vệ callback.
4. Lấy App ID, App Secret và **Advertiser authorization URL** do portal sinh với
   đúng callback. Đợi xét duyệt cần thiết của TikTok.
5. Nhập cấu hình ứng dụng bằng công cụ local (App Secret nhập ẩn):

```powershell
& '.\VioAgencyAnalytics-Admin\.venv\Scripts\python.exe' '.\VioAgencyAnalytics-Web\scripts\configure_customer_providers.py' tiktok
```

Backend dùng `auth_code` Marketing của advertiser, kiểm tra state và browser
binding; không dùng TikTok Login Kit hoặc token creator thay cho Ads. Reporting
dùng POST v2.0. Long-term advertiser token chỉ nằm trong kho mã hóa backend.
TikTok có thể yêu cầu chính người cấp quyền xác nhận danh tính tại TikTok; Vio
không bỏ qua bước bảo vệ của nhà cung cấp.

Tài liệu: [Advertiser authorization](https://business-api.tiktok.com/gateway/docs/index?doc_id=1738373141733378&language=ENGLISH),
[v2.0 API reference](https://business-api.tiktok.com/portal/docs/api-reference/v2.0),
[Synchronous report](https://business-api.tiktok.com/portal/docs/run-a-synchronous-report/v2.0).

## 5. Áp dụng cấu hình và thử tài khoản thật

Kiểm tra cấu hình local, không in secret:

```powershell
& '.\VioAgencyAnalytics-Admin\.venv\Scripts\python.exe' '.\VioAgencyAnalytics-Web\scripts\customer_connector_status.py'
```

Sau khi nhập app settings, recreate đúng Customer Admin với **cả hai Compose**:

```powershell
Set-Location 'D:\VioAgencyAnalytics\VioAgencyAnalytics-Web'
docker compose -f compose.customer.yaml -f compose.customer.https.yaml up -d --no-deps --no-build --wait customer-admin
```

Không chạy `down --volumes`. Không dùng một mình base Compose để tránh mất HTTPS.

Mở [Kết nối nền tảng local](https://localhost:8444/workspace/integrations).
Chọn nguồn → tiếp tục với nhà cung cấp → chọn tài khoản → kết nối & đồng bộ.
Sau lần đồng bộ thành công, chọn **Xem báo cáo**. Trang dữ liệu chỉ đọc snapshot;
không gọi provider API khi xem hoặc in. Nút In/PDF dùng chức năng in trình duyệt,
không tạo link báo cáo public và không phát hành Published Bundle.

Mỗi nguồn cần kiểm chứng: đúng tài khoản/phạm vi, hủy consent, thiếu quyền,
không có asset, token hết hạn, ngày không có quan sát, tiền tệ/múi giờ, pagination,
đối chiếu KPI với provider và cách ly một Workspace khác. Ban đầu đồng bộ 30 ngày
đã kết thúc; các lần mới do khách yêu cầu. Chưa có scheduler đồng bộ định kỳ,
billing, white-label hoặc bảo đảm production SLA trong lượt mở rộng này.
