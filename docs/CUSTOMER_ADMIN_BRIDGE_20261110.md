# Web ↔ Admin Customer — 10/11/2026

Đã cập nhật Web Docker `vio-bridge-web:20261110` cùng Customer Admin và Primary
Admin; public origin/callback giữ nguyên. Database và snapshot/KPI không đổi.

Web giữ thao tác khách hàng và BFF; Customer Admin giữ OAuth/token, quyền,
queue/worker, snapshot và KPI target/revision. Primary Admin chỉ giám sát
metadata qua credential riêng; Published Bundle/Viewer giữ luồng quyền hiện có.

Chín source ID dùng chung giữa consent và báo cáo:
`facebook_content`, `facebook_ads`, `instagram`, `ga4`, `gsc`, `google_ads`,
`youtube`, `business_profile`, `tiktok_ads`.

Thay đổi chính ở `app/customer_transport.py` và `app/customer_auth.py`: response
streaming tối đa 16 MiB, deadline/timeout, JSON/type/structure guard, không theo
redirect/proxy hoặc tự retry mutation, bỏ trường credential/secret, kiểm tra
cookie age, lỗi an toàn, pin provider/Workspace/client/connection/asset/job.
Meta Business Login yêu cầu Configuration ID. `app/customer_data.py` dùng cùng
registry cho source presentation. Không sửa actual, null/0, kỳ hoặc phép tính KPI.

Full Web: **614 PASS, 1 SKIP opt-in**, 6 warnings deprecation đã có. Bộ transport
mới gồm 49 ca. Test `tests/test_customer_admin_bridge.py` có thể bật với
`VIO_ADMIN_TEST_ROOT` trỏ tới checkout Admin, trong môi trường cài đủ test
dependencies của cả hai repo; không chạy cùng database dự án. Muốn chạy các ca
PostgreSQL, chỉ dùng `TEST_DATABASE_URL` của database thử dùng một lần.

Đã chạy chín nguồn qua Web/Admin/worker/adapter/report/dashboard/KPI với provider
wire responses giả lập, SQLite và PostgreSQL riêng. Lưu KPI 0, version conflict,
tenant denial và Viewer denial được kiểm tra; original snapshot hash giữ nguyên.
Đây không phải bằng chứng consent hoặc đối chiếu KPI live cho cả chín nguồn.

Image ứng viên đọc dữ liệu trên clone PostgreSQL, bảy trang Web và báo cáo có
snapshot PASS. Live Web login/session HTTP 200, cookie Secure/HttpOnly, CSRF và
internal API isolation PASS. Source/UI/runtime proof và dump riêng ở Admin
`.work/customer-bridge-20261110/`, được ignore; không đưa credential vào Git/image.

TikTok vẫn cần ứng dụng Vio; các nguồn còn lại cần Lead xác nhận quyền/API/app
approval và số liệu thật. Production và Customer publication/sharing/schedules
cần acceptance riêng. Không chuyển profile public về localhost trong lúc Lead thử.
