/* Read saved observations. Consent, asset selection and sync remain in Integrations. */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s), report = JSON.parse($('#connector-report-data').textContent);
  const example = document.body.hasAttribute('data-report-example');
  const details = example ? null : JSON.parse($('#library-data').textContent), workspaceId = details?.workspace.id;
  const current = new URLSearchParams(location.search);
  const reportParams = new URLSearchParams({source: report.source});
  for (const key of ['style', 'palette', 'order', 'hidden', 'template', 'comparison', 'comparison_start', 'comparison_end']) {
    if (current.has(key)) reportParams.set(key, current.get(key));
  }
  const base = '/workspace/reports/data?' + reportParams;
  let session, busy = false, timer;
  const node = (tag,value,cls) => { const el = document.createElement(tag); el.textContent = value; if (cls) el.className = cls; return el; };
  const fold = (s) => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[đĐ]/g,'d').toLowerCase();
  function format(value,unit) {
    return window.VioDataFormat.format(value,unit,report.snapshot?.currency);
  }
  function feedback(message) { $('#data-feedback').textContent = message; $('#data-feedback').hidden = !message; }
  function controls() {
    $('#data-refresh').disabled = busy;
    $('#data-client').disabled = busy || !session?.user || !details.clients.length;
    $('#data-period').disabled = busy || !report.periods.length;
    $('#data-source').disabled = busy;
    $('#library-workspace-select').disabled = busy || !session?.workspaces?.length;
    $('#library-logout').disabled = busy || !session?.user;
  }
  async function api(path,body) {
    const options = {credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}};
    if (body !== undefined) Object.assign(options,{method:'POST',body:JSON.stringify(body),headers:{...options.headers,'Content-Type':'application/json','X-CSRF-Token':session?.csrf || ''}});
    const response = await fetch('/api/customer/'+path,options), value = await response.json();
    if (!response.ok) {
      if (response.status === 401) location.replace('/workspace/login');
      if (['client_changed','workspace_changed','workspace_access'].includes(value.code)) location.replace('/workspace');
      throw new Error(value.error || 'Chưa tải được dữ liệu. Hãy thử lại.');
    }
    return value;
  }
  async function run(action) {
    if (busy) return; busy = true; controls(); feedback('');
    try { await action(); } catch (error) { feedback(error.message); } finally { busy = false; controls(); }
  }
  function chart(target, key, interactive = false) {
    const paired = window.VioReportCharts.render(target,report,key,{
      kind: target?.dataset.chartKind || 'bar', compare: interactive,
      onRead: interactive ? (value) => { $('#data-chart-readout').textContent = value; } : null,
    });
    if (interactive) {
      const legend = $('#data-chart-legend .pr-legend-previous'); if (legend) legend.hidden = !paired;
    }
  }
  function drawCharts() {
    const selected = $('#data-chart-metric')?.value;
    chart($('#data-chart'),selected,true);
    const secondary = $('#data-secondary-charts'); if (!secondary) return;
    const candidates = report.metrics.filter((metric) => metric.key !== selected && metric.grain !== 'snapshot'
      && metric.unit !== 'percent' && report.daily.some((row) => row.values[metric.key] !== null && row.values[metric.key] !== undefined)).slice(0,2);
    secondary.replaceChildren(...candidates.map((metric) => {
      const panel = node('section','','cd-card cr-mini-chart'); panel.append(node('h2',metric.label));
      const area = node('div','','cd-chart cr-chart'); area.setAttribute('role','region'); area.tabIndex = 0; area.setAttribute('aria-label',metric.label+' theo ngày');
      panel.append(area); chart(area,metric.key); return panel;
    }));
    secondary.hidden = candidates.length === 0;
  }
  const tableRenders = [];
  for (const block of document.querySelectorAll('[data-table]')) {
    const table = report.tables.find((t) => t.id === block.dataset.table); if (!table) continue;
    let page = 1;
    function render(print = false) {
      const query = fold(block.querySelector('[data-table-search]').value.trim());
      const rows = print ? table.rows : table.rows.filter((r) => table.columns.some((col) => fold(r[col.key]).includes(query)));
      const pages = Math.max(1,Math.ceil(rows.length/20)); page = Math.min(page,pages);
      block.querySelector('[data-table-rows]').replaceChildren(...(print ? rows : rows.slice((page-1)*20,page*20)).map((row) => {
        const tr = document.createElement('tr');
        for (const col of table.columns) {
          const td = node('td',col.unit === 'text' ? row[col.key] ?? '—' : format(row[col.key],col.unit));
          if (!example && report.source === 'youtube' && col.key === 'video' && /^[A-Za-z0-9_-]{11}$/.test(row[col.key])) {
            const link = node('a',row[col.key]+' ↗'); link.href = 'https://www.youtube.com/watch?v='+row[col.key]; link.target = '_blank'; link.rel = 'noopener noreferrer'; td.replaceChildren(link);
          }
          tr.append(td);
        }
        return tr;
      }));
      block.querySelector('[data-table-empty]').hidden = rows.length > 0;
      block.querySelector('[data-table-count]').textContent = `${rows.length} hàng · Trang ${page}/${pages}`;
      block.querySelector('[data-table-prev]').disabled = page <= 1;
      block.querySelector('[data-table-next]').disabled = page >= pages;
    }
    block.querySelector('[data-table-search]').addEventListener('input',() => { page = 1; render(); });
    block.querySelector('[data-table-prev]').addEventListener('click',() => { page -= 1; render(); });
    block.querySelector('[data-table-next]').addEventListener('click',() => { page += 1; render(); });
    tableRenders.push(render); render();
  }
  $('#data-chart-metric')?.addEventListener('change',drawCharts); drawCharts();
  if (document.body.dataset.pdfRender === 'true') {
    $('#report-method').open = true;
    for (const render of tableRenders) render(true);
    return;
  }
  let methodWasOpen = false;
  window.addEventListener('beforeprint',() => { methodWasOpen = $('#report-method').open; $('#report-method').open = true; for (const render of tableRenders) render(true); });
  window.addEventListener('afterprint',() => { $('#report-method').open = methodWasOpen; for (const render of tableRenders) render(); });
  $('#data-print')?.addEventListener('click',event => window.VioReportNotes ? window.VioReportNotes.print(event.currentTarget) : window.print());
  document.querySelectorAll('a[href="#report-method"]').forEach((link) => link.addEventListener('click',() => { $('#report-method').open = true; }));
  if (example) return;
  $('#data-source').addEventListener('change',() => {
    const value = $('#data-source').value;
    if (![...$('#data-source').options].some((option) => option.value === value)) return;
    const filters = new URLSearchParams({source: value});
    for (const key of ['style', 'palette']) if (current.has(key)) filters.set(key, current.get(key));
    location.assign('/workspace/reports/data?' + filters);
  });
  $('#data-period').addEventListener('change',() => { const value = $('#data-period').value; if (report.periods.some((p) => p.id === value)) location.assign(base+'&snapshot='+encodeURIComponent(value)); });
  $('#data-refresh').addEventListener('click',() => location.reload());
  $('#data-client').addEventListener('change',() => run(async () => {
    const id = $('#data-client').value; if (!details.clients.some((c) => c.id === id)) return;
    await api(`workspaces/${workspaceId}/clients/${id}/select`,{}); location.assign(base);
  }));
  $('#library-workspace-select').addEventListener('change',() => run(async () => {
    const id = $('#library-workspace-select').value; if (!session.workspaces.some((w) => w.id === id)) return;
    await api(`workspaces/${id}/select`,{}); location.assign(base);
  }));
  $('#library-logout').addEventListener('click',() => run(async () => { await api('auth/logout',{}); location.assign('/workspace/login'); }));
  async function poll() {
    const params = new URLSearchParams(location.search), periodQuery = new URLSearchParams();
    for (const key of ['start','end']) if (params.has(key)) periodQuery.set(key,params.get(key));
    const next = await api(`workspaces/${workspaceId}/data/${report.source}`+(periodQuery.size ? '?'+periodQuery : ''));
    if (next.scope?.client_id !== report.scope.client_id || next.scope?.workspace_id !== workspaceId) { location.replace(base); return; }
    if (next.snapshot?.id !== report.snapshot?.id || next.latest_sync?.status !== report.latest_sync?.status || next.connection?.status !== report.connection?.status) { location.reload(); return; }
    schedule();
  }
  function schedule() { clearTimeout(timer); if (!document.hidden && !new URLSearchParams(location.search).has('snapshot') && ['queued','running'].includes(report.latest_sync?.status)) timer = setTimeout(() => run(poll),6000); }
  document.addEventListener('visibilitychange',() => { if (document.hidden) clearTimeout(timer); else schedule(); });
  window.addEventListener('pageshow',(event) => { if (event.persisted) location.reload(); });
  run(async () => { session = await api('session'); if (session.workspace?.id !== workspaceId) location.replace('/workspace'); else schedule(); });
})();
