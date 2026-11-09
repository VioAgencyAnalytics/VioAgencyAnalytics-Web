# Customer Web HTTPS trên localhost

Meta báo “ứng dụng không sử dụng kết nối bảo mật” khi callback đang là HTTP.
Theo [Meta Login Security](https://developers.facebook.com/documentation/facebook-login/security#https),
OAuth phải dùng HTTPS và redirect URI phải khớp chính xác với danh sách đăng ký.
Không tắt Enforce HTTPS/Strict Mode để sửa lỗi này.

Chế độ Docker local dùng `https://localhost:8444`. Nó không public máy lên mạng;
các cổng Docker vẫn chỉ bind `127.0.0.1`. Không dùng Quick Tunnel cho cấu hình này.
Admin nội bộ tiếp tục chạy ở `http://localhost:8090`.

## Cấu hình một lần của Vio

Giữ callback cũ, thêm và lưu:

- Meta App đang dùng trong `CUSTOMER_DATA_META_APP_ID` → Facebook Login for
  Business → Settings → Valid OAuth Redirect URIs:
  `https://localhost:8444/auth/customer/providers/meta/callback`.
- Google OAuth Web client **Customer Identity** → Authorized redirect URIs:
  `https://localhost:8444/auth/customer/google/callback`.
- Nếu dùng Google Data OAuth GA4/GSC: đăng ký riêng
  `https://localhost:8444/auth/customer/providers/google/callback` trong client
  Data. Client này khác client đăng nhập Google.

Khách hàng không phải tạo app hoặc chỉnh Meta Developer. Để phục vụ doanh nghiệp
bên ngoài còn cần điều kiện Live/App Review/Advanced Access theo Meta; việc HTTPS
hoạt động không chứng minh ứng dụng đã được xét duyệt.

## Chuẩn bị và chạy

Từ thư mục Web, dùng Python Admin có sẵn thư viện cryptography:

```powershell
..\VioAgencyAnalytics-Admin\.venv\Scripts\python.exe scripts\prepare_customer_https.py --trust-current-user --activate
docker compose -f compose.customer.yaml -f compose.customer.https.yaml up -d --build --no-deps customer-admin web
```

Helper tạo chứng chỉ server tự ký chỉ cho **localhost**, thời hạn 90 ngày,
`CA=false` và không có quyền ký chứng chỉ. `--trust-current-user` thêm đúng chứng
chỉ đó vào kho tin cậy của người dùng Windows hiện tại, không thay kho hệ thống
hoặc tắt xác thực TLS. Key chỉ nằm trong `.work/customer-dev/tls/` bị Git/Docker
build ignore và mount read-only vào Web; không cho vào image, source hoặc API.
Không tải/chia sẻ private key. Đổi/chứng chỉ hết hạn cần cấp lại và tin cậy lại.

`--activate` giữ credential Google/Meta/SMTP/DB/service/encryption, sao lưu private
config/env cũ rồi chỉ đổi origin sang HTTPS. Luôn chạy **cả hai Compose file** ở
trên khi recreate stack HTTPS; `docker restart` vẫn giữ cấu hình đã áp dụng.

TLS kết thúc trực tiếp trong Web container, không tin `X-Forwarded-*`. Healthcheck
xác thực TLS/hostname bằng chứng chỉ và kiểm tra chuỗi BFF → Customer backend → DB.
Session/browser cookies có Secure/HttpOnly/SameSite=Lax; kiểm tra Host, Origin,
CSRF, OAuth state/browser binding/actor/client/version vẫn giữ nguyên.

Mở `https://localhost:8444/workspace/login`, đăng nhập lại rồi kết nối Facebook.
Bookmark HTTP `http://127.0.0.1:8084/workspace/...` tự chuyển sang HTTPS; HTTP
không xử lý POST, API hoặc callback và không chuyển tiếp query chứa code/state.
Không bỏ qua cảnh báo chứng chỉ nếu Windows/trình duyệt chưa tin cậy đúng cert.

## Kiểm tra và khôi phục

```powershell
docker compose -f compose.customer.yaml -f compose.customer.https.yaml ps
```

Chỉ kiểm tra consent thật bằng tài khoản người dùng tự đăng nhập trên Facebook.
Kiểm tra tự động dùng fixture không thay cho nghiệm thu quyền/Fanpage thật.

Muốn quay lại HTTP: phục hồi `config.json` và các `docker-*.env` từ đúng bản backup
trong `.work/customer-dev/https-backup`, rồi chạy chỉ `compose.customer.yaml`.
Không xóa volume hoặc tạo lại DB. Meta có thể tiếp tục từ chối callback HTTP;
khôi phục chỉ dành cho chẩn đoán local, không phải sửa HTTPS.
