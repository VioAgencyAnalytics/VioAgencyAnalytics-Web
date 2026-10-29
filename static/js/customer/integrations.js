/* Integration UI consumes safe customer DTOs; no provider credentials or API calls. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const initial = JSON.parse($('#integrations-data').textContent);
  const workspaceId = initial.workspace.id;
  const base = `workspaces/${workspaceId}`;
  const params = new URLSearchParams(location.search);
  let current = initial, session, busy = false, ready = false, loadFailed = false, changingScope = false, historyTimer;
  let category = initial.categories.some((item) => item.id === params.get('category')) ? params.get('category') : 'all';
  const fold = (value) => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[đĐ]/g, 'd').toLowerCase();
  const stateLabels = {connected: 'Đã kết nối', syncing: 'Đang đồng bộ', expired: 'Cần cấp quyền lại', error: 'Cần kiểm tra', disconnected: 'Đã ngắt kết nối', pending: 'Chờ hoàn tất'};
  const attentionStates = ['expired', 'error', 'disconnected'];
  const colors = new Set(['blue', 'amber', 'teal', 'purple', 'red', 'dark']);
  function node(tag, text, className) {
    const item = document.createElement(tag); item.textContent = text;
    if (className) item.className = className;
    return item;
  }
  function icon(name, className = '') {
    const item = node('span', name, 'material-symbols-outlined ' + className);
    item.setAttribute('aria-hidden', 'true'); return item;
  }
  function status(message, kind = 'info') {
    $('#integrations-status').textContent = message; $('#integrations-status').hidden = !message;
    $('#integrations-status').dataset.kind = kind;
  }
  function controls() {
    $('#integrations-refresh').disabled = busy;
    $('#integrations-logout').disabled = busy || !session?.user;
    $('#integration-client').disabled = busy || !ready || !current.clients.length;
    $('#integration-workspace-select').disabled = busy || !ready;
    document.querySelectorAll('[data-platform-details], [data-sidebar-platform]').forEach((button) => { button.disabled = changingScope; });
    $('#connected-list').setAttribute('aria-busy', String(changingScope));
    $('#platform-catalogue').setAttribute('aria-busy', String(busy));
  }
  async function api(path, data) {
    const options = {credentials: 'same-origin', cache: 'no-store', headers: {Accept: 'application/json'}};
    if (data !== undefined) {
      options.method = 'POST'; options.headers['Content-Type'] = 'application/json';
      options.headers['X-CSRF-Token'] = session?.csrf || ''; options.body = JSON.stringify(data);
    }
    const response = await fetch('/api/customer/' + path, options);
    const payload = await response.json();
    if (!response.ok) {
      if (response.status === 401) location.replace('/workspace/login');
      if (['workspace_changed', 'workspace_access'].includes(payload.code)) location.replace('/workspace');
      throw new Error(payload.error || 'Chưa thể tải trạng thái. Vui lòng thử lại.');
    }
    return payload;
  }
  function connections() {
    const clientId = current.selected_client?.id;
    if (!clientId || !ready || changingScope) return [];
    const known = new Set(current.platforms.map((platform) => platform.id));
    return (Array.isArray(current.connections) ? current.connections : []).filter((item) => item
      && item.workspace_id === workspaceId && item.client_id === clientId && known.has(item.platform_id)
      && typeof item.id === 'string' && item.id.length <= 128 && Object.hasOwn(stateLabels, item.state));
  }
  function platformState(platform) {
    const rows = connections().filter((item) => item.platform_id === platform.id);
    if (rows.some((item) => attentionStates.includes(item.state))) return 'attention';
    if (rows.some((item) => ['connected', 'syncing'].includes(item.state))) return 'connected';
    return 'upcoming';
  }
  function saveFilters() {
    clearTimeout(historyTimer);
    const url = new URL(location.href);
    for (const key of ['platform', 'q', 'category', 'status']) url.searchParams.delete(key);
    const query = $('#platform-search').value.trim();
    if (query) url.searchParams.set('q', query);
    if (category !== 'all') url.searchParams.set('category', category);
    if ($('#platform-status-filter').value !== 'all') url.searchParams.set('status', $('#platform-status-filter').value);
    history.replaceState(null, '', url.pathname + url.search);
  }
  function filter(persist = false) {
    const words = fold($('#platform-search').value.trim()).split(/\s+/).filter(Boolean);
    const availability = $('#platform-status-filter').value;
    let count = 0;
    for (const platform of current.platforms) {
      const card = document.querySelector(`[data-platform="${platform.id}"]`);
      if (!card) continue;
      const haystack = fold([platform.id.replaceAll('_', ' '), platform.name, platform.subtitle, platform.description].join(' '));
      const state = platformState(platform);
      const matches = (category === 'all' || platform.categories.includes(category))
        && (availability === 'all' || availability === state) && words.every((word) => haystack.includes(word));
      card.hidden = !matches;
      if (matches) count += 1;
      const badge = card.querySelector('[data-platform-state]'); badge.dataset.state = state;
      badge.textContent = state === 'connected' ? 'Đã kết nối' : state === 'attention' ? 'Cần kiểm tra' : platform.status_label;
      const button = card.querySelector('[data-platform-details]');
      button.replaceChildren(node('span', connections().some((item) => item.platform_id === platform.id) ? 'Xem tài khoản' : 'Tìm hiểu'), icon('arrow_forward'));
    }
    document.querySelectorAll('[data-category]').forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.category === category));
      button.querySelector('[data-category-count]').textContent = current.platforms.filter((item) => button.dataset.category === 'all' || item.categories.includes(button.dataset.category)).length;
    });
    $('#platform-result-count').textContent = `Hiển thị ${count} / ${current.platforms.length} nền tảng`;
    $('#platform-no-results').hidden = count !== 0;
    $('#platform-clear-filters').hidden = !words.length && category === 'all' && availability === 'all';
    if (persist) { clearTimeout(historyTimer); historyTimer = setTimeout(saveFilters, 180); }
  }
  function connectionCard(item) {
    const platform = current.platforms.find((entry) => entry.id === item.platform_id);
    const card = node('article', '', 'ig-connection-card'); card.dataset.connectionId = item.id;
    const heading = node('div', '', 'ig-connection-top'), title = node('div', '');
    title.append(node('h3', platform.name), node('p', item.account_name || platform.asset_label));
    heading.append(icon(platform.icon, 'ig-provider ig-' + (colors.has(platform.color) ? platform.color : 'blue')), title);
    const badge = node('span', stateLabels[item.state], 'ig-badge');
    badge.dataset.state = attentionStates.includes(item.state) ? 'attention' : item.state === 'pending' ? 'upcoming' : 'connected';
    const meta = node('div', '', 'ig-connection-meta');
    const stamp = item.last_sync_at && new Date(item.last_sync_at);
    const syncLabel = stamp && !Number.isNaN(stamp.getTime()) ? new Intl.DateTimeFormat('vi-VN', {dateStyle: 'short', timeStyle: 'short', timeZone: current.workspace.timezone || 'Asia/Ho_Chi_Minh'}).format(stamp) : 'Chưa đồng bộ';
    for (const [label, value] of [['Tài sản', item.asset_name || 'Chưa chọn tài sản'], ['Đồng bộ gần nhất', syncLabel]]) {
      const row = node('div', ''); row.append(node('span', label), node('strong', value)); meta.append(row);
    }
    const actions = node('div', '', 'ig-connection-actions');
    const info = node('button', 'Thông tin kết nối'); info.type = 'button'; info.addEventListener('click', () => showPlatform(platform.id));
    const link = node('a', 'Xem nền tảng ↗'); link.href = '#platform-catalogue';
    link.addEventListener('click', (event) => { event.preventDefault(); resetFilters(platform.name); browse(); });
    actions.append(info, link); card.append(heading, badge, meta, actions); return card;
  }
  function renderConnections() {
    const rows = connections();
    $('#connected-list').replaceChildren(...rows.map(connectionCard));
    $('#connected-empty').hidden = rows.length > 0;
    $('#connected-count').textContent = ready && !changingScope ? `${rows.length} tài khoản` : 'Đang cập nhật';
    const attention = rows.filter((item) => attentionStates.includes(item.state)).length;
    const syncing = rows.filter((item) => item.state === 'syncing').length;
    $('#integration-sync-note').textContent = !ready || changingScope ? loadFailed ? 'Chưa xác định trạng thái' : 'Đang cập nhật trạng thái'
      : attention ? `${attention} tài khoản cần kiểm tra`
      : syncing ? `${syncing} tài khoản đang đồng bộ` : current.summary?.automatic_sync === true && rows.length ? 'Đồng bộ tự động đang bật' : 'Chưa bật đồng bộ tự động';
    const client = current.selected_client;
    $('#connected-empty-title').textContent = !ready ? loadFailed ? 'Chưa tải được trạng thái kết nối' : 'Đang tải trạng thái kết nối…'
      : changingScope ? 'Đang chuyển phạm vi làm việc…'
      : !client ? 'Chọn khách hàng để xem kết nối' : 'Chưa có tài khoản được kết nối';
    $('#connected-description').textContent = !ready ? loadFailed ? 'Vui lòng kiểm tra lại. Tài khoản đã kết nối sẽ hiển thị sau khi tải thành công.' : 'Vui lòng chờ trong khi cập nhật thông tin của Workspace.'
      : changingScope ? 'Trạng thái kết nối sẽ được cập nhật theo khách hàng hoặc Workspace mới.'
      : !client ? current.clients.length ? 'Chọn khách hàng trong danh sách phía trên để xác định nơi tổ chức kết nối và dữ liệu.'
        : 'Thêm khách hàng đầu tiên ở trang Tổng quan để bắt đầu tổ chức nguồn dữ liệu.'
        : 'Các tài khoản được cấp quyền cho khách hàng này sẽ xuất hiện tại đây.';
    $('#connected-browse').textContent = loadFailed ? 'Thử tải lại' : !client ? current.clients.length ? 'Chọn khách hàng' : current.permissions.manage_connections ? 'Thêm khách hàng' : 'Về Tổng quan' : 'Khám phá nền tảng ↓';
  }
  function render() {
    const select = $('#integration-client');
    select.replaceChildren(new Option('Chọn khách hàng', ''), ...current.clients.map((client) => new Option(client.name, client.id)));
    select.value = current.selected_client?.id || ''; select.options[0].disabled = Boolean(current.selected_client);
    $('#integration-scope').textContent = current.selected_client ? `Đang làm việc: ${current.selected_client.name}` : current.clients.length
      ? 'Chọn khách hàng để xác định nơi tổ chức kết nối và dữ liệu.' : 'Workspace chưa có khách hàng. Thêm khách hàng ở trang Tổng quan để bắt đầu.';
    $('#integration-permission-note').textContent = current.permissions.manage_connections ? 'Bạn có quyền quản lý kết nối trong Workspace này.' : 'Bạn có quyền xem. Owner/Admin quản lý cấp quyền kết nối.';
    $('#integration-step-client').dataset.complete = String(Boolean(current.selected_client));
    $('#integration-step-client b').textContent = current.selected_client ? '✓' : '1';
    renderConnections(); filter(); controls();
  }
  async function refresh() {
    try {
      session = await api('session');
      if (!session.user) { location.replace('/workspace/login'); return; }
      if (session.workspace?.id !== workspaceId) { location.replace('/workspace'); return; }
      const next = await api(base + '/integrations');
      if (next.workspace.id !== workspaceId) { location.replace('/workspace'); return; }
      if ($('#integration-dialog').open && next.selected_client?.id !== current.selected_client?.id) $('#integration-dialog').close();
      current = next; ready = true; loadFailed = false; render();
    } catch (error) {
      ready = false; loadFailed = true; render(); throw error;
    }
  }
  async function operation(action) {
    if (busy) return;
    busy = true; controls(); status('');
    try { await action(); }
    catch (error) { status(error.message || 'Chưa thể kết nối dịch vụ. Vui lòng thử lại.', 'error'); }
    finally { busy = false; controls(); }
  }
  function showDialog(title, description, extra = [], platform = null) {
    $('#integration-dialog-title').textContent = title;
    $('#integration-dialog-description').textContent = description;
    $('#integration-dialog-extra').replaceChildren(...extra);
    $('#integration-dialog-icon').textContent = platform?.icon || 'hub';
    $('#integration-dialog-icon').className = 'material-symbols-outlined ig-provider' + (platform && colors.has(platform.color) ? ' ig-' + platform.color : '');
    $('#integration-dialog-badge').textContent = platform ? platformState(platform) === 'connected' ? 'Đã kết nối' : platformState(platform) === 'attention' ? 'Cần kiểm tra' : platform.status_label : '';
    $('#integration-dialog-badge').hidden = !platform;
    $('#integration-dialog-badge').dataset.state = platform ? platformState(platform) : 'upcoming';
    $('#integration-dialog-context').hidden = Boolean(current.selected_client) || !platform;
    $('#integration-dialog-context').textContent = current.clients.length ? 'Chọn khách hàng' : current.permissions.manage_connections ? 'Thêm khách hàng' : 'Về Tổng quan';
    $('#integration-dialog').showModal();
  }
  function showPlatform(id) {
    if (changingScope) return;
    const platform = current.platforms.find((item) => item.id === id); if (!platform) return;
    const own = connections().filter((item) => item.platform_id === id);
    const context = !current.selected_client ? 'Trước tiên, chọn hoặc thêm khách hàng để xác định phạm vi kết nối.'
      : !current.permissions.manage_connections ? `Khách hàng: ${current.selected_client.name}. Bạn có quyền xem; Owner/Admin quản lý cấp quyền kết nối.`
        : `Khách hàng đang chọn: ${current.selected_client.name}. Kết nối chỉ được gắn với khách hàng này.`;
    const extra = [node('p', context, 'ig-dialog-note')];
    if (own.length) {
      extra.push(node('h3', 'Tài khoản trong phạm vi hiện tại', 'ig-dialog-subheading'));
      const list = node('ul', '', 'ig-dialog-assets');
      own.forEach((item) => list.append(node('li', `${item.account_name || platform.asset_label} · ${item.asset_name || 'Chưa chọn tài sản'} · ${stateLabels[item.state]}`)));
      extra.push(list);
    } else {
      const steps = node('ol', '');
      ['Chọn khách hàng / thương hiệu.', `Cấp quyền trên nền tảng và chọn ${platform.asset_label}.`,
        'Hệ thống kiểm tra quyền và đồng bộ dữ liệu.', 'Xem hiệu suất và tạo báo cáo khi có dữ liệu.'].forEach((text) => steps.append(node('li', text)));
      extra.push(steps);
    }
    extra.push(node('p', own.length ? 'Không chia sẻ token hay mật khẩu của nguồn dữ liệu. Liên hệ Owner/Admin khi cần thay đổi quyền kết nối.' : 'Chức năng cấp quyền và đồng bộ tự phục vụ đang được mở theo từng nền tảng. Không cần nhập token hay mật khẩu tại đây.', 'ig-dialog-note'));
    showDialog(platform.name, own.length ? 'Thông tin các tài khoản được cấp quyền cho khách hàng đang chọn.' : platform.readiness_note, extra, platform);
  }
  function resetFilters(query = '') {
    $('#platform-search').value = query; $('#platform-status-filter').value = 'all'; category = 'all'; filter(); saveFilters();
  }
  function browse() { $('#platform-catalogue').scrollIntoView({block: 'start'}); $('#platform-search').focus({preventScroll: true}); }
  function chooseContext() {
    if (busy) return;
    if (!current.clients.length) { location.assign('/workspace#client-card'); return; }
    $('#integration-client').scrollIntoView({block: 'center'}); $('#integration-client').focus({preventScroll: true});
  }
  function guide() {
    showDialog('Hướng dẫn kết nối', 'Đăng nhập và kết nối nguồn dữ liệu là hai bước riêng. Bạn tự quyết định nền tảng và tài sản nào được cấp quyền.',
      [node('p', 'Chọn khách hàng → tìm nền tảng → cấp quyền trên trang chính thức → chọn tài sản → chờ đồng bộ → xem dữ liệu.', 'ig-dialog-note'),
       node('p', 'Danh mục hiện có chín nền tảng. Tích hợp tự phục vụ được mở theo từng nguồn; Owner/Admin quản lý cấp quyền trong Workspace.', 'ig-dialog-note')]);
  }
  document.querySelectorAll('[data-platform-details]').forEach((button) => button.addEventListener('click', () => showPlatform(button.dataset.platformDetails)));
  document.querySelectorAll('[data-sidebar-platform]').forEach((button) => button.addEventListener('click', () => showPlatform(button.dataset.sidebarPlatform)));
  document.querySelectorAll('[data-category]').forEach((button) => button.addEventListener('click', () => { category = button.dataset.category; filter(true); }));
  $('#platform-search').addEventListener('input', () => filter(true));
  $('#platform-status-filter').addEventListener('change', () => filter(true));
  for (const selector of ['#platform-reset', '#platform-clear-filters']) $(selector).addEventListener('click', () => { resetFilters(); $('#platform-search').focus(); });
  $('#connected-browse').addEventListener('click', (event) => { event.preventDefault(); if (busy) return; if (loadFailed) $('#integrations-refresh').click(); else if (!current.selected_client) chooseContext(); else { resetFilters(); browse(); } });
  $('#integration-dialog-context').addEventListener('click', () => { $('#integration-dialog').close(); chooseContext(); });
  $('#integration-client').addEventListener('change', () => operation(async () => {
    const clientId = $('#integration-client').value;
    if (!current.clients.some((client) => client.id === clientId)) { render(); return; }
    changingScope = true; render(); controls();
    try { await api(`${base}/clients/${clientId}/select`, {}); await refresh(); status('Đã cập nhật khách hàng đang làm việc.'); }
    catch (error) { try { await refresh(); } catch { ready = false; } throw error; }
    finally { changingScope = false; render(); }
  }));
  $('#integration-workspace-select').addEventListener('change', () => operation(async () => {
    const id = $('#integration-workspace-select').value;
    if (!session.workspaces.some((item) => item.id === id)) { $('#integration-workspace-select').value = workspaceId; return; }
    changingScope = true; render(); controls();
    try { await api(`workspaces/${id}/select`, {}); location.assign('/workspace/integrations'); }
    catch (error) { changingScope = false; $('#integration-workspace-select').value = workspaceId; try { await refresh(); } catch { ready = false; } render(); throw error; }
  }));
  $('#integrations-refresh').addEventListener('click', () => operation(async () => {
    await refresh();
    const checked = new Intl.DateTimeFormat('vi-VN', {hour: '2-digit', minute: '2-digit', timeZone: current.workspace.timezone || 'Asia/Ho_Chi_Minh'}).format(new Date());
    status(`Đã cập nhật trạng thái lúc ${checked}. ${connections().length ? 'Thông tin được hiển thị theo khách hàng đang chọn.' : 'Chưa có tài khoản nào được kết nối.'}`);
  }));
  $('#integrations-logout').addEventListener('click', () => operation(async () => { await api('auth/logout', {}); location.assign('/workspace/login'); }));
  $('#integration-dialog-close').addEventListener('click', () => $('#integration-dialog').close());
  $('#integration-guide').addEventListener('click', guide);
  document.querySelectorAll('[data-integration-guide]').forEach((button) => button.addEventListener('click', guide));
  document.querySelectorAll('[data-future]').forEach((button) => button.addEventListener('click', () => showDialog(button.dataset.future, 'Khu vực này đang được hoàn thiện cho Workspace. Bạn có thể quản lý khách hàng ở Tổng quan và khám phá nguồn dữ liệu tại trang Kết nối nền tảng.')));
  window.addEventListener('pageshow', (event) => { if (event.persisted) location.reload(); });
  const requested = initial.platforms.find((platform) => platform.id === params.get('platform'));
  $('#platform-search').value = requested ? requested.name : (params.get('q') || '').slice(0, 150);
  if (['connected', 'attention', 'upcoming'].includes(params.get('status'))) $('#platform-status-filter').value = params.get('status');
  render(); operation(refresh);
})();
