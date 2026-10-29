/* Tenant-scoped customer management. Admin owns validation and authorization. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  let details = JSON.parse($('#overview-data').textContent);
  const workspaceId = details.workspace.id;
  const base = `workspaces/${workspaceId}`;
  let session, ready = false, busy = false, editing = null, requestKey = '', confirmation = null;
  const editor = $('#client-editor');
  const confirm = $('#client-confirm');
  function message(selector, text) { const box = $(selector); box.textContent = text; box.hidden = !text; }
  async function api(path, body) {
    const options = {credentials: 'same-origin', cache: 'no-store', headers: {Accept: 'application/json'}};
    if (body !== undefined) {
      Object.assign(options, {method: 'POST', body: JSON.stringify(body)});
      Object.assign(options.headers, {'Content-Type': 'application/json', 'X-CSRF-Token': session?.csrf || ''});
    }
    const response = await fetch('/api/customer/' + path, options);
    const payload = await response.json();
    if (!response.ok) {
      if (response.status === 401) location.replace('/workspace/login');
      const error = new Error(payload.error || 'Chưa hoàn tất yêu cầu. Vui lòng thử lại.');
      error.code = payload.code;
      throw error;
    }
    return payload;
  }
  function controls() {
    document.querySelectorAll('[data-client-control]').forEach((item) => {
      item.disabled = busy || !ready || item.dataset.locked === 'true';
    });
    $('#client-fields').disabled = busy;
    editor.querySelectorAll('button').forEach((item) => { item.disabled = busy; });
    confirm.querySelectorAll('button').forEach((item) => { item.disabled = busy; });
  }
  async function run(task) {
    if (busy || !ready) return;
    busy = true; controls();
    message('#client-status', ''); message('#client-error', ''); message('#client-confirm-error', '');
    try { await task(); }
    catch (error) {
      const target = editor.open ? '#client-error' : confirm.open ? '#client-confirm-error' : '#client-status';
      message(target, error.message || 'Mất kết nối. Vui lòng thử lại.');
      $('#client-reload-latest').hidden = !(editor.open && error.code === 'client_conflict');
      if (error.code === 'workspace_changed') location.replace('/workspace');
    } finally { busy = false; controls(); }
  }
  function element(tag, text, className) {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = text;
    if (className) item.className = className;
    return item;
  }
  function button(text, task, secondary = true) {
    const item = element('button', text, 'ov-button' + (secondary ? ' ov-secondary' : ''));
    item.type = 'button'; item.dataset.clientControl = '';
    item.addEventListener('click', task);
    return item;
  }
  function openEditor(client = null) {
    if (!ready || busy || !details.permissions.manage_clients) return;
    editing = client; requestKey = crypto.randomUUID().replaceAll('-', '');
    $('#client-form').reset(); $('#client-name').value = client?.name || ''; $('#client-website').value = client?.website || '';
    $('#client-editor-title').textContent = client ? 'Chỉnh sửa khách hàng / thương hiệu' : 'Thêm khách hàng / thương hiệu';
    $('#client-editor-note').textContent = client ? 'Thay đổi tên và website không sửa dữ liệu báo cáo đã phát hành.' : 'Sau khi tạo, khách hàng này sẽ được chọn để làm việc.';
    $('#client-save').textContent = client ? 'Lưu thay đổi' : 'Tạo và chọn';
    message('#client-error', ''); $('#client-reload-latest').hidden = true;
    editor.showModal(); $('#client-name').focus();
  }
  function ask(client, action) {
    if (busy || !ready) return;
    confirmation = {client, action};
    $('#client-confirm-title').textContent = action === 'archive' ? 'Lưu trữ khách hàng?' : 'Khôi phục khách hàng?';
    $('#client-confirm-description').textContent = action === 'archive'
      ? `Lưu trữ “${client.name}” sẽ bỏ lựa chọn đang làm việc của các phiên trong Workspace. Thông tin và báo cáo đã lưu vẫn được giữ.`
      : `Khôi phục “${client.name}” vào danh sách đang hoạt động. Bạn có thể chọn lại khách hàng này sau đó.`;
    message('#client-confirm-error', ''); confirm.showModal();
  }
  function renderClients() {
    const archived = $('#client-filter').value === 'archived';
    const all = archived ? details.archived_clients : details.clients;
    const query = $('#client-search').value.trim().toLocaleLowerCase('vi');
    const matches = all.filter((client) => `${client.name} ${client.website}`.toLocaleLowerCase('vi').includes(query));
    const rows = matches.map((client) => {
      const row = element('li'); row.dataset.clientId = client.id;
      const identity = element('div', undefined, 'ov-client-identity');
      identity.append(element('span', client.name.slice(0, 1), 'ov-client-initial'));
      const info = element('div'); info.append(element('strong', client.name));
      if (client.website) {
        const link = element('a', client.website); link.href = client.website;
        link.target = '_blank'; link.rel = 'noopener noreferrer'; info.append(link);
      }
      info.append(element('small', archived ? 'Đã lưu trữ' : 'Chưa kết nối nguồn dữ liệu'));
      identity.append(info); row.append(identity);
      const actions = element('div', undefined, 'ov-client-actions');
      if (!archived) {
        const selected = details.selected_client?.id === client.id;
        const select = button(selected ? 'Đang chọn' : 'Chọn làm việc', () => run(async () => {
          apply(await api(`${base}/clients/${client.id}/select`, {})); message('#client-status', `Đã chọn ${client.name}.`);
        }));
        select.dataset.locked = String(selected); select.setAttribute('aria-pressed', String(selected)); actions.append(select);
      }
      if (details.permissions.manage_clients) {
        if (!archived) actions.append(button('Chỉnh sửa', () => openEditor(client)));
        actions.append(button(archived ? 'Khôi phục' : 'Lưu trữ', () => ask(client, archived ? 'restore' : 'archive')));
      }
      row.append(actions); return row;
    });
    if (!rows.length) rows.push(element('li', query ? 'Không có khách hàng phù hợp.' : archived ? 'Chưa có khách hàng đã lưu trữ.' : 'Chưa có khách hàng. Owner/Admin có thể thêm khách hàng đầu tiên.'));
    $('#client-list').replaceChildren(...rows);
    $('#client-result-count').textContent = `${matches.length} / ${all.length} khách hàng ${archived ? 'đã lưu trữ' : 'đang hoạt động'}`;
    controls();
  }
  function renderSetup() {
    $('#setup-summary').textContent = `${details.setup.completed}/${details.setup.total} bước đã hoàn thành`;
    $('#setup-progress').max = details.setup.total; $('#setup-progress').value = details.setup.completed;
    $('#setup-checklist').replaceChildren(...details.setup.steps.map((step) => {
      const item = element('li'); item.dataset.setupStep = step.key; item.dataset.state = step.state;
      item.append(element('span', step.state === 'complete' ? '✓' : '○', 'ov-check-state'));
      const label = element('div'); label.append(element('strong', step.title), element('small', step.state === 'complete' ? 'Đã hoàn thành' : step.state === 'planned' ? 'Cấp quyền và đồng bộ đang được triển khai' : 'Cần thực hiện'));
      item.append(label);
      if (step.state !== 'complete') {
        if (step.action === 'add_client' && details.permissions.manage_clients) item.append(button('Thêm khách hàng', () => openEditor()));
        if (step.action === 'choose_client' && details.clients.length) item.append(button('Chọn khách hàng', () => { $('#client-filter').value = 'active'; $('#client-search').value = ''; renderClients(); $('#client-card').scrollIntoView({block: 'center'}); $('#client-card').focus(); }));
        if (step.action === 'integrations') item.append(button('Khám phá nền tảng', () => location.assign('/workspace/integrations')));
      }
      return item;
    }));
    controls();
  }
  function apply(next) {
    if (next.workspace.id !== workspaceId) { location.replace('/workspace'); return; }
    details = next;
    $('#active-client-count').textContent = details.clients.length; $('#archived-client-count').textContent = details.archived_clients.length;
    $('#selected-client-summary').textContent = details.selected_client ? `Đang làm việc: ${details.selected_client.name}` : 'Chưa chọn khách hàng đang làm việc.';
    $('#add-client').hidden = !details.permissions.manage_clients;
    $('#client-permission-note').textContent = details.permissions.manage_clients
      ? 'Owner/Admin được thêm, sửa, lưu trữ và khôi phục. Lưu trữ giữ nguyên dữ liệu.'
      : 'Bạn có quyền xem và chọn khách hàng. Liên hệ Owner/Admin để thay đổi danh sách.';
    renderClients(); renderSetup();
    document.dispatchEvent(new CustomEvent('customer:workspace-detail', {detail: details}));
  }
  $('#add-client').addEventListener('click', () => openEditor());
  $('#client-search').addEventListener('input', renderClients);
  $('#client-filter').addEventListener('change', renderClients);
  $('#reload-clients').addEventListener('click', () => run(async () => { apply(await api(base)); message('#client-status', 'Đã cập nhật danh sách.'); }));
  $('#client-form').addEventListener('submit', (event) => {
    event.preventDefault(); if (!$('#client-form').reportValidity()) return;
    run(async () => {
      const data = {name: $('#client-name').value.trim(), website: $('#client-website').value.trim()};
      if (editing) data.version = editing.version; else data.request_key = requestKey;
      apply(await api(editing ? `${base}/clients/${editing.id}/update` : `${base}/clients`, data));
      editor.close(); message('#client-status', editing ? 'Đã lưu thay đổi.' : 'Đã tạo và chọn khách hàng.');
    });
  });
  $('#client-confirm-submit').addEventListener('click', () => run(async () => {
    const {client, action} = confirmation;
    apply(await api(`${base}/clients/${client.id}/${action}`, {version: client.version}));
    confirm.close(); message('#client-status', action === 'archive' ? 'Đã lưu trữ và giữ nguyên dữ liệu.' : 'Đã khôi phục khách hàng.');
  }));
  $('#client-reload-latest').addEventListener('click', () => run(async () => {
    const id = editing.id; apply(await api(base));
    const current = details.clients.find((client) => client.id === id); editor.close();
    if (current) { busy = false; openEditor(current); } else message('#client-status', 'Khách hàng không còn hoạt động. Danh sách đã cập nhật.');
  }));
  document.querySelectorAll('[data-close-client]').forEach((item) => item.addEventListener('click', () => { if (!busy) item.closest('dialog').close(); }));
  for (const modal of [editor, confirm]) modal.addEventListener('cancel', (event) => { if (busy) event.preventDefault(); });
  $('#overview-workspace-select').addEventListener('change', (event) => run(async () => {
    await api(`workspaces/${event.target.value}/select`, {}); location.assign('/workspace');
  }));
  document.addEventListener('customer:select-client', (event) => {
    const id = event.detail?.id;
    if (!details.clients.some((client) => client.id === id)) return;
    run(async () => {
      try { apply(await api(`${base}/clients/${id}/select`, {})); }
      catch (error) {
        document.dispatchEvent(new CustomEvent('customer:workspace-detail', {detail: details}));
        document.dispatchEvent(new CustomEvent('customer:client-selection-error', {detail: {message: error.message}}));
        throw error;
      }
    });
  });
  async function init() {
    try {
      session = await api('session');
      if (!session.user) { location.replace('/workspace/login'); return; }
      if (session.workspace?.id !== workspaceId) { location.replace('/workspace'); return; }
      const next = await api(base); ready = true; apply(next);
    } catch (error) { message('#client-status', error.message || 'Chưa tải được khách hàng. Tải lại trang để thử lại.'); }
  }
  $('#client-search').disabled = true; $('#client-filter').disabled = true;
  init().finally(() => { $('#client-search').disabled = !ready; $('#client-filter').disabled = !ready; controls(); });
})();
