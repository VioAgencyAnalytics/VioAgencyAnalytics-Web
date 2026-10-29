(() => {
  'use strict';
  const W = window.VioWorkspace, $ = (selector) => document.querySelector(selector), form = $('#settings-form');
  const fields = ['name','website','country','timezone','currency','company_name','report_name','report_footer','accent_color','week_start'];
  let baseline = '';
  function values() {
    const payload = Object.fromEntries(fields.map((key) => [key, form.elements.namedItem(key).value]));
    payload.default_period = form.querySelector('[name=default_period]:checked')?.value || 'last30';
    payload.compare_previous = $('#settings-compare').checked;
    return payload;
  }
  function preview() {
    const data = values(), title = data.report_name.trim() || data.company_name.trim() || data.name.trim() || 'Báo cáo Marketing';
    $('#preview-title').textContent = title; $('#preview-footer').textContent = data.report_footer.trim() || 'Thông tin chân trang';
    $('#preview-logo').textContent = title.slice(0,1).toUpperCase(); $('#settings-logo-initial').textContent = (data.company_name.trim() || data.name.trim() || 'V').slice(0,1).toUpperCase();
    if (/^#[a-fA-F0-9]{6}$/.test(data.accent_color)) { $('#settings-preview').style.setProperty('--preview-accent', data.accent_color); $('#settings-accent-picker').value = data.accent_color; }
  }
  function render() {
    const data = W.data, profile = data.profile;
    for (const key of fields) {
      const value = Object.hasOwn(profile, key) ? profile[key] : data.workspace[key] || '';
      const field = form.elements.namedItem(key);
      if (field.tagName === 'SELECT' && ![...field.options].some((o) => o.value === value)) field.append(new Option(value, value));
      field.value = value;
    }
    form.querySelector(`[name=default_period][value="${profile.default_period}"]`).checked = true;
    $('#settings-compare').checked = profile.compare_previous;
    $('#settings-member-count').textContent = `${data.member_count} thành viên hoạt động`;
    $('#settings-email-status').textContent = W.session?.user.email_verified ? 'Email đã xác minh' : 'Email chưa xác minh';
    $('#settings-saved-at').textContent = profile.updated_at ? 'Lưu gần nhất: ' + W.date(profile.updated_at, true) : 'Chưa có thay đổi cài đặt';
    baseline = JSON.stringify(values()); W.setDirty(false); preview();
  }
  function controls() {
    const canEdit = W.ready && W.data.permissions.manage_settings;
    $('#settings-fields').disabled = W.busy || !W.ready;
    form.querySelectorAll('input,select').forEach((field) => { field.disabled = W.busy || !canEdit; });
    $('#settings-copy-id').disabled = W.busy || !W.ready;
    $('#settings-permission-note').hidden = !W.ready || canEdit;
    $('#settings-save').disabled = W.busy || !canEdit || !W.dirty;
    $('#settings-discard').disabled = W.busy || !canEdit || !W.dirty;
    $('#settings-save-bar').hidden = !canEdit || !W.dirty;
    $('#settings-save-bottom').disabled = W.busy || !canEdit || !W.dirty;
  }
  function changed() { preview(); W.setDirty(JSON.stringify(values()) !== baseline); }
  form.addEventListener('input', changed); form.addEventListener('change', changed);
  $('#settings-accent-picker').addEventListener('input', () => { $('#settings-accent').value = $('#settings-accent-picker').value.toUpperCase(); changed(); });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!W.ready || W.busy || !W.dirty || !W.data.permissions.manage_settings) return;
    const payload = {...values(),version:W.data.profile.version};
    if ((payload.currency !== W.data.workspace.currency || payload.timezone !== W.data.workspace.timezone)
        && !await W.confirm('Thay đổi tiền tệ hoặc múi giờ?', 'Tùy chọn mới được dùng khi hiển thị Dashboard. Dữ liệu nguồn và báo cáo đã phát hành không được quy đổi hoặc sửa lại.', 'Lưu cài đặt')) return;
    await W.run(async () => { const result = await W.api(W.base + '/settings', payload); W.adopt(result); W.notify('Đã lưu cài đặt Workspace. Mặc định mới sẽ áp dụng khi mở lại Tổng quan hoặc Dashboard.', 'success'); }, (error) => { if (error.code === 'settings_version') W.notify(error.message + ' Biểu mẫu hiện tại được giữ lại để bạn đối chiếu. Dùng Tải lại để xem bản đã lưu.', 'error'); });
  });
  $('#settings-discard').addEventListener('click', async () => { if (!W.busy && W.dirty && await W.confirm('Hủy các thay đổi trên biểu mẫu?', 'Khôi phục giá trị đã tải gần nhất. Các cài đặt đang được lưu trong hệ thống không thay đổi.', 'Hủy thay đổi')) { render(); W.notify('Đã hủy thay đổi trên biểu mẫu.'); } });
  $('#settings-save-bottom').addEventListener('click', () => form.requestSubmit());
  $('#settings-copy-id').addEventListener('click', () => W.copy(W.data.workspace.id));
  document.addEventListener('keydown', (event) => { if ((event.ctrlKey || event.metaKey) && !event.altKey && event.key.toLowerCase() === 's' && !document.querySelector('dialog[open]')) { event.preventDefault(); if (!$('#settings-save').disabled) form.requestSubmit(); } });
  W.mount(render, controls, () => W.info('Cài đặt Workspace', 'Chủ sở hữu hoặc quản trị viên có thể cập nhật thông tin doanh nghiệp, khu vực và tùy chọn hiển thị.\n\nLưu thay đổi hoặc bấm Ctrl+S. Nếu có người khác vừa cập nhật, hệ thống sẽ yêu cầu tải bản mới để tránh ghi đè.\n\nThông tin thương hiệu được lưu để chuẩn bị cho phần Báo cáo; bản xem trước không phải báo cáo đã phát hành. Logo, chuyển chủ sở hữu và xóa Workspace chưa được mở.'));
})();
