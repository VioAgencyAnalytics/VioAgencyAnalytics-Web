/* Shared authenticated controller for Members and Settings. Admin enforces policy. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const page = document.body.dataset.customerPage;
  let data = JSON.parse($('#workspace-page-data').textContent), session, busy = false, ready = false, dirty = false;
  const workspaceId = data.workspace.id, base = `workspaces/${workspaceId}`;
  let renderer = () => {}, pageControls = () => {}, guide = () => {}, resolver;
  const roles = {owner: 'Chủ sở hữu', admin: 'Quản trị viên', member: 'Thành viên', viewer: 'Người xem'};
  const node = (tag, text, className) => { const item = document.createElement(tag); item.textContent = text; if (className) item.className = className; return item; };
  const fold = (value) => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[đĐ]/g, 'd').toLowerCase();
  function date(value, full = false) {
    if (typeof value !== 'string' || !value) return '—';
    const parsed = new Date(value); if (Number.isNaN(parsed.getTime())) return '—';
    return new Intl.DateTimeFormat('vi-VN', {dateStyle: 'short', ...(full ? {timeStyle: 'short'} : {}), timeZone: data.workspace.timezone || 'Asia/Ho_Chi_Minh'}).format(parsed);
  }
  function notify(message, kind = 'info') { const status = $('#workspace-page-status'); status.textContent = message; status.hidden = !message; status.dataset.kind = kind; }
  function controls() {
    $('#workspace-page-select').disabled = busy || !ready;
    $('#workspace-page-refresh').disabled = busy;
    $('#workspace-page-logout').disabled = busy || !session?.user;
    document.querySelectorAll('[data-close-dialog]').forEach((button) => { button.disabled = busy; });
    pageControls();
  }
  function info(title, message) { $('#workspace-info-title').textContent = title; $('#workspace-info-description').textContent = message; $('#workspace-info').showModal(); }
  function confirm(title, message, accept = 'Xác nhận') {
    if (resolver) return Promise.resolve(false);
    $('#workspace-confirm-title').textContent = title; $('#workspace-confirm-description').textContent = message;
    $('#workspace-confirm-accept').textContent = accept; $('#workspace-confirm').showModal();
    return new Promise((resolve) => { resolver = resolve; });
  }
  function finishConfirm(accepted) { const resolve = resolver; resolver = null; $('#workspace-confirm').close(); resolve?.(accepted); }
  async function api(path, payload) {
    const options = {credentials: 'same-origin', cache: 'no-store', headers: {Accept: 'application/json'}};
    if (payload !== undefined) { options.method = 'POST'; options.headers['Content-Type'] = 'application/json'; options.headers['X-CSRF-Token'] = session?.csrf || ''; options.body = JSON.stringify(payload); }
    const reply = await fetch('/api/customer/' + path, options), value = await reply.json();
    if (!reply.ok) {
      if (reply.status === 401) location.replace('/workspace/login');
      if (['workspace_access', 'workspace_changed'].includes(value.code)) { dirty = false; location.replace('/workspace'); }
      const error = new Error(value.error || 'Chưa thể hoàn tất yêu cầu. Vui lòng thử lại.'); error.code = value.code; throw error;
    }
    return value;
  }
  function adopt(value) {
    if (value.workspace?.id !== workspaceId) throw new Error('Phạm vi Workspace đã thay đổi. Vui lòng tải lại.');
    data = value; ready = true;
    const name = data.workspace.name;
    const option = [...$('#workspace-page-select').options].find((item) => item.value === workspaceId); if (option) option.textContent = name;
    $('.wh-workspace').title = name; $('.wh-workspace span:last-child').textContent = name;
    $('#workspace-search-dialog .wh-search-heading p').textContent = 'Trong Workspace ' + name;
    renderer(); controls();
  }
  async function reload() {
    session = await api('session');
    if (!session.user) { dirty = false; location.replace('/workspace/login'); return; }
    if (session.workspace?.id !== workspaceId) { dirty = false; location.replace('/workspace'); return; }
    adopt(await api(base + '/' + page));
  }
  async function run(action, onError) {
    if (busy) return false;
    busy = true; controls(); notify('');
    try { await action(); return true; }
    catch (error) { notify(error.message || 'Chưa thể hoàn tất. Vui lòng thử lại.', 'error'); if (onError) onError(error); return false; }
    finally { busy = false; controls(); }
  }
  async function leave() { return !dirty || await confirm('Bỏ thay đổi chưa lưu?', 'Những chỉnh sửa trên biểu mẫu chưa được lưu. Bạn muốn rời trang và bỏ các thay đổi này?', 'Bỏ thay đổi'); }
  async function copy(value, input) {
    try { await navigator.clipboard.writeText(value); notify('Đã sao chép.', 'success'); }
    catch { input?.focus(); input?.select(); notify('Chọn nội dung và bấm Ctrl+C để sao chép.'); }
  }
  $('#workspace-confirm-accept').addEventListener('click', () => finishConfirm(true));
  $('#workspace-confirm-cancel').addEventListener('click', () => finishConfirm(false));
  $('#workspace-confirm').addEventListener('cancel', (event) => { event.preventDefault(); finishConfirm(false); });
  $('#workspace-confirm').addEventListener('close', () => { if (resolver) { const resolve = resolver; resolver = null; resolve(false); } });
  document.querySelectorAll('[data-close-dialog]').forEach((button) => button.addEventListener('click', () => { if (!busy) button.closest('dialog').close(); }));
  document.querySelectorAll('dialog.wa-dialog').forEach((dialog) => dialog.addEventListener('cancel', (event) => { if (busy) event.preventDefault(); }));
  $('#workspace-page-select').addEventListener('change', async () => {
    const id = $('#workspace-page-select').value;
    if (id === workspaceId || !session?.workspaces.some((item) => item.id === id)) return;
    if (!await leave()) { $('#workspace-page-select').value = workspaceId; return; }
    await run(async () => { await api(`workspaces/${id}/select`, {}); dirty = false; ready = false; renderer(); location.assign('/workspace/' + page); }, () => { $('#workspace-page-select').value = workspaceId; });
  });
  $('#workspace-page-refresh').addEventListener('click', async () => { if (await leave()) await run(async () => { await reload(); dirty = false; notify('Đã tải dữ liệu mới nhất.'); }, () => { ready = false; renderer(); }); });
  $('#workspace-page-logout').addEventListener('click', async () => { if (await leave()) await run(async () => { await api('auth/logout', {}); dirty = false; location.assign('/workspace/login'); }); });
  document.addEventListener('click', async (event) => {
    const link = event.target.closest('a[href]'); if (!link || !dirty || event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.button !== 0 || link.target || link.hasAttribute('download')) return;
    const target = new URL(link.href); if (target.origin !== location.origin || (target.pathname === location.pathname && target.search === location.search)) return;
    event.preventDefault(); if (await leave()) { dirty = false; location.assign(target.href); }
  });
  window.addEventListener('beforeunload', (event) => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
  window.addEventListener('pageshow', (event) => { if (event.persisted) location.reload(); });
  $('#workspace-page-guide').addEventListener('click', () => guide());
  document.querySelectorAll('[data-future]').forEach((button) => button.addEventListener('click', () => info(button.dataset.future, 'Khu vực này sẽ được hoàn thiện ở các bước tiếp theo. Hiện bạn có thể quản lý đội ngũ, cài đặt và chuẩn bị nguồn dữ liệu cho Workspace.')));
  document.querySelectorAll('[data-sidebar-platform]').forEach((button) => button.addEventListener('click', () => info(button.textContent.trim(), 'Phân tích chuyên sâu sẽ được triển khai sau. Bạn có thể xem danh mục nguồn dữ liệu tại trang Kết nối nền tảng.')));
  window.VioWorkspace = Object.freeze({get data() { return data; }, get session() { return session; }, get busy() { return busy; }, get ready() { return ready; }, get dirty() { return dirty; }, base, roles, node, fold, date, api, adopt, reload, run, notify, info, confirm, copy,
    setDirty(value) { dirty = Boolean(value); controls(); }, controls,
    mount(render, updateControls, help) { renderer = render; pageControls = updateControls; guide = help; renderer(); controls(); run(reload, () => { ready = false; renderer(); }); }});
})();
