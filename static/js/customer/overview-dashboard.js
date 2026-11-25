/* Overview presentation adapter. Missing values stay null; scope and period must match. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const initial = JSON.parse($('#overview-analytics-data').textContent);
  let details = JSON.parse($('#overview-data').textContent);
  let metric = 'spend', period, snapshot, selectingClient = false;
  const saved = window.VioSavedAnalytics;
  let analytics, generation = 0, controller, timer;
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
    if (analytics?.focus) return saved.format(value,snapshot.metrics[key]);
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
    $('#overview-comparison').textContent = '';
    $('#overview-comparison').hidden = $('#overview-compare')?.value === 'none';
    $('#overview-period-label').textContent = `${displayDate(start)} – ${displayDate(end)} · ${initial.timezone}`;
    $('#overview-start').value = start; $('#overview-end').value = end;
    $('#overview-start').removeAttribute('max'); $('#overview-end').removeAttribute('max');
    analytics=null;snapshot = empty(true); render(); notify('');
    document.dispatchEvent(new CustomEvent('customer:overview-context', {detail: getContext()}));
    loadSaved();
  }
  function preset(key) {
    if (key === 'custom') { $('#overview-custom-period').hidden = false; return; }
    $('#overview-custom-period').hidden = true;
    if (key === 'latest') { setPeriod(shift(today,-30),shift(today,-1)); return; }
    const chosen=saved.periodRange(key,analytics?.calendar,today);setPeriod(chosen.start,chosen.end);
  }
  function renderMetrics() {
    for (const [key, metadata] of Object.entries(initial.metrics)) {
      const item = snapshot.metrics[key] || {};
      const ready = ['ready', 'partial'].includes(item.status) && saved.measured(item.value);
      const card = document.querySelector(`[data-kpi="${key}"]`);
      card.querySelector('h2').textContent=item.label || metadata.label;
      card.querySelector('.ui-tip p').textContent=item.hint || metadata.hint;
      card.dataset.state = ready ? item.status : item.status === 'error' ? 'error' : 'empty';
      card.querySelector('[data-kpi-value]').textContent = ready ? formatted(item.value, key) : '—';
      card.querySelector('[data-kpi-status]').textContent = ready ? item.status === 'partial' ? 'Dữ liệu một phần' : 'Có dữ liệu' : item.status === 'error' ? 'Chưa tải được' : 'Chưa có dữ liệu';
      const change = card.querySelector('[data-kpi-change]');
      change.textContent = saved.changeText(item);
      change.dataset.effect = item.comparison?.effect || 'context';
      change.hidden = !ready || !change.textContent || $('#overview-compare')?.value === 'none';
      card.querySelector('.od-kpi-footer>span:last-child').textContent = item.source_label || metadata.source_label;
      let goal=card.querySelector('.sa-goal'); if (!goal) { goal=element('small','','sa-goal'); card.append(goal); }
      goal.textContent=saved.goalText(item.target); goal.hidden=!goal.textContent;
    }
  }
  function renderChart() {
    const trend = snapshot.trends[metric] || {};
    const points = (Array.isArray(trend.points) ? trend.points : []).slice(0, 366).filter((point) => point && validDate(point.date)
      && point.date >= period.start && point.date <= period.end).sort((a, b) => a.date.localeCompare(b.date));
    const ready = ['ready', 'partial'].includes(trend.status) && points.some((point) => saved.measured(point.value));
    $('#overview-chart-empty').hidden = ready; $('#overview-chart-live').hidden = !ready; $('#overview-trend-table').hidden = !ready;
    $('#overview-chart-description').textContent = trend.status === 'error' ? 'Chưa tải được dữ liệu xu hướng. Kiểm tra trạng thái nguồn và thử lại.'
      : analytics?.snapshot ? 'Nguồn chưa cung cấp chuỗi ngày cho chỉ số này; xem định nghĩa trong báo cáo.' : analytics?.focus ? 'Chưa có bản dữ liệu đúng kỳ. Mở báo cáo để chọn kỳ hoặc đồng bộ.' : 'Kết nối nguồn để xem xu hướng trong kỳ.';
    const emptyLink=$('#overview-chart-empty a');emptyLink.href=saved.href(analytics?.report_href) || '/workspace/integrations';emptyLink.textContent=analytics?.focus ? 'Mở báo cáo nguồn →' : 'Kết nối nền tảng →';
    $('#overview-trend-panel').setAttribute('aria-labelledby', 'trend-tab-' + metric);
    const svg = $('#overview-trend-svg'); svg.replaceChildren();
    $('#overview-trend-table tbody').replaceChildren();
    if (!ready) return;
    const metadata = snapshot.metrics[metric];
    const previous = analytics?.comparison?.status === 'ready' && metadata.comparison?.status === 'ready'
      ? window.VioReportCharts.points(analytics.comparison.daily, analytics.comparison.period?.start,
          analytics.comparison.period?.end, metadata.key) : [];
    window.VioReportCharts.renderSeries(svg, points, {
      title: metadata.label, kind: 'bar', previous, integer: metadata.unit === 'count',
      format: (value) => formatted(value, metric), maxGapDays: 1, legend: true,
      axisFormat: (value) => new Intl.NumberFormat('vi-VN', {notation: 'compact', maximumFractionDigits: 1}).format(metadata.unit === 'percent' ? value * 100 : value) + (metadata.unit === 'percent' ? '%' : ''),
    });
    $('#overview-trend-caption').textContent = snapshot.metrics[metric].label;
    for (const point of points) { const row = document.createElement('tr'); row.append(element('td', displayDate(point.date)), element('td', formatted(point.value, metric))); $('#overview-trend-table tbody').append(row); }
  }
  function renderConnections() {
    const known = new Set(initial.platforms.map((platform) => platform.id));
    const connections = (Array.isArray(snapshot.connections) ? snapshot.connections : []).filter((item) => item && known.has(item.platform_id));
    for (const platform of initial.platforms) {
      const row = document.querySelector(`[data-source="${platform.id}"]`);
      const connection = connections.find((item) => item.platform_id === platform.id);
      const source=analytics?.sources.find((item)=>item.source===platform.id);
      const states = {connected: 'Đã kết nối', syncing: 'Đang đồng bộ', error: 'Cần kiểm tra', expired: 'Cần cấp quyền lại'};
      row.dataset.state = connection?.state || 'empty';
      row.querySelector('[data-source-description]').textContent = source?.snapshot ? (source.latest_sync_failed ? 'Bản lưu cũ · lần mới cần kiểm tra' : source.snapshot.start_date+' → '+source.snapshot.end_date) : connection ? states[connection.state] || 'Chưa kết nối' : platform.subtitle;
      const link=row.querySelector('[data-source-action]');
      link.textContent=source?.snapshot ? 'Báo cáo' : connection ? ['error','expired'].includes(connection.state) ? 'Kết nối lại' : 'Quản lý' : 'Kết nối';
      link.href=source?.snapshot ? saved.href(source.href) : '/workspace/integrations?platform='+platform.id;
    }
    const count = new Set(connections.filter((item) => ['connected', 'syncing'].includes(item.state)).map((item) => item.platform_id)).size;
    $('#overview-source-count').textContent = count ? `${count} nguồn đang hoạt động` : 'Chưa có nguồn hoạt động';
    const stamp = snapshot.last_updated_at && new Date(snapshot.last_updated_at);
    $('#overview-freshness').textContent = stamp && !Number.isNaN(stamp.getTime())
      ? 'Cập nhật: ' + new Intl.DateTimeFormat('vi-VN', {dateStyle: 'short', timeStyle: 'short', timeZone: initial.timezone}).format(stamp)
      : 'Chưa đồng bộ dữ liệu.';
  }
  function reportHref(value) {
    const href=saved.href(value); if (href) return href;
    return typeof value === 'string' && /^\/reports\/rpt_[a-f0-9]{32}\?revision=[1-9]\d*$/.test(value) ? value : '';
  }
  function renderReports() {
    const reports = (Array.isArray(snapshot.reports) ? snapshot.reports : []).filter((item) => item && typeof item === 'object').slice(0, 5);
    $('#overview-reports-empty').hidden = reports.length > 0; $('#overview-reports-list').hidden = !reports.length;
    $('#overview-reports-list').replaceChildren(...reports.map((report) => {
      const row = element('div', '', 'od-report-row'); const text = element('div', '');
      text.append(element('strong', report.name || 'Báo cáo'), element('small', report.period_label || report.start+' → '+report.end),element('small',report.asset_name || ''));
      row.append(text, element('span', report.status === 'saved' ? 'Đã đồng bộ' : report.status === 'final' ? 'Đã phát hành' : 'Bản tạm'));
      const href = reportHref(report.href);
      if (href) { const link = element('a', 'Xem báo cáo'); link.href = href; row.append(link); }
      return row;
    }));
  }
  function render() {
    renderMetrics(); renderChart(); renderConnections(); renderReports();
    document.querySelectorAll('[data-trend]').forEach((tab) => { tab.textContent=snapshot.metrics[tab.dataset.trend]?.label || initial.metrics[tab.dataset.trend].label; });
    $('#overview-saved-caption').textContent=saved.caption(analytics);
    const link=$('#overview-saved-report'), address=saved.href(analytics?.report_href); link.hidden=!address; if(address)link.href=address;
    $('#overview-comparison').hidden=details.preferences?.compare_previous===false || !analytics?.comparison_available;
    $('#integration-card').hidden=Boolean(analytics?.reports.length);
  }
  async function loadSaved() {
    const ticket=++generation,clientId=details.selected_client?.id || null;
    controller?.abort(); clearTimeout(timer); controller=new AbortController(); analytics=null;
    if (!period || selectingClient || !clientId) { if(snapshot)render(); return; }
    $('#overview-saved-focus').setAttribute('aria-busy','true');
    try {
      const result=await saved.read(initial.scope.workspace_id,clientId,$('#overview-source').value,$('#overview-period').value==='latest' ? null : period,
        $('#overview-compare')?.value || (details.preferences?.compare_previous===false ? 'none' : 'previous'),controller.signal,'day',comparisonControls.range());
      if(ticket!==generation || selectingClient || details.selected_client?.id!==clientId)return;
      analytics=result;
      const selectedPreset=$('#overview-period').value;
      if(!['latest','custom'].includes(selectedPreset) && result.calendar){
        const aligned=saved.periodRange(selectedPreset,result.calendar,today);
        if(aligned.start!==period.start || aligned.end!==period.end){setPeriod(aligned.start,aligned.end);return;}
      }
      comparisonControls.update();
      $('#overview-comparison').textContent=saved.comparisonText(result.comparison);
      $('#overview-comparison').hidden=!$('#overview-comparison').textContent;
      if ($('#overview-period').value==='latest' && result.period) {
        period={start:result.period.start,end:result.period.end};
        $('#overview-start').value=period.start;$('#overview-end').value=period.end;
        $('#overview-period-label').textContent=displayDate(period.start)+' – '+displayDate(period.end)+' · '+(result.calendar?.timezone || result.snapshot?.timezone || initial.timezone);
      }
      snapshot=empty();snapshot.metrics={...snapshot.metrics,...result.metrics};snapshot.trends={...snapshot.trends,...result.trends};
      snapshot.connections=result.connections;snapshot.reports=result.reports;snapshot.last_updated_at=result.last_updated_at;render();notify('');
      schedule();
    } catch(error) { if(ticket!==generation || error.name==='AbortError')return; snapshot=empty();analytics=null;render();notify(error.message); }
    finally { if(ticket===generation)$('#overview-saved-focus').setAttribute('aria-busy','false'); }
  }
  function schedule(){clearTimeout(timer);if(!document.hidden)timer=setTimeout(loadSaved,analytics?.connections.some((item)=>item.state==='syncing') ? 6000 : 60000);}
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
    if (previousId !== (next.selected_client?.id || null)) { analytics=null;snapshot = empty(); render(); document.dispatchEvent(new CustomEvent('customer:overview-context', {detail: getContext()})); }
    loadSaved();
  }
  $('#overview-client-context').addEventListener('change', (event) => {
    if (event.target.value) {
      selectingClient = true;generation+=1;controller?.abort();analytics=null; snapshot = empty(); render(); notify('Đang chuyển khách hàng…');
      document.dispatchEvent(new CustomEvent('customer:scope-changing'));
      document.dispatchEvent(new CustomEvent('customer:select-client', {detail: {id: event.target.value}}));
    }
  });
  document.addEventListener('customer:workspace-detail', (event) => updateClients(event.detail));
  document.addEventListener('customer:client-selection-error', (event) => notify(event.detail.message || 'Chưa thể chuyển khách hàng. Vui lòng thử lại.'));
  $('#overview-period').addEventListener('change', (event) => preset(event.target.value));
  $('#overview-custom-period').addEventListener('submit', (event) => {
    event.preventDefault(); const start = $('#overview-start').value, end = $('#overview-end').value;
    if (!validDate(start) || !validDate(end) || start > end || (date(end) - date(start)) / dayMs > 89) { notify('Chọn khoảng thời gian hợp lệ, tối đa 90 ngày.'); return; }
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
    const rows = [['Workspace', details.workspace.name], ['Khách hàng', details.selected_client?.name || 'Chưa chọn'], ['Từ ngày', period.start], ['Đến ngày', period.end], ['Múi giờ', initial.timezone], ['Tiền tệ Workspace (không tự quy đổi)', initial.currency], [], ['Chỉ số', 'Giá trị', 'Trạng thái', 'Nguồn']];
    for (const [key, metadata] of Object.entries(initial.metrics)) { const item = snapshot.metrics[key]; const ready = ['ready', 'partial'].includes(item.status) && saved.measured(item.value); rows.push([item.label || metadata.label, ready ? item.value : '', ready ? item.status === 'partial' ? 'Dữ liệu một phần' : 'Có dữ liệu' : 'Chưa có dữ liệu', item.source_label || metadata.source_label,item.currency || '']); }
    const blob = new Blob(['\ufeff' + rows.map((row) => row.map(quote).join(',')).join('\r\n')], {type: 'text/csv;charset=utf-8'});
    const url = URL.createObjectURL(blob), link = document.createElement('a'); link.href = url; link.download = `vio-overview-${period.start}-${period.end}.csv`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    notify('Đã xuất tóm tắt CSV. Chỉ số chưa có dữ liệu được để trống trong tệp.');
  });
  window.VioOverview = Object.freeze({getContext, applySnapshot, reset: () => { snapshot = empty(); render(); }});
  $('#overview-source').addEventListener('change',()=>{analytics=null;snapshot=empty();render();loadSaved();});
  document.addEventListener('visibilitychange',()=>{clearTimeout(timer);if(!document.hidden)loadSaved();});
  window.addEventListener('pagehide',()=>{clearTimeout(timer);controller?.abort();});
  if($('#overview-compare') && details.preferences?.compare_previous===false)$('#overview-compare').value='none';
  const comparisonControls=saved.bindComparison('overview','#overview-compare',()=>analytics?.period || period,()=>analytics?.calendar,()=>{
    analytics=null; snapshot=empty(); render(); loadSaved();
  });
  const preferred = saved.preferredPeriod(details.preferences);
  $('#overview-period').value = [...$('#overview-period').options].some((option)=>option.value===preferred) ? preferred : 'latest';
  preset($('#overview-period').value);
})();
