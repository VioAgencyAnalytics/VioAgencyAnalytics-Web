/* Customer presentation only. Future analytics must be authorized and normalized by Admin. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const initial = JSON.parse($('#marketing-analytics-data').textContent);
  let details = JSON.parse($('#marketing-data').textContent);
  const workspaceId = initial.scope.workspace_id, base = `workspaces/${workspaceId}`;
  const pageId = crypto.randomUUID(), dayMs = 86400000;
  const metrics = Object.keys(initial.metrics), paidIds = initial.platforms.filter((p) => p.group === 'paid').map((p) => p.id);
  const states = {active: 'Đang chạy', paused: 'Tạm dừng', ended: 'Đã kết thúc', unknown: 'Chưa xác định'};
  const definitions = {
    spend: 'Tổng chi phí quảng cáo trong kỳ theo nguồn đang chọn. Chỉ cộng khi dữ liệu đã được chuẩn hóa về cùng tiền tệ. Kênh organic không có dữ liệu chi tiêu sẽ hiển thị “—”.',
    impressions: 'Số lần nội dung hoặc quảng cáo được hiển thị theo định nghĩa của từng nguồn. Không phải số người duy nhất; một người có thể tạo nhiều lượt hiển thị.',
    clicks: 'Số lượt nhấp được nền tảng ghi nhận. Lượt nhấp quảng cáo, lượt nhấp tìm kiếm và phiên truy cập website là những chỉ số khác nhau.',
    conversions: 'Số sự kiện chuyển đổi theo cấu hình và mô hình ghi nhận của từng nguồn. Không tự suy ra doanh thu, lịch hẹn hoặc khách hàng mới; dữ liệu đa nguồn có thể trùng lặp.',
  };
  const finite = (value) => typeof value === 'number' && Number.isFinite(value);
  const date = (value) => new Date(value + 'T00:00:00Z');
  const iso = (value) => value.toISOString().slice(0, 10);
  const shift = (value, days) => iso(new Date(date(value).getTime() + days * dayMs));
  const validDate = (value) => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(date(value).getTime()) && iso(date(value)) === value;
  const displayDate = (value) => new Intl.DateTimeFormat('vi-VN', {timeZone: 'UTC'}).format(date(value));
  const fold = (value) => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[đĐ]/g, 'd').toLowerCase();
  const parts = new Intl.DateTimeFormat('en', {timeZone: initial.timezone, year: 'numeric', month: '2-digit', day: '2-digit'}).formatToParts(new Date());
  const part = (key) => parts.find((p) => p.type === key).value;
  const today = `${part('year')}-${part('month')}-${part('day')}`;
  let session, busy = false, ready = false, failed = false, generation = 0, metric = 'spend', group = 'all', campaignPage = 1;
  let period = {start: shift(today, -29), end: today}, snapshot, filteredCampaigns = [];
  function node(tag, text, className) { const item = document.createElement(tag); item.textContent = text; if (className) item.className = className; return item; }
  function icon(name, className = '') { const item = node('span', name, 'material-symbols-outlined ' + className); item.setAttribute('aria-hidden', 'true'); return item; }
  function notify(text, kind = 'info') { const status = $('#marketing-status'); status.textContent = text; status.hidden = !text; status.dataset.kind = kind; }
  function format(value, key) {
    if (!finite(value)) return '—';
    if (['spend', 'cpc', 'cpa', 'budget_daily'].includes(key)) return new Intl.NumberFormat('vi-VN', {style: 'currency', currency: initial.currency, maximumFractionDigits: initial.currency === 'VND' ? 0 : 2}).format(value);
    return new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 2}).format(value) + (key === 'ctr' ? '%' : '');
  }
  function stamp(value) {
    if (typeof value !== 'string' || !value) return null;
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : new Intl.DateTimeFormat('vi-VN', {dateStyle: 'short', timeStyle: 'short', timeZone: initial.timezone}).format(parsed);
  }
  function getContext() {
    return {schema_version: 1, request_id: `${pageId}:${generation}`, scope: {workspace_id: workspaceId, client_id: details.selected_client?.id || null}, period: {...period},
      source: $('#marketing-source').value, granularity: $('#marketing-granularity').value, comparison: $('#marketing-comparison').value, currency: initial.currency, timezone: initial.timezone};
  }
  function empty() { return {...structuredClone(initial), ...getContext(), connections: [], platform_metrics: [], campaigns: []}; }
  function invalidate() { generation += 1; snapshot = empty(); campaignPage = 1; render(); document.dispatchEvent(new CustomEvent('customer:marketing-context', {detail: getContext()})); }
  function saveFilters() {
    const url = new URL(location.href);
    for (const key of ['start', 'end', 'source', 'granularity', 'comparison']) url.searchParams.delete(key);
    url.searchParams.set('start', period.start); url.searchParams.set('end', period.end);
    for (const [key, selector, fallback] of [['source', '#marketing-source', 'all'], ['granularity', '#marketing-granularity', 'day'], ['comparison', '#marketing-comparison', 'previous']]) {
      if ($(selector).value !== fallback) url.searchParams.set(key, $(selector).value);
    }
    history.replaceState(null, '', url.pathname + url.search);
  }
  function updatePeriod() {
    const days = Math.round((date(period.end) - date(period.start)) / dayMs) + 1;
    const prior = $('#marketing-comparison').value === 'previous' ? ` · so với ${displayDate(shift(period.start, -days))} – ${displayDate(shift(period.start, -1))}` : '';
    $('#marketing-period-label').textContent = `${displayDate(period.start)} – ${displayDate(period.end)}${prior}`;
    $('#marketing-start').value = period.start; $('#marketing-end').value = period.end;
    $('#marketing-start').max = today; $('#marketing-end').max = today;
  }
  function presetRange(key) {
    const first = today.slice(0, 8) + '01';
    if (key === 'this_month') return {start: first, end: today};
    if (key === 'previous_month') { const end = shift(first, -1); return {start: end.slice(0, 8) + '01', end}; }
    return {start: shift(today, key === 'last7' ? -6 : key === 'last90' ? -89 : -29), end: today};
  }
  function preset(key) {
    $('#marketing-custom-period').hidden = key !== 'custom';
    if (key === 'custom') return;
    period = presetRange(key);
    updatePeriod(); invalidate(); saveFilters(); notify('');
  }
  function inScope(item) { return item && item.workspace_id === workspaceId && item.client_id === details.selected_client?.id && initial.platforms.some((p) => p.id === item.platform_id); }
  function sourceMatches(id) { return $('#marketing-source').value === 'all' || $('#marketing-source').value === id; }
  function rows(key) { return snapshot[key].filter((item) => inScope(item) && sourceMatches(item.platform_id) && (!item.currency || item.currency === initial.currency)); }
  function renderMetrics() {
    for (const key of metrics) {
      const item = snapshot.metrics[key], card = document.querySelector(`[data-metric="${key}"]`);
      const hasValue = ['ready', 'partial'].includes(item.status) && finite(item.value);
      card.dataset.state = hasValue ? item.status : item.status === 'error' ? 'error' : 'empty';
      card.querySelector('[data-metric-value]').textContent = hasValue ? format(item.value, key) : '—';
      card.querySelector('[data-metric-status]').textContent = hasValue ? item.status === 'partial' ? 'Dữ liệu một phần' : 'Có dữ liệu' : item.status === 'error' ? 'Chưa tải được' : 'Chưa có dữ liệu';
      card.querySelector('[data-metric-source]').textContent = item.source_label || initial.metrics[key].source_label;
      const change = card.querySelector('[data-metric-change]');
      change.hidden = !hasValue || !finite(item.previous) || $('#marketing-comparison').value === 'none';
      change.textContent = !finite(item.previous) ? '' : item.previous === 0 ? item.value === 0 ? 'Không đổi so với kỳ trước' : 'Kỳ trước bằng 0'
        : new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 1, signDisplay: 'exceptZero'}).format((item.value - item.previous) / Math.abs(item.previous) * 100) + '% so với kỳ trước';
    }
  }
  function svgNode(tag, attrs, text) {
    const item = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(attrs)) item.setAttribute(key, String(value));
    if (text !== undefined) item.textContent = text; return item;
  }
  function renderChart() {
    const trend = snapshot.trends[metric];
    const points = (Array.isArray(trend.points) ? trend.points : []).filter((p) => p && validDate(p.date) && p.date >= period.start && p.date <= period.end).slice(0, 366).sort((a, b) => a.date.localeCompare(b.date));
    const hasValue = ['ready', 'partial'].includes(trend.status) && points.some((p) => finite(p.value));
    $('#marketing-chart-empty').hidden = hasValue; $('#marketing-chart-live').hidden = !hasValue; $('#marketing-trend-table').hidden = !hasValue;
    $('#marketing-chart-description').textContent = trend.status === 'error' ? 'Chưa tải được dữ liệu xu hướng. Kiểm tra nguồn dữ liệu và thử lại.' : 'Xu hướng sẽ xuất hiện khi nguồn được kết nối và có dữ liệu trong kỳ đã chọn.';
    $('#marketing-chart-panel').setAttribute('aria-labelledby', 'marketing-tab-' + metric);
    $('#marketing-trend-unit').textContent = metric === 'spend' ? initial.currency : 'Lượt';
    $('#marketing-chart-legend').textContent = initial.metrics[metric].label;
    const svg = $('#marketing-chart-svg'); svg.replaceChildren(); $('#marketing-trend-table tbody').replaceChildren();
    if (!hasValue) return;
    const values = points.filter((p) => finite(p.value)).map((p) => p.value), min = Math.min(0, ...values), max = Math.max(1, ...values), span = max - min || 1;
    const x = (p) => period.start === period.end ? 375 : 65 + (date(p.date) - date(period.start)) / (date(period.end) - date(period.start)) * 600;
    const y = (value) => 220 - (value - min) / span * 185;
    for (let i = 0; i < 4; i += 1) { const value = min + span * i / 3, yy = y(value); svg.append(svgNode('line', {x1: 65, x2: 665, y1: yy, y2: yy, stroke: '#e2e8f0'}), svgNode('text', {x: 55, y: yy + 3, 'text-anchor': 'end'}, new Intl.NumberFormat('vi-VN', {notation: 'compact', maximumFractionDigits: 1}).format(value))); }
    let path = '', pen = false, previous;
    points.forEach((p) => {
      const row = node('tr', ''); row.append(node('td', displayDate(p.date)), node('td', format(p.value, metric))); $('#marketing-trend-table tbody').append(row);
      if (!finite(p.value)) { pen = false; previous = p.date; return; }
      const days = previous ? (date(p.date) - date(previous)) / dayMs : 0;
      if (days > (getContext().granularity === 'day' ? 1 : getContext().granularity === 'week' ? 7 : 31)) pen = false;
      path += `${pen ? 'L' : 'M'}${x(p).toFixed(2)} ${y(p.value).toFixed(2)} `; pen = true; previous = p.date;
      const point = svgNode('circle', {cx: x(p), cy: y(p.value), r: 3.5, fill: '#d9232e'}); point.append(svgNode('title', {}, `${displayDate(p.date)}: ${format(p.value, metric)}`)); svg.append(point);
    });
    svg.prepend(svgNode('path', {d: path.trim(), fill: 'none', stroke: '#d9232e', 'stroke-width': 2.5, 'stroke-linejoin': 'round'}));
    svg.append(svgNode('text', {x: 65, y: 251}, displayDate(period.start)), svgNode('text', {x: 665, y: 251, 'text-anchor': 'end'}, displayDate(period.end)));
    svg.setAttribute('aria-label', `${initial.metrics[metric].label}, ${displayDate(period.start)} đến ${displayDate(period.end)}. Xem bảng dữ liệu bên dưới để đọc từng giá trị.`);
  }
  function renderSources() {
    const platforms = initial.platforms.filter((p) => sourceMatches(p.id)), values = rows('platform_metrics');
    const count = platforms.filter((p) => values.some((v) => v.platform_id === p.id && ['ready', 'partial'].includes(v.status) && Object.values(v.values || {}).some(finite))).length;
    $('#marketing-coverage-count').textContent = `${count}/${platforms.length} có dữ liệu`;
    $('#marketing-sources').replaceChildren(...platforms.map((platform) => {
      const row = node('li', ''); row.dataset.selected = String($('#marketing-source').value === platform.id);
      const value = values.find((v) => v.platform_id === platform.id), connection = rows('connections').find((v) => v.platform_id === platform.id);
      const label = value?.status === 'partial' ? 'Dữ liệu một phần' : value?.status === 'ready' && Object.values(value.values || {}).some(finite) ? 'Có dữ liệu trong kỳ'
        : connection?.state === 'syncing' ? 'Đang đồng bộ' : ['expired', 'error', 'disconnected'].includes(connection?.state) ? 'Kết nối cần kiểm tra' : connection?.state === 'connected' ? 'Chưa có dữ liệu trong kỳ' : 'Chưa kết nối';
      const text = node('div', ''); text.append(node('strong', platform.name), node('small', label));
      const link = node('a', connection ? 'Kiểm tra' : 'Tìm hiểu'); link.href = '/workspace/integrations?platform=' + encodeURIComponent(platform.id); link.setAttribute('aria-label', `${link.textContent} ${platform.name}`);
      row.append(icon(platform.icon, 'mk-provider mk-' + platform.color), text, link); return row;
    }));
    const updated = stamp(snapshot.last_updated_at);
    $('#marketing-last-updated').textContent = updated ? 'Dữ liệu cập nhật: ' + updated : 'Chưa có lần cập nhật dữ liệu';
  }
  function dataCell(value, key) { return node('td', format(value, key), finite(value) ? '' : 'mk-missing'); }
  function platformValues(platform) { const item = rows('platform_metrics').find((r) => r.platform_id === platform.id); return item && ['ready', 'partial'].includes(item.status) ? item.values || {} : {}; }
  function renderPlatforms() {
    const allowed = initial.platforms.filter((p) => sourceMatches(p.id)), selected = allowed.filter((p) => group === 'all' || p.group === group);
    document.querySelectorAll('[data-platform-group]').forEach((button) => { button.setAttribute('aria-pressed', String(button.dataset.platformGroup === group)); button.querySelector('span').textContent = allowed.filter((p) => button.dataset.platformGroup === 'all' || p.group === button.dataset.platformGroup).length; });
    $('#marketing-platform-rows').replaceChildren(...selected.map((platform) => {
      const row = node('tr', ''), titleCell = node('td', ''), title = node('div', '', 'mk-platform-name'), text = node('div', '');
      text.append(node('strong', platform.name), node('small', platform.subtitle)); title.append(icon(platform.icon, 'mk-provider mk-' + platform.color), text); titleCell.append(title);
      row.append(titleCell, node('td', initial.groups.find((g) => g.id === platform.group).label));
      const value = platformValues(platform);
      for (const key of ['spend', 'impressions', 'clicks', 'ctr', 'cpc', 'conversions']) row.append(dataCell(value[key], key));
      const action = node('td', ''), link = node('a', rows('connections').some((r) => r.platform_id === platform.id) ? 'Nguồn dữ liệu ↗' : 'Kết nối ↗'); link.href = '/workspace/integrations?platform=' + encodeURIComponent(platform.id); action.append(link); row.append(action); return row;
    }));
    $('#marketing-platform-empty').hidden = selected.length > 0; $('#marketing-platform-count').textContent = `${selected.length} / ${initial.platforms.length} nền tảng`;
  }
  function campaigns() { return rows('campaigns').filter((item) => paidIds.includes(item.platform_id) && typeof item.id === 'string' && item.id && typeof item.name === 'string'); }
  function renderCampaigns() {
    const words = fold($('#marketing-campaign-search').value.trim()).split(/\s+/).filter(Boolean), platform = $('#marketing-campaign-platform').value, state = $('#marketing-campaign-state').value;
    const all = campaigns();
    filteredCampaigns = all.filter((item) => words.every((w) => fold(item.name).includes(w)) && (platform === 'all' || item.platform_id === platform) && (state === 'all' || (Object.hasOwn(states, item.state) ? item.state : 'unknown') === state));
    const sort = $('#marketing-campaign-sort').value;
    filteredCampaigns.sort((a, b) => sort === 'name' ? a.name.localeCompare(b.name, 'vi') : (finite(b.values?.[sort]) ? b.values[sort] : -Infinity) - (finite(a.values?.[sort]) ? a.values[sort] : -Infinity) || a.name.localeCompare(b.name, 'vi'));
    const pages = Math.max(1, Math.ceil(filteredCampaigns.length / 10)); campaignPage = Math.min(campaignPage, pages);
    $('#marketing-campaign-rows').replaceChildren(...filteredCampaigns.slice((campaignPage - 1) * 10, campaignPage * 10).map((item) => {
      const row = node('tr', ''), platformInfo = initial.platforms.find((p) => p.id === item.platform_id), stateCell = node('td', ''), badge = node('span', states[item.state] || states.unknown, 'mk-campaign-state'); badge.dataset.state = Object.hasOwn(states, item.state) ? item.state : 'unknown'; stateCell.append(badge);
      row.append(node('td', item.name), node('td', platformInfo.name), stateCell);
      const values = ['ready', 'partial'].includes(item.data_status) ? item.values || {} : {};
      for (const key of ['budget_daily', 'spend', 'clicks', 'ctr', 'conversions', 'cpa']) row.append(dataCell(values[key], key)); return row;
    }));
    $('#marketing-campaign-count').textContent = `${filteredCampaigns.length} chiến dịch`;
    $('#marketing-campaign-empty').hidden = filteredCampaigns.length > 0;
    $('#marketing-campaign-empty-title').textContent = all.length ? 'Không có chiến dịch phù hợp' : 'Chưa có dữ liệu chiến dịch quảng cáo';
    $('#marketing-campaign-description').textContent = all.length ? 'Thử tên khác hoặc xóa bộ lọc chiến dịch để xem dữ liệu trong phạm vi đang chọn.' : 'Khi tài khoản quảng cáo được kết nối và đồng bộ, các chiến dịch sẽ xuất hiện tại đây.';
    $('#marketing-campaign-connect').hidden = all.length > 0; $('#marketing-campaign-reset').hidden = !all.length;
    $('#marketing-pagination').hidden = filteredCampaigns.length === 0;
    $('#marketing-page-label').textContent = `Trang ${campaignPage}/${pages} · ${filteredCampaigns.length} chiến dịch`;
    $('#marketing-page-prev').disabled = campaignPage === 1; $('#marketing-page-next').disabled = campaignPage === pages;
  }
  function render() {
    renderMetrics(); renderChart(); renderSources(); renderPlatforms(); renderCampaigns();
    const selected = details.selected_client;
    $('#marketing-client-label').textContent = selected ? `Khách hàng: ${selected.name}` : 'Chưa chọn khách hàng';
    $('#marketing-onboarding').hidden = selected && (rows('connections').length > 0 || metrics.some((key) => finite(snapshot.metrics[key].value) && ['ready', 'partial'].includes(snapshot.metrics[key].status)));
    $('#marketing-onboarding-title').textContent = !ready ? failed ? 'Chưa tải được thông tin Workspace' : 'Đang cập nhật phạm vi dữ liệu…' : !selected ? 'Chọn khách hàng để bắt đầu theo dõi' : 'Bắt đầu từ nguồn dữ liệu của bạn';
    $('#marketing-onboarding-description').textContent = failed ? 'Bấm Cập nhật để thử lại. Chỉ số được giữ trống khi chưa xác định được phạm vi dữ liệu.' : !selected ? 'Mỗi khách hàng có nguồn dữ liệu và báo cáo riêng. Chọn khách hàng phía trên hoặc thêm mới ở Tổng quan.' : 'Khám phá nền tảng và chuẩn bị cấp quyền cho khách hàng đang chọn. Tích hợp tự phục vụ được mở theo từng nguồn.';
    $('#marketing-onboarding-link').href = !selected ? '/workspace#client-card' : '/workspace/integrations'; $('#marketing-onboarding-link').textContent = !selected ? 'Quản lý khách hàng →' : 'Kết nối nền tảng →';
  }
  function controls() { $('#marketing-client').disabled = busy || !ready || !details.clients.length; $('#marketing-workspace-select').disabled = busy || !ready; $('#marketing-refresh').disabled = busy; $('#marketing-logout').disabled = busy || !session?.user; $('#marketing-export').disabled = busy || !ready; $('#marketing-client').setAttribute('aria-busy', String(busy)); }
  async function api(path, data) {
    const options = {credentials: 'same-origin', cache: 'no-store', headers: {Accept: 'application/json'}};
    if (data !== undefined) { options.method = 'POST'; options.headers['Content-Type'] = 'application/json'; options.headers['X-CSRF-Token'] = session?.csrf || ''; options.body = JSON.stringify(data); }
    const response = await fetch('/api/customer/' + path, options), payload = await response.json();
    if (!response.ok) { if (response.status === 401) location.replace('/workspace/login'); if (['workspace_changed', 'workspace_access'].includes(payload.code)) location.replace('/workspace'); throw new Error(payload.error || 'Chưa thể cập nhật dữ liệu. Vui lòng thử lại.'); }
    return payload;
  }
  async function refresh() {
    session = await api('session');
    if (!session.user) { location.replace('/workspace/login'); return; }
    if (session.workspace?.id !== workspaceId) { location.replace('/workspace'); return; }
    const [next, catalogue] = await Promise.all([api(base), api(base + '/integrations')]);
    if (next.workspace.id !== workspaceId || catalogue.workspace.id !== workspaceId || (next.selected_client?.id || null) !== (catalogue.selected_client?.id || null)) throw new Error('Phạm vi dữ liệu đã thay đổi. Bấm Cập nhật để tải lại.');
    details = next; ready = true; failed = false;
    const select = $('#marketing-client'); select.replaceChildren(new Option('Chọn khách hàng', ''), ...details.clients.map((c) => new Option(c.name, c.id))); select.value = details.selected_client?.id || ''; select.options[0].disabled = Boolean(details.selected_client);
    invalidate();
  }
  async function operation(action) {
    if (busy) return;
    busy = true; notify(''); controls();
    try { await action(); }
    catch (error) { ready = false; failed = true; $('#marketing-workspace-select').value = workspaceId; invalidate(); notify(error.message || 'Chưa thể cập nhật. Vui lòng thử lại.', 'error'); }
    finally { busy = false; controls(); }
  }
  function applySnapshot(payload) {
    const c = getContext();
    if (!ready || busy || !c.scope.client_id || payload?.schema_version !== 1 || payload.request_id !== c.request_id || payload.scope?.workspace_id !== c.scope.workspace_id || payload.scope?.client_id !== c.scope.client_id
      || payload.period?.start !== c.period.start || payload.period?.end !== c.period.end || payload.source !== c.source || payload.granularity !== c.granularity || payload.comparison !== c.comparison || payload.currency !== c.currency || payload.timezone !== c.timezone) return false;
    const next = empty();
    for (const key of metrics) {
      const item = payload.metrics?.[key]; if (item && (!item.currency || item.currency === c.currency)) next.metrics[key] = {...next.metrics[key], ...item};
      if (payload.trends?.[key] && (!payload.trends[key].currency || payload.trends[key].currency === c.currency)) next.trends[key] = structuredClone(payload.trends[key]);
    }
    for (const key of ['connections', 'platform_metrics', 'campaigns']) next[key] = Array.isArray(payload[key]) ? structuredClone(payload[key].slice(0, key === 'campaigns' ? 1000 : 100)) : [];
    next.last_updated_at = payload.last_updated_at || null; snapshot = next; campaignPage = 1; render(); return true;
  }
  function dialog(title, description, href = '/workspace/integrations') { $('#marketing-dialog-title').textContent = title; $('#marketing-dialog-description').textContent = description; $('#marketing-dialog-link').hidden = !href; if (href) $('#marketing-dialog-link').href = href; $('#marketing-dialog').showModal(); }
  function guide() { dialog('Đọc Dashboard Marketing', '1. Chọn khách hàng / thương hiệu.\n2. Chọn khoảng thời gian, kỳ so sánh và nguồn dữ liệu.\n3. Đọc KPI, xem xu hướng rồi so sánh từng nền tảng.\n4. Lọc chiến dịch và xuất CSV theo phạm vi đang chọn.\n\nCác nguồn cần được cấp quyền và đồng bộ trước khi có số liệu. “—” là thiếu dữ liệu hoặc không áp dụng; số 0 là giá trị được nguồn ghi nhận.'); }
  function csvQuote(value) { let text = String(value ?? ''); if (/^[\s\uFEFF]*[=+\-@]|^[\t\r\n]/.test(text)) text = "'" + text; return '"' + text.replaceAll('"', '""') + '"'; }
  function exportCSV() {
    const lines = [['Workspace', details.workspace.name], ['Khách hàng', details.selected_client?.name || 'Chưa chọn'], ['Từ ngày', period.start], ['Đến ngày', period.end], ['Tiền tệ', initial.currency], ['Múi giờ', initial.timezone], ['Nguồn', $('#marketing-source').selectedOptions[0].textContent], ['Nhóm nền tảng', group], ['Từ khóa chiến dịch', $('#marketing-campaign-search').value], ['Lọc chiến dịch', $('#marketing-campaign-platform').value, $('#marketing-campaign-state').value], [], ['Chỉ số', 'Giá trị', 'Trạng thái', 'Nguồn']];
    for (const key of metrics) { const item = snapshot.metrics[key], hasValue = ['ready', 'partial'].includes(item.status) && finite(item.value); lines.push([initial.metrics[key].label, hasValue ? item.value : '', hasValue ? item.status : item.status === 'error' ? 'Chưa tải được' : 'Chưa có dữ liệu', item.source_label || initial.metrics[key].source_label]); }
    lines.push([], ['Nền tảng', 'Chi tiêu', 'Hiển thị', 'Lượt nhấp', 'CTR (%)', 'CPC', 'Chuyển đổi']);
    for (const platform of initial.platforms.filter((p) => sourceMatches(p.id) && (group === 'all' || p.group === group))) { const value = platformValues(platform); lines.push([platform.name, ...['spend', 'impressions', 'clicks', 'ctr', 'cpc', 'conversions'].map((key) => finite(value[key]) ? value[key] : '')]); }
    lines.push([], ['Chiến dịch', 'Nền tảng', 'Trạng thái', 'Ngân sách/ngày', 'Chi tiêu', 'Lượt nhấp', 'CTR (%)', 'Chuyển đổi', 'CPA']);
    for (const item of filteredCampaigns) { const value = ['ready', 'partial'].includes(item.data_status) ? item.values || {} : {}; lines.push([item.name, initial.platforms.find((p) => p.id === item.platform_id).name, states[item.state] || states.unknown, ...['budget_daily', 'spend', 'clicks', 'ctr', 'conversions', 'cpa'].map((key) => finite(value[key]) ? value[key] : '')]); }
    const blob = new Blob(['\ufeff' + lines.map((row) => row.map(csvQuote).join(',')).join('\r\n')], {type: 'text/csv;charset=utf-8'}), url = URL.createObjectURL(blob), link = node('a', ''); link.href = url; link.download = `vio-marketing-${period.start}-${period.end}.csv`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); notify('Đã xuất CSV theo bộ lọc hiện tại. Chỉ số chưa có dữ liệu được để trống.');
  }
  $('#marketing-client').addEventListener('change', () => operation(async () => {
    const id = $('#marketing-client').value; if (!details.clients.some((c) => c.id === id)) return;
    invalidate();
    try { await api(`${base}/clients/${id}/select`, {}); await refresh(); notify('Đã cập nhật khách hàng. Dashboard đang chờ dữ liệu nguồn trong phạm vi mới.'); }
    catch (error) { try { await refresh(); } catch { /* Keep controls locked until a successful retry. */ } throw error; }
  }));
  $('#marketing-workspace-select').addEventListener('change', () => operation(async () => { const id = $('#marketing-workspace-select').value; if (!session.workspaces.some((w) => w.id === id)) return; invalidate(); await api(`workspaces/${id}/select`, {}); location.assign('/workspace/dashboard'); }));
  $('#marketing-refresh').addEventListener('click', () => operation(async () => { invalidate(); await refresh(); notify('Đã kiểm tra thông tin Workspace. Dữ liệu Marketing sẽ xuất hiện khi nguồn được kết nối và đồng bộ.'); }));
  $('#marketing-logout').addEventListener('click', () => operation(async () => { await api('auth/logout', {}); location.assign('/workspace/login'); }));
  $('#marketing-period').addEventListener('change', (e) => preset(e.target.value));
  $('#marketing-custom-period').addEventListener('submit', (e) => { e.preventDefault(); const start = $('#marketing-start').value, end = $('#marketing-end').value; if (!validDate(start) || !validDate(end) || start > end || end > today || (date(end) - date(start)) / dayMs > 365) { notify('Chọn khoảng thời gian hợp lệ, tối đa 366 ngày và không vượt quá hôm nay.', 'error'); return; } period = {start, end}; updatePeriod(); invalidate(); saveFilters(); notify(''); });
  for (const selector of ['#marketing-comparison', '#marketing-source', '#marketing-granularity']) $(selector).addEventListener('change', () => { updatePeriod(); invalidate(); saveFilters(); notify(''); });
  const tabs = [...document.querySelectorAll('[data-chart-metric]')];
  tabs.forEach((tab, index) => { tab.addEventListener('click', () => { metric = tab.dataset.chartMetric; tabs.forEach((t) => { t.setAttribute('aria-selected', String(t === tab)); t.tabIndex = t === tab ? 0 : -1; }); renderChart(); }); tab.addEventListener('keydown', (e) => { if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return; e.preventDefault(); const next = e.key === 'Home' ? tabs[0] : e.key === 'End' ? tabs[tabs.length - 1] : tabs[(index + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length]; next.click(); next.focus(); }); });
  document.querySelectorAll('[data-platform-group]').forEach((button) => button.addEventListener('click', () => { group = button.dataset.platformGroup; renderPlatforms(); }));
  for (const selector of ['#marketing-campaign-search', '#marketing-campaign-platform', '#marketing-campaign-state', '#marketing-campaign-sort']) $(selector).addEventListener(selector.endsWith('search') ? 'input' : 'change', () => { campaignPage = 1; renderCampaigns(); });
  $('#marketing-campaign-reset').addEventListener('click', () => { $('#marketing-campaign-search').value = ''; $('#marketing-campaign-platform').value = 'all'; $('#marketing-campaign-state').value = 'all'; campaignPage = 1; renderCampaigns(); $('#marketing-campaign-search').focus(); });
  $('#marketing-page-prev').addEventListener('click', () => { campaignPage -= 1; renderCampaigns(); }); $('#marketing-page-next').addEventListener('click', () => { campaignPage += 1; renderCampaigns(); });
  $('#marketing-export').addEventListener('click', exportCSV); $('#marketing-guide').addEventListener('click', guide);
  $('#marketing-definitions').addEventListener('click', () => dialog('Cách đọc dữ liệu đa nguồn', 'CTR = lượt nhấp / lượt hiển thị × 100%. CPC = chi phí / lượt nhấp. CPA = chi phí / chuyển đổi. Giá trị chỉ được hiển thị khi nguồn đã cung cấp dữ liệu phù hợp; không tự tính khi thiếu mẫu số.\n\nNgân sách/ngày có thể không áp dụng cho chiến dịch dùng ngân sách trọn đời. Chuyển đổi giữa các nền tảng có thể trùng lặp và không đồng nghĩa khách hàng mới. Các tổng KPI cần được chuẩn hóa, xác định phạm vi và mô hình ghi nhận trước khi đưa vào Dashboard.'));
  document.querySelectorAll('[data-metric-info]').forEach((b) => b.addEventListener('click', () => dialog(initial.metrics[b.dataset.metricInfo].label, definitions[b.dataset.metricInfo], null)));
  document.querySelectorAll('[data-marketing-future], [data-future]').forEach((b) => b.addEventListener('click', () => location.assign('/workspace/reports')));
  document.querySelectorAll('[data-sidebar-platform]').forEach((b) => b.addEventListener('click', () => { const platform = initial.platforms.find((p) => p.id === b.dataset.sidebarPlatform); if (platform) dialog(platform.name, platform.description + '\n\nPhân tích chuyên sâu cho Workspace đang được hoàn thiện. Bạn có thể xem thông tin nguồn và chuẩn bị kết nối trước.', '/workspace/integrations?platform=' + encodeURIComponent(platform.id)); }));
  $('#marketing-dialog-close').addEventListener('click', () => $('#marketing-dialog').close());
  window.addEventListener('pageshow', (e) => { if (e.persisted) location.reload(); });
  const params = new URLSearchParams(location.search), start = params.get('start'), end = params.get('end');
  const defaultPeriod = details.preferences?.default_period || 'last30';
  $('#marketing-period').value = defaultPeriod; period = presetRange(defaultPeriod);
  if (details.preferences?.compare_previous === false) $('#marketing-comparison').value = 'none';
  if (validDate(start) && validDate(end) && start <= end && end <= today && (date(end) - date(start)) / dayMs <= 365) { period = {start, end}; $('#marketing-period').value = 'custom'; }
  for (const [key, selector] of [['source', '#marketing-source'], ['granularity', '#marketing-granularity'], ['comparison', '#marketing-comparison']]) { const value = params.get(key); if ([...$(selector).options].some((o) => o.value === value)) $(selector).value = value; }
  $('#marketing-custom-period').hidden = $('#marketing-period').value !== 'custom';
  $('#marketing-timezone').textContent = `${initial.currency} · ${initial.timezone}`;
  updatePeriod(); snapshot = empty(); render(); controls();
  window.VioMarketing = Object.freeze({getContext, applySnapshot, reset: invalidate});
  operation(refresh);
})();
