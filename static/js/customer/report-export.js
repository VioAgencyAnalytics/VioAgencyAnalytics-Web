(() => {
  'use strict';
  const button = document.querySelector('[data-report-pdf]');
  const reader = document.getElementById('report-note-reader');
  if (!button || !reader) return;
  const {pdf} = JSON.parse(reader.textContent);
  if (!pdf) return;
  const {endpoint, ...request} = pdf;
  const status = document.getElementById('report-export-status');
  const label = button.querySelector('[data-pdf-label]');
  const filename = (document.title.replace(/\s*\|\s*VioAgencyAnalytics.*$/, '')
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, ' ').replace(/\s+/g, ' ').trim().replace(/\.+$/, '').slice(0, 140) || 'Vio - Báo cáo') + '.pdf';

  function feedback(message, error = false) {
    status.textContent = message;
    status.dataset.error = String(error);
    status.hidden = !message;
  }

  function post(path, data, csrf, keepalive = false) {
    return fetch(path, {method: 'POST', cache: 'no-store', keepalive,
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf}, body: JSON.stringify(data)});
  }

  async function acknowledge(receipt, csrf) {
    const {client_id, form, report_id} = request;
    for (let attempt = 0; attempt < 2; attempt += 1) {
      try {
        const response = await post(endpoint + '/saved', {client_id, form, report_id, receipt}, csrf, true);
        if (response.ok) return (await response.json()).recorded === true;
        if (response.status < 500) return false;
      } catch (_) { /* Retry an ambiguous reply using the same receipt. */ }
    }
    return false;
  }

  button.addEventListener('click', async () => {
    if (button.disabled) return;
    button.disabled = true;
    feedback('');
    let file, writable, choosing = false;
    try {
      if (typeof window.showSaveFilePicker === 'function') {
        choosing = true;
        file = await window.showSaveFilePicker({suggestedName: filename,
          types: [{description: 'Tệp PDF', accept: {'application/pdf': ['.pdf']}}]});
        choosing = false;
      }
      label.textContent = 'Đang tạo PDF…';
      feedback('Đang tạo PDF theo dữ liệu của báo cáo này.');
      const sessionResponse = await fetch('/api/customer/session', {cache: 'no-store'});
      const session = await sessionResponse.json();
      if (!sessionResponse.ok || !session.user) throw new Error('Phiên đăng nhập đã hết hạn. Hãy tải lại báo cáo.');
      const response = await post(endpoint, request, session.csrf);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || 'Chưa tạo được PDF. Hãy thử lại.');
      }
      const receipt = response.headers.get('X-Vio-PDF-Receipt');
      const content = await response.blob();
      if (!receipt || content.type !== 'application/pdf' || !content.size) throw new Error('Tệp PDF chưa hoàn chỉnh.');
      if (!file) {
        const url = URL.createObjectURL(content);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.append(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 60000);
        feedback('PDF đã tạo. Hãy kiểm tra mục tải xuống của trình duyệt.');
        return;
      }
      label.textContent = 'Đang lưu tệp…';
      writable = await file.createWritable();
      await writable.write(content);
      await writable.close();
      writable = null;
      feedback('Đã lưu PDF thành công.');
      if (await acknowledge(receipt, session.csrf)) window.VioNotifications?.update();
      else feedback('Đã lưu PDF. Vio chưa cập nhật được chuông thông báo.');
    } catch (error) {
      if (writable) await writable.abort().catch(() => {});
      if (choosing && error.name === 'AbortError') feedback('Đã hủy lưu PDF.');
      else feedback(error.name === 'SecurityError' || error.name === 'NotAllowedError'
        ? 'Trình duyệt chưa cấp quyền lưu. Hãy mở báo cáo trực tiếp trong Chrome hoặc Edge.'
        : error instanceof DOMException ? 'Chưa lưu được PDF. Chọn một thư mục khác và thử lại.'
          : error.message || 'Chưa lưu được PDF. Hãy thử lại.', true);
    } finally {
      label.textContent = 'Xuất PDF';
      button.disabled = false;
    }
  });
})();
