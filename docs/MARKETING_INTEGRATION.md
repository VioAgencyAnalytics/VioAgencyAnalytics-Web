# KDH-Report-New — bàn giao tích hợp Marketing

Cập nhật 10/10/2026. Tiếp nối renderer local hiện có, giữ FastAPI/Jinja2/Vanilla JS. Admin Flask tại `D:\KDH-Report-Admin` sở hữu dữ liệu, tài khoản, review và publication. New không truy cập PostgreSQL Admin.

## Đường người dùng

- Production `/` chuyển tới `/login`.
- `/login` xác thực tài khoản ứng dụng qua backend Admin; không phải OAuth lấy dữ liệu Google.
- `/reports` chỉ liệt kê report/revision được cấp; `/reports/{id}?revision=N` render Bundle đó.
- `/internal-preview/{candidate_id}` chỉ dành cho Admin, gắn nhãn chưa xác minh/chưa xuất bản.
- `/published/{id}` giữ developer Basic Auth/allowlist, đóng trong production.
- Dashboard mock cũ và `/demo-bundles/...` bị middleware chặn khi production. Không có fallback mock khi Internal API lỗi.

## Kết nối

`AdminViewerRepository` gửi service token và session opaque tới `/api/internal/v1/viewer/...`. Admin kiểm tra user active, expiry, role, client, report, khoảng revision và quyền loại báo cáo. Cấu hình hai backend cùng `REPORT_SERVICE_TOKEN`, chỉ lưu ở server. New cookie HttpOnly chứa phiên user, không chứa service/provider token.

Compose dùng `REPORT_ADMIN_BASE_URL=http://admin:8090`, network ngoài `kdh-report-admin_default`; chạy Compose Admin trước New. `APP_ENV=production`, `DEBUG=false`. URL host mặc định New `http://localhost:8080`. `.env` thật chưa được sửa trong đợt này.

## Renderer

Contract vẫn `schema_version=1.0`. Marketing release thêm dữ liệu bên trong section: widgets/comparison, nguồn, evidence đã xác minh, Opportunity đã duyệt, metadata approval, giới hạn kết luận và 12 nguồn Catalog. New kiểm tra contract, không có khóa ký của Admin và không tự nâng trạng thái verification. Null giữ empty state; chỉ số và biểu đồ không được lấy số demo để bù.

Các file tiếp nối: `app/repositories/viewer.py`, `app/routes/viewer.py`, `app/mappers/bundle.py`, `app/services/bundle.py`, `templates/pages/published/`, `static/css/pages/published.css`, `static/js/pages/published.js`.

## Kiểm thử và trạng thái

184 pytest đạt; 4 cảnh báo deprecation sẵn có. Thêm `test_viewer.py` và `test_marketing_view.py` cho auth/CSRF/revision, production isolation, release contract và empty/approved states. HTTP E2E giữa hai ứng dụng chạy từ Admin:

```powershell
Set-Location D:\KDH-Report-New
.\.venv\Scripts\python.exe -m pytest tests -q
Get-ChildItem static/js -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }
git diff --check

Set-Location D:\KDH-Report-Admin
.\.venv\Scripts\python.exe tests/run_marketing_e2e.py --new-root D:\KDH-Report-New
```

Docker build/smoke thành công trên container test riêng; image New `marketing-qa-20261010` gồm bản sửa mới nhất, không tự nâng cấp container đang phục vụ. Chromium headless chạy đủ workflow, chart/tooltip/menu/revoke và chụp 7 màn hình ở 1440/768/390px. Runner ở Admin `tests/run_marketing_browser.py`, ảnh/log trong `test-results/marketing-browser/`.

Đã sửa login browser bị `Origin: null` bằng Referrer-Policy `same-origin`; vẫn chặn Origin lạ/null và CSRF sai. Menu mobile cho focus tới nút logout, trục biểu đồ tỷ lệ không làm tròn trùng nhãn. Dữ liệu thật KinderHealth chưa được nghiệm thu; provider tests dùng fixture độc lập.

Bộ tài liệu đầy đủ nằm trong `D:\KDH-Report-Admin\docs`: `KDH_ARCHITECTURE.md`, `KDH_DATA_FLOW.md`, `KDH_REPORT_BUNDLE_CONTRACT.md`, `KDH_API_INTEGRATION.md`, `KDH_PROVIDER_STATUS.md`, `KDH_TEST_RESULTS.md`, `KDH_DEPLOYMENT_GUIDE.md`, `KDH_HANDOVER.md`. Đọc handover trước khi tiếp tục; code local, GitHub và Docker là ba trạng thái khác nhau.
