/* Private saved observations only. Provider operations remain in Integrations. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const initial = $('#facebook-content-data'), library = $('#library-data');
  if (!initial || !library) return;
  const details = JSON.parse(library.textContent), data = JSON.parse(initial.textContent);
  const workspaceId = details.workspace.id, clientId = details.selected_client?.id || null;
  const report = Boolean(document.querySelector('[data-fc-report]'));
  const path = report ? '/workspace/reports/facebook-content' : '/workspace/channels/facebook-content';
  let session, busy = false, page = 1, timer, selectedFormat = 'all';
  const pageSize = 10, number = (value) => typeof value === 'number' && Number.isFinite(value) && value >= 0;
  const format = (value) => number(value) ? new Intl.NumberFormat('vi-VN').format(value) : 'Chưa có';
  const fold = (value) => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[đĐ]/g, 'd').toLowerCase();
  const formats = {photo:['Ảnh','image'],album:['Album','photo_library'],video:['Video','play_circle'],link:['Liên kết','link'],unknown:['Khác','article']};
  function node(tag, text, className) { const element = document.createElement(tag); element.textContent = text; if (className) element.className = className; return element; }
  function date(value, clock = false) {
    const stamp = new Date(clock ? value : value + 'T00:00:00Z');
    if (Number.isNaN(stamp.getTime())) return 'Chưa có ngày';
    return new Intl.DateTimeFormat('vi-VN', {dateStyle:'short', ...(clock ? {timeStyle:'short'} : {}), timeZone:'UTC'}).format(stamp);
  }
  function feedback(message) { if ($('#fc-feedback')) { $('#fc-feedback').textContent = message; $('#fc-feedback').hidden = !message; } }
  function disable(selector, value) { const item = $(selector); if (item) item.disabled = value; }
  function controls() {
    disable('#fc-refresh', busy); disable('#fc-client', busy || !details.clients.length);
    disable('#library-logout', busy || !session?.user);
    disable('#fc-snapshot', busy || !data.periods.length);
    disable('#library-workspace-select', busy || !session?.workspaces?.length);
  }
  async function api(route, body) {
    const options = {credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}};
    if (body !== undefined) Object.assign(options,{method:'POST',body:JSON.stringify(body),headers:{...options.headers,'Content-Type':'application/json','X-CSRF-Token':session?.csrf || ''}});
    const response = await fetch('/api/customer/' + route, options), value = await response.json();
    if (!response.ok) {
      if (response.status === 401) location.replace('/workspace/login');
      if (['workspace_changed','client_changed','workspace_access'].includes(value.code)) location.replace('/workspace');
      throw new Error(value.error || 'Chưa thể đọc trạng thái. Vui lòng thử lại.');
    }
    return value;
  }
  async function operation(action) {
    if (busy) return;
    busy = true; controls(); feedback('');
    try { await action(); } catch (error) { feedback(error.message); } finally { busy = false; controls(); }
  }
  function postLink(post) {
    const match = /^([0-9]{1,40})_([0-9]{1,40})$/.exec(post.post_id);
    if (!match || match[1] !== data.asset?.external_id) return null;
    return 'https://www.facebook.com/permalink.php?' + new URLSearchParams({story_fbid:match[2], id:match[1]}).toString();
  }
  function anchor(post, label, className) {
    const href = postLink(post);
    if (!href) return null;
    const link = node('a',label,className);
    link.href = href; link.target = '_blank'; link.rel = 'noopener noreferrer';
    return link;
  }
  function renderPosts(printing = false) {
    if (!$('#fc-post-rows')) return;
    const q = printing ? '' : fold($('#fc-post-search').value.trim()), filter = printing ? 'all' : selectedFormat;
    const sort = printing ? 'newest' : $('#fc-post-sort')?.value || 'newest';
    const metric = sort === 'views' ? 'post_media_view_lifetime' : sort === 'reactions' ? 'reactions_lifetime' : null;
    const rows = data.posts.filter((post) => (filter === 'all' || (post.format || 'unknown') === filter) && fold((post.message || post.title || '') + ' ' + post.post_id).includes(q));
    rows.sort((a,b) => {
      if (metric) { const order = (number(b[metric]) ? b[metric] : -1) - (number(a[metric]) ? a[metric] : -1); if (order) return order; }
      return b.date.localeCompare(a.date) || a.post_id.localeCompare(b.post_id);
    });
    const pages = Math.max(1,Math.ceil(rows.length / pageSize)); page = Math.max(1,Math.min(page,pages));
    const shown = printing ? rows : rows.slice((page - 1) * pageSize,page * pageSize);
    $('#fc-post-rows').replaceChildren(...shown.map((post) => {
      const row = document.createElement('tr'), content = document.createElement('td');
      row.dataset.postId = post.post_id;
      const kind = formats[post.format] || formats.unknown;
      const badge = node('span','', 'fc-format'); const icon = node('span',kind[1],'material-symbols-outlined'); icon.setAttribute('aria-hidden','true');
      badge.append(icon,document.createTextNode(kind[0])); content.append(badge);
      const message = post.message || post.title || 'Bài đăng không có nội dung chữ';
      const heading = message.split('\n').find((line) => line.trim()) || message;
      content.append(anchor(post,heading.slice(0,160),'fc-post-title') || node('span',heading.slice(0,160),'fc-post-title'));
      if (message.length > heading.length) {
        const more = document.createElement('details'); more.className = 'fc-post-expand';
        more.append(node('summary','Đọc nội dung'),node('p',message,'fc-post-message')); content.append(more);
      }
      row.append(content,node('td',date(post.date),'fc-post-date'));
      for (const key of ['post_media_view_lifetime','reactions_lifetime','comments_lifetime','shares_lifetime']) {
        const cell = node('td',format(post[key]),number(post[key]) ? 'fc-number' : 'fc-cell-missing');
        if (!number(post[key])) cell.title = 'Meta chưa trả số đếm này cho bài viết; đây không phải số 0.';
        row.append(cell);
      }
      const action = document.createElement('td'); action.className = 'fc-post-action';
      const link = anchor(post,'Xem bài trên Facebook','fc-post-link');
      if (link) { const icon = node('span','arrow_outward','material-symbols-outlined'); icon.setAttribute('aria-hidden','true'); link.append(icon); link.setAttribute('aria-label','Xem bài trên Facebook: ' + heading.slice(0,100)); action.append(link); }
      else action.append(node('span','Chưa có liên kết','fc-cell-missing'));
      row.append(action); return row;
    }));
    $('#fc-post-empty').hidden = rows.length > 0;
    $('#fc-post-count').textContent = rows.length ? ((printing ? 1 : (page - 1) * pageSize + 1) + '–' + (printing ? rows.length : Math.min(page * pageSize,rows.length)) + ' trong ' + rows.length + ' bài') : '0 bài phù hợp';
    disable('#fc-prev',page <= 1); disable('#fc-next',page >= pages);
  }
  function activateChart(button) {
    document.querySelectorAll('[data-fc-chart]').forEach((tab) => { const active = tab === button; tab.setAttribute('aria-selected',String(active)); tab.tabIndex = active ? 0 : -1; });
    document.querySelectorAll('[data-fc-chart-panel]').forEach((panel) => { panel.hidden = panel.dataset.fcChartPanel !== button.dataset.fcChart; });
  }
  const chartTabs = [...document.querySelectorAll('[data-fc-chart]')];
  chartTabs.forEach((button,index) => {
    button.addEventListener('click',() => activateChart(button));
    button.addEventListener('keydown',(event) => {
      if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
      event.preventDefault(); const next = event.key === 'Home' ? 0 : event.key === 'End' ? chartTabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + chartTabs.length) % chartTabs.length;
      chartTabs[next].click(); chartTabs[next].focus();
    });
  });
  document.querySelectorAll('.fc-chart-point').forEach((point) => {
    const read = () => { const output = point.closest('.fc-chart-panel').querySelector('.fc-chart-readout'); output.textContent = (point.dataset.chartDate.includes('T') ? date(point.dataset.chartDate,true) + ' UTC · mốc Meta' : date(point.dataset.chartDate) + ' UTC') + '  ·  ' + point.dataset.chartValue; };
    point.addEventListener('pointerenter',read); point.addEventListener('focus',read);
  });
  async function checkStatus() {
    const next = await api('workspaces/' + workspaceId + '/channels/facebook-content');
    if (next.scope?.workspace_id !== workspaceId || next.scope?.client_id !== clientId) { location.replace(path); return; }
    if (next.snapshot?.id !== data.snapshot?.id || next.latest_sync?.status !== data.latest_sync?.status || next.connection?.status !== data.connection?.status) location.reload();
    else if (['queued','running'].includes(next.latest_sync?.status)) schedule();
  }
  function schedule() { clearTimeout(timer); if (!document.hidden && !report) timer = setTimeout(() => operation(checkStatus),5000); }
  $('#fc-refresh')?.addEventListener('click',() => location.reload());
  $('#fc-snapshot')?.addEventListener('change',() => { const value = $('#fc-snapshot').value; if (data.periods.some((row) => row.id === value)) location.assign(path + '?snapshot=' + encodeURIComponent(value)); });
  $('#fc-client')?.addEventListener('change',() => operation(async () => {
    const value = $('#fc-client').value; if (!details.clients.some((client) => client.id === value)) return;
    await api('workspaces/' + workspaceId + '/clients/' + value + '/select',{}); location.assign(path);
  }));
  $('#library-logout')?.addEventListener('click',() => operation(async () => { await api('auth/logout',{}); location.assign('/workspace/login'); }));
  $('#library-workspace-select')?.addEventListener('change',() => operation(async () => {
    const id = $('#library-workspace-select').value; if (!session?.workspaces.some((workspace) => workspace.id === id)) return;
    await api('workspaces/' + id + '/select',{}); location.assign(path);
  }));
  $('#fc-post-search')?.addEventListener('input',() => { page = 1; renderPosts(); });
  $('#fc-post-sort')?.addEventListener('change',() => { page = 1; renderPosts(); });
  document.querySelectorAll('[data-fc-format]').forEach((button) => button.addEventListener('click',() => {
    selectedFormat = button.dataset.fcFormat; page = 1;
    document.querySelectorAll('[data-fc-format]').forEach((item) => item.setAttribute('aria-pressed',String(item === button))); renderPosts();
  }));
  $('#fc-prev')?.addEventListener('click',() => { page -= 1; renderPosts(); });
  $('#fc-next')?.addEventListener('click',() => { page += 1; renderPosts(); });
  $('#fc-print')?.addEventListener('click',() => window.print());
  window.addEventListener('beforeprint',() => renderPosts(true));
  window.addEventListener('afterprint',() => renderPosts());
  renderPosts(); controls(); operation(async () => {
    session = await api('session');
    if (!session.user) { location.replace('/workspace/login'); return; }
    if (session.workspace?.id !== workspaceId) { location.replace('/workspace'); return; }
    if (['queued','running'].includes(data.latest_sync?.status)) schedule();
  });
  document.querySelectorAll('.fc-main time[datetime]').forEach((item) => { if (item.dateTime.includes('T')) item.textContent = date(item.dateTime,true) + ' UTC'; });
  document.addEventListener('visibilitychange',() => { clearTimeout(timer); if (!report && !document.hidden && ['queued','running'].includes(data.latest_sync?.status)) operation(checkStatus); });
  window.addEventListener('pagehide',() => clearTimeout(timer));
  window.addEventListener('pageshow',(event) => { if (event.persisted) location.reload(); });
})();
