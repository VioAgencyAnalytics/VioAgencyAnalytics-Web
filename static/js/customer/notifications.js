/* Scoped activity inbox for the current Workspace customer. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const root = $('workspace-notifications');
  if (!root) return;
  const {workspaceId, accountId} = root.dataset;
  if (!/^[a-f0-9]{32}$/.test(workspaceId || '')) return;

  const bell = $('workspace-bell'), badge = $('workspace-bell-count'), inbox = $('workspace-inbox');
  const list = $('workspace-inbox-items'), empty = $('workspace-inbox-empty'), status = $('workspace-inbox-status');
  const readAll = $('workspace-inbox-read'), retry = $('workspace-inbox-retry');
  const filters = [...inbox.querySelectorAll('[data-wn-filter]')];
  const toast = $('workspace-notice-toast');
  const endpoint = `/api/customer/workspaces/${workspaceId}/notifications`;
  const labels = {connected: 'link', choose_asset: 'touch_app', reconnect: 'link_off', sync_done: 'sync', sync_failed: 'sync_problem',
    report_created: 'description', notes_finalized: 'verified', pdf_saved: 'picture_as_pdf', seo_import: 'upload_file',
    seo_sync_done: 'article', seo_sync_failed: 'error'};
  const time = new Intl.DateTimeFormat('vi-VN', {timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit'});
  const interval = 12000;
  let clientId = root.dataset.clientId, clientName = root.dataset.clientName;
  let filter = 'all', items = [], announced, issue = '', scopeChanged = false;
  let timer, toastTimer, controller, generation = 0, loaded = false, queued = false, saving = false, csrf;

  function element(tag, value = '', className = '') {
    const node = document.createElement(tag);
    node.className = className;
    node.textContent = value;
    return node;
  }

  function readShown() {
    return items.filter(item => filter === 'unread' ? !item.read : filter === 'attention' ? item.attention : true);
  }

  function row(item) {
    const node = element('li', '', 'wn-item');
    node.dataset.noticeId = item.id;
    node.dataset.unread = String(!item.read);
    node.dataset.attention = String(item.attention);
    const icon = item.source && window.VioPlatformBrand?.known(item.source)
      ? window.VioPlatformBrand.logo(item.source, 'wn-icon') : element('span', labels[item.kind], 'wn-icon material-symbols-outlined');
    icon.setAttribute('aria-hidden', 'true');
    const content = element('div');
    content.append(element('strong', item.title));
    if (item.detail) content.append(element('p', item.detail));
    const meta = element('div', '', 'wn-item-meta');
    if (item.at) meta.append(element('small', time.format(new Date(item.at))));
    const link = element('a', item.action);
    link.href = item.href;
    if (!item.read) link.addEventListener('click', async event => {
      if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const ticket = generation;
      await mark([item.id]);
      if (ticket === generation) location.assign(item.href);
    });
    meta.append(link);
    content.append(meta);
    node.append(icon, content);
    if (!item.read) {
      const dot = element('button', '', 'wn-mark');
      dot.type = 'button';
      dot.title = 'Đánh dấu đã đọc';
      dot.setAttribute('aria-label', `Đánh dấu đã đọc thông báo ${item.title}`);
      dot.disabled = saving;
      dot.append(element('span'));
      dot.addEventListener('click', () => mark([item.id]));
      node.append(dot);
    }
    return node;
  }

  function render() {
    const unread = items.filter(item => !item.read).length;
    badge.hidden = unread === 0;
    badge.textContent = String(unread);
    bell.setAttribute('aria-label', unread ? `Thông báo, ${unread} chưa đọc` : 'Thông báo');
    $('workspace-inbox-client').textContent = clientName || 'Chưa chọn khách hàng';
    readAll.disabled = !unread || saving;
    status.hidden = !issue || !items.length;
    status.textContent = issue;
    filters.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.wnFilter === filter)));
    const visible = readShown();
    const focused = document.activeElement;
    const focusedId = focused?.closest?.('[data-notice-id]')?.dataset.noticeId;
    const focusedTag = focused?.tagName;
    list.replaceChildren(...visible.map(row));
    if (focusedId) {
      const target = list.querySelector(`[data-notice-id="${focusedId}"] ${focusedTag.toLowerCase()}`);
      (target && !target.disabled ? target : filters.find(button => button.dataset.wnFilter === filter)).focus({preventScroll: true});
    }
    empty.hidden = visible.length > 0;
    empty.querySelector('p').textContent = issue || (!clientId ? 'Chọn khách hàng để xem hoạt động.' : !loaded ? 'Đang tải thông báo…'
      : filter === 'unread' ? 'Bạn đã đọc hết thông báo.' : filter === 'attention' ? 'Hiện chưa có việc cần xử lý.' : 'Chưa có hoạt động nào để hiển thị.');
    retry.hidden = !issue || !clientId;
    retry.textContent = scopeChanged ? 'Tải lại trang' : 'Thử lại';
  }

  function setOpen(open) {
    inbox.hidden = !open;
    bell.setAttribute('aria-expanded', String(open));
    if (open) update();
  }

  function closeToast() {
    clearTimeout(toastTimer);
    if (toast.hidePopover && toast.matches(':popover-open')) toast.hidePopover();
    toast.hidden = true;
  }

  function showToast(items) {
    const top = items.find(item => item.attention) || items[0];
    const warning = top.attention || top.kind.endsWith('_failed');
    toast.dataset.attention = String(warning);
    toast.querySelector('.wn-toast-icon').textContent = warning ? 'error' : 'check_circle';
    toast.querySelector('strong').textContent = top.title;
    toast.querySelector('p').textContent = items.length > 1 ? `Còn ${items.length - 1} cập nhật mới trong chuông.` : top.detail;
    toast.hidden = false;
    if (toast.showPopover) {
      if (!toast.matches(':popover-open')) toast.showPopover();
    } else toast.removeAttribute('popover');
    document.dispatchEvent(new Event('vio:notification-arrived'));
    clearTimeout(toastTimer);
    toastTimer = setTimeout(closeToast, warning ? 8000 : 5400);
  }

  function announce() {
    const key = `vio-notice-seen/${accountId}/${workspaceId}/${clientId}`;
    if (!announced) {
      try { announced = new Set(JSON.parse(sessionStorage.getItem(key) || '[]')); }
      catch (_) { announced = new Set(); }
    }
    const recent = items.filter(item => !item.read && !announced.has(item.id)
      && (loaded || item.at && Date.now() - new Date(item.at).valueOf() <= 120000));
    const kept = [...new Set([...items.map(item => item.id), ...announced])].slice(0, 110);
    announced = new Set(kept);
    try { sessionStorage.setItem(key, JSON.stringify(kept)); } catch (_) { /* Optional toast deduplication. */ }
    if (recent.length && !document.hidden) showToast(recent);
  }

  async function update() {
    clearTimeout(timer);
    if (!clientId || document.hidden || scopeChanged) return;
    if (controller || saving) { queued = true; return; }
    const ticket = generation;
    const active = new AbortController();
    controller = active;
    try {
      const response = await fetch(endpoint + '?' + new URLSearchParams({client_id: clientId}), {cache: 'no-store', signal: active.signal});
      if (ticket !== generation || active.signal.aborted) return;
      if ([401, 403, 404, 409].includes(response.status)) {
        items = [];
        scopeChanged = true;
        issue = response.status === 401 ? 'Phiên đăng nhập đã hết hạn. Tải lại trang để đăng nhập.' : 'Phạm vi đã thay đổi. Tải lại trang để xem thông báo.';
        closeToast();
        render();
        return;
      }
      if (!response.ok) throw new Error();
      const data = await response.json();
      if (ticket !== generation || active.signal.aborted) return;
      if (data.scope?.workspace_id !== workspaceId || data.scope?.client_id !== clientId || !Array.isArray(data.items)) throw new Error();
      const changed = !loaded || issue || JSON.stringify(items) !== JSON.stringify(data.items);
      items = data.items;
      issue = '';
      announce();
      loaded = true;
      if (changed) render();
    } catch (_) {
      if (ticket === generation && !active.signal.aborted) { issue = 'Chưa tải được thông báo. Vui lòng thử lại.'; render(); }
    } finally {
      if (controller === active) {
        controller = null;
        const runNext = queued;
        queued = false;
        if (!scopeChanged && !document.hidden) timer = setTimeout(update, runNext ? 0 : interval);
      }
    }
  }

  async function post(path, data) {
    if (!csrf) {
      const session = await fetch('/api/customer/session', {cache: 'no-store', signal: AbortSignal.timeout?.(5000)});
      if (!session.ok) throw new Error();
      csrf = (await session.json()).csrf;
      if (!csrf) throw new Error();
    }
    const response = await fetch(path, {method: 'POST', keepalive: true, signal: AbortSignal.timeout?.(5000),
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf}, body: JSON.stringify(data)});
    if (response.status === 403) csrf = null;
    if (!response.ok) throw new Error();
    return response.json();
  }

  async function mark(ids) {
    if (!ids.length || !clientId || saving) return;
    const ticket = generation;
    saving = true;
    controller?.abort();
    controller = null;
    readAll.disabled = true;
    try {
      const saved = await post(endpoint + '/read', {client_id: clientId, ids});
      if (ticket !== generation) return;
      const confirmed = new Set(saved.read_ids);
      items.forEach(item => { if (confirmed.has(item.id)) item.read = true; });
      issue = '';
    } catch (_) {
      if (ticket === generation) issue = 'Chưa đánh dấu được thông báo. Vui lòng thử lại.';
    } finally {
      if (ticket === generation) { saving = false; render(); update(); }
    }
  }

  function setClient(next) {
    const id = next?.id || '';
    if (id !== clientId || scopeChanged) {
      generation += 1;
      controller?.abort();
      controller = null;
      clearTimeout(timer);
      closeToast();
      clientId = id; clientName = next?.name || '';
      items = []; loaded = false; announced = null; issue = ''; scopeChanged = false; saving = false; queued = false;
      render();
    }
    update();
  }

  bell.addEventListener('click', () => setOpen(inbox.hidden));
  document.addEventListener('click', event => { if (!inbox.hidden && !root.contains(event.target)) setOpen(false); });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !inbox.hidden) { setOpen(false); bell.focus(); }
  });
  filters.forEach(button => button.addEventListener('click', () => { filter = button.dataset.wnFilter; render(); }));
  readAll.addEventListener('click', () => mark(items.filter(item => !item.read).map(item => item.id)));
  retry.addEventListener('click', () => { if (scopeChanged) location.reload(); else update(); });
  toast.querySelector('button').addEventListener('click', closeToast);
  document.addEventListener('customer:scope-changing', () => setClient(null));
  document.addEventListener('customer:workspace-detail', event => {
    if (event.detail.workspace?.id === workspaceId) setClient(event.detail.selected_client);
  });
  document.addEventListener('vio:seo-loaded', update);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { clearTimeout(timer); controller?.abort(); closeToast(); }
    else update();
  });
  window.addEventListener('pagehide', () => { clearTimeout(timer); controller?.abort(); });
  window.VioNotifications = Object.freeze({update});
  render();
  update();
})();
