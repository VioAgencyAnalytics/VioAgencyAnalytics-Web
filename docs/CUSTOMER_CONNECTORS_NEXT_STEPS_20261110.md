# Các bước mở kết nối còn lại — 10/11/2026

Tài liệu dành cho người vận hành Vio. Khách hàng chỉ đăng nhập, cấp quyền, chọn
tài khoản và đồng bộ trên Customer Web. Khách hàng không tạo ứng dụng developer.

## Trạng thái đã kiểm tra

| Nguồn | Ứng dụng Vio trong Docker | Việc ngoài Vio còn cần xác nhận |
|---|---|---|
| Facebook Content | Có; đã có snapshot thật | Giữ cấu hình và quyền đang chạy |
| Search Console | Có; đã thấy connection lưu ở trạng thái connected | API được người dùng xác nhận bật; chưa chọn website, chưa có snapshot Google |
| GA4 | Có; người dùng xác nhận đã bật API ngày 10/11 | Tự cấp quyền Google, chọn property và đồng bộ thử thật |
| YouTube | Có; người dùng xác nhận đã bật API ngày 10/11 | Tự cấp quyền Google, chọn kênh và đồng bộ thử thật |
| Google Ads | Có | Bật API và có access level phù hợp của Cloud project để đọc tài khoản thật |
| Business Profile | Có | Project được duyệt quyền GBP, bật các API và tài khoản có quyền địa điểm |
| Facebook Ads | Có; Config ID mới đã áp dụng Docker | Chưa nghiệm thu consent/ad account/sync thật |
| Instagram | Có; Config ID mới đã áp dụng Docker | Cần nghiệm thu consent/tài khoản Professional liên kết Page/sync thật |
| TikTok Ads | Chưa có App settings | Đăng ký ứng dụng Marketing API của Vio và hoàn tất phê duyệt cần thiết |

“Có ứng dụng” chỉ xác nhận cấu hình local. Không chứng minh Google/Meta/TikTok
đã bật API, duyệt app hoặc đã cấp quyền dữ liệu của một khách hàng.

## Google: bật bốn API trước

**Đã hoàn tất theo xác nhận người dùng ngày 10/11:** API GA4 và YouTube đã bật.
Các bước Enable bên dưới được giữ làm hướng dẫn cài đặt lại; hiện tiếp tục từ
bước chọn nền tảng/cấp quyền, không yêu cầu người dùng bật lại API. Chưa có
snapshot GA4/YouTube để đối chiếu số liệu thật.

1. Mở [API Library](https://console.cloud.google.com/apis/library).
2. Bấm tên project ở thanh trên cùng, chọn **wea-app-cloud**. Kiểm tra lại tên
   project mỗi khi mở link mới. Đây là project chứa OAuth client đang dùng.
3. Mở [Google Analytics Admin API](https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com),
   bấm **Enable/Bật**. Nếu đã có **Manage/Quản lý**, API này đã bật.
4. Làm tương tự với [Google Analytics Data API](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com).
5. Làm tương tự với [YouTube Data API v3](https://console.cloud.google.com/apis/library/youtube.googleapis.com).
6. Làm tương tự với [YouTube Analytics API](https://console.cloud.google.com/apis/library/youtubeanalytics.googleapis.com).
7. Giữ OAuth Web client và hai callback đã lưu; không cần tạo thêm client:
   `https://localhost:8444/auth/customer/google/callback` và
   `https://localhost:8444/auth/customer/providers/google/callback`.
8. Nếu ứng dụng đang Testing, vào **Google Auth Platform → Audience → Test users**
   và thêm tài khoản được dùng để thử. Chỉ thêm tài khoản bạn có quyền sử dụng.

Sau đó mở [Kết nối nền tảng](https://localhost:8444/workspace/integrations), chọn
GA4 hoặc YouTube → **Tiếp tục với Google** → tự đăng nhập/cấp quyền → chọn property
hoặc kênh → **Kết nối & đồng bộ**. Không cần tài khoản Google này là tài khoản
đăng nhập Vio. Gmail cá nhân và Google Workspace đều dùng được khi có đúng quyền.

Search Console chỉ cần quyền website Search Console; không đòi có GA4. GA4 cần
quyền xem property GA4; YouTube cần quyền kênh. Tài khoản đăng nhập cùng Google
không tự động có quyền mọi dịch vụ.

Tài liệu: [Analytics API quickstart](https://developers.google.com/analytics/devguides/config/admin/v1/quickstart),
[YouTube authorization](https://developers.google.com/youtube/reporting/guides/authorization/client-side-web-apps),
[Enable services](https://docs.cloud.google.com/service-usage/docs/enable-disable).

## Meta: tạo hai Configuration ID trong ứng dụng hiện có

1. Mở [Meta App của Vio](https://developers.facebook.com/apps/1831786608275511/).
   Kiểm tra đúng App ID **1831786608275511**; tên hiển thị có thể đã đổi.
2. Mở **Facebook Login for Business → Configurations/Cấu hình**. Giữ nguyên
   Content configuration đang dùng; không sửa quyền của cấu hình này.
3. Bấm **Create configuration/Tạo cấu hình**, đặt tên **Vio Facebook Ads**.
4. Chọn luồng đăng nhập doanh nghiệp thông thường và **User access token**.
   Connector này kiểm tra token USER; không dùng WhatsApp Embedded Signup hoặc
   System-user token để thay thế.
5. Chọn quyền **ads_read** và quyền truy cập ad account tương ứng nếu wizard hỏi
   loại tài sản. Không cần xin quyền chỉnh sửa quảng cáo. Hoàn tất rồi sao chép
   **Configuration ID**.
6. Tạo cấu hình thứ hai tên **Vio Instagram**, cũng dùng **User access token**.
   Chọn **pages_show_list**, **pages_read_engagement**, **instagram_basic** và
   Page/Instagram assets tương ứng nếu có. Sao chép Configuration ID thứ hai.
7. Kiểm tra trong **Settings → Valid OAuth Redirect URIs** vẫn có
   `https://localhost:8444/auth/customer/providers/meta/callback`.
8. Gắn hai ID vào cấu hình backend bằng helper dưới đây, thay phần trong dấu `< >`
   bằng ID số thật. Lệnh dùng lại App ID/Secret local hiện có; không hỏi lại secret.

```powershell
Set-Location 'D:\VioAgencyAnalytics'
& '.\VioAgencyAnalytics-Admin\.venv\Scripts\python.exe' '.\VioAgencyAnalytics-Web\scripts\configure_customer_providers.py' meta --meta-source ads --meta-config-id '<ADS_CONFIG_ID>'
& '.\VioAgencyAnalytics-Admin\.venv\Scripts\python.exe' '.\VioAgencyAnalytics-Web\scripts\configure_customer_providers.py' meta --meta-source instagram --meta-config-id '<INSTAGRAM_CONFIG_ID>'
Set-Location '.\VioAgencyAnalytics-Web'
docker compose -f compose.customer.yaml -f compose.customer.https.yaml up -d --no-deps --no-build --wait customer-admin
```

Helper chỉ kiểm tra định dạng ID và giữ App settings hiện có; không thể tự chứng
minh permissions bên Meta. Chỉ nhập ID sau khi đã kiểm tra đúng app, USER token
và quyền ở wizard. Không sao chép Content Config ID để giả vờ hai nguồn đã sẵn sàng.

Instagram cần tài khoản Professional đã liên kết Fanpage người cấp quyền quản lý.
Nếu không thấy `ads_read` hoặc các quyền Instagram trong wizard, kiểm tra use case,
Permissions and Features/App Review của app; không thay bằng permission khác tùy ý.
Ngày 10/11, người dùng xác nhận app ban đầu chưa có use case Instagram. Cách xử
lý: **Trường hợp sử dụng → Thêm trường hợp sử dụng**, thêm mục Instagram rồi
quay lại kiểm tra đủ ba quyền. Người dùng sau đó cung cấp ảnh cấu hình Instagram
đã tạo thành công với ba lựa chọn. Nếu app khác chỉ có **Unified login** và loại
token khác, cần đối chiếu flow và thêm adapter/test tương ứng trước khi áp dụng;
không tắt điều kiện token USER của connector hiện tại.
Thử bằng tài khoản thuộc app roles trong giai đoạn phát triển; phục vụ khách ngoài
nhóm thử phải đáp ứng yêu cầu Live/Advanced Access/Business của Meta.

Tài liệu: [Facebook Login for Business](https://developers.facebook.com/docs/facebook-login/facebook-login-for-business/),
[Instagram với Facebook Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/).

## Google Ads, Business Profile và TikTok

Google Ads: bật [Google Ads API](https://console.cloud.google.com/apis/library/googleads.googleapis.com)
trong cùng Cloud project, rồi mở [Google Ads API Overview](https://console.cloud.google.com/google-ads-api/overview)
để kiểm tra/nâng access level. Test access không đủ để nghiệm thu đọc tài khoản
production. Google đã sunset Developer Token ngày 09/09/2026; connector không yêu
cầu token này. [Nguồn](https://developers.google.com/google-ads/api/docs/api-policy/developer-token).

Business Profile: cần project được Google duyệt quyền API. Quota bằng 0 không có
nghĩa chỉ cần đăng nhập lại; xem [Prerequisites](https://developers.google.com/my-business/content/prereqs)
và [Limits](https://developers.google.com/my-business/content/limits). Sau khi có
access, bật Account Management, Business Information và Business Profile Performance.
Không suy ra project đã được duyệt chỉ từ việc có OAuth Client ID/Secret.

TikTok: mở [TikTok API for Business](https://business-api.tiktok.com/portal/) →
đăng ký developer → My Apps → tạo ứng dụng **Marketing API** của Vio. Cần thông
tin doanh nghiệp thật, quyền đọc advertiser/report và callback
`https://localhost:8444/auth/customer/providers/tiktok/callback`. Sau khi portal
cho phép, lấy App ID, App Secret và Advertiser authorization URL để nhập qua
`configure_customer_providers.py tiktok`. App Secret nhập ẩn trên máy, không gửi
trong chat. Nếu portal từ chối localhost, phải thống nhất domain HTTPS trước khi
thay origin/callback; không tự tắt bảo vệ HTTPS.

## Cách đọc lỗi sau bản cập nhật

- **Vio cần bật API/kiểm tra ứng dụng:** việc cấu hình của Vio; không bắt khách
  đăng nhập lại và không xóa grant đã có.
- **Chưa có đủ quyền đọc:** kiểm tra đúng tài khoản, asset và permission đã cấp.
- **Chưa có kênh YouTube phù hợp:** chọn tài khoản quản lý kênh, không nhầm token
  hợp lệ với việc tài khoản đã có kênh.
- **Giới hạn lượt đọc:** giữ kết nối, thử sau; không lặp consent.
- **Quyền hết hiệu lực:** kết nối lại bằng OAuth của nhà cung cấp.

Thông báo chỉ dùng mã lỗi được cho phép. Body lỗi, secret, token và activation
URL do provider trả về không được hiển thị cho khách. Report tiếp tục chỉ đọc
snapshot đã lưu; không sửa số thiếu thành 0 và không gọi provider khi xem/in.
