/* All non-Content connectors share one scoped, accessible three-step journey. */
(() => {
  'use strict';
  const providers = {ga4:'Google',gsc:'Google',google_ads:'Google',youtube:'Google',business_profile:'Google',facebook_ads:'Facebook',instagram:'Facebook',tiktok_ads:'TikTok'};
  const assetNames = {ga4:'property GA4',gsc:'website',google_ads:'tài khoản quảng cáo',youtube:'kênh YouTube',business_profile:'địa điểm',facebook_ads:'tài khoản quảng cáo',instagram:'tài khoản Instagram',tiktok_ads:'tài khoản quảng cáo'};
  const fold = (value) => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[đĐ]/g,'d').toLowerCase();
  const el = (tag, value, cls) => { const item = document.createElement(tag); item.textContent = value; if (cls) item.className = cls; return item; };
  function create(options) {
    const dialog = document.querySelector('#connector-connect-dialog'), $ = (selector) => dialog.querySelector(selector);
    let source, ticket = 0, busy = false, choosing = false, forceConnect = false, assets = [], selected = '', returnFocus, scopeKey = '', connectionKey = '', state = 'connect';
    const ctx = () => options.context(source);
    const binding = (value) => [value.workspaceId,value.clientId,value.user?.id].join(':');
    const key = (value) => value.connection ? value.connection.id+':'+value.connection.version : '';
    const active = (generation, scope) => dialog.open && generation === ticket && binding(ctx()) === scope && ctx().ready;
    function feedback(message = '') { $('#connector-feedback').textContent = message; $('#connector-feedback').hidden = !message; }
    function close() {
      if (busy && state !== 'discover') return;
      ticket += 1; busy = false; assets = []; selected = ''; choosing = false; dialog.close();
      if (returnFocus?.isConnected) returnFocus.focus({preventScroll:true});
    }
    function controls() {
      $('#connector-primary').disabled = busy || state === 'assets' && !selected;
      $('#connector-close').disabled = $('#connector-later').disabled = busy && state !== 'discover';
      dialog.querySelector('.cc-body').setAttribute('aria-busy',String(busy));
      dialog.querySelectorAll('input,select,[data-cc-action]').forEach((item) => { item.disabled = busy; });
      if (busy) $('#connector-primary').textContent = state === 'discover' ? 'Đang tải tài khoản…' : 'Đang xử lý…';
    }
    function action(label, fn) {
      const button = el('button',label,'cc-text-button'); button.type = 'button'; button.dataset.ccAction = 'true'; button.addEventListener('click',fn); return button;
    }
    async function run(fn, failure = 'Chưa thể hoàn tất. Vui lòng thử lại.') {
      if (busy) return;
      const generation = ticket, scope = scopeKey; busy = true; feedback(); controls();
      try { await fn(() => active(generation,scope)); }
      catch (error) { if (active(generation,scope)) { if (state === 'discover') state = 'choose'; feedback(error.message || failure); } }
      finally { if (active(generation,scope)) { busy = false; render(); controls(); } }
    }
    function render() {
      const value = ctx(), connection = value.connection, box = $('#connector-content');
      if (!dialog.open) return;
      const nextScope = binding(value), nextKey = key(value);
      if (scopeKey && scopeKey !== nextScope) { busy = false; close(); options.notify('Phạm vi làm việc đã thay đổi. Hãy mở lại kết nối.'); return; }
      if (connectionKey !== nextKey) { ticket += 1; busy = false; assets = []; selected = ''; choosing = false; }
      scopeKey = nextScope; connectionKey = nextKey;
      $('#connector-brand').textContent = value.platform.name;
      $('#connector-title').textContent = 'Kết nối '+value.platform.name;
      $('#connector-icon').textContent = value.platform.icon;
      $('#connector-icon').className = 'material-symbols-outlined ig-provider ig-'+value.platform.color;
      $('#connector-context').textContent = value.workspaceName+(value.clientName ? ' / '+value.clientName : '');
      $('#connector-report').hidden = true; $('#connector-primary').hidden = false;
      $('#connector-description').textContent = '';
      $('#connector-later').textContent = 'Để sau';
      if (!value.ready) state = 'loading';
      else if (!value.clientId) state = 'client';
      else if (!value.canManage) state = 'viewer';
      else if (!value.platform.can_connect) state = 'unavailable';
      else if (forceConnect || !connection || ['disconnected','expired','pending'].includes(connection.state)) state = 'connect';
      else if (choosing || !connection.asset_id) state = assets.length ? 'assets' : state === 'discover' ? 'discover' : 'choose';
      else state = 'done';
      const step = ['assets','choose','discover'].includes(state) ? 2 : state === 'done' ? 3 : 1;
      dialog.querySelectorAll('[data-connector-step]').forEach((item) => { item.dataset.active = String(Number(item.dataset.connectorStep) === step); item.setAttribute('aria-current',Number(item.dataset.connectorStep) === step ? 'step' : 'false'); });
      box.replaceChildren();
      let title = '', description = '', label = 'Đóng';
      if (state === 'loading') { title = 'Đang kiểm tra kết nối…'; label = 'Đang tải…'; }
      if (state === 'client') {
        title = 'Kết nối cho '+value.scopeLabel.toLowerCase()+' nào?';
        const select = el('select',''); select.id = 'connector-client'; select.setAttribute('aria-label',value.scopeLabel);
        select.append(new Option('Chọn '+value.scopeLabel.toLowerCase(),''),...value.clients.map((item) => new Option(item.name,item.id)));
        box.append(select); label = 'Tiếp tục';
        description = value.clients.length ? 'Dữ liệu sẽ thuộc phạm vi bạn chọn.' : 'Thêm '+value.scopeLabel.toLowerCase()+' tại Tổng quan trước khi kết nối.';
      }
      if (state === 'viewer') { title = 'Bạn đang có quyền xem'; description = 'Chủ sở hữu hoặc quản trị viên có thể quản lý kết nối này.'; }
      if (state === 'unavailable') { title = 'Kết nối đang được chuẩn bị'; description = 'Vio đang hoàn tất thiết lập cho nền tảng này. Bạn có thể sử dụng các kết nối đã sẵn sàng.'; }
      if (state === 'connect') {
        title = 'Đăng nhập bằng tài khoản quản lý'; label = 'Tiếp tục với '+providers[source];
        description = 'Bạn sẽ chuyển đến '+providers[source]+' để đăng nhập và chọn quyền truy cập.';
        if (source === 'instagram') box.append(el('p','Sử dụng Facebook quản lý Page đã liên kết tài khoản Instagram chuyên nghiệp.','cc-tip'));
        box.append(el('p','Vio không nhận hoặc lưu mật khẩu '+providers[source]+'.','cc-trust'));
      }
      if (state === 'choose' || state === 'discover') { title = 'Chọn '+assetNames[source]+' của bạn'; label = 'Tải danh sách tài khoản'; description = 'Chỉ hiển thị các tài khoản bạn vừa cấp quyền.'; }
      if (state === 'assets') {
        title = 'Chọn '+assetNames[source]; label = 'Kết nối & đồng bộ';
        const search = el('input',''); search.type = 'search'; search.placeholder = 'Tìm theo tên hoặc mã…'; search.setAttribute('aria-label','Tìm tài khoản');
        const list = el('div','','cc-assets'), count = el('p','','cc-count'); list.setAttribute('role','radiogroup'); list.setAttribute('aria-label','Tài khoản được cấp quyền');
        const draw = () => {
          const found = assets.filter((item) => fold(item.name+' '+item.id).includes(fold(search.value)));
          const visible = found.slice(0,50);
          count.textContent = found.length ? `${visible.length} / ${found.length} tài khoản` : 'Không có kết quả phù hợp';
          list.replaceChildren(...visible.map((item) => {
            const row = el('label','','cc-asset'), input = el('input',''); input.type = 'radio'; input.name = 'connector-asset'; input.value = item.id; input.checked = selected === item.id;
            const text = el('span',''); text.append(el('strong',item.name),el('small',item.id+(item.currency ? ' · '+item.currency : '')));
            input.addEventListener('change',() => { selected = item.id; controls(); }); row.append(input,text); return row;
          }));
        };
        search.addEventListener('input',draw); draw(); box.append(search,count,list);
        description = 'Vio sẽ tự đồng bộ 30 ngày đã kết thúc sau khi bạn xác nhận.';
      }
      if (state === 'done') {
        const failed = connection.state === 'error', syncing = connection.state === 'syncing';
        title = failed ? 'Cần thử đồng bộ lại' : syncing ? 'Đang đồng bộ dữ liệu' : 'Kết nối đã sẵn sàng';
        box.append(el('span',failed ? 'info' : syncing ? 'sync' : 'check_circle','material-symbols-outlined cc-result-icon'));
        box.append(el('strong',connection.asset_name || value.platform.name,'cc-result-name'));
        description = failed ? 'Kết nối được giữ nguyên. Hãy thử lại sau ít phút.' : syncing ? 'Bạn có thể đóng cửa sổ này và tiếp tục làm việc.' : 'Dữ liệu đã lưu được dùng để tạo KPI, biểu đồ và báo cáo.';
        label = syncing ? 'Đóng' : 'Đồng bộ lại';
        if (connection.synced_at) { $('#connector-report').hidden = false; $('#connector-report').href = '/workspace/reports/data?source='+encodeURIComponent(source); $('#connector-primary').hidden = true; }
        const actions = el('div','','cc-management');
        actions.append(action('Đổi tài khoản',() => { choosing = true; assets = []; selected = ''; render(); discover(); }),
          action('Tùy chọn đồng bộ',() => { close(); options.manage('sync',connection); }),
          action('Ngắt kết nối',() => { close(); options.manage('disconnect',connection); }));
        box.append(actions); $('#connector-later').textContent = 'Đóng';
      }
      if (['choose','assets'].includes(state)) {
        box.append(action('Đăng nhập tài khoản khác',() => {
          if (busy) return;
          ticket += 1; assets = []; selected = ''; forceConnect = true; feedback(); render();
        }));
      }
      box.prepend(el('h3',title)); $('#connector-description').textContent = description; $('#connector-primary').textContent = label; controls();
    }
    function discover() {
      const value = ctx(), connection = value.connection; if (!connection) return;
      state = 'discover'; render();
      run(async (valid) => {
        const result = await options.request(`workspaces/${value.workspaceId}/connections/${connection.id}/discover`,{client_id:value.clientId,version:connection.version});
        if (!valid()) return;
        if (result.connection_id !== connection.id || result.workspace_id !== value.workspaceId || result.client_id !== value.clientId || result.version !== connection.version) throw new Error('Phạm vi kết nối đã thay đổi. Hãy mở lại.');
        if (!Array.isArray(result.assets) || result.assets.some((item) => typeof item.id !== 'string' || typeof item.name !== 'string')) throw new Error('Danh sách tài khoản chưa hợp lệ. Hãy thử lại.');
        assets = result.assets; selected = assets.some((item) => item.id === connection.asset_external_id) ? connection.asset_external_id : assets.length === 1 ? assets[0].id : '';
        busy = false; state = assets.length ? 'assets' : 'choose'; render();
        if (!assets.length) feedback('Chưa tìm thấy '+assetNames[source]+'. Kiểm tra đúng tài khoản đăng nhập và quyền quản lý trên '+providers[source]+'.');
      });
    }
    $('#connector-primary').addEventListener('click',() => {
      const value = ctx(), connection = value.connection;
      if (state === 'client') { const id = $('#connector-client')?.value; if (value.clients.some((item) => item.id === id)) run(async () => { scopeKey = ''; await options.selectClient(id); busy = false; render(); }); return; }
      if (state === 'choose') { discover(); return; }
      if (state === 'connect') {
        run(async (valid) => {
          const result = await options.request(`workspaces/${value.workspaceId}/providers/${source}/start`,{client_id:value.clientId});
          if (!valid()) return;
          const url = new URL(result.authorization_url);
          const ok = providers[source] === 'Google' ? url.hostname === 'accounts.google.com' && url.pathname === '/o/oauth2/v2/auth'
            : providers[source] === 'TikTok' ? url.hostname === 'business-api.tiktok.com' && /^\/portal\/auth\/?$/.test(url.pathname)
              : url.hostname === 'www.facebook.com' && /^\/v\d+\.\d+\/dialog\/oauth$/.test(url.pathname);
          if (!ok || url.protocol !== 'https:' || url.username || url.password || url.hash || url.port) throw new Error('Địa chỉ cấp quyền chưa hợp lệ.');
          location.assign(url.href);
        }); return;
      }
      if (state === 'assets' && connection && assets.some((item) => item.id === selected)) {
        run(async (valid) => {
          await options.request(`workspaces/${value.workspaceId}/connections/${connection.id}/select`,{client_id:value.clientId,version:connection.version,external_id:selected});
          if (!valid()) return;
          choosing = false; await options.refresh(); if (dialog.open) { busy = false; render(); }
        }); return;
      }
      if (state === 'done' && connection.state !== 'syncing') { close(); options.manage('sync',connection); return; }
      close();
    });
    $('#connector-close').addEventListener('click',close); $('#connector-later').addEventListener('click',close);
    dialog.addEventListener('cancel',(event) => { event.preventDefault(); close(); });
    return {update:render, open(id, error) {
      if (!Object.hasOwn(providers,id)) return false;
      source = id; ticket += 1; busy = false; choosing = false; forceConnect = false; assets = []; selected = ''; scopeKey = ''; connectionKey = ''; state = 'connect';
      returnFocus = document.activeElement; feedback(error || ''); if (!dialog.open) dialog.showModal(); render();
      if (state === 'choose') discover(); return true;
    }};
  }
  window.VioConnectorConnect = {create};
})();
