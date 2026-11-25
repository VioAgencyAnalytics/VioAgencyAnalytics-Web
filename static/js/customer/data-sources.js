/* One private source contract for every connector; never invent cross-source totals. */
(() => {
  'use strict';
  const root = document.querySelector('[data-customer-sources]'); if (!root) return;
  const initial = JSON.parse(document.querySelector('#overview-data, #marketing-data, #library-data').textContent);
  const workspaceId = initial.workspace.id, all = root.dataset.mode === 'all';
  const grid = root.querySelector('[data-sources-grid]'), status = root.querySelector('[data-sources-status]');
  let selected = initial.selected_client?.id || null, generation = 0, controller;
  const labels = {no_client:'Chọn khách hàng', not_connected:'Chưa kết nối', planned:'Sắp hỗ trợ', select_asset:'Chọn tài khoản',
    syncing:'Đang đồng bộ', sync_error:'Cần kiểm tra', empty:'Chờ dữ liệu', ready:'Có dữ liệu', invalid:'Cần đồng bộ lại'};
  const node = (tag, value, cls) => { const el = document.createElement(tag); el.textContent = value; if (cls) el.className = cls; return el; };
  function format(metric) {
    return window.VioDataFormat.format(metric.value,metric.unit,metric.currency);
  }
  function card(source) {
    const el = node('article', '', 'cd-source'), heading = node('div', '', 'cd-source-heading');
    el.dataset.source = source.source;
    window.VioPlatformBrand?.setTheme(el, source.source);
    const icon = window.VioPlatformBrand?.logo(source.source, 'cd-source-icon') || node('span', source.connector.icon, 'material-symbols-outlined cd-source-icon'); icon.setAttribute('aria-hidden','true');
    const title = node('div',''); title.append(node('h3',source.connector.name),node('span',labels[source.state] || 'Chưa có dữ liệu','cd-source-state'));
    heading.append(icon,title); el.append(heading);
    const metric = source.metrics[0], hasData = source.state === 'ready';
    const value = node('div','','cd-source-value');
    if (source.source === 'facebook_content' && !all) value.id = 'meta-summary-metric';
    const strong = node('strong',hasData && metric ? format(metric) : '—');
    if (source.source === 'facebook_content' && !all) strong.id = 'meta-summary-posts';
    value.append(strong,node('span',metric?.label || 'Dữ liệu nguồn')); el.append(value);
    const period = source.snapshot;
    el.append(node('p',period ? `${period.start_date} → ${period.end_date} · ${period.timezone}` : source.asset ? 'Chọn kỳ báo cáo và đặt mục tiêu KPI.' : source.availability === 'not_configured' ? 'Chờ VIO cấu hình ứng dụng.' : source.state === 'planned' ? 'Connector đang được phát triển.' : 'Cấp quyền và chọn tài khoản.','cd-source-period'));
    const canRead = hasData || Boolean(source.asset), facebookReport = canRead && source.source === 'facebook_content';
    if (facebookReport && all) el.classList.add('cd-report-ready');
    if (hasData && source.latest_sync?.status === 'failed') el.append(node('p','Lần đồng bộ mới cần kiểm tra. Báo cáo vẫn giữ dữ liệu đã lưu.','cd-source-period'));
    const link = node('a',hasData ? 'Xem báo cáo →' : source.asset ? 'Chọn kỳ & đặt KPI →' : source.state === 'planned' || source.availability === 'not_configured' ? 'Xem nền tảng →' : 'Quản lý kết nối →','cd-detail-link');
    link.href = facebookReport ? '/workspace/reports/facebook-content'+(period ? '?snapshot='+encodeURIComponent(period.id) : '') : canRead ? '/workspace/reports/data?source='+encodeURIComponent(source.source)+(period ? '&snapshot='+encodeURIComponent(period.id) : '') : '/workspace/integrations?platform='+encodeURIComponent(source.source);
    el.append(link); return el;
  }
  async function refresh() {
    const ticket = ++generation, clientId = selected;
    controller?.abort(); controller = new AbortController();
    grid.replaceChildren(); root.hidden = !all; root.setAttribute('aria-busy','true');
    root.querySelector('[data-sources-other]')?.replaceChildren();
    if (root.querySelector('[data-sources-catalogue]')) root.querySelector('[data-sources-catalogue]').hidden = true;
    root.querySelector('[data-sources-retry]').hidden = true;
    status.textContent = clientId ? 'Đang tải dữ liệu đã đồng bộ…' : 'Chọn khách hàng để xem dữ liệu các nền tảng.';
    if (!clientId) { root.setAttribute('aria-busy','false'); return; }
    try {
      const response = await fetch(`/api/customer/workspaces/${workspaceId}/data`, {credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'},signal:controller.signal});
      const data = await response.json();
      if (ticket !== generation || clientId !== selected) return;
      if (response.status === 401) { location.replace('/workspace/login'); return; }
      if (!response.ok || data.scope?.workspace_id !== workspaceId || data.scope?.client_id !== clientId || !Array.isArray(data.sources)) throw new Error();
      const sources = data.sources.filter((s) => all || !['planned','no_client','not_connected'].includes(s.state));
      root.hidden = !all && !sources.length;
      const catalogue = root.querySelector('[data-sources-other]');
      if (all && catalogue) {
        const ready = sources.filter((s) => s.state === 'ready'), others = sources.filter((s) => s.state !== 'ready');
        grid.replaceChildren(...ready.map(card)); catalogue.replaceChildren(...others.map(card));
        const disclosure = root.querySelector('[data-sources-catalogue]'); disclosure.hidden = !others.length;
        root.querySelector('[data-sources-other-count]').textContent = others.length;
        if (!ready.length) disclosure.open = true;
      } else grid.replaceChildren(...sources.map(card));
      status.textContent = `${data.sources.filter((s) => s.state === 'ready').length} nguồn có dữ liệu · Mỗi nguồn hiển thị kỳ đã lưu gần nhất.`;
    } catch (error) {
      if (ticket !== generation || error.name === 'AbortError') return;
      root.hidden = false; status.textContent = 'Chưa tải được dữ liệu. Hãy thử lại.';
      root.querySelector('[data-sources-retry]').hidden = false;
    } finally { if (ticket === generation) root.setAttribute('aria-busy','false'); }
  }
  root.querySelector('[data-sources-retry]').addEventListener('click', refresh);
  document.addEventListener('customer:scope-changing',()=>{selected=null;refresh();});
  document.addEventListener('customer:workspace-detail',(event) => { selected = event.detail.selected_client?.id || null; refresh(); });
  document.addEventListener('customer:marketing-context',(event) => { const id = event.detail.scope?.client_id || null; if (id !== selected) { selected = id; refresh(); } });
  document.addEventListener('customer:library-context',(event) => { const id = event.detail.scope?.client_id || null; selected = id; refresh(); });
  window.addEventListener('pageshow',(event) => { if (event.persisted) refresh(); });
  refresh();
})();
