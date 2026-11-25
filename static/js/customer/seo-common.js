(function () {
  'use strict';
  const node = document.querySelector('#seo-context-data');
  if (!node) return;
  const scope = JSON.parse(node.textContent);
  let session;
  function element(tag, text = '', className = '') {
    const value = document.createElement(tag); value.textContent = text;
    if (className) value.className = className;
    return value;
  }
  function message(text = '', error = false, target = document.querySelector('#seo-message')) {
    if (!target) return;
    target.textContent = text; target.hidden = !text; target.dataset.error = String(error);
  }
  function date(value) { return /^\d{4}-\d{2}-\d{2}$/.test(value || '') ? value.slice(8) + '/' + value.slice(5, 7) + '/' + value.slice(0, 4) : '—'; }
  function timestamp(value) {
    const stamp = new Date(value);
    return Number.isFinite(stamp.getTime()) ? new Intl.DateTimeFormat('vi-VN', {
      timeZone:scope.timezone || 'Asia/Ho_Chi_Minh', hour:'2-digit', minute:'2-digit', day:'2-digit',
      month:'2-digit', year:'numeric', timeZoneName:'short'
    }).format(stamp) : '—';
  }
  function monthRange(month) {
    const match = /^(\d{4})-(\d{2})$/.exec(month || '');
    if (!match || +match[1] < 1 || +match[1] > 9998 || +match[2] < 1 || +match[2] > 12) throw new Error('Chọn tháng hợp lệ.');
    const lastDay = new Date(month + '-01T00:00:00Z');
    lastDay.setUTCMonth(lastDay.getUTCMonth() + 1); lastDay.setUTCDate(0);
    const last = lastDay.getUTCDate();
    return {start: month + '-01', end: month + '-' + last};
  }
  function today() { return new Intl.DateTimeFormat('en-CA', {timeZone: scope.timezone || 'Asia/Ho_Chi_Minh', year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date()); }
  function validPeriod(start, end) {
    const a = Date.parse(start + 'T00:00:00Z'), b = Date.parse(end + 'T00:00:00Z');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(start) || !/^\d{4}-\d{2}-\d{2}$/.test(end) || !Number.isFinite(a) || !Number.isFinite(b) || new Date(a).toISOString().slice(0, 10) !== start || new Date(b).toISOString().slice(0, 10) !== end || b < a || (b - a) / 86400000 > 89) throw new Error('Chọn khoảng ngày hợp lệ, tối đa 90 ngày.');
    return {start, end};
  }
  function comparisonWindow(period, mode, custom, closed = today()) {
    validPeriod(period.start, period.end);
    if (mode === 'none') return null;
    if (mode === 'custom') return validPeriod(custom.start, custom.end);
    if (!['previous', 'previous_month'].includes(mode)) throw new Error('Chọn kiểu đối chiếu hợp lệ.');
    const end = period.end < closed ? period.end : closed;
    if (period.start > end) return null;
    const first = new Date(period.start + 'T00:00:00Z'), last = new Date(end + 'T00:00:00Z');
    const iso = value => value.toISOString().slice(0, 10);
    if (mode === 'previous') {
      return validPeriod(iso(new Date(first.getTime() - (last - first + 86400000))), iso(new Date(first - 86400000)));
    }
    function shift(value) {
      const year = Number(value.slice(0, 4)), month = Number(value.slice(5, 7));
      const previous = month === 1 ? String(year - 1).padStart(4, '0') + '-12' : value.slice(0, 4) + '-' + String(month - 1).padStart(2, '0');
      const range = monthRange(previous);
      return previous + '-' + String(Math.min(Number(value.slice(8)), Number(range.end.slice(8)))).padStart(2, '0');
    }
    const start = shift(period.start);
    const fullMonth = period.start.endsWith('-01') && period.start.slice(0, 7) === period.end.slice(0, 7) && monthRange(period.end.slice(0, 7)).end === period.end && end === period.end;
    return validPeriod(start, fullMonth ? monthRange(start.slice(0, 7)).end : shift(end));
  }
  function comparisonControls(prefix, getPeriod) {
    const select = document.querySelector('#' + prefix + '-comparison');
    const first = document.querySelector('#' + prefix + '-comparison-start');
    const last = document.querySelector('#' + prefix + '-comparison-end');
    function update() {
      const custom = select.value === 'custom';
      for (const input of [first, last]) { input.closest('label').hidden = !custom; input.disabled = !custom; input.required = custom; }
      if (custom && !first.value && !last.value) {
        const previous = comparisonWindow(getPeriod(), 'previous');
        if (previous) { first.value = previous.start; last.value = previous.end; }
      }
    }
    function value() {
      if (!['none', 'previous', 'previous_month', 'custom'].includes(select.value)) throw new Error('Chọn kiểu đối chiếu hợp lệ.');
      if (select.value !== 'custom') return {comparison: select.value};
      validPeriod(first.value, last.value);
      if (last.value > today()) throw new Error('Kỳ đối chiếu chưa kết thúc.');
      return {comparison: 'custom', comparison_start: first.value, comparison_end: last.value};
    }
    const query = new URLSearchParams(location.search), mode = query.get('comparison');
    if (['none', 'previous', 'previous_month', 'custom'].includes(mode)) select.value = mode;
    first.value = query.get('comparison_start') || ''; last.value = query.get('comparison_end') || '';
    select.addEventListener('change', update);
    return {update, value};
  }
  function link(url, label = 'Mở liên kết ↗') {
    try { const parsed = new URL(url); if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) throw new Error(); const a = element('a', label); a.href = parsed.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a; }
    catch (_) { return element('span', '—'); }
  }
  async function api(path, data, upload) {
    const headers = {Accept: 'application/json'};
    const options = {credentials: 'same-origin', cache: 'no-store', headers, signal: AbortSignal.timeout(50000)};
    if (data !== undefined) { options.method = 'POST'; headers['X-CSRF-Token'] = session?.csrf || ''; headers['Content-Type'] = upload ? 'application/octet-stream' : 'application/json'; options.body = upload ? data : JSON.stringify(data); }
    const response = await fetch('/api/customer/' + path, options);
    const payload = await response.json();
    if (!response.ok) {
      if (response.status === 401) location.assign('/workspace/login');
      const error = new Error(payload.error || 'Chưa thể hoàn tất thao tác.');
      error.code = payload.code; error.status = response.status; throw error;
    }
    if (payload.scope && (payload.scope.workspace_id !== scope.workspace_id || payload.scope.client_id !== scope.client_id)) throw new Error('Khách hàng đã thay đổi. Tải lại trang để tiếp tục.');
    return payload;
  }
  async function ready() {
    session = await api('session');
    if (!session.user) { location.assign('/workspace/login'); throw new Error('Vui lòng đăng nhập.'); }
    if (session.workspace?.id !== scope.workspace_id) { location.assign('/workspace'); throw new Error('Workspace đã thay đổi.'); }
    const select = document.querySelector('#library-workspace-select');
    if (select) { select.disabled = false; select.addEventListener('change', async () => { select.disabled = true; try { await api('workspaces/' + select.value + '/select', {}); location.assign(location.pathname); } catch (error) { message(error.message, true); select.disabled = false; } }); }
    const logout = document.querySelector('#library-logout');
    if (logout) {
      logout.disabled = false;
      logout.addEventListener('click', () => busy(logout, async () => {
        await api('auth/logout', {});
        location.assign('/workspace/login');
      }));
    }
    document.querySelectorAll('[data-seo-close]').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
    const sidebar = document.querySelector('#workspace-sidebar'), toggle = document.querySelector('#workspace-nav-toggle'), shell = document.querySelector('.seo-page');
    if (sidebar && toggle && shell) {
      const mobile = window.matchMedia('(max-width:700px)'), backdrop = element('button');
      backdrop.type = 'button'; backdrop.className = 'seo-nav-backdrop'; backdrop.setAttribute('aria-label', 'Đóng điều hướng'); shell.append(backdrop);
      function menu(open) { document.body.dataset.seoNavOpen = String(mobile.matches && open); sidebar.inert = mobile.matches && !open; if (mobile.matches) { toggle.setAttribute('aria-expanded', String(open)); toggle.setAttribute('aria-label', open ? 'Đóng điều hướng' : 'Mở điều hướng'); } }
      menu(false); toggle.addEventListener('click', () => { if (mobile.matches) menu(document.body.dataset.seoNavOpen !== 'true'); }); backdrop.addEventListener('click', () => menu(false));
      document.addEventListener('keydown', event => { if (event.key === 'Escape') menu(false); }); mobile.addEventListener('change', () => menu(false));
    }
    return session;
  }
  async function busy(button, action, target) {
    if (button?.disabled) return;
    if (button) button.disabled = true;
    try { return await action(); }
    catch (error) { message(error.name === 'TimeoutError' ? 'Dịch vụ phản hồi chậm. Tải lại trạng thái trước khi thử tiếp.' : error.message, true, target); }
    finally { if (button) button.disabled = false; }
  }
  window.VioSEO = {scope, element, message, date, timestamp, monthRange, today, validPeriod, comparisonWindow, comparisonControls, link, api, ready, busy, base: 'workspaces/' + scope.workspace_id};
}());
