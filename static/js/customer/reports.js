/* Saved reports in the active customer scope. */
(() => {
  'use strict';
  const W = window.VioLibrary, {$, node} = W, initial = W.initial, params = new URLSearchParams(location.search);
  const states = {draft: 'Bản nháp', scheduled: 'Định kỳ', published: 'Đã phát hành'};
  let tab = Object.hasOwn(states, params.get('tab')) ? params.get('tab') : 'all', currentPage = 1;
  const pagination = node('div', '', 'lb-pagination'); pagination.hidden = true; $('#reports-panel').append(pagination);
  function safeRows() {
    if (!W.ready || !W.snapshot?.reports_loaded || !Array.isArray(W.snapshot.reports)) return [];
    return W.snapshot.reports.slice(0, 1000).filter((r) => W.owned(r) && typeof r.id === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(r.id) && typeof r.name === 'string' && r.name.length <= 160 && Object.hasOwn(states, r.status));
  }
  function periodLabel(r) { return r.period?.start <= r.period?.end ? W.displayDate(r.period.start) + ' – ' + W.displayDate(r.period.end) : '—'; }
  function row(r) {
    const tr = node('tr', '');
    const sources = initial.sources.filter((s) => Array.isArray(r.source_ids) && r.source_ids.includes(s.id)).map((s) => s.name);
    tr.append(node('td', r.name), node('td', periodLabel(r)), node('td', sources.join(', ') || '—'));
    const state = node('td', ''); state.append(node('span', states[r.status], 'lb-state')); tr.append(state, node('td', W.stamp(r.updated_at)));
    const action = node('td', ''), button = node('button', 'Thông tin', 'lb-button lb-secondary'); button.type = 'button';
    button.addEventListener('click', () => W.info(r.name, `Trạng thái: ${states[r.status]}\nKỳ báo cáo: ${periodLabel(r)}\nNguồn: ${sources.join(', ') || 'Chưa xác định'}\nCập nhật: ${W.stamp(r.updated_at)}\n\nTrình xem bản phát hành, xuất file và liên kết chia sẻ sẽ được mở khi báo cáo sẵn sàng.`));
    action.append(button); tr.append(action); return tr;
  }
  function renderSaved() {
    const loaded = W.ready && W.snapshot?.reports_loaded === true && Array.isArray(W.snapshot.reports), rows = safeRows();
    const query = W.fold($('#reports-search').value.trim());
    const filtered = rows.filter((r) => (tab === 'all' || r.status === tab) && W.fold(r.name).includes(query)).sort((a, b) => (Date.parse(b.updated_at) || 0) - (Date.parse(a.updated_at) || 0));
    const pages = Math.max(1, Math.ceil(filtered.length / 10)); currentPage = Math.min(currentPage, pages);
    $('#reports-rows').replaceChildren(...filtered.slice((currentPage - 1) * 10, currentPage * 10).map(row));
    $('#reports-saved-count').textContent = loaded ? String(rows.length) : '—';
    for (const button of document.querySelectorAll('[data-report-tab]')) {
      const key = button.dataset.reportTab; button.setAttribute('aria-selected', String(key === tab)); button.tabIndex = key === tab ? 0 : -1;
      button.querySelector('[data-report-count]').textContent = !loaded ? '—' : String(key === 'all' ? rows.length : rows.filter((r) => r.status === key).length);
    }
    $('#reports-panel').setAttribute('aria-labelledby', 'reports-tab-' + tab);
    $('#reports-empty').hidden = filtered.length > 0;
    $('#reports-empty-title').textContent = !loaded ? 'Chưa có báo cáo được tải' : rows.length ? 'Không có báo cáo khớp bộ lọc' : 'Chưa có báo cáo đã lưu';
    $('#reports-empty-description').textContent = !loaded ? 'Bạn có thể xem cách trình bày trong Kho mẫu báo cáo.' : rows.length ? 'Thử từ khóa khác hoặc chuyển về Tất cả để xem lại các báo cáo.' : 'Chưa có báo cáo đã lưu cho khách hàng này.';
    pagination.replaceChildren(); pagination.hidden = pages <= 1;
    if (pages > 1) {
      pagination.append(node('span', `Trang ${currentPage} / ${pages} · ${filtered.length} báo cáo`));
      const actions = node('div', '');
      for (const [label, delta, disabled] of [['Trang trước', -1, currentPage === 1], ['Trang sau', 1, currentPage === pages]]) {
        const b = node('button', label, 'lb-button lb-secondary'); b.type = 'button'; b.disabled = disabled;
        b.addEventListener('click', () => { currentPage += delta; renderSaved(); $('#reports-saved-title').scrollIntoView({block: 'start'}); }); actions.append(b);
      }
      pagination.append(actions);
    }
  }
  function renderHistory() {
    const rows = (W.ready && Array.isArray(W.snapshot?.exports) ? W.snapshot.exports : []).slice(0, 100).filter((r) => W.owned(r) && typeof r.name === 'string' && r.name.length <= 160 && typeof r.created_at === 'string');
    const content = $('#report-history-content'); content.replaceChildren(); content.classList.toggle('lb-empty', !rows.length);
    if (!rows.length) { const icon = node('span', 'download', 'material-symbols-outlined'); icon.setAttribute('aria-hidden', 'true'); content.append(icon, node('h3', W.snapshot?.exports_loaded ? 'Chưa có lần xuất file nào' : 'Chưa có lịch sử được tải'), node('p', 'Lịch sử sẽ xuất hiện khi chức năng xuất báo cáo sẵn sàng.')); }
    for (const r of rows) { const item = node('div', '', 'lb-history-row'); item.append(node('strong', r.name), node('small', W.stamp(r.created_at))); content.append(item); }
  }
  const tabs = [...document.querySelectorAll('[data-report-tab]')];
  tabs.forEach((b, i) => {
    b.addEventListener('click', () => { tab = b.dataset.reportTab; currentPage = 1; W.url({tab: tab === 'all' ? '' : tab}); renderSaved(); });
    b.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault(); const next = event.key === 'Home' ? tabs[0] : event.key === 'End' ? tabs[tabs.length - 1] : tabs[(i + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length]; next.click(); next.focus();
    });
  });
  $('#reports-search').addEventListener('input', () => { currentPage = 1; renderSaved(); });
  $('#reports-history').addEventListener('click', () => { renderHistory(); $('#report-history-dialog').showModal(); });
  document.addEventListener('customer:library-context', () => { currentPage = 1; });
  window.VioReports = Object.freeze({getContext: W.context, render: W.accept});
  W.mount(renderSaved);
})();
