/* Overview presentation adapter. Missing values stay null; scope and period must match. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const initial = JSON.parse($('#overview-analytics-data').textContent);
  let details = JSON.parse($('#overview-data').textContent);
  let metric = 'spend', period, snapshot, selectingClient = false;
  const dayMs = 86400000;
  const finite = (value) => typeof value === 'number' && Number.isFinite(value);
  const iso = (date) => date.toISOString().slice(0, 10);
  const date = (value) => new Date(value + 'T00:00:00Z');
  const shift = (value, days) => iso(new Date(date(value).getTime() + days * dayMs));
  const validDate = (value) => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(date(value).getTime()) && iso(date(value)) === value;
  const displayDate = (value) => new Intl.DateTimeFormat('vi-VN', {timeZone: 'UTC'}).format(date(value));
  const parts = new Intl.DateTimeFormat('en', {timeZone: initial.timezone, year: 'numeric', month: '2-digit', day: '2-digit'}).formatToParts(new Date());
  const part = (key) => parts.find((item) => item.type === key).value;
  const today = `${part('year')}-${part('month')}-${part('day')}`;
  function element(tag, text, className) {
    const node = document.createElement(tag); node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function notify(text) { $('#overview-marketing-status').textContent = text; $('#overview-marketing-status').hidden = !text; }
  function empty(keepConnections = false) {
    return {...structuredClone(initial), scope: {workspace_id: initial.scope.workspace_id, client_id: details.selected_client?.id || null},
      period: {...period}, connections: keepConnections ? snapshot?.connections || [] : []};
  }
  function formatted(value, key) {
    if (!finite(value)) return '—';
    return key === 'spend' ? new Intl.NumberFormat('vi-VN', {style: 'currency', currency: initial.currency, maximumFractionDigits: initial.currency === 'VND' ? 0 : 2}).format(value)
      : new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 2}).format(value);
  }
  function previousPeriod() {
    const days = Math.round((date(period.end) - date(period.start)) / dayMs) + 1;
    return {start: shift(period.start, -days), end: shift(period.start, -1), days};
  }
  function setPeriod(start, end) {
    period = {start, end};
    const previous = previousPeriod();
    $('#overview-comparison').textContent = `so với ${previous.days} ngày trước`;
    $('#overview-comparison').hidden = details.preferences?.compare_previous === false;
    $('#overview-period-label').textContent = `${displayDate(start)} – ${displayDate(end)} · ${initial.timezone}`;
    $('#overview-start').value = start; $('#overview-end').value = end;
    $('#overview-start').max = today; $('#overview-end').max = today;
    snapshot = empty(true); render(); notify('');
    document.dispatchEvent(new CustomEvent('customer:overview-context', {detail: getContext()}));
  }
  function preset(key) {
    if (key === 'custom') { $('#overview-custom-period').hidden = false; return; }
    $('#overview-custom-period').hidden = true;
    const first = today.slice(0, 8) + '01';
    if (key === 'this_month') setPeriod(first, today);
    else if (key === 'previous_month') { const end = shift(first, -1); setPeriod(end.slice(0, 8) + '01', end); }
    else setPeriod(shift(today, key === 'last7' ? -6 : key === 'last90' ? -89 : -29), today);
  }
  function renderMetrics() {
    for (const [key, metadata] of Object.entries(initial.metrics)) {
      const item = snapshot.metrics[key] || {};
      const ready = ['ready', 'partial'].includes(item.status) && finite(item.value);
      const card = document.querySelector(`[data-kpi="${key}"]`);
      card.dataset.state = ready ? item.status : item.status === 'error' ? 'error' : 'empty';
      card.querySelector('[data-kpi-value]').textContent = ready ? formatted(item.value, key) : '—';
      card.querySelector('[data-kpi-status]').textContent = ready ? item.status === 'partial' ? 'Dữ liệu một phần' : 'Có dữ liệu' : item.status === 'error' ? 'Chưa tải được' : 'Chưa có dữ liệu';
      const change = card.querySelector('[data-kpi-change]');
      change.hidden = !ready || !finite(item.previous) || details.preferences?.compare_previous === false;
      change.textContent = item.previous === 0 ? item.value === 0 ? 'Không thay đổi so với kỳ trước' : 'Kỳ trước có giá trị 0'
        : finite(item.previous) ? `${new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 1, signDisplay: 'exceptZero'}).format((item.value - item.previous) / Math.abs(item.previous) * 100)}% so với kỳ trước` : '';
      card.querySelector('.od-kpi-footer>span:last-child').textContent = item.source_label || metadata.source_label;
    }
  }
  function svgNode(tag, attributes, text) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function renderChart() {
    const trend = snapshot.trends[metric] || {};
    const points = (Array.isArray(trend.points) ? trend.points : []).slice(0, 366).filter((point) => point && validDate(point.date)
      && point.date >= period.start && point.date <= period.end).sort((a, b) => a.date.localeCompare(b.date));
    const ready = ['ready', 'partial'].includes(trend.status) && points.some((point) => finite(point.value));
    $('#overview-chart-empty').hidden = ready; $('#overview-chart-live').hidden = !ready; $('#overview-trend-table').hidden = !ready;
    $('#overview-chart-description').textContent = trend.status === 'error' ? 'Chưa tải được dữ liệu xu hướng. Kiểm tra trạng thái nguồn và thử lại.'
      : 'Xu hướng sẽ xuất hiện khi nguồn được kết nối và có dữ liệu trong kỳ đã chọn.';
    $('#overview-trend-panel').setAttribute('aria-labelledby', 'trend-tab-' + metric);
    const svg = $('#overview-trend-svg'); svg.replaceChildren();
    $('#overview-trend-table tbody').replaceChildren();
    if (!ready) return;
    const values = points.filter((point) => finite(point.value)).map((point) => point.value);
    const min = Math.min(0, ...values), max = Math.max(1, ...values), span = max - min || 1;
    const x = (index) => points.length === 1 ? 330 : 65 + index / (points.length - 1) * 550;
    const y = (value) => 205 - (value - min) / span * 170;
    for (let i = 0; i < 4; i += 1) {
      const value = min + span * i / 3, yy = y(value);
      svg.append(svgNode('line', {x1: 65, x2: 615, y1: yy, y2: yy, stroke: '#e2e8f0', 'stroke-width': 1}));
      svg.append(svgNode('text', {x: 55, y: yy + 3, 'text-anchor': 'end'}, new Intl.NumberFormat('vi-VN', {notation: 'compact', maximumFractionDigits: 1}).format(value)));
    }
    let path = '', pen = false;
    points.forEach((point, index) => {
      if (!finite(point.value)) { pen = false; return; }
      path += `${pen ? 'L' : 'M'}${x(index).toFixed(2)} ${y(point.value).toFixed(2)} `; pen = true;
    });
    svg.append(svgNode('path', {d: path, fill: 'none', stroke: '#d9232e', 'stroke-width': 2.5, 'stroke-linejoin': 'round', 'stroke-linecap': 'round'}));
    if (values.length === 1) {
      const index = points.findIndex((point) => finite(point.value));
      svg.append(svgNode('circle', {cx: x(index), cy: y(points[index].value), r: 4, fill: '#d9232e'}));
    }
    svg.append(svgNode('text', {x: 65, y: 233}, displayDate(points[0].date)), svgNode('text', {x: 615, y: 233, 'text-anchor': 'end'}, displayDate(points[points.length - 1].date)));
    svg.setAttribute('aria-label', `Xu hướng ${initial.metrics[metric].label}, ${displayDate(period.start)} đến ${displayDate(period.end)}`);
    $('#overview-trend-caption').textContent = initial.metrics[metric].label;
    for (const point of points) { const row = document.createElement('tr'); row.append(element('td', displayDate(point.date)), element('td', formatted(point.value, metric))); $('#overview-trend-table tbody').append(row); }
  }
  function renderConnections() {
    const known = new Set(initial.platforms.map((platform) => platform.id));
    const connections = (Array.isArray(snapshot.connections) ? snapshot.connections : []).filter((item) => item && known.has(item.platform_id));
    for (const platform of initial.platforms) {
      const row = document.querySelector(`[data-source="${platform.id}"]`);
      const connection = connections.find((item) => item.platform_id === platform.id);
      const states = {connected: 'Đã kết nối', syncing: 'Đang đồng bộ', error: 'Cần kiểm tra', expired: 'Cần cấp quyền lại'};
      row.dataset.state = connection?.state || 'empty';
      row.querySelector('[data-source-description]').textContent = connection ? states[connection.state] || 'Chưa kết nối' : platform.subtitle;
      row.querySelector('[data-source-action]').textContent = connection ? ['error', 'expired'].includes(connection.state) ? 'Kiểm tra' : 'Quản lý' : 'Kết nối';
    }
    const count = new Set(connections.filter((item) => ['connected', 'syncing'].includes(item.state)).map((item) => item.platform_id)).size;
    $('#overview-source-count').textContent = count ? `${count} nguồn đang hoạt động` : 'Chưa có nguồn hoạt động';
    const stamp = snapshot.last_updated_at && new Date(snapshot.last_updated_at);
    $('#overview-freshness').textContent = stamp && !Number.isNaN(stamp.getTime())
      ? 'Cập nhật: ' + new Intl.DateTimeFormat('vi-VN', {dateStyle: 'short', timeStyle: 'short', timeZone: initial.timezone}).format(stamp)
      : 'Dữ liệu sẽ hiển thị sau khi kết nối và đồng bộ.';
  }
  function reportHref(value) {
    return typeof value === 'string' && /^\/reports\/rpt_[a-f0-9]{32}\?revision=[1-9]\d*$/.test(value) ? value : '';
  }
  function renderReports() {
    const reports = (Array.isArray(snapshot.reports) ? snapshot.reports : []).filter((item) => item && typeof item === 'object').slice(0, 5);
    $('#overview-reports-empty').hidden = reports.length > 0; $('#overview-reports-list').hidden = !reports.length;
    $('#overview-reports-list').replaceChildren(...reports.map((report) => {
      const row = element('div', '', 'od-report-row'); const text = element('div', '');
      text.append(element('strong', report.name || 'Báo cáo'), element('small', report.period_label || 'Chưa có thông tin kỳ báo cáo'));
      row.append(text, element('span', report.status === 'final' ? 'Đã phát hành' : 'Bản tạm'));
      const href = reportHref(report.href);
      if (href) { const link = element('a', 'Xem báo cáo'); link.href = href; row.append(link); }
      return row;
    }));
  }
  function render() { renderMetrics(); renderChart(); renderConnections(); renderReports(); }
  function getContext() { return {schema_version: 1, scope: {workspace_id: initial.scope.workspace_id, client_id: details.selected_client?.id || null}, period: {...period}, currency: initial.currency, timezone: initial.timezone}; }
  function applySnapshot(payload) {
    const context = getContext();
    if (selectingClient || payload?.schema_version !== 1 || payload.scope?.workspace_id !== context.scope.workspace_id || payload.scope?.client_id !== context.scope.client_id
        || payload.period?.start !== period.start || payload.period?.end !== period.end
        || payload.currency !== initial.currency || payload.timezone !== initial.timezone
        || (payload.metrics?.spend?.currency && payload.metrics.spend.currency !== initial.currency)) return false;
    const next = empty();
    for (const key of Object.keys(initial.metrics)) if (payload.metrics?.[key]) next.metrics[key] = {...next.metrics[key], ...payload.metrics[key]};
    for (const key of Object.keys(initial.trends)) if (payload.trends?.[key]) next.trends[key] = structuredClone(payload.trends[key]);
    next.connections = structuredClone(payload.connections || []); next.reports = structuredClone(payload.reports || []); next.last_updated_at = payload.last_updated_at || null;
    snapshot = next; render(); return true;
  }
  function updateClients(next) {
    if (next.workspace.id !== initial.scope.workspace_id) return;
    selectingClient = false; notify('');
    const previousId = details.selected_client?.id || null; details = next;
    const select = $('#overview-client-context');
    select.replaceChildren(new Option('Chọn khách hàng / thương hiệu', ''), ...next.clients.map((client) => new Option(client.name, client.id)));
    select.value = next.selected_client?.id || ''; select.options[0].disabled = Boolean(next.selected_client);
    select.dataset.clientControl = ''; select.dataset.locked = String(!next.clients.length); select.disabled = !next.clients.length;
    if (previousId !== (next.selected_client?.id || null)) { snapshot = empty(); render(); document.dispatchEvent(new CustomEvent('customer:overview-context', {detail: getContext()})); }
  }
  $('#overview-client-context').addEventListener('change', (event) => {
    if (event.target.value) {
      selectingClient = true; snapshot = empty(); render(); notify('Đang chuyển khách hàng…');
      document.dispatchEvent(new CustomEvent('customer:select-client', {detail: {id: event.target.value}}));
    }
  });
  document.addEventListener('customer:workspace-detail', (event) => updateClients(event.detail));
  document.addEventListener('customer:client-selection-error', (event) => notify(event.detail.message || 'Chưa thể chuyển khách hàng. Vui lòng thử lại.'));
  $('#overview-period').addEventListener('change', (event) => preset(event.target.value));
  $('#overview-custom-period').addEventListener('submit', (event) => {
    event.preventDefault(); const start = $('#overview-start').value, end = $('#overview-end').value;
    if (!start || !end || start > end || end > today || (date(end) - date(start)) / dayMs > 365) { notify('Chọn khoảng thời gian hợp lệ, tối đa 366 ngày và không vượt quá hôm nay.'); return; }
    setPeriod(start, end);
  });
  const tabs = [...document.querySelectorAll('[data-trend]')];
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => { metric = tab.dataset.trend; tabs.forEach((item) => { item.setAttribute('aria-selected', String(item === tab)); item.tabIndex = item === tab ? 0 : -1; }); renderChart(); });
    tab.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault(); const next = event.key === 'Home' ? tabs[0] : event.key === 'End' ? tabs[tabs.length - 1] : tabs[(index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length]; next.click(); next.focus();
    });
  });
  document.querySelectorAll('[data-overview-channel]').forEach((button) => button.addEventListener('click', () => {
    const id = button.dataset.overviewChannel;
    const channel = initial.channels.find((item) => item.id === id) || initial.platforms.find((item) => item.id === id);
    if (!channel) return;
    location.assign('/workspace/channels?channel=' + encodeURIComponent(id));
  }));
  $('#overview-export').addEventListener('click', () => {
    const quote = (value) => { let text = String(value ?? ''); if (/^[\s\uFEFF]*[=+\-@]|^[\t\r\n]/.test(text)) text = "'" + text; return '"' + text.replaceAll('"', '""') + '"'; };
    const rows = [['Workspace', details.workspace.name], ['Khách hàng', details.selected_client?.name || 'Chưa chọn'], ['Từ ngày', period.start], ['Đến ngày', period.end], ['Múi giờ', initial.timezone], ['Tiền tệ', initial.currency], [], ['Chỉ số', 'Giá trị', 'Trạng thái', 'Nguồn']];
    for (const [key, metadata] of Object.entries(initial.metrics)) { const item = snapshot.metrics[key]; const ready = ['ready', 'partial'].includes(item.status) && finite(item.value); rows.push([metadata.label, ready ? item.value : '', ready ? item.status === 'partial' ? 'Dữ liệu một phần' : 'Có dữ liệu' : 'Chưa có dữ liệu', item.source_label || metadata.source_label]); }
    const blob = new Blob(['\ufeff' + rows.map((row) => row.map(quote).join(',')).join('\r\n')], {type: 'text/csv;charset=utf-8'});
    const url = URL.createObjectURL(blob), link = document.createElement('a'); link.href = url; link.download = `vio-overview-${period.start}-${period.end}.csv`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    notify('Đã xuất tóm tắt CSV. Chỉ số chưa có dữ liệu được để trống trong tệp.');
  });
  window.VioOverview = Object.freeze({getContext, applySnapshot, reset: () => { snapshot = empty(); render(); }});
  $('#overview-period').value = details.preferences?.default_period || 'last30';
  preset($('#overview-period').value);
})();
