/* Workspace overview and a versioned, account-scoped product tour. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const details = JSON.parse($('#overview-data').textContent);
  const dialog = $('#product-tour');
  const tooltip = $('#tour-tooltip');
  let session;
  let progress = details.tour;
  let busy = false;
  let returnFocus;
  const steps = [
    ['workspace-switch', 'Không gian làm việc của bạn', 'Đây là Workspace đang sử dụng. Bấm vào đây khi muốn chọn Workspace khác hoặc tạo thêm một không gian làm việc.'],
    ['client-card', 'Khách hàng & thương hiệu', 'Các khách hàng đã tạo xuất hiện tại đây. Sau này, mỗi khách hàng sẽ có nguồn dữ liệu và báo cáo riêng trong Workspace.'],
    ['integration-card', 'Kết nối nguồn dữ liệu', 'Bước tiếp theo là tự cấp quyền Google, Meta hoặc nền tảng khác và chọn tài khoản của khách hàng. Chức năng kết nối đang được triển khai.'],
    ['nav-dashboard', 'Dashboard Marketing', 'Khu vực theo dõi các chỉ số từ nguồn đã kết nối. Dashboard sẽ khả dụng sau khi chức năng kết nối và đồng bộ được hoàn thiện.'],
    ['nav-channels', 'Phân tích từng kênh', 'Đây sẽ là nơi xem báo cáo chi tiết của SEO, Facebook, YouTube và các kênh được hỗ trợ. Phần báo cáo cũ sẽ được đưa vào khu vực này.'],
    ['nav-reports', 'Tạo và chia sẻ báo cáo', 'Khu vực dành cho mẫu báo cáo, kỳ báo cáo và chia sẻ kết quả. Chức năng này đang được triển khai cho Workspace.'],
    ['nav-members', 'Cùng làm việc với đội ngũ', 'Mục này đưa bạn về phần thiết lập Workspace. Chủ sở hữu hoặc quản trị có email đã xác minh có thể tạo mã mời và phân quyền cho thành viên.'],
    ['nav-settings', 'Thông tin & cài đặt Workspace', 'Xem lại tên, website, tiền tệ và múi giờ của Workspace. Bạn đã biết các khu vực chính! Có thể mở lại hướng dẫn bất cứ lúc nào.'],
  ];
  const features = {
    integrations: ['Kết nối nền tảng', 'Chức năng kết nối đang được triển khai. Khi sẵn sàng, bạn sẽ tự cấp quyền và chọn tài khoản nguồn cho từng khách hàng. Hiện chưa có nền tảng nào được kết nối qua Workspace.'],
    dashboard: ['Dashboard Marketing', 'Dashboard của Workspace sẽ hiển thị các chỉ số sau khi bạn kết nối nguồn và dữ liệu được đồng bộ. Chức năng này chưa khả dụng.'],
    channels: ['Phân tích kênh', 'Báo cáo theo từng kênh sẽ được kết nối với khách hàng và quyền truy cập của Workspace. Chức năng này chưa khả dụng.'],
    reports: ['Báo cáo', 'Tạo báo cáo, chọn kỳ và chia sẻ kết quả sẽ được bổ sung cho Workspace. Hiện chưa có báo cáo nào trong luồng này.'],
    settings: ['Thông tin Workspace', 'Đây là thông tin đã lưu khi tạo Workspace. Chức năng chỉnh sửa sẽ được bổ sung trong trang Cài đặt.'],
  };
  function status(message) {
    $('#overview-status').textContent = message;
    $('#overview-status').hidden = !message;
  }
  async function api(path, data) {
    const options = {credentials: 'same-origin', cache: 'no-store', headers: {Accept: 'application/json'}};
    if (data !== undefined) {
      options.method = 'POST';
      options.headers['Content-Type'] = 'application/json';
      options.headers['X-CSRF-Token'] = session?.csrf || '';
      options.body = JSON.stringify(data);
    }
    const response = await fetch('/api/customer/' + path, options);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Không thể lưu tiến độ. Vui lòng thử lại.');
    return payload;
  }
  function summary() {
    const completed = progress.status === 'completed';
    $('#tour-summary').textContent = completed ? 'Đã xem xong 8 bước hướng dẫn' : progress.status === 'new' ? 'Hướng dẫn làm quen · 8 bước' : `Tiếp tục hướng dẫn từ bước ${progress.step + 1}/8`;
    document.querySelector('.ov-welcome [data-start-tour]').textContent = completed ? 'Xem lại hướng dẫn' : progress.status === 'new' ? 'Bắt đầu hướng dẫn →' : 'Tiếp tục hướng dẫn →';
  }
  function position() {
    if (!dialog.open) return;
    const target = document.getElementById(steps[progress.step][0]);
    const rect = target.getBoundingClientRect();
    const pad = 4;
    const highlight = $('#tour-highlight');
    Object.assign(highlight.style, {left: `${Math.max(3, rect.left - pad)}px`, top: `${Math.max(3, rect.top - pad)}px`, width: `${Math.min(innerWidth - 6, rect.width + pad * 2)}px`, height: `${Math.min(innerHeight - 6, rect.height + pad * 2)}px`});
    const box = tooltip.getBoundingClientRect();
    let left = rect.right + 20;
    let top = rect.top;
    if (innerWidth <= 700) {
      left = (innerWidth - box.width) / 2;
      top = innerHeight - box.height - 12;
    } else if (left + box.width > innerWidth - 16) {
      left = rect.left;
      top = rect.bottom + 20;
      if (top + box.height > innerHeight - 16) top = rect.top - box.height - 20;
    }
    Object.assign(tooltip.style, {left: `${Math.max(12, Math.min(left, innerWidth - box.width - 12))}px`, top: `${Math.max(12, Math.min(top, innerHeight - box.height - 12))}px`});
  }
  function render() {
    const [id, title, description] = steps[progress.step];
    $('#tour-title').textContent = title;
    $('#tour-description').textContent = description;
    $('#tour-counter').textContent = `BƯỚC ${progress.step + 1} / 8`;
    $('#tour-progress').style.width = `${(progress.step + 1) * 12.5}%`;
    $('#tour-highlight').setAttribute('aria-label', `Đã xem: ${title}. ${progress.step === 7 ? 'Hoàn tất hướng dẫn' : 'Đến bước tiếp theo'}`);
    $('#tour-back').hidden = progress.step === 0;
    $('#tour-next').textContent = progress.step === 7 ? 'Hoàn tất' : 'Tiếp tục';
    $('#tour-error').hidden = true;
    const target = document.getElementById(id);
    target.scrollIntoView({block: innerWidth <= 700 ? 'start' : 'center', inline: 'center', behavior: 'instant'});
    position();
    $('#tour-next').focus({preventScroll: true});
    summary();
  }
  async function save(step, state) {
    if (!session) throw new Error('Đang kết nối tài khoản. Vui lòng thử lại.');
    const result = await api(`workspaces/${details.workspace.id}/tour`, {version: 1, step, status: state});
    progress = result.tour;
    summary();
  }
  async function operation(task) {
    if (busy) return;
    busy = true;
    dialog.querySelectorAll('button').forEach((button) => { button.disabled = true; });
    try { await task(); }
    catch (error) {
      const message = error.message || 'Mất kết nối. Vui lòng thử lại.';
      if (dialog.open) { $('#tour-error').textContent = message; $('#tour-error').hidden = false; position(); }
      else status(message);
    } finally {
      busy = false;
      dialog.querySelectorAll('button').forEach((button) => { button.disabled = false; });
      if (dialog.open) $('#tour-next').focus({preventScroll: true});
    }
  }
  function close() {
    dialog.close();
    returnFocus?.focus({preventScroll: true});
    summary();
  }
  function start() {
    return operation(async () => {
      status('');
      returnFocus = document.activeElement;
      await save(progress.status === 'completed' ? 0 : progress.step, 'active');
      dialog.showModal();
      render();
    });
  }
  function next() {
    return operation(async () => {
      if (progress.step === 7) { await save(7, 'completed'); close(); }
      else { await save(progress.step + 1, 'active'); render(); }
    });
  }
  function dismiss() { return operation(async () => { await save(progress.step, 'dismissed'); close(); }); }
  document.querySelectorAll('[data-start-tour]').forEach((button) => button.addEventListener('click', start));
  $('#tour-next').addEventListener('click', next);
  $('#tour-highlight').addEventListener('click', next);
  $('#tour-back').addEventListener('click', () => operation(async () => { await save(Math.max(0, progress.step - 1), 'active'); render(); }));
  $('#tour-dismiss').addEventListener('click', dismiss);
  $('#tour-skip').addEventListener('click', dismiss);
  dialog.addEventListener('cancel', (event) => { event.preventDefault(); dismiss(); });
  window.addEventListener('resize', position);
  window.addEventListener('scroll', position, true);
  window.addEventListener('pageshow', (event) => { if (event.persisted) location.reload(); });
  document.querySelectorAll('[data-feature]').forEach((button) => button.addEventListener('click', () => {
    const [title, description] = features[button.dataset.feature];
    $('#feature-title').textContent = title;
    $('#feature-description').textContent = description;
    $('#workspace-settings').hidden = button.dataset.feature !== 'settings';
    $('#feature-dialog').showModal();
  }));
  $('#overview-logout').addEventListener('click', () => operation(async () => { await api('auth/logout', {}); location.assign('/workspace/login'); }));
  async function init() {
    summary();
    try {
      session = await api('session');
      if (!session.user) { location.replace('/workspace/login'); return; }
      if (!session.workspace || session.workspace.id !== details.workspace.id) { location.replace('/workspace'); return; }
      if (['new', 'active'].includes(progress.status)) await start();
    } catch (error) { status(error.message || 'Chưa thể tải hướng dẫn. Vui lòng thử lại.'); }
  }
  init();
})();
