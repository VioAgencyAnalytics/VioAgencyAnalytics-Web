/* Integration UI consumes safe customer DTOs; no provider credentials or API calls. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const initial = JSON.parse($('#integrations-data').textContent);
  const workspaceId = initial.workspace.id;
  const base = `workspaces/${workspaceId}`;
  const params = new URLSearchParams(location.search);
  let current = initial, session, busy = false, ready = false, loadFailed = false, changingScope = false, historyTimer, syncTimer;
  let category = initial.categories.some((item) => item.id === params.get('category')) ? params.get('category') : 'all';
  const fold = (value) => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[đĐ]/g, 'd').toLowerCase();
  const stateLabels = {connected: 'Đã kết nối', syncing: 'Đang đồng bộ', expired: 'Cần cấp quyền lại', error: 'Cần kiểm tra', disconnected: 'Đã ngắt kết nối', pending: 'Chờ hoàn tất'};
  const attentionStates = ['expired', 'error', 'disconnected'];
  const colors = new Set(['blue', 'amber', 'teal', 'purple', 'red', 'dark']);
  const business = (details = current) => details.workspace.kind === 'business';
  const singleBrand = (details = current) => business(details) && details.clients.length === 1;
  const scopeLabel = () => business() ? 'Thương hiệu' : 'Khách hàng';
  const scopeWord = () => scopeLabel().toLocaleLowerCase('vi-VN');
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
    $('#integration-client').disabled = busy || !ready || !current.clients.length || singleBrand();
    $('#integration-workspace-select').disabled = busy || !ready;
    document.querySelectorAll('[data-platform-details], [data-sidebar-platform], [data-connection-info]').forEach((button) => { button.disabled = busy || changingScope; });
    document.querySelectorAll('[data-provider-action]').forEach((button) => { button.disabled = busy || changingScope; });
    $('#integration-dialog-close').disabled = busy;
    $('#integration-dialog form button').disabled = busy;
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
    let payload;
    try { payload = await response.json(); }
    catch { throw new Error('Dịch vụ tạm thời chưa phản hồi. Vui lòng thử lại.'); }
    if (!response.ok) {
      if (response.status === 401) location.replace('/workspace/login');
      if (['workspace_changed', 'workspace_access', 'client_changed'].includes(payload.code)) location.replace('/workspace');
      const error = new Error(payload.error || 'Chưa thể tải trạng thái. Vui lòng thử lại.');
      error.code = payload.code; error.status = response.status; throw error;
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
  const facebook = window.VioFacebookConnect.create({
    context: () => ({
      workspaceId, workspaceName: current.workspace.name, timezone: current.workspace.timezone,
      clientId: current.selected_client?.id || null, clientName: current.selected_client?.name || '', clients: current.clients,
      scopeLabel: scopeLabel(),
      user: session?.user,
      canManage: current.permissions.manage_connections === true, ready: ready && !changingScope, loadFailed,
      platform: current.platforms.find((item) => item.id === 'facebook_content'),
      connection: connections().find((item) => item.platform_id === 'facebook_content') || null,
    }),
    request: api, refresh, selectClient, notify: (message) => status(message),
    manage: (action, connection) => action === 'sync' ? syncDialog(connection) : disconnectDialog(connection),
  });
  const connector = window.VioConnectorConnect.create({
    context: (source) => ({workspaceId, workspaceName:current.workspace.name,
      clientId:current.selected_client?.id || null, clientName:current.selected_client?.name || '',
      clients:current.clients, scopeLabel:scopeLabel(), user:session?.user,
      canManage:current.permissions.manage_connections === true, ready:ready && !changingScope,
      platform:current.platforms.find((item) => item.id === source),
      connection:connections().find((item) => item.platform_id === source) || null}),
    request:api, refresh, selectClient, notify:(message) => status(message),
    manage:(action, connection) => action === 'sync' ? syncDialog(connection) : disconnectDialog(connection),
  });
  function facebookLabel(connection) {
    if (!current.selected_client) return `Chọn ${scopeWord()}`;
    if (!current.permissions.manage_connections) return 'Xem kết nối';
    if (!connection) return 'Kết nối Facebook';
    if (['expired','disconnected','pending'].includes(connection.state)) return 'Kết nối lại';
    return connection.asset_id ? 'Quản lý' : 'Chọn Fanpage';
  }
  function platformState(platform) {
    const rows = connections().filter((item) => item.platform_id === platform.id);
    if (rows.some((item) => attentionStates.includes(item.state))) return 'attention';
    if (rows.some((item) => ['connected', 'syncing'].includes(item.state))) return 'connected';
    return platform.can_connect ? 'available' : platform.availability === 'not_configured' ? 'not_configured' : 'upcoming';
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
      const connection = connections().find((item) => item.platform_id === platform.id);
      const isFacebook = platform.id === 'facebook_content';
      if (isFacebook && connection && !connection.asset_id && state === 'connected') badge.textContent = 'Chưa chọn Fanpage';
      const label = isFacebook && platform.can_connect ? facebookLabel(connection) : connection ? 'Quản lý' : platform.can_connect ? 'Kết nối' : 'Chi tiết';
      button.replaceChildren(node('span', label), icon('arrow_forward'));
      button.setAttribute('aria-label', `${label} · ${platform.name}`);
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
    const isFacebook = platform.id === 'facebook_content';
    const activePage = isFacebook && item.asset_id && !['expired','disconnected','pending'].includes(item.state);
    const card = node('article', '', 'ig-connection-card'); card.dataset.connectionId = item.id;
    const heading = node('div', '', 'ig-connection-top'), title = node('div', '');
    title.append(node('h3', isFacebook ? item.asset_name || platform.name : platform.name), node('p', isFacebook ? 'Facebook Content' : item.account_name || platform.asset_label));
    heading.append(icon(platform.icon, 'ig-provider ig-' + (colors.has(platform.color) ? platform.color : 'blue')), title);
    const badge = node('span', isFacebook && !item.asset_id && item.state === 'connected' ? 'Chưa chọn Fanpage' : stateLabels[item.state], 'ig-badge');
    badge.dataset.state = attentionStates.includes(item.state) ? 'attention' : item.state === 'pending' ? 'upcoming' : 'connected';
    const meta = node('div', '', 'ig-connection-meta');
    const stamp = (item.synced_at || item.last_sync_at) && new Date(item.synced_at || item.last_sync_at);
    const syncLabel = stamp && !Number.isNaN(stamp.getTime()) ? new Intl.DateTimeFormat('vi-VN', {dateStyle: 'short', timeStyle: 'short', timeZone: current.workspace.timezone || 'Asia/Ho_Chi_Minh'}).format(stamp) : 'Chưa đồng bộ';
    for (const [label, value] of [[isFacebook ? 'Fanpage' : 'Tài sản', item.asset_name || (isFacebook ? 'Chưa chọn Fanpage' : 'Chưa chọn tài sản')], ['Đồng bộ gần nhất', syncLabel]]) {
      const row = node('div', ''); row.append(node('span', label), node('strong', value)); meta.append(row);
    }
    const actions = node('div', '', 'ig-connection-actions');
    const info = node('button', isFacebook ? facebookLabel(item) : 'Thông tin kết nối'); info.type = 'button'; info.dataset.connectionInfo = 'true'; info.addEventListener('click', () => showPlatform(platform.id, true));
    actions.append(info);
    if (activePage) {
      const link = node('a', 'Xem Fanpage →'); link.href = '/workspace/channels/facebook-content'; actions.append(link);
    } else if (!isFacebook && item.asset_id && platform.data_contract?.adapter_ready && !['disconnected','pending'].includes(item.state)) {
      const link = node('a', 'Xem dữ liệu →'); link.href = '/workspace/reports/data?source=' + encodeURIComponent(platform.id); actions.append(link);
    } else if (!isFacebook) {
      const link = node('a', 'Xem nền tảng ↗'); link.href = '#platform-catalogue';
      link.addEventListener('click', (event) => { event.preventDefault(); resetFilters(platform.name); browse(); }); actions.append(link);
    }
    card.append(heading, badge, meta, actions); return card;
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
      : syncing ? `${syncing} tài khoản đang đồng bộ` : current.summary?.automatic_sync === true && rows.length ? 'Đồng bộ tự động đang bật' : rows.length ? 'Đồng bộ lần đầu tự động · cập nhật theo yêu cầu' : 'Chọn tài sản để bắt đầu đồng bộ';
    const client = current.selected_client;
    $('#connected-empty-title').textContent = !ready ? loadFailed ? 'Chưa tải được trạng thái kết nối' : 'Đang tải trạng thái kết nối…'
      : changingScope ? `Đang cập nhật ${scopeWord()}…`
      : !client ? `Chọn ${scopeWord()} để xem kết nối` : 'Chưa có kết nối';
    $('#connected-description').textContent = !ready ? loadFailed ? 'Thử tải lại để kiểm tra kết nối.' : 'Vui lòng chờ…'
      : changingScope ? 'Đang cập nhật kết nối.'
      : !client ? current.clients.length ? `Chọn ${scopeWord()} ở phía trên.`
        : `Thêm ${scopeWord()} đầu tiên tại Tổng quan.`
        : 'Chọn nền tảng bên dưới để bắt đầu.';
    $('#connected-browse').textContent = loadFailed ? 'Thử tải lại' : !client ? current.clients.length ? `Chọn ${scopeWord()}` : current.permissions.manage_connections ? `Thêm ${scopeWord()}` : 'Về Tổng quan' : 'Chọn nền tảng ↓';
  }
  function render() {
    const select = $('#integration-client');
    const automatic = singleBrand();
    $('#integration-context').dataset.singleBrand = String(automatic);
    $('#integration-subtitle').textContent = automatic ? 'Kết nối các tài khoản Marketing của doanh nghiệp.' : `Chọn ${scopeWord()}, rồi kết nối nguồn dữ liệu.`;
    $('#integration-context').setAttribute('aria-label', `${scopeLabel()} đang kết nối`);
    $('#integration-client-picker').hidden = automatic;
    $('#integration-scope-label').textContent = scopeLabel();
    $('#integration-brand-summary').hidden = !automatic;
    $('#integration-brand-name').textContent = automatic ? current.clients[0].name : '';
    $('#integration-manage-clients').hidden = automatic;
    $('#integration-manage-clients').textContent = `Quản lý ${scopeWord()} ↗`;
    select.replaceChildren(new Option(`Chọn ${scopeWord()}`, ''), ...current.clients.map((client) => new Option(client.name, client.id)));
    select.value = current.selected_client?.id || ''; select.options[0].disabled = Boolean(current.selected_client);
    $('#integration-scope').hidden = Boolean(current.selected_client);
    $('#integration-scope').textContent = automatic ? 'Đang chuẩn bị kết nối…' : current.clients.length ? `Chọn ${scopeWord()} để bắt đầu.` : `Thêm ${scopeWord()} tại Tổng quan để bắt đầu.`;
    $('#integration-permission-note').textContent = current.permissions.manage_connections ? '' : 'Chế độ xem · Chủ sở hữu hoặc quản trị viên quản lý kết nối.';
    $('#integration-scope').parentElement.hidden = Boolean(current.selected_client) && current.permissions.manage_connections;
    $('#integration-step-client').dataset.complete = String(Boolean(current.selected_client));
    $('#integration-step-client').hidden = automatic;
    $('#integration-client-step-label').textContent = `Chọn ${scopeWord()}`;
    $('#integration-step-client b').textContent = current.selected_client ? '✓' : '1';
    $('#integration-step-authorize b').textContent = automatic ? '1' : '2';
    $('#integration-step-assets b').textContent = automatic ? '2' : '3';
    renderConnections(); filter(); controls(); facebook.update(); connector.update();
  }
  async function refresh() {
    try {
      session = await api('session');
      if (!session.user) { location.replace('/workspace/login'); return; }
      if (session.workspace?.id !== workspaceId) { location.replace('/workspace'); return; }
      let next = await api(base + '/integrations');
      if (next.workspace.id !== workspaceId) { location.replace('/workspace'); return; }
      // Select the only business brand through the existing authenticated API.
      // A hidden picker must never invent a scope or skip server authorization.
      if (singleBrand(next) && !next.selected_client) {
        const clientId = next.clients[0].id;
        changingScope = true; render(); controls();
        try {
          await api(`${base}/clients/${clientId}/select`, {});
          next = await api(base + '/integrations');
          if (next.workspace.id !== workspaceId || next.selected_client?.id !== clientId) {
            throw new Error('Thương hiệu đang làm việc đã thay đổi. Vui lòng tải lại.');
          }
        } finally { changingScope = false; }
      }
      if ($('#integration-dialog').open && next.selected_client?.id !== current.selected_client?.id) $('#integration-dialog').close();
      current = next; ready = true; loadFailed = false; render();
      clearTimeout(syncTimer);
      if (!document.hidden && connections().some((item) => item.state === 'syncing')) syncTimer = setTimeout(() => operation(refresh), 5000);
    } catch (error) {
      ready = false; loadFailed = true; render(); throw error;
    }
  }
  async function operation(action) {
    if (busy) return;
    busy = true; controls(); status('');
    try { await action(); }
    catch (error) {
      const message = error.message || 'Chưa thể kết nối dịch vụ. Vui lòng thử lại.';
      status(message, 'error');
      if ($('#integration-dialog').open) {
        let feedback = $('#integration-dialog-feedback');
        if (!feedback) { feedback = node('p', '', 'ov-status'); feedback.id = 'integration-dialog-feedback'; feedback.setAttribute('role','alert'); $('#integration-dialog-extra').prepend(feedback); }
        feedback.textContent = message; feedback.dataset.kind = 'error';
      }
    }
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
    $('#integration-dialog-context').textContent = current.clients.length ? `Chọn ${scopeWord()}` : current.permissions.manage_connections ? `Thêm ${scopeWord()}` : 'Về Tổng quan';
    if (!$('#integration-dialog').open) $('#integration-dialog').showModal();
  }
  $('#integration-dialog').addEventListener('cancel', (event) => { if (busy) event.preventDefault(); });
  function showPlatform(id, connectOnClick = false) {
    if (changingScope) return;
    const platform = current.platforms.find((item) => item.id === id); if (!platform) return;
    if (id === 'facebook_content') { facebook.open({authorize:connectOnClick}); return; }
    connector.open(id);
  }

  function providerButton(label, action, danger = false) {
    const button = node('button', label, 'ov-button ' + (danger ? 'ig-danger' : 'ov-secondary'));
    button.type = 'button'; button.dataset.providerAction = 'true';
    button.addEventListener('click', action); return button;
  }
  function scoped(connection) { return {client_id: current.selected_client.id, version: connection.version}; }
  function syncDialog(connection) {
    const scope = scoped(connection);
    const sourceZone = ['gsc','youtube'].includes(connection.platform_id) ? 'America/Los_Angeles'
      : ['facebook_content','instagram','business_profile'].includes(connection.platform_id) ? 'UTC' : connection.asset_timezone || current.workspace.timezone || 'UTC';
    let stamp;
    try {
      const parts = new Intl.DateTimeFormat('en',{timeZone:sourceZone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
      const part = (key) => parts.find((item) => item.type === key).value;
      stamp = `${part('year')}-${part('month')}-${part('day')}`;
    } catch { stamp = new Date().toISOString().slice(0,10); }
    const today = new Date(stamp+'T00:00:00Z'); today.setUTCDate(today.getUTCDate() - (connection.platform_id === 'business_profile' ? 2 : 1));
    const end = today.toISOString().slice(0,10); today.setUTCDate(today.getUTCDate() - 29);
    const start = node('input', ''), finish = node('input', ''); start.type = finish.type = 'date';
    start.value = today.toISOString().slice(0,10); finish.value = end; finish.max = end;
    const a = node('label', 'Từ ngày'), b = node('label', 'Đến ngày'); a.append(start); b.append(finish);
    const requestKey = crypto.randomUUID().replaceAll('-', '');
    showDialog('Đồng bộ dữ liệu', 'Chọn tối đa 90 ngày đã kết thúc. Chạy lại không thay đổi snapshot hoặc báo cáo đã phát hành.', [a,b,providerButton('Thêm tác vụ đồng bộ', () => operation(async () => {
      await api(base + '/connections/' + connection.id + '/sync', {...scope,start:start.value,end:finish.value,request_key:requestKey});
      $('#integration-dialog').close(); await refresh(); status('Đã thêm tác vụ đồng bộ. Bạn có thể tiếp tục làm việc.', 'success');
    }))]);
  }
  function disconnectDialog(connection) {
    const scope = scoped(connection);
    showDialog('Ngắt kết nối tại Vio?', 'Xóa token được lưu cho nguồn này tại Vio và dừng các tác vụ đang chờ. Dữ liệu đã đồng bộ vẫn được giữ.',
      [node('p', 'Thao tác này không thu hồi toàn bộ ứng dụng ở Google/Meta, vì việc đó có thể ảnh hưởng các kết nối khác dùng chung tài khoản. Bạn có thể quản lý quyền ứng dụng trực tiếp tại nền tảng.', 'ig-dialog-note'),
        providerButton('Xác nhận ngắt kết nối', () => operation(async () => {
          const result = await api(base + '/connections/' + connection.id + '/disconnect', scope);
          $('#integration-dialog').close(); await refresh(); status(result.message, 'success');
        }), true)]);
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
  async function selectClient(clientId) {
    if (!current.clients.some((client) => client.id === clientId)) { render(); return; }
    changingScope = true; render(); controls();
    try { await api(`${base}/clients/${clientId}/select`, {}); await refresh(); status(`Đã chọn ${current.selected_client?.name || scopeWord()}.`); }
    catch (error) { try { await refresh(); } catch { ready = false; } throw error; }
    finally { changingScope = false; render(); }
  }
  function guide() {
    showDialog('Hướng dẫn kết nối', 'Đăng nhập và kết nối nguồn dữ liệu là hai bước riêng. Bạn tự quyết định nền tảng và tài sản nào được cấp quyền.',
      [node('p', `${singleBrand() ? '' : `Chọn ${scopeWord()} → `}Tìm nền tảng → cấp quyền trên trang chính thức → chọn tài sản → xem dữ liệu.`, 'ig-dialog-note'),
       node('p', 'Danh mục hiện có chín nền tảng. Tích hợp tự phục vụ được mở theo từng nguồn; Owner/Admin quản lý cấp quyền trong Workspace.', 'ig-dialog-note')]);
  }
  document.querySelectorAll('[data-platform-details]').forEach((button) => button.addEventListener('click', () => showPlatform(button.dataset.platformDetails, true)));
  document.querySelectorAll('[data-sidebar-platform]').forEach((button) => button.addEventListener('click', () => showPlatform(button.dataset.sidebarPlatform, true)));
  document.querySelectorAll('[data-category]').forEach((button) => button.addEventListener('click', () => { category = button.dataset.category; filter(true); }));
  $('#platform-search').addEventListener('input', () => filter(true));
  $('#platform-status-filter').addEventListener('change', () => filter(true));
  for (const selector of ['#platform-reset', '#platform-clear-filters']) $(selector).addEventListener('click', () => { resetFilters(); $('#platform-search').focus(); });
  $('#connected-browse').addEventListener('click', (event) => { event.preventDefault(); if (busy) return; if (loadFailed) $('#integrations-refresh').click(); else if (!current.selected_client) chooseContext(); else { resetFilters(); browse(); } });
  $('#integration-dialog-context').addEventListener('click', () => { $('#integration-dialog').close(); chooseContext(); });
  $('#integration-client').addEventListener('change', () => operation(() => selectClient($('#integration-client').value)));
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
    status(`Đã cập nhật lúc ${checked}.${connections().length ? '' : ' Chưa có tài khoản nào được kết nối.'}`);
  }));
  $('#integrations-logout').addEventListener('click', () => operation(async () => { await api('auth/logout', {}); location.assign('/workspace/login'); }));
  $('#integration-dialog-close').addEventListener('click', () => $('#integration-dialog').close());
  $('#integration-guide').addEventListener('click', guide);
  document.querySelectorAll('[data-integration-guide]').forEach((button) => button.addEventListener('click', guide));
  document.querySelectorAll('[data-future]').forEach((button) => button.addEventListener('click', () => showDialog(button.dataset.future, 'Khu vực này đang được hoàn thiện cho Workspace. Bạn có thể quản lý khách hàng ở Tổng quan và khám phá nguồn dữ liệu tại trang Kết nối nền tảng.')));
  window.addEventListener('pageshow', (event) => { if (event.persisted) location.reload(); });
  const requested = initial.platforms.find((platform) => platform.id === params.get('platform'));
  $('#platform-search').value = requested ? requested.name : (params.get('q') || '').slice(0, 150);
  if (['connected', 'attention', 'upcoming', 'available', 'not_configured'].includes(params.get('status'))) $('#platform-status-filter').value = params.get('status');
  render(); operation(async () => {
    await refresh();
    const messages = {connected:'Cấp quyền thành công.',provider_cancelled:'Bạn đã hủy cấp quyền. Các kết nối trước đó được giữ nguyên.',oauth_state:'Phiên cấp quyền đã hết hạn hoặc đã thay đổi. Vui lòng bắt đầu lại.',provider_scopes:'Chưa được cấp đủ quyền đọc. Vui lòng kiểm tra các quyền trên nền tảng.',workspace_changed:'Workspace đã thay đổi. Chọn lại phạm vi làm việc trước khi kết nối.',client_changed:'Khách hàng đã thay đổi. Chọn lại trước khi kết nối.',email_verification_required:'Vui lòng xác minh email trước khi kết nối.',connector_not_configured:'Ứng dụng nền tảng chưa được cấu hình. Liên hệ hỗ trợ VIO.',provider_reauth:'Quyền truy cập không còn hợp lệ. Vui lòng cấp quyền lại.',provider_failed:'Chưa thể hoàn tất cấp quyền. Thử lại hoặc liên hệ hỗ trợ.'};
    const code = params.get('oauth');
    const callbackSource = requested?.id || connections().find((item) => item.id === params.get('connection'))?.platform_id;
    const legacyEmailGate = callbackSource === 'facebook_content' && ['email_verification_required','email_unverified'].includes(code);
    if (legacyEmailGate) status('Phiên kết nối cũ cần được mở lại. Tiếp tục kết nối với Facebook.', 'info');
    else if (messages[code]) status(messages[code], code === 'connected' ? 'success' : 'error');
  }).then(() => {
    if (!ready) return;
    const code = params.get('oauth');
    const resumed = code ? facebook.resume(code, params.get('connection'), requested?.id === 'facebook_content') : false;
    if (!code && requested) showPlatform(requested.id);
    if (!resumed && code === 'connected') {
      const item = connections().find((entry) => entry.id === params.get('connection'));
      if (item) showPlatform(item.platform_id);
    }
    if (!resumed && code && code !== 'connected' && requested && requested.id !== 'facebook_content') connector.open(requested.id,messages[code] || 'Chưa hoàn tất kết nối. Vui lòng thử lại.');
    if (code) {
      const url = new URL(location.href); url.searchParams.delete('oauth'); url.searchParams.delete('connection');
      history.replaceState(null, '', url.pathname + url.search);
    }
  });
  document.addEventListener('visibilitychange', () => {clearTimeout(syncTimer); if (!document.hidden && !busy && ready && connections().some((item) => item.state === 'syncing')) operation(refresh);});
  window.addEventListener('pagehide', () => clearTimeout(syncTimer));
})();
