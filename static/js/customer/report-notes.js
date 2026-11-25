(() => {
  'use strict';

  const reader = document.getElementById('report-note-reader');
  if (!reader) return;
  const read = JSON.parse(reader.textContent);
  const status = document.getElementById('report-note-status');
  const notes = new Map([...document.querySelectorAll('[data-report-note]')].map(note => [note.dataset.reportNote, note]));
  let printing = false;

  function render(saved) {
    const finalized = saved.status === 'finalized';
    for (const [key, text] of Object.entries(saved.notes)) {
      const note = notes.get(key);
      if (!note) continue;
      note.querySelector('[data-report-note-text]').textContent = text;
      note.dataset.noteFinal = String(finalized);
    }
    status.textContent = finalized ? 'Nhận xét đã chốt và sẽ xuất hiện trong PDF.' : 'Đã lưu nháp nhận xét. Chốt để đưa vào PDF.';
    if (finalized) document.getElementById('report-note-edit')?.remove();
  }

  window.VioReportNotes = {async print(button) {
    if (printing) return;
    printing = true;
    button.disabled = true;
    try {
      const response = await fetch(read.endpoint, {headers: {'X-Report-Note-Proof': read.proof}, cache: 'no-store'});
      if (!response.ok) throw new Error('Không tải được nhận xét báo cáo.');
      const saved = await response.json();
      if (saved.status === 'finalized') render(saved);
      else status.textContent = 'Bản in hiện chỉ có số liệu. Chốt nhận xét để đưa vào PDF.';
      window.print();
    } catch (_) {
      status.textContent = 'Chưa kiểm tra được nhận xét đã chốt. Hãy thử in lại hoặc tải lại báo cáo.';
      status.scrollIntoView({block: 'nearest'});
    } finally {
      printing = false;
      button.disabled = false;
    }
  }};

  const configuration = document.getElementById('report-note-editor');
  if (!configuration) return;
  const config = JSON.parse(configuration.textContent);
  const dialog = document.getElementById('report-note-dialog');
  const form = document.getElementById('report-note-form');
  const edit = document.getElementById('report-note-edit');
  const feedback = document.getElementById('report-note-feedback');
  const fields = [...form.querySelectorAll('[data-report-note-field]')];
  const buttons = [...form.querySelectorAll('button')];
  let busy = false;

  function message(text) {
    feedback.textContent = text;
    feedback.hidden = !text;
    if (text) feedback.scrollIntoView({block: 'nearest'});
  }

  edit.addEventListener('click', () => {
    message('');
    for (const field of fields) {
      field.setCustomValidity('');
      field.value = notes.get(field.dataset.reportNoteField).querySelector('[data-report-note-text]').textContent;
    }
    dialog.showModal();
  });
  document.getElementById('report-note-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('cancel', event => { if (busy) event.preventDefault(); });
  for (const field of fields) field.addEventListener('input', () => field.setCustomValidity(''));

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (busy) return;
    const empty = fields.find(field => !field.value.trim());
    if (empty) {
      empty.setCustomValidity('Nhập nội dung nhận xét của mục này.');
      empty.reportValidity();
      return;
    }
    message('');
    busy = true;
    buttons.forEach(button => { button.disabled = true; });
    try {
      const sessionResponse = await fetch('/api/customer/session', {cache: 'no-store'});
      const session = await sessionResponse.json();
      if (!sessionResponse.ok || !session.user) throw new Error('Phiên đăng nhập đã hết hạn. Hãy tải lại báo cáo.');
      const response = await fetch(config.endpoint, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': session.csrf},
        body: JSON.stringify({
          client_id: config.client_id, version: config.version, proof: config.proof,
          action: event.submitter?.value === 'finalize' ? 'finalize' : 'save',
          notes: Object.fromEntries(fields.map(field => [field.dataset.reportNoteField, field.value])),
        }),
      });
      const saved = await response.json();
      if (!response.ok) throw new Error(saved.error || 'Chưa lưu được nhận xét. Hãy thử lại.');
      config.version = saved.version;
      render(saved);
      dialog.close();
      if (saved.status === 'finalized') window.VioNotifications?.update();
    } catch (error) {
      message(error.message || 'Chưa lưu được nhận xét. Hãy thử lại.');
    } finally {
      busy = false;
      buttons.forEach(button => { button.disabled = false; });
    }
  });
})();
