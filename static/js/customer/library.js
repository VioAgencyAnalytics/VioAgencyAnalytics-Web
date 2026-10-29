/* Scoped presentation controller. No analytics, report mutation or provider endpoint is invented here. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const initial = JSON.parse($('#library-model').textContent);
  let details = JSON.parse($('#library-data').textContent), catalogue = null, session;
  const workspaceId = initial.scope.workspace_id, base = `workspaces/${workspaceId}`, pageId = crypto.randomUUID();
  const page = document.body.dataset.customerPage, dayMs = 86400000;
  const date = (s) => new Date(s + 'T00:00:00Z'), iso = (d) => d.toISOString().slice(0, 10);
  const shift = (s, days) => iso(new Date(date(s).getTime() + days * dayMs));
  const validDate = (s) => typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s) && !Number.isNaN(date(s).getTime()) && iso(date(s)) === s;
  const parts = new Intl.DateTimeFormat('en', {timeZone: initial.timezone, year: 'numeric', month: '2-digit', day: '2-digit'}).formatToParts(new Date());
  const part = (key) => parts.find((p) => p.type === key).value;
  const today = `${part('year')}-${part('month')}-${part('day')}`;
  const params = new URLSearchParams(location.search);
  let period, generation = 0, renderer = () => {}, snapshot = null, ready = false, busy = false;
  const labels = {not_connected: 'Chưa kết nối', empty: 'Chờ dữ liệu', syncing: 'Đang đồng bộ', ready: 'Có dữ liệu', attention: 'Cần kiểm tra'};
  const node = (tag, text, cls) => { const el = document.createElement(tag); el.textContent = text; if (cls) el.className = cls; return el; };
  const fold = (s) => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[đĐ]/g, 'd').toLowerCase();
  function range(key) {
    const first = today.slice(0, 8) + '01';
    if (key === 'this_month') return {start: first, end: today};
    if (key === 'previous_month') { const end = shift(first, -1); return {start: end.slice(0, 8) + '01', end}; }
    return {start: shift(today, key === 'last7' ? -6 : key === 'last90' ? -89 : -29), end: today};
  }
  function displayDate(value) { return validDate(value) ? new Intl.DateTimeFormat('vi-VN', {timeZone: 'UTC'}).format(date(value)) : '—'; }
  function stamp(value) {
    if (typeof value !== 'string' || !value || Number.isNaN(new Date(value).getTime())) return '—';
    return new Intl.DateTimeFormat('vi-VN', {dateStyle: 'short', timeStyle: 'short', timeZone: initial.timezone}).format(new Date(value));
  }
  function format(value, unit) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || (unit === 'percent' && value > 1)) return '—';
    if (unit === 'currency') return new Intl.NumberFormat('vi-VN', {style: 'currency', currency: initial.currency, maximumFractionDigits: initial.currency === 'VND' ? 0 : 2}).format(value);
    if (unit === 'percent') return new Intl.NumberFormat('vi-VN', {style: 'percent', maximumFractionDigits: 2}).format(value);
    return new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 2}).format(value) + (unit === 'ratio' ? '×' : '');
  }
  function notify(text, kind = 'info') { $('#library-notice').textContent = text; $('#library-notice').hidden = !text; $('#library-notice').dataset.kind = kind; }
  function url(values) {
    const target = new URL(location.href);
    for (const [key, value] of Object.entries(values)) { if (value === '' || value == null) target.searchParams.delete(key); else target.searchParams.set(key, value); }
    history.replaceState(null, '', target.pathname + target.search + target.hash);
  }
  function context() { return {schema_version: 1, request_id: `${pageId}:${generation}`, scope: {workspace_id: workspaceId, client_id: details.selected_client?.id || null}, period: {...period}, currency: initial.currency, timezone: initial.timezone}; }
  function invalidate() {
    generation += 1; snapshot = null;
    document.querySelectorAll('dialog.lb-dialog[open]').forEach((d) => d.close());
    document.dispatchEvent(new CustomEvent('customer:library-context', {detail: context()}));
    renderer();
  }
  function updatePeriod() {
    $('#library-period-label').textContent = displayDate(period.start) + ' – ' + displayDate(period.end);
    $('#library-start').value = period.start; $('#library-end').value = period.end;
    $('#library-start').max = today; $('#library-end').max = today;
  }
  function owned(row) { return Boolean(ready && !busy && details.selected_client && row && row.workspace_id === workspaceId && row.client_id === details.selected_client.id); }
  function connectionState(channel) {
    if (!ready || busy || !details.selected_client) return 'not_connected';
    if (!catalogue) return channel.state;
    const states = catalogue.connections.filter((c) => owned(c) && channel.source_ids.includes(c.platform_id)).map((c) => c.state);
    return states.some((s) => ['error', 'expired', 'disconnected'].includes(s)) ? 'attention' : states.includes('syncing') ? 'syncing' : states.includes('connected') ? 'empty' : 'not_connected';
  }
  function channel(id) {
    const original = initial.channels.find((c) => c.id === id);
    if (!original) return null;
    const row = (Array.isArray(snapshot?.channels) ? snapshot.channels : []).find((c) => owned(c) && c.id === id);
    const metrics = original.metrics.map((m) => ({...m, value: row?.state === 'ready' && row.metrics && Object.hasOwn(row.metrics, m.key) ? row.metrics[m.key] : null}));
    const hasValues = metrics.some((m) => format(m.value, m.unit) !== '—');
    return {...original, metrics, state: row?.state === 'ready' && hasValues ? 'ready' : ['syncing', 'attention'].includes(row?.state) ? row.state : connectionState(original)};
  }
  function controls() {
    $('#library-workspace-select').disabled = busy || !ready;
    $('#library-client').disabled = busy || !ready || !details.clients?.length;
    $('#library-refresh').disabled = busy;
    $('#library-logout').disabled = busy || !session?.user;
    document.querySelectorAll('[data-open-channel],[data-open-template],[data-open-builder]').forEach((b) => { b.disabled = busy || !ready; });
    $('#library-no-client').hidden = Boolean(details.selected_client);
    $('.lb-main').setAttribute('aria-busy', String(busy));
  }
  async function api(path, data) {
    const options = {credentials: 'same-origin', cache: 'no-store', headers: {Accept: 'application/json'}};
    if (data !== undefined) { options.method = 'POST'; options.headers['Content-Type'] = 'application/json'; options.headers['X-CSRF-Token'] = session?.csrf || ''; options.body = JSON.stringify(data); }
    const response = await fetch('/api/customer/' + path, options), payload = await response.json();
    if (!response.ok) {
      if (response.status === 401) location.replace('/workspace/login');
      if (['workspace_changed', 'workspace_access'].includes(payload.code)) location.replace('/workspace');
      throw new Error(payload.error || 'Chưa thể tải dữ liệu. Vui lòng thử lại.');
    }
    return payload;
  }
  async function reload() {
    session = await api('session');
    if (!session.user) { location.replace('/workspace/login'); return; }
    if (session.workspace?.id !== workspaceId) { location.replace('/workspace'); return; }
    const [next, sources] = await Promise.all([api(base), api(base + '/integrations')]);
    if (next.workspace?.id !== workspaceId || sources.workspace?.id !== workspaceId || (next.selected_client?.id || null) !== (sources.selected_client?.id || null)) throw new Error('Phạm vi khách hàng đã thay đổi. Vui lòng tải lại.');
    details = next; catalogue = {...sources, connections: Array.isArray(sources.connections) ? sources.connections : []}; ready = true;
    const clients = (details.clients || []).map((c) => { const option = node('option', c.name); option.value = c.id; return option; });
    if (!clients.length) { const option = node('option', 'Chưa có khách hàng'); option.value = ''; clients.push(option); }
    $('#library-client').replaceChildren(...clients); $('#library-client').value = details.selected_client?.id || '';
    invalidate();
  }
  async function run(action) {
    if (busy) return;
    busy = true; controls(); notify('');
    try { await action(); }
    catch (error) { ready = false; snapshot = null; renderer(); notify(error.message || 'Chưa thể hoàn tất yêu cầu.', 'error'); }
    finally { busy = false; controls(); renderer(); }
  }
  function info(title, text) { $('#library-info-title').textContent = title; $('#library-info-description').textContent = text; $('#library-info').showModal(); }
  function preview(item, options = {}) {
    if (!ready || busy) return;
    const selectedPeriod = options.period || period;
    $('#library-preview-title').textContent = options.name || item.name;
    $('#library-preview-description').textContent = item.description;
    $('#library-preview-client').textContent = details.selected_client?.name || 'Chưa chọn khách hàng';
    $('#library-preview-period').textContent = displayDate(selectedPeriod.start) + ' – ' + displayDate(selectedPeriod.end);
    $('#library-preview-currency').textContent = initial.currency + ' · ' + initial.timezone;
    $('#library-preview-topics').replaceChildren(...item.topics.map((s) => node('span', s)));
    $('#library-preview-metrics').replaceChildren(...item.metrics.map((m) => { const box = node('div', ''); const value = format(m.value, m.unit); box.append(node('span', m.label), node('strong', value), node('small', value === '—' ? 'Chưa có dữ liệu' : 'Theo nguồn trong kỳ')); return box; }));
    $('#library-preview-metrics').hidden = !item.metrics.length;
    $('#library-preview .lb-preview-section h3').textContent = options.blank ? 'Khu vực nội dung tùy chỉnh' : 'Xu hướng hiệu suất';
    $('#library-preview .lb-preview-chart strong').textContent = options.blank ? 'Không gian cho nội dung báo cáo của bạn' : 'Biểu đồ sẽ hiển thị khi có dữ liệu';
    $('#library-preview .lb-preview-chart p').textContent = options.blank ? 'Chọn các phần nội dung để hoàn thiện bố cục khi trình chỉnh sửa sẵn sàng.' : 'Không suy ra số liệu từ các nguồn chưa sẵn sàng.';
    const ids = options.sources || item.source_ids;
    $('#library-preview-sources').replaceChildren(...initial.sources.filter((s) => ids.includes(s.id)).map((s) => node('span', s.name)));
    $('#library-preview-note').textContent = options.builder ? 'Bản thử bố cục chưa được lưu. Đóng trang sẽ không tạo báo cáo, lịch gửi hoặc liên kết chia sẻ.' : 'Đây là khung xem trước. Biểu đồ, bảng chi tiết và chức năng xuất file sẽ được mở khi dữ liệu và báo cáo đã sẵn sàng.';
    $('#library-preview-edit').hidden = !options.builder;
    $('#library-preview-connect').href = item.id === 'seo' ? '/workspace/integrations?category=seo' : item.id === 'overview' ? '/workspace/integrations' : '/workspace/integrations?platform=' + encodeURIComponent(item.id);
    $('#library-preview').showModal();
  }
  function accept(value) {
    const expected = context();
    if (!ready || busy || !expected.scope.client_id || value?.schema_version !== 1 || value.request_id !== expected.request_id || value.scope?.workspace_id !== workspaceId || value.scope?.client_id !== expected.scope.client_id || value.period?.start !== period.start || value.period?.end !== period.end || value.currency !== initial.currency || value.timezone !== initial.timezone) return false;
    try { snapshot = structuredClone(value); } catch { return false; }
    renderer(); return true;
  }
  document.querySelectorAll('[data-library-close]').forEach((b) => b.addEventListener('click', () => b.closest('dialog').close()));
  $('#library-workspace-select').addEventListener('change', () => run(async () => {
    const id = $('#library-workspace-select').value;
    if (!session.workspaces.some((w) => w.id === id)) throw new Error('Workspace không hợp lệ.');
    ready = false; invalidate(); await api(`workspaces/${id}/select`, {}); location.assign('/workspace/' + page);
  }));
  $('#library-client').addEventListener('change', () => run(async () => {
    const id = $('#library-client').value;
    if (!details.clients.some((c) => c.id === id)) throw new Error('Khách hàng không hợp lệ.');
    ready = false; invalidate(); await api(`${base}/clients/${id}/select`, {}); await reload();
  }));
  $('#library-refresh').addEventListener('click', () => run(async () => { ready = false; invalidate(); await reload(); notify('Đã tải lại phạm vi và trạng thái nguồn dữ liệu.'); }));
  $('#library-logout').addEventListener('click', () => run(async () => { ready = false; invalidate(); await api('auth/logout', {}); location.assign('/workspace/login'); }));
  $('#library-period').addEventListener('change', () => {
    const key = $('#library-period').value; $('#library-custom-period').hidden = key !== 'custom';
    if (key !== 'custom') { period = range(key); updatePeriod(); invalidate(); url({period: key, start: '', end: ''}); notify(''); }
  });
  $('#library-custom-period').addEventListener('submit', (event) => {
    event.preventDefault(); const start = $('#library-start').value, end = $('#library-end').value;
    if (!validDate(start) || !validDate(end) || start > end || end > today || (date(end) - date(start)) / dayMs > 365) { notify('Chọn khoảng ngày hợp lệ, tối đa 366 ngày và không vượt quá hôm nay.', 'error'); return; }
    period = {start, end}; updatePeriod(); invalidate(); url({period: 'custom', start, end}); notify('');
  });
  $('#library-guide').addEventListener('click', () => info(page === 'channels' ? 'Khám phá Phân tích kênh' : 'Làm quen với Trung tâm Báo cáo', page === 'channels'
    ? '1. Chọn khách hàng và khoảng ngày.\n2. Tìm kênh hoặc lọc theo nhóm và trạng thái.\n3. Mở “Xem phân tích” để xem các chỉ số và cấu trúc chi tiết.\n\nDấu “—” nghĩa là chưa có dữ liệu; không phải giá trị bằng 0. Số liệu giữa các nền tảng có thể có cách ghi nhận khác nhau.'
    : '1. Chọn khách hàng và kỳ báo cáo.\n2. Khám phá bố cục tổng hợp hoặc theo từng nền tảng.\n3. Thử thiết kế để xem trước tên, bố cục và nguồn dữ liệu.\n\nBản thử bố cục chưa được lưu. Danh sách báo cáo, lịch sử xuất file và chia sẻ sẽ hoạt động khi báo cáo sẵn sàng.'));
  window.addEventListener('pageshow', (event) => { if (event.persisted) location.reload(); });
  const preferred = params.get('period') || details.preferences?.default_period || 'last30';
  $('#library-period').value = [...$('#library-period').options].some((o) => o.value === preferred) ? preferred : 'last30';
  const start = params.get('start'), end = params.get('end');
  if ($('#library-period').value === 'custom' && validDate(start) && validDate(end) && start <= end && end <= today && (date(end) - date(start)) / dayMs <= 365) period = {start, end};
  else { if ($('#library-period').value === 'custom') $('#library-period').value = 'last30'; period = range($('#library-period').value); }
  $('#library-custom-period').hidden = $('#library-period').value !== 'custom'; updatePeriod();
  window.VioLibrary = Object.freeze({$, node, fold, format, stamp, displayDate, labels, range, url, info, preview, context, accept, owned, channel,
    get initial() { return structuredClone(initial); }, get details() { return details; }, get snapshot() { return snapshot; }, get ready() { return ready && !busy; },
    mount(render) { renderer = render; renderer(); controls(); run(reload); }});
})();
