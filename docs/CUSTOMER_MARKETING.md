# Trang 05 — Dashboard Marketing

URL `/workspace/dashboard`, giao diện thật có xác thực, tham khảo bản Stitch
`stitch_legacy_mock_data_exporter (3)` do người dùng cung cấp. Dùng chung
sidebar/topbar, font Inter/Plus Jakarta Sans và theme slate/đỏ của trang 03–04.
Bản preview cũ vẫn ở preview app; không thay nội dung mock thành dữ liệu thật.

## Phạm vi giao diện

- Chọn Workspace, khách hàng đã lưu, thời gian (preset/tùy chỉnh tối đa 366 ngày),
  kỳ so sánh cùng độ dài và nguồn trong danh mục Admin. URL giữ thời gian,
  nguồn, granularity, comparison; không dùng client ID từ URL để cấp quyền.
- Bốn KPI: chi tiêu, hiển thị, lượt nhấp, chuyển đổi; có giải thích định nghĩa,
  trạng thái trống/một phần/lỗi và kỳ trước. `null` khác số 0; không tự cộng
  Marketing đa nguồn hoặc suy ra số lịch hẹn/doanh thu từ conversion.
- Xu hướng từng chỉ số, granularity ngày/tuần/tháng, SVG có nhãn và bảng dữ liệu.
  Điểm null hoặc thiếu kỳ làm ngắt đường; không nội suy thành số 0. Chọn tuần/tháng
  yêu cầu dữ liệu đã được Admin tổng hợp tương ứng, không tự cộng dữ liệu thiếu.
- Tình trạng chín nguồn, bảng nền tảng theo nhóm quảng cáo/tìm kiếm/nội dung,
  bảng chiến dịch với tìm kiếm nhiều từ không dấu, lọc nguồn/trạng thái,
  sắp xếp và phân trang 10 dòng. Bảng cuộn ngang trong khối, cột tên cố định.
- CSV xuất KPI, nền tảng theo nhóm/nguồn và toàn bộ chiến dịch đã lọc (không chỉ
  trang hiện tại). UTF-8 BOM, quote đúng chuẩn, chống công thức Excel; giá trị
  thiếu để ô trống. Tệp có scope, tiền tệ, múi giờ và kỳ; không có token/secret.
- Báo cáo và phân tích sâu chưa mở được giải thích bằng dialog; không chuyển
  người dùng sang trang 404 hoặc báo tạo thành công khi chưa có backend.

## Kiến trúc và dữ liệu

Không thêm Customer analytics API hoặc migration trong lượt dựng khung này.
Web chỉ gọi các endpoint Customer đã tồn tại: session, Workspace detail,
integrations catalogue và POST select Workspace/client/logout có CSRF.
Admin tiếp tục kiểm tra session, membership, scope, ownership và cấp quyền.
Production chỉ mở thêm chính xác route UI `/workspace/dashboard`; các trang
customer còn lại, legacy report và API chưa tồn tại vẫn bị chặn.

`app/mappers/customer_marketing.py` tạo model trống từ metadata Customer có quyền,
không lấy connections/metrics/campaigns từ legacy hoặc tự gán cho Workspace.
Hiện cả chín nguồn còn planned, không có customer OAuth/sync/analytics thực.
KPI và bảng sẽ tự nhận dữ liệu khi adapter tương lai gọi bridge hiển thị:

```javascript
const context = window.VioMarketing.getContext();
// Adapter tương lai: chỉ truyền DTO an toàn đã được Admin kiểm tra quyền.
window.VioMarketing.applySnapshot({...context, metrics, trends,
  connections, platform_metrics, campaigns, last_updated_at});
```

Đây là contract hiển thị, không phải API cấp quyền. Mọi bộ lọc đổi làm tăng
`request_id`, xóa snapshot và phát event `customer:marketing-context`. Payload chỉ
được nhận khi scope Workspace/client, period, source, granularity, comparison,
request ID, currency, timezone khớp, đã tải metadata thành công và không đang
đổi phạm vi. Chặn response cũ kể cả đổi bộ lọc rồi quay lại cùng giá trị.

- KPI `{status: empty|ready|partial|error, value, previous, source_label}`;
  `value`/`previous` là number hữu hạn hoặc null. `currency` khác bị bỏ qua.
- Trends `{status, points:[{date:'YYYY-MM-DD',value}]}` theo metric; điểm nằm trong
  kỳ, đơn vị giống KPI. Bỏ trend có currency không khớp. Không trộn đơn vị lên
  một trục biểu đồ hoặc tự suy ra tổng từ bảng chi tiết.
- Mỗi record connections/platform_metrics/campaigns cần `workspace_id`,
  `client_id`, `platform_id` trong danh mục. Sai scope không render/export.
- Platform metrics `{status,values:{spend,impressions,clicks,ctr,cpc,conversions}}`.
  CTR tính bằng điểm phần trăm (3.5 nghĩa là 3.5%), CPC/CPA theo tiền tệ Workspace;
  tỷ lệ đã được Admin chuẩn hóa, không tự tính khi thiếu hoặc mẫu số bằng 0.
- Campaign `{id,name,state:active|paused|ended|unknown,data_status:ready|partial,
  values:{budget_daily,spend,clicks,ctr,conversions,cpa}}` chỉ thuộc nguồn quảng cáo.
  Mọi giá trị thiếu/không áp dụng giữ null. UI hiện nhận tối đa 1.000 campaign;
  analytics API tương lai cần server pagination hoặc hợp đồng export riêng khi lớn hơn.
- Kết nối dùng `state` (connected/syncing/expired/error/disconnected/pending).
  Có kết nối không đồng nghĩa có dữ liệu trong kỳ. Thời gian cập nhật chỉ hiển thị
  khi payload có timestamp hợp lệ; không quảng bá realtime/lịch đồng bộ giả.

## Nghiệm thu

`tests/test_customer_auth.py`: route UI cần đăng nhập/Workspace, member/viewer vẫn
qua Admin, không mở API/report legacy. `tests/test_customer_marketing_model.py`:
null/không có analytics, không nhận connections legacy, không sửa catalogue đầu vào.

`scripts/check_customer_marketing_ui.py` tạo tài khoản QA `.invalid`; kiểm tra
1440/1024/390, menu cố định, bộ lọc/reload/tab bàn phím, 0 khác null, đường biểu đồ
bị ngắt, phân trang/search/filter, CSV/formula, scope/currency/timezone/late response,
lỗi/retry, CSRF, đổi khách hàng/Workspace và logout. Dữ liệu số giả lập chỉ tồn tại
trong browser test, không ghi connection/campaign/KPI xuống DB hoặc gửi email.
Artifact riêng trong `.work/customer-marketing-qa/`, không đưa vào Git.

Kết quả nghiệm thu 28/10/2026:

- **370 pytest PASS**, 6 deprecation warnings có sẵn; Python/JavaScript syntax,
  CSS build trong Docker và `git diff --check`: PASS.
- Dashboard browser **3 PASS**: 1440/1024/390; gồm kiểm tra dữ liệu giả lập chỉ
  trong browser, snapshot scope/bộ lọc, CSV, refresh lỗi/thử lại, CSRF,
  select Workspace/client và logout. Không JS error hoặc external request.
- Tìm kiếm Ctrl+K dẫn tới Dashboard từ cả Tổng quan và Kết nối: PASS.
  Menu ngang mobile tự đưa trang đang mở vào vùng nhìn thấy.
- Tour tám bước trên 1440/390: **2 PASS**, giữ ID và tiến độ đã có.
- Ba service Docker Customer healthy; hash **12 file** triển khai khớp source.
  Không thay schema, không đổi backend Admin, không gửi email hoặc gọi provider.
  Chưa commit/push.
