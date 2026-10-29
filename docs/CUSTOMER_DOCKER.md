# Customer Web, Admin API và PostgreSQL trên Docker

Triển khai local ngày 27/10/2026. Đây là stack Customer riêng; không sử dụng
database báo cáo KinderHealth/VIO sandbox hay các container Viewer cũ.

| Thành phần | Container | Địa chỉ |
|---|---|---|
| Customer Web | `VioAgencyAnalytics-Web` | `http://127.0.0.1:8084` |
| Customer Admin API | `VioAgencyAnalytics-Customer-Admin` | `customer-admin:8094` trong mạng Compose, không publish ra host |
| PostgreSQL | `vio-customer-postgres-dev` | `customer-postgres:5432`, host loopback `127.0.0.1:5434` |

Web giữ origin/callback Google hiện có. Bridge loopback trong Web chuyển tiếp
đến service `customer-admin` qua Docker DNS, không phụ thuộc tiến trình Windows.
Customer Admin dùng Flask/services cũ, chỉ phục vụ `/health` và
`/api/internal/customer/*`; bearer service auth và session/membership vẫn bắt buộc.
Không chạy worker Marketing hoặc mở giao diện quản trị legacy trong service này.

## Chạy và cập nhật

Hai repository cần nằm cạnh nhau trong workspace. PostgreSQL dùng volume bền vững
đã có `vio-customer-pg-data`; Compose khai báo external để tránh tạo DB trống khi
gõ sai tên. `instance/customer-dev` bên Admin được giữ làm thư mục file ứng dụng.

Từ thư mục Web:

```powershell
.\.venv\Scripts\python.exe scripts/customer_docker.py
docker compose --env-file .env.example -f compose.customer.yaml up -d --build --wait
docker compose --env-file .env.example -f compose.customer.yaml ps
```

Truy cập `http://127.0.0.1:8084/workspace/login`. Sau khi cập nhật Google/SMTP
bằng `customer_dev.py configure-google` / `configure-smtp`, chạy lại hai lệnh đầu
để tạo env riêng và recreate service với cấu hình mới. Không cần mở terminal
chạy `customer_dev.py admin` hoặc `web` nữa.

```powershell
docker compose --env-file .env.example -f compose.customer.yaml stop
docker compose --env-file .env.example -f compose.customer.yaml up -d --wait
```

Service có `restart: unless-stopped`; Docker Engine cần hoạt động. Sau khi chủ động
`stop`, dùng `up` để bật lại. Web chờ Admin healthy; Admin chờ PostgreSQL healthy.
Healthcheck Web gọi BFF session xuyên qua Admin tới DB, nên không chỉ kiểm tra
server HTTP. Google/SMTP có cấu hình không đồng nghĩa đã nghiệm thu dịch vụ thật.

## Cấu hình riêng và dữ liệu

`scripts/customer_docker.py` đọc `.work/customer-dev/config.json` hiện có và tạo:

- `docker-web.env`: cờ bật, origin, địa chỉ backend và service token; không chứa Google/SMTP/DB secret.
- `docker-admin.env`: service token, encryption key cũ, URL DB nội bộ và cấu hình Google/SMTP.
- `docker-postgres.env`: tài khoản DB hiện có.

Các file env và backup đều Git ignored; không mount vào static hoặc COPY vào image.
Không đổi encryption key, mật khẩu DB hoặc xóa volume để khắc phục lỗi kết nối.
Không dùng `down --volumes` hay khởi động đồng thời hai PostgreSQL trên cùng volume.

Container PostgreSQL tạo thủ công trước đây được dừng, đổi tên thành
`vio-customer-postgres-dev-before-compose-20261027`, đặt restart policy `no` để
giữ cấu hình tham chiếu. Container Compose sử dụng đúng volume cũ; không sao chép
dữ liệu sang DB mới. Backup custom-format và hash manifest trước chuyển nằm tại
`.work/customer-dev/customer-before-compose-20261027.dump` và
`.work/customer-dev/docker-db-before.json`. Backup chỉ chứa dữ liệu nội bộ.

## Kiểm tra triển khai

- Đối chiếu tất cả 45 bảng trước/sau chuyển và sau dừng/bật toàn stack, bao gồm
  account/Workspace, session, OAuth transaction và revision cũ.
- Kiểm tra endpoint Customer qua Web, cookie, CSRF và service boundary.
- Test trình duyệt tài khoản/Workspace/tour dùng tài khoản QA có tên rõ, không gửi email.
- Các test PostgreSQL cần schema/DB dùng riêng; không đặt `TEST_DATABASE_URL`
  thành database `vio_customer` đang phục vụ người dùng.

Tắt container không xóa tài khoản/Workspace. Rollback ứng dụng phải giữ cùng
volume/key và migration; không chạy cả container PostgreSQL dự phòng và hiện tại.

## Kết quả xác minh 27–28/10/2026

- Ba service chạy healthy; API session và trang login qua Web trả HTTP 200.
- Ngày 28/10, sau Docker Engine khởi động lại, chạy `up --wait` và xác nhận lại
  cả chuỗi Web → Admin → DB. Google và SMTP vẫn báo đã cấu hình; không gửi email
  hoặc chạy Google consent thật trong kiểm thử Docker này.
- Trước/sau chuyển Compose và sau stop/up toàn stack: count/hash của cả 45 bảng
  giống nhau, giữ 12 tài khoản và 13 Workspace ban đầu. Migration cao nhất là 10.
- Browser acceptance 1440px/390px: đăng ký, tạo Workspace, tour 8 bước, lưu/reload,
  bỏ qua, replay, logout/login đều PASS; không có lỗi JavaScript. Kiểm thử này thêm
  2 tài khoản QA `tour-qa-…@example.invalid` và 2 Workspace QA; hiện có 14 tài khoản,
  15 Workspace. Không xóa dữ liệu người dùng để dọn kiểm thử.
- Web Python: 359 PASS. Admin Python chạy trên đúng image không nạp `.env`
  vận hành: 590 test, 433 PASS và 157 SKIP do thiếu PostgreSQL test riêng.
- Kiểm tra boundary trên container thật: health 200, private API thiếu service
  auth 401, root/legacy Bundle API 404. Env Web không có Google/SMTP/DB/encryption key.
- Admin UI: 102 PASS / 0 FAIL; JS syntax và Git whitespace checks PASS. Kiểm thử được cập nhật
  theo 8 liên kết chính + 2 mục planned; route phụ vẫn kiểm tra qua menu cha,
  không bỏ kiểm tra provider hoặc quyền Viewer.

Ảnh/kết quả trình duyệt nằm trong `.work/customer-tour-qa/` bên Web; log Python/UI
nằm trong `test-results/customer-docker-*.log` bên Admin, đều Git ignored.
Lần chạy Python trực tiếp trên Windows bị ảnh hưởng bởi `.env` vận hành và không
được dùng làm acceptance. Dùng image không chứa `.env` để kiểm tra backend sạch:

```powershell
# Chạy từ thư mục Admin; không truyền env/volume dữ liệu customer vào container test.
docker run --rm --mount "type=bind,source=$($PWD.Path)/tests,target=/app/tests,readonly" --entrypoint python vioagencyanalytics-customer-admin:local -m unittest discover -s tests -q
```
