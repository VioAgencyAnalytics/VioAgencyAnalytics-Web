/* Shared quick navigation; all customer metadata comes from scoped BFF APIs. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const initial = JSON.parse($('#overview-data, #integrations-data, #marketing-data, #workspace-page-data, #library-data').textContent);
  const workspaceId = initial.workspace.id;
  const dialog = $('#workspace-search-dialog');
  const input = $('#workspace-search-input');
  const results = $('#workspace-search-results');
  let clients = [], platforms = [], session;
  let loading = false, selecting = false, issue = '', generation = 0;
  const fold = (value) => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[đĐ]/g, 'd').toLowerCase();
  const pages = [
    {name: 'Tổng quan Workspace', note: 'Khách hàng và tiến độ thiết lập', icon: 'space_dashboard', href: '/workspace'},
    {name: 'Kết nối nền tảng', note: 'Khám phá các nguồn dữ liệu Marketing', icon: 'hub', href: '/workspace/integrations'},
    {name: 'Dashboard Marketing', note: 'KPI, xu hướng và hiệu suất đa kênh', icon: 'monitoring', href: '/workspace/dashboard'},
    {name: 'Phân tích kênh', note: '9 kênh Marketing và khung phân tích chuyên sâu', icon: 'query_stats', href: '/workspace/channels'},
    {name: 'Trung tâm Báo cáo', note: 'Bố cục báo cáo đa kênh và báo cáo đã lưu', icon: 'description', href: '/workspace/reports'},
    {name: 'Thành viên', note: 'Đội ngũ, lời mời và quyền truy cập Workspace', icon: 'group', href: '/workspace/members'},
    {name: 'Cài đặt Workspace', note: 'Thông tin, khu vực và tùy chọn hiển thị', icon: 'settings', href: '/workspace/settings'},
    {name: 'Quản lý khách hàng', note: 'Thêm, sửa và chọn khách hàng / thương hiệu', icon: 'business_center', href: '/workspace#client-card'},
    {name: 'Tạo / tham gia Workspace', note: 'Chọn không gian làm việc hoặc dùng mã mời', icon: 'domain_add', href: '/workspace/onboarding'},
    {name: 'Mời thành viên', note: 'Tạo mã mời theo quyền của bạn', icon: 'group_add', href: '/workspace/members#invite'},
  ];
  function element(tag, text, className) {
    const item = document.createElement(tag);
    item.textContent = text;
    if (className) item.className = className;
    return item;
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
      throw new Error(payload.error || 'Chưa thể tải dữ liệu tìm kiếm.');
    }
    return payload;
  }
  function result(item) {
    const row = element(item.href ? 'a' : 'button', '', 'wh-result');
    if (item.href) row.href = item.href;
    else { row.type = 'button'; row.disabled = selecting; row.addEventListener('click', () => selectClient(item.id)); }
    const icon = element('span', item.icon, 'material-symbols-outlined'); icon.setAttribute('aria-hidden', 'true');
    const content = element('div', ''); content.append(element('strong', item.name), element('small', item.note));
    row.append(icon, content);
    return row;
  }
  function render() {
    const query = fold(input.value.trim());
    const groups = [
      ['ĐIỀU HƯỚNG', pages],
      ['KHÁCH HÀNG / THƯƠNG HIỆU', clients.map((client) => ({id: client.id, name: client.name,
        note: 'Chọn khách hàng và mở Tổng quan' + (client.website ? ' · ' + client.website : ''), icon: 'business_center'}))],
      ['NỀN TẢNG', platforms.map((platform) => ({name: platform.name, note: platform.status_label,
        keywords: platform.id + ' ' + platform.subtitle,
        icon: platform.icon, href: '/workspace/integrations?platform=' + encodeURIComponent(platform.id)}))],
    ];
    const nodes = [];
    let total = 0;
    for (const [title, items] of groups) {
      const matches = items.filter((item) => fold(item.name + ' ' + item.note + ' ' + (item.keywords || '')).includes(query));
      total += matches.length;
      if (matches.length) {
        nodes.push(element('h3', title));
        nodes.push(...matches.slice(0, 8).map(result));
        if (matches.length > 8) nodes.push(element('p', `Còn ${matches.length - 8} kết quả. Nhập tên cụ thể hơn.`, 'wh-more-results'));
      }
    }
    results.replaceChildren(...nodes);
    $('#workspace-search-status').textContent = selecting ? 'Đang chọn khách hàng…' : loading ? 'Đang tải dữ liệu trong Workspace…'
      : issue || (total ? `${total} kết quả trong Workspace này` : 'Không tìm thấy kết quả. Thử từ khóa khác.');
    results.setAttribute('aria-busy', String(loading || selecting));
  }
  async function selectClient(id) {
    if (selecting || loading) return;
    selecting = true; issue = ''; render();
    try {
      await api(`workspaces/${workspaceId}/clients/${id}/select`, {});
      location.assign('/workspace');
    } catch (error) { selecting = false; issue = error.message; render(); }
  }
  async function open() {
    if (document.querySelector('dialog[open]')) return;
    const ticket = ++generation;
    clients = []; platforms = []; issue = ''; input.value = ''; loading = true;
    render(); dialog.showModal(); input.focus();
    try {
      session = await api('session');
      if (!session.user) { location.replace('/workspace/login'); return; }
      if (session.workspace?.id !== workspaceId) { location.replace('/workspace'); return; }
      const data = await Promise.allSettled([api(`workspaces/${workspaceId}`), api(`workspaces/${workspaceId}/integrations`)]);
      if (ticket !== generation) return;
      if (data[0].status === 'fulfilled') clients = data[0].value.clients;
      if (data[1].status === 'fulfilled') platforms = data[1].value.platforms;
      if (data.some((item) => item.status === 'rejected')) issue = 'Chưa tải đủ dữ liệu. Bạn vẫn có thể dùng các lối tắt hoặc đóng và mở lại tìm kiếm.';
    } catch (error) { if (ticket === generation) issue = error.message; }
    finally { if (ticket === generation) { loading = false; render(); } }
  }
  $('#workspace-search-open').addEventListener('click', open);
  $('#workspace-search-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => { generation += 1; $('#workspace-search-open').focus(); });
  input.addEventListener('input', render);
  dialog.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && document.activeElement === input && !loading && !selecting) {
      const first = results.querySelector('a, button:not([disabled])');
      if (first) { event.preventDefault(); first.click(); }
      return;
    }
    if (!['ArrowDown', 'ArrowUp'].includes(event.key)) return;
    const rows = [...results.querySelectorAll('a, button:not([disabled])')];
    if (!rows.length) return;
    event.preventDefault();
    const index = rows.indexOf(document.activeElement);
    const next = event.key === 'ArrowDown' ? (index + 1) % rows.length : index <= 0 ? rows.length - 1 : index - 1;
    rows[next].focus();
  });
  document.addEventListener('keydown', (event) => {
    if (!(event.ctrlKey || event.metaKey) || event.altKey || event.key.toLowerCase() !== 'k') return;
    if (document.querySelector('dialog[open]') && !dialog.open) return;
    event.preventDefault();
    if (dialog.open) { input.focus(); input.select(); } else open();
  });
  function help() {
    const guide = $('[data-start-tour]') || $('#integration-guide') || $('#marketing-guide') || $('#workspace-page-guide') || $('#library-guide');
    if (guide && !guide.disabled) guide.click();
  }
  $('#workspace-help').addEventListener('click', help);
  document.querySelectorAll('[data-shell-guide]').forEach((button) => button.addEventListener('click', help));
  const mobileNavigation = matchMedia('(max-width:700px)');
  const fitNavigation = () => {
    const menu = $('#nav-channels')?.closest('details'); if (menu) menu.open = !mobileNavigation.matches;
    requestAnimationFrame(() => {
      const nav = $('.ov-nav'), active = nav?.querySelector('[aria-current=page]');
      if (!active) return;
      const item = active.getBoundingClientRect(), viewport = nav.getBoundingClientRect();
      if (mobileNavigation.matches) {
        nav.scrollLeft += item.left - viewport.left - (nav.clientWidth - active.clientWidth) / 2;
      } else {
        nav.scrollLeft = 0;
        if (item.bottom > viewport.bottom) nav.scrollTop += item.bottom - viewport.bottom + 8;
        else if (item.top < viewport.top) nav.scrollTop += item.top - viewport.top - 8;
      }
    });
  };
  mobileNavigation.addEventListener('change', fitNavigation); fitNavigation();
  if (/Mac|iPhone|iPad/.test(navigator.platform)) $('#workspace-search-open kbd').textContent = '⌘ K';
})();
