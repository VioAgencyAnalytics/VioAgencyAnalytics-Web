# SEO & Website Traffic / Keywords — 15/10/2026

## Phạm vi và trạng thái

New chỉ đọc Bundle qua Internal API có phiên Viewer của Admin. Không thay Admin,
không gọi Google/Meta, không sửa `.env`, không commit/push/merge hoặc đổi branch.
Nhánh: `feat/seo-multisource-contract`.

Trước khi sửa có 3 file tracked thay đổi: `README.md`,
`tests/test_dashboard_binding.py`, `tests/test_reports.py`; và 4 file untracked:
`app/design_preview.py`, `compose.design-preview.yaml`, `debug.log`,
`tests/test_design_preview.py`. Giữ nguyên nội dung những thay đổi này.

Đã kiểm chứng bằng fixture tổng hợp, mapper, route Viewer với MockTransport và
trình duyệt trên server QA localhost riêng. **Chưa nghiệm thu dữ liệu khách hàng
thật qua live Internal API**; cần report ID/revision đã xuất bản được cấp quyền.
Fixture QA nằm trong `tests/`, `scripts/`, ảnh ở `.work/`; các thư mục này đã được
loại khỏi Docker image theo `.dockerignore` hiện có.

## Contract và cách hiển thị

Đối chiếu chỉ đọc mã Admin cùng workspace: `kdh/google.py` (`Google.keywords`,
`parse_keywords`), `kdh/metric_catalog.py`, `kdh/metric_snapshot.py`,
`kdh/seo_composite.py`, `tests/test_keyword_tiers.py`.

- Sáu trường: `keywords.top5`, `.top10`, `.top20`, `.top30`, `.top50`, `.top100`.
- Top K là **lũy kế**, thỏa `1 <= position <= K`, ở ngày tracking mới nhất
  trong kỳ. Không cộng các ngày và không cộng sáu Top K thành tổng từ khóa.
- Ví dụ một bản ghi vị trí 4 thuộc cả sáu mốc. Vị trí 25 thuộc Top 30/50/100.
  Nếu cần nhóm rời nhau, các khoảng là `[1,5]`, `(5,10]`, `(10,20]`, `(20,30]`,
  `(30,50]`, `(50,100]`. New không tạo những nhóm này hoặc tự trừ các tổng.
- Với snapshot thông thường, New đọc `sources.keywords.totals`; với Release đã
  duyệt, KPI chỉ đọc `marketing.widgets` đã xác minh/publishable. Không dùng totals
  thô để điền vào widget thiếu. Giá trị 0 được giữ; thiếu hoặc key mâu thuẫn là
  “Chưa có dữ liệu”. Không dùng số hàng chi tiết để thay KPI.
- **Giới hạn upstream:** Admin hiện đếm bản ghi tại ngày mới nhất, chưa có bước
  distinct từ khóa trong hàm này. New giữ nguyên số đã xuất bản. Bản ghi trùng
  `keyword/date/url` được cảnh báo; không xóa hàng hoặc sửa KPI. Chưa thể cam kết
  số từ khóa duy nhất khi chưa có contract định danh/phạm vi và loại trùng từ Admin.
- Bộ lọc Top K chỉ chọn hàng có vị trí số hợp lệ `1 <= position <= K`. Kết quả là
  số hàng lịch sử phù hợp, không phải tổng từ khóa duy nhất. Có tìm kiếm, sắp xếp,
  phân trang và chi tiết hàng. Cột ngày tracking và các chiều dữ liệu nguồn được giữ.
- Bộ lọc ngày chỉ lọc chuỗi ngày và hàng có trường `date`; hàng không có ngày
  không bị gán ngày suy đoán. KPI, Top K và kỳ so sánh luôn giữ phạm vi toàn kỳ.
  Phạm vi lọc chi tiết được thông báo riêng trên dashboard.
- `previous_position`/`change` chỉ hiển thị giá trị có sẵn khi kỳ so sánh dataset
  khớp Bundle và dataset không đặt `compare=false`. New không ghép `previous_entries`
  theo tên từ khóa hoặc tự tính thay đổi khi chưa có contract định danh.

## Các sửa đổi

1. Thêm sáu thẻ Top K có nguồn, ngày tracking và giá trị kỳ trước; sửa bộ lọc demo
   Top 10 vốn chỉ lấy vị trí 4–10 thành lũy kế 1–10. Đồng bộ lọc UI/CSV demo.
2. Giữ ngày và cột phụ trong bảng SEO; giữ được `landingPage` thay vì chỉ đọc
   `pagePath`. Không ghép bảng GA4 và GSC thành bản ghi chung.
3. Ẩn so sánh thứ hạng chưa xác minh trong cả bảng nguồn và bảng trình bày tường minh.
4. Hiển thị các KPI GA4/GSC thực có riêng với nguồn và đơn vị. `activeUsers` không
   phải Organic Users; không cộng daily users, không suy ra Leads/CR từ sessions,
   clicks hoặc tỷ lệ chuyển đổi khác. Đổi tiêu đề chart để tránh gọi toàn bộ GA4 là organic.
5. Giữ khoảng trống của chuỗi ngày, null khác 0; tooltip cũ được ẩn khi vẽ lại chart.
6. Lọc ngày đặt lại phân trang, xóa lỗi ngày cũ khi hợp lệ và giữ thông báo phạm vi;
   hỗ trợ mở trực tiếp mục SEO qua query `view`, giữ nguyên report ID/revision.
7. Chặn Bundle có provenance demo trên route Viewer khi `APP_ENV=production`.
   Snapshot Release hợp lệ vẫn được render. Không đổi cơ chế handoff/session/ACL.
8. Loại style inline của scrollbar sidebar gây lỗi CSP; rebuild CSS. Giữ bố cục
   dashboard, thẻ Top K chuyển 6/3/2 cột và bảng cuộn ngang trong vùng của bảng.

## Kiểm thử

| Kiểm tra | Kết quả |
| --- | --- |
| Baseline toàn New pytest | 228 PASS |
| Toàn New pytest sau sửa | **247 PASS, 0 FAIL, 0 SKIP** |
| CSS build | PASS; cảnh báo Browserslist database cũ |
| Browser QA Edge headless | PASS |
| Responsive | 1440×1000, 1024×768, 768×1024, 390×844, 360×800; không tràn ngang trang |
| JS/CSP, request ngoài localhost trong QA | Không có lỗi/request ngoài |
| Live Bundle khách hàng / provider | Chưa chạy; không có report ID/revision thật được nghiệm thu |

Pytest còn 5 cảnh báo deprecation Starlette/AnyIO có từ baseline. Browser QA bao
phủ biên Top K, vị trí 0/null/>100, kết hợp tìm kiếm, rỗng, sort, phân trang,
chi tiết hàng, ngày, KPI không đổi khi lọc, đổi chart, CSV, menu mobile/Escape.
Các test cũ về handoff, session Viewer, quyền, report ID/revision và chặn route
demo trong production vẫn PASS. Lỗi CSP phát hiện trong lượt browser đầu đã sửa;
lượt chạy cuối PASS.

Chạy lại trong New (không đổi `.env`):

```powershell
$env:DEBUG = 'false'
.venv/Scripts/python.exe -m pytest -q
npm run build:css
# Terminal QA riêng, chỉ bind localhost:
.venv/Scripts/python.exe scripts/serve_seo_snapshot_qa.py
# Terminal khác; cần Playwright và Microsoft Edge sẵn trên máy:
node scripts/qa_seo_snapshot.cjs
```

## File của đợt sửa này

| Nhóm | File |
| --- | --- |
| Mapper | `app/mappers/bundle.py`, `app/mappers/dashboard.py` |
| Bảo vệ production | `app/routes/viewer.py` |
| Lọc demo | `app/integrations/mock/seo.py`, `app/routes/reports.py`, `static/js/pages/seo.js`, `templates/pages/seo/controls.html` |
| Keywords/Traffic | `templates/pages/seo/partials/keywords.html`, `templates/pages/seo/partials/trend.html`, `static/css/pages/seo.css` |
| Thành phần snapshot | `templates/pages/snapshot/components.html`, `templates/pages/snapshot/status.html`, `static/js/pages/snapshot.js`, `static/css/pages/snapshot.css`, `static/js/shared/charts.js` |
| Sidebar/CSS | `templates/components/dashboard/sidebar.html`, `static/css/shared/dashboard.source.css`, `static/css/dist/dashboard.css` |
| Test/QA mới | `tests/test_seo_snapshot.py`, `scripts/serve_seo_snapshot_qa.py`, `scripts/qa_seo_snapshot.cjs` |
| Tài liệu mới | `docs/SEO_KEYWORDS_AUDIT.md` |

## Dữ liệu còn chờ Admin và 5 ưu tiên tiếp theo

1. Nghiệm thu một **SEO composite Release đã xuất bản** với report ID/revision thật,
   đủ GA4/GSC/Keywords, quyền Viewer, kỳ, freshness và số liệu đối chiếu. New tiếp tục
   từ chối composite draft; không chuyển draft thành báo cáo khách hàng.
2. Chốt identity của từ khóa theo ngày, URL và phạm vi tracking; loại trùng trước
   xuất bản và xác nhận ý nghĩa Top K là số bản ghi hay số từ khóa duy nhất.
3. Cung cấp contract so sánh keyword: khóa ghép ổn định, ngày chụp hai kỳ, ý nghĩa
   dấu của `change`, trạng thái mới/mất hạng/ngoài Top 100. Sau đó mới triển khai
   hiển thị tăng/giảm và xu hướng ranking đầy đủ.
4. Chuẩn hóa/phê duyệt `ga4.organic_users`, `seo.leads`, `seo.conversion_rate` và
   dữ liệu trang đích theo nguồn/phạm vi phù hợp; cần định nghĩa attribution,
   tử/mẫu số và đơn vị CR trước khi binding thêm.
5. Đưa browser regression và bộ fixture Release nhiều nguồn vào CI, gồm dữ liệu
   thiếu/trùng, tablet/mobile và bảo vệ mock production. Chỉ mở rộng Facebook khi
   có dữ liệu chuẩn hóa cùng contract đã xác nhận.
