/* Guided Facebook UI. Every mutation still uses the authenticated, scoped BFF. */
(() => {
  'use strict';
  function create(options) {
    const dialog = document.querySelector('#facebook-connect-dialog');
    const $ = (selector) => dialog.querySelector(selector);
    const source = 'facebook_content', pageSize = 25;
    const fold = (value) => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[đĐ]/g, 'd').toLowerCase();
    const recoveryCodes = new Set(['provider_reauth', 'provider_scopes', 'connection_version', 'connection_access', 'provider_asset_scope', 'connection_permission', 'email_verification_required', 'email_unverified']);
    const messages = {
      provider_cancelled: 'Bạn đã hủy trên Facebook. Khi sẵn sàng, bạn có thể kết nối lại.',
      oauth_state: 'Phiên kết nối đã hết hạn. Bấm tiếp tục để thử lại.',
      provider_scopes: 'Facebook chưa cấp đủ quyền đọc Fanpage. Vui lòng chọn lại quyền.',
      provider_reauth: 'Quyền Facebook cần được cấp lại. Kết nối lại để tiếp tục.',
      provider_failed: 'Chưa kết nối được Facebook. Vui lòng thử lại.',
      connector_not_configured: 'Kết nối Facebook chưa sẵn sàng. Vui lòng liên hệ VIO.',
      email_verification_required: 'Phiên kết nối cũ cần được mở lại. Bấm tiếp tục với Facebook.',
      email_unverified: 'Phiên kết nối cũ cần được mở lại. Bấm tiếp tục với Facebook.',
      provider_asset_scope: 'Fanpage không còn trong quyền truy cập. Chọn lại quyền trên Facebook.',
      connection_version: 'Kết nối vừa thay đổi. Vui lòng chọn lại Fanpage.',
      connection_access: 'Kết nối không còn khả dụng trong phạm vi này.',
      connection_permission: 'Quyền của bạn vừa thay đổi. Chủ sở hữu hoặc quản trị viên có thể quản lý kết nối.',
    };
    let scope, connectionKey, accessKey, generation = 0, busy = '', pagesState = 'idle', totalPages = 1;
    let assets = [], selected = '', page = 0, forcePages = false, forceConnect = false, message = '', messageKind = 'info', returnFocus;
    const ctx = () => options.context();
    const key = (value) => value.connection ? value.connection.id + ':' + value.connection.version : '';
    const access = (value) => [value.canManage, value.platform?.can_connect].join(':');
    const node = (tag, text, className) => {
      const item = document.createElement(tag); item.textContent = text;
      if (className) item.className = className;
      return item;
    };
    const binding = (value) => ({workspace: value.workspaceId, client: value.clientId || null, actor: value.user?.id});
    const sameScope = (a, value) => Boolean(a && a.workspace === value.workspaceId && a.client === (value.clientId || null) && a.actor === value.user?.id);
    const active = (ticket, expected) => dialog.open && ticket === generation && sameScope(expected, ctx()) && ctx().ready;
    function state(value = ctx()) {
      if (!value.ready) return 'loading';
      if (!value.clientId) return 'client';
      if (!value.canManage) return 'viewer';
      if (!value.platform?.can_connect) return 'unavailable';
      if (forceConnect || !value.connection || ['expired', 'disconnected', 'pending'].includes(value.connection.state)) return 'connect';
      if (forcePages || !value.connection.asset_id) return 'pages';
      return 'done';
    }
    function clearPages() {
      assets = []; selected = ''; page = 0; pagesState = 'idle';
      $('#facebook-page-search').value = ''; $('#facebook-pages').replaceChildren();
    }
    function feedback(text = '', kind = 'info') {
      message = text; messageKind = kind;
      $('#facebook-feedback').textContent = text; $('#facebook-feedback').hidden = !text;
      $('#facebook-feedback').dataset.kind = kind;
    }
    function close() {
      if (busy && busy !== 'discover') return;
      generation += 1; busy = ''; forcePages = false; clearPages();
      dialog.close();
      if (returnFocus?.isConnected) returnFocus.focus({preventScroll: true});
    }
    function updateControls() {
      const value = ctx(), view = state(value), primary = $('#facebook-primary');
      let label = 'Tiếp tục', disabled = Boolean(busy), showReport = false;
      if (view === 'client') { label = 'Tiếp tục'; disabled ||= !$('#facebook-client').value; }
      if (view === 'connect') label = 'Tiếp tục với Facebook';
      if (view === 'pages') { label = 'Kết nối Fanpage'; disabled ||= pagesState !== 'ready' || !assets.some((item) => item.id === selected); }
      if (view === 'done') {
        label = 'Thử đồng bộ lại';
        showReport = value.connection.state !== 'error' && Boolean(value.connection.synced_at || value.connection.state === 'syncing');
        if (!showReport && value.connection.state !== 'error') label = 'Đồng bộ dữ liệu';
      }
      if (view === 'viewer') { label = 'Đóng'; showReport = Boolean(value.connection?.asset_id && value.connection.synced_at && value.connection.state !== 'expired'); }
      if (view === 'unavailable') label = 'Đóng';
      if (view === 'loading') { label = 'Đang kiểm tra…'; disabled = true; }
      if (busy) label = ({authorize:'Đang mở Facebook…',select:'Đang kết nối…',sync:'Đang gửi yêu cầu…',client:'Đang chọn…',check:'Đang kiểm tra…'})[busy] || label;
      primary.textContent = label; primary.disabled = disabled; primary.hidden = showReport;
      $('#facebook-view-report').hidden = !showReport;
      $('#facebook-close').disabled = Boolean(busy && busy !== 'discover');
      $('#facebook-later').disabled = Boolean(busy && busy !== 'discover');
      $('#facebook-later').textContent = ['done','viewer','unavailable'].includes(view) ? 'Đóng' : 'Để sau';
      for (const selector of ['#facebook-regrant','#facebook-load-pages','#facebook-retry-pages','#facebook-empty-retry','#facebook-change-page','#facebook-custom-sync','#facebook-disconnect','#facebook-client']) $(selector).disabled = Boolean(busy);
      dialog.querySelectorAll('[name=facebook-page]').forEach((input) => { input.disabled = Boolean(busy); });
      $('#facebook-page-search').disabled = Boolean(busy);
      $('#facebook-page-prev').disabled = Boolean(busy) || page === 0;
      $('#facebook-page-next').disabled = Boolean(busy) || page + 1 >= totalPages;
      $('#facebook-retry-state').disabled = Boolean(busy);
      $('#facebook-custom-sync').disabled ||= value.connection?.state === 'syncing';
      $('#facebook-reconnect').hidden = !value.ready || !value.canManage || !value.platform?.can_connect || !value.connection
        || view === 'connect';
      $('#facebook-reconnect').disabled = Boolean(busy && busy !== 'discover');
    }
    function renderDone(value) {
      const connection = value.connection, syncing = connection.state === 'syncing', failed = connection.state === 'error';
      const saved = Boolean(connection.synced_at), icon = $('#facebook-result-icon');
      icon.textContent = syncing ? 'sync' : failed ? 'info' : 'check_circle';
      icon.dataset.state = failed ? 'error' : saved ? 'ready' : 'connected'; icon.classList.toggle('fb-spin', syncing);
      $('#facebook-result-title').textContent = failed ? 'Fanpage cần đồng bộ lại' : saved && !syncing ? 'Đã đồng bộ Fanpage' : 'Đã kết nối Fanpage';
      $('#facebook-result-description').textContent = failed ? 'Chưa cập nhật được dữ liệu. Thử đồng bộ lại để tiếp tục.'
        : syncing ? saved ? 'Đang cập nhật dữ liệu. Bạn vẫn có thể xem lần đồng bộ trước.' : 'Đang đồng bộ dữ liệu đầu tiên. Bạn có thể đóng cửa sổ và tiếp tục làm việc.'
          : saved ? 'Bạn có thể xem bài đăng và các chỉ số đã thu thập.' : 'Bấm đồng bộ để tải dữ liệu Fanpage.';
      $('#facebook-result-page').textContent = connection.asset_name || 'Fanpage đã chọn';
      const stamp = connection.synced_at && new Date(connection.synced_at);
      $('#facebook-result-updated').textContent = stamp && !Number.isNaN(stamp.getTime())
        ? 'Cập nhật: ' + new Intl.DateTimeFormat('vi-VN',{dateStyle:'short',timeStyle:'short',timeZone:value.timezone || 'Asia/Ho_Chi_Minh'}).format(stamp)
        : syncing ? 'Đang chờ dữ liệu đầu tiên' : 'Chưa có lần đồng bộ thành công';
      $('#facebook-existing-report').hidden = !failed || !saved;
    }
    function render() {
      if (!dialog.open) return;
      const value = ctx(), view = state(value), step = view === 'pages' ? 1 : view === 'done' ? 2 : 0;
      const headerIcon = $('#facebook-header-icon');
      dialog.dataset.view = view;
      dialog.setAttribute('aria-describedby', 'facebook-scope');
      headerIcon.className = 'fb-brand'; headerIcon.textContent = 'f';
      window.VioPlatformBrand?.setLogo(headerIcon, 'facebook_content');
      $('#facebook-header-label').textContent = 'FACEBOOK';
      $('#facebook-connect-title').textContent = 'Kết nối Fanpage';
      $('#facebook-close').setAttribute('aria-label', 'Đóng kết nối Fanpage');
      $('#facebook-state-message').textContent = value.loadFailed ? 'Chưa tải được trạng thái kết nối.' : 'Đang kiểm tra kết nối…';
      $('#facebook-retry-state').hidden = !value.loadFailed;
      $('#facebook-scope').textContent = value.workspaceName + (value.clientName && value.clientName !== value.workspaceName ? ' / ' + value.clientName : '');
      $('#facebook-scope').hidden = false;
      dialog.querySelectorAll('[data-facebook-view]').forEach((item) => { item.hidden = item.dataset.facebookView !== view; });
      $('#facebook-steps').hidden = ['viewer','unavailable','client','loading'].includes(view);
      dialog.querySelectorAll('[data-facebook-step]').forEach((item, index) => {
        item.dataset.complete = String(index < step); item.querySelector('b').textContent = index < step ? '✓' : String(index + 1);
        if (index === step) item.setAttribute('aria-current','step'); else item.removeAttribute('aria-current');
      });
      $('#facebook-connect-heading').textContent = forceConnect || value.connection?.state === 'expired' ? 'Kết nối lại Facebook để tiếp tục' : 'Dùng Facebook có quyền quản lý Fanpage';
      $('#facebook-pages-loading').hidden = pagesState !== 'loading';
      $('#facebook-pages-idle').hidden = pagesState !== 'idle';
      $('#facebook-pages-error').hidden = pagesState !== 'error';
      $('#facebook-pages-empty').hidden = pagesState !== 'ready' || assets.length > 0;
      $('#facebook-pages-picker').hidden = pagesState !== 'ready' || !assets.length;
      $('#facebook-page-total').textContent = pagesState === 'ready' ? `${assets.length} Fanpage` : '';
      if (view === 'done') renderDone(value);
      feedback(message, messageKind); updateControls();
    }
    function selection() {
      const item = assets.find((item) => item.id === selected), connection = ctx().connection;
      $('#facebook-selected-page').hidden = !item;
      $('#facebook-selected-page').textContent = item ? 'Đã chọn: ' + item.name : '';
      $('#facebook-page-change-note').hidden = !item || !connection?.asset_external_id || connection.asset_external_id === item.id;
      updateControls();
    }
    function drawPages() {
      const words = fold($('#facebook-page-search').value.trim()).split(/\s+/).filter(Boolean);
      const matches = assets.filter((asset) => words.every((word) => fold(asset.name + ' ' + asset.id).includes(word)));
      totalPages = Math.max(1, Math.ceil(matches.length / pageSize)); page = Math.min(page, totalPages - 1);
      const rows = matches.slice(page * pageSize, (page + 1) * pageSize);
      $('#facebook-pages').replaceChildren(...rows.map((asset) => {
        const label = node('label', '', 'fb-page-choice'), radio = document.createElement('input');
        radio.type = 'radio'; radio.name = 'facebook-page'; radio.value = asset.id; radio.checked = selected === asset.id;
        radio.addEventListener('change', () => { selected = asset.id; selection(); });
        const avatar = node('span', asset.name.slice(0,1).toUpperCase() || 'f', 'fb-page-avatar'); avatar.setAttribute('aria-hidden','true');
        const text = node('div', ''); text.append(node('strong', asset.name), node('small', 'ID ' + asset.id));
        label.append(radio, avatar, text); return label;
      }));
      $('#facebook-page-no-results').hidden = matches.length > 0;
      $('#facebook-pages-pagination').hidden = totalPages <= 1;
      $('#facebook-page-count').textContent = `Trang ${page + 1}/${totalPages} · ${matches.length} Fanpage`;
      $('#facebook-page-prev').disabled = page === 0; $('#facebook-page-next').disabled = page + 1 >= totalPages;
      selection();
    }
    async function run(kind, task) {
      if (busy || !dialog.open) return;
      const ticket = generation, expected = {...scope}; busy = kind; feedback(); render();
      try { await task(ticket, expected); }
      catch (error) {
        if (!active(ticket, expected)) return;
        if (kind === 'discover') pagesState = 'error';
        if (recoveryCodes.has(error.code)) {
          clearPages(); forcePages = false;
          try { await options.refresh(); } catch { /* Keep the safe scoped state and offer retry. */ }
        }
        if (active(ticket, expected)) feedback(messages[error.code] || (error.status === 429 ? 'Bạn đã thử nhiều lần. Vui lòng chờ trước khi thử lại.' : error.message || 'Chưa thể thực hiện. Vui lòng thử lại.'), 'error');
      } finally {
        if (ticket === generation) { busy = ''; update(); }
      }
    }
    function loadPages() {
      const value = ctx(), connection = value.connection;
      if (busy || state(value) !== 'pages' || !connection || !value.canManage) return;
      pagesState = 'loading';
      return run('discover', async (ticket, expected) => {
        const payload = await options.request(`workspaces/${value.workspaceId}/connections/${connection.id}/discover`, {client_id:value.clientId, version:connection.version});
        if (!active(ticket, expected)) return;
        if (payload.connection_id !== connection.id || payload.workspace_id !== value.workspaceId || payload.client_id !== value.clientId || payload.version !== connection.version
            || ctx().connection?.id !== connection.id || ctx().connection?.version !== connection.version || !Array.isArray(payload.assets) || payload.assets.length > 15000
            || payload.assets.some((item) => !item || typeof item.id !== 'string' || !/^\d{1,250}$/.test(item.id) || typeof item.name !== 'string' || item.name.length > 250)) throw new Error('Danh sách Fanpage đã thay đổi. Vui lòng tải lại.');
        assets = [...new Map(payload.assets.map((item) => [item.id, {id:item.id,name:item.name || item.id}])).values()];
        selected = assets.some((item) => item.id === connection.asset_external_id) ? connection.asset_external_id : assets.length === 1 ? assets[0].id : '';
        pagesState = 'ready'; page = 0; drawPages();
      });
    }
    function remember() {
      const value = ctx();
      try { sessionStorage.setItem('vio:facebook:connect:' + value.workspaceId, JSON.stringify({...binding(value), expires:Date.now() + 600000})); } catch { /* Storage is optional; explicit Page selection still works on return. */ }
    }
    function consumeIntent() {
      const key = 'vio:facebook:connect:' + ctx().workspaceId;
      try {
        const raw = sessionStorage.getItem(key); sessionStorage.removeItem(key);
        if (!raw || raw.length > 1000) return false;
        const intent = JSON.parse(raw);
        return intent.expires > Date.now() && intent.expires <= Date.now() + 600000 && sameScope(intent, ctx());
      } catch { return false; }
    }
    function authorize() {
      const value = ctx();
      if (!value.ready || !value.canManage || !value.clientId || !value.platform?.can_connect) return;
      return run('authorize', async (ticket, expected) => {
        const result = await options.request(`workspaces/${value.workspaceId}/providers/${source}/start`, {client_id:value.clientId});
        if (!active(ticket, expected)) return;
        const url = new URL(result.authorization_url);
        if (url.protocol !== 'https:' || url.host !== 'www.facebook.com' || url.username || url.password || url.hash || !/^\/v\d+\.\d+\/dialog\/oauth$/.test(url.pathname)
            || url.searchParams.get('redirect_uri') !== location.origin + '/auth/customer/providers/meta/callback') throw new Error('Chưa mở được Facebook. Vui lòng thử lại.');
        remember(); location.assign(url.href);
      });
    }
    function confirmPage() {
      const value = ctx(), connection = value.connection, chosen = selected;
      if (state(value) !== 'pages' || pagesState !== 'ready' || !connection || !assets.some((item) => item.id === chosen)) return;
      return run('select', async (ticket, expected) => {
        const result = await options.request(`workspaces/${value.workspaceId}/connections/${connection.id}/select`, {client_id:value.clientId, version:connection.version, external_id:chosen});
        if (!active(ticket, expected)) return;
        if (result.connection_id !== connection.id || !result.asset_id) throw new Error('Chưa xác nhận được Fanpage. Vui lòng cập nhật trạng thái.');
        forcePages = false; clearPages();
        await options.refresh();
      });
    }
    function sync() {
      const value = ctx(), connection = value.connection;
      if (state(value) !== 'done' || !connection?.asset_id || connection.state === 'syncing') return;
      const last = connection.latest_sync;
      const validDate = (date) => typeof date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(date);
      const end = new Date(); end.setUTCDate(end.getUTCDate() - 1);
      const start = new Date(end); start.setUTCDate(start.getUTCDate() - 29);
      const period = last && validDate(last.start_date) && validDate(last.end_date) ? {start:last.start_date,end:last.end_date} : {start:start.toISOString().slice(0,10),end:end.toISOString().slice(0,10)};
      const requestKey = crypto.randomUUID().replaceAll('-','');
      return run('sync', async (ticket, expected) => {
        await options.request(`workspaces/${value.workspaceId}/connections/${connection.id}/sync`, {client_id:value.clientId, version:connection.version, ...period, request_key:requestKey});
        if (active(ticket, expected)) await options.refresh();
      });
    }
    function chooseClient() {
      const chosen = $('#facebook-client').value, value = ctx();
      if (!value.clients.some((client) => client.id === chosen)) return;
      return run('client', async () => {
        await options.selectClient(chosen);
        if (!dialog.open || ctx().workspaceId !== scope.workspace || ctx().user?.id !== scope.actor || ctx().clientId !== chosen) return;
        scope = binding(ctx()); connectionKey = key(ctx()); accessKey = access(ctx()); clearPages();
      });
    }
    function open(settings = {}) {
      if (dialog.open || !ctx().ready || document.querySelector('dialog[open]')) return;
      const value = ctx(); generation += 1; scope = binding(value); connectionKey = key(value); accessKey = access(value);
      busy = ''; forcePages = false; forceConnect = settings.reconnect === true; clearPages(); feedback(); returnFocus = document.activeElement;
      $('#facebook-options').open = false;
      const label = value.scopeLabel || 'Khách hàng', word = label.toLocaleLowerCase('vi-VN');
      $('#facebook-client-heading').textContent = `Kết nối cho ${word} nào?`;
      $('#facebook-client-label').textContent = label;
      $('#facebook-add-client').textContent = `Thêm ${word} tại Tổng quan →`;
      $('#facebook-client').replaceChildren(new Option(`Chọn ${word}`,''), ...value.clients.map((client) => new Option(client.name,client.id)));
      $('#facebook-add-client').hidden = value.clients.length > 0 || !value.canManage;
      dialog.showModal();
      if (settings.error) feedback(messages[settings.error] || messages.provider_failed);
      render(); $('#facebook-connect-title').focus({preventScroll:true});
      if (state() === 'pages' && settings.discover !== false) loadPages();
      if (state() === 'connect' && settings.authorize === true) authorize();
    }
    function update() {
      if (!dialog.open) return;
      const value = ctx();
      if (busy === 'client' && value.workspaceId === scope.workspace && value.user?.id === scope.actor) return;
      if (!sameScope(scope, value)) {
        busy = ''; close(); options.notify('Phạm vi hoặc tài khoản đã thay đổi. Mở lại kết nối Fanpage để tiếp tục.'); return;
      }
      if (!value.ready) { generation += 1; busy = ''; clearPages(); }
      if (value.ready && accessKey !== access(value)) {
        generation += 1; busy = ''; forcePages = false; clearPages(); accessKey = access(value); feedback();
      }
      if (connectionKey !== key(value)) {
        const ownSelection = busy === 'select';
        if (!ownSelection) { generation += 1; busy = ''; }
        forcePages = false; clearPages(); connectionKey = key(value);
        if (!ownSelection) feedback('Kết nối vừa thay đổi. Vui lòng kiểm tra trạng thái mới.');
      }
      render();
    }
    function resume(code, connectionId, requested = false) {
      const intended = consumeIntent(), value = ctx();
      const matching = code === 'connected' && value.connection?.id === connectionId;
      if (!intended && !matching && !requested) return false;
      open({discover:matching && intended, error:code && code !== 'connected' ? code : null});
      return true;
    }
    $('#facebook-close').addEventListener('click', close); $('#facebook-later').addEventListener('click', close);
    dialog.addEventListener('cancel', (event) => { event.preventDefault(); close(); });
    $('#facebook-primary').addEventListener('click', () => {
      const view = state();
      if (view === 'client') chooseClient();
      else if (view === 'connect') authorize();
      else if (view === 'pages') confirmPage();
      else if (view === 'done') sync();
      else close();
    });
    $('#facebook-client').addEventListener('change', updateControls);
    $('#facebook-retry-state').addEventListener('click', () => run('check', () => options.refresh()));
    for (const selector of ['#facebook-load-pages','#facebook-retry-pages','#facebook-empty-retry']) $(selector).addEventListener('click', loadPages);
    $('#facebook-regrant').addEventListener('click', authorize);
    $('#facebook-reconnect').addEventListener('click',() => {
      const value=ctx();
      if (busy && busy !== 'discover' || !value.ready || !value.canManage || !value.platform?.can_connect || !value.clientId) return;
      generation += 1; busy=''; forcePages=false; forceConnect=true; clearPages(); feedback(); render();
    });
    $('#facebook-page-search').addEventListener('input', () => { page = 0; drawPages(); });
    $('#facebook-clear-search').addEventListener('click', () => { $('#facebook-page-search').value = ''; page = 0; drawPages(); $('#facebook-page-search').focus(); });
    $('#facebook-page-prev').addEventListener('click', () => { if (page > 0) { page -= 1; drawPages(); } });
    $('#facebook-page-next').addEventListener('click', () => { page += 1; drawPages(); });
    $('#facebook-change-page').addEventListener('click', () => { forcePages = true; clearPages(); render(); loadPages(); });
    for (const [selector, action] of [['#facebook-custom-sync','sync'],['#facebook-disconnect','disconnect']]) $(selector).addEventListener('click', () => {
      const connection = ctx().connection;
      if (busy || !ctx().canManage || !connection) return;
      close(); options.manage(action, connection);
    });
    return Object.freeze({open, update, resume, get isOpen() { return dialog.open; }});
  }
  window.VioFacebookConnect = Object.freeze({create});
})();
