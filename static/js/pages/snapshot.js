(() => {
  'use strict';
  const payload = document.getElementById('snapshot-data');
  if (!payload) return;
  const data = JSON.parse(payload.textContent);
  const $ = selector => document.querySelector(selector);
  const $$ = selector => [...document.querySelectorAll(selector)];
  const note = text => { const box = $('#dashboard-toast'); box.textContent = text; box.hidden = false; setTimeout(() => { box.hidden = true; }, 6000); };
  $('form[action="/logout"]')?.addEventListener('submit', async event => {
    event.preventDefault();
    try {
      // Keep the CSRF form on New; navigate to Admin only after revocation.
      const response = await fetch('/logout', {method: 'POST', redirect: 'manual',
        body: new URLSearchParams(new FormData(event.currentTarget))});
      if (response.type === 'opaqueredirect') location.replace('/reports');
      else note('Chưa kết thúc được phiên xem. Tải lại trang rồi thử lại.');
    } catch { note('Chưa kết nối được hệ thống. Vui lòng thử lại.'); }
  });
  $$('[data-close-dialog]').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
  $$('[data-bundle-chart]').forEach(element => {
    const chart = JSON.parse(element.querySelector('script').textContent);
    window.dashboardCharts.renderBundleChart(element, chart);
    if (chart.kind !== 'donut') {
      let lastWidth = element.clientWidth;
      new ResizeObserver(() => {
        if (element.clientWidth !== lastWidth && element.clientWidth > 0) {
          lastWidth = element.clientWidth;
          window.dashboardCharts.renderBundleChart(element, element.filteredChart || chart);
        }
      }).observe(element);
    }
  });
  $$('[data-snapshot-series]').forEach(select => select.addEventListener('change', () => {
    [...select.closest('.snapshot-chart-group').querySelectorAll('[data-bundle-chart]')].forEach((chart, i) => { chart.hidden = i !== Number(select.value); });
  }));
  // Include optional channel charts in print, then restore the reader's choices.
  let printDetails = null;
  window.addEventListener('beforeprint', () => {
    if (printDetails !== null) return;
    printDetails = $$('.channel-trend, .executive-briefing details').map(element => [element, element.open]);
    printDetails.forEach(([element]) => { element.open = true; });
  });
  window.addEventListener('afterprint', () => {
    printDetails?.forEach(([element, open]) => { element.open = open; });
    printDetails = null;
  });
  const filterTables = () => $$('[data-snapshot-table]').forEach(table => {
    const query = table.querySelector('[data-snapshot-search]').value.toLocaleLowerCase('vi');
    const rows = [...table.querySelectorAll('tbody tr')];
    const rank = table.querySelector('[data-snapshot-rank]')?.value || 'all';
    const matching = rows.filter(row => row.textContent.toLocaleLowerCase('vi').includes(query) && row.dataset.dateHidden !== 'true'
      && (rank === 'all' || (row.dataset.position !== '' && Number.isFinite(Number(row.dataset.position))
        && Number(row.dataset.position) >= 1 && Number(row.dataset.position) <= Number(rank))));
    const sizeValue = table.querySelector('[data-page-size]')?.value || 'all';
    const size = sizeValue === 'all' ? Math.max(1, matching.length) : Number(sizeValue);
    const pages = Math.max(1, Math.ceil(matching.length / size));
    const page = Math.min(Math.max(1, Number(table.dataset.page || 1)), pages); table.dataset.page = page;
    const visible = new Set(matching.slice((page - 1) * size, page * size));
    rows.forEach(row => { row.hidden = !visible.has(row); });
    table.querySelector('[data-row-count]').textContent = `${visible.size} hàng đang xem · ${matching.length} / ${rows.length} hàng phù hợp`;
    if (table.querySelector('[data-page-number]')) {
      table.querySelector('[data-page-number]').textContent = `${page} / ${pages}`;
      table.querySelector('[data-page-prev]').disabled = page === 1;
      table.querySelector('[data-page-next]').disabled = page === pages;
    }
  });
  $$('[data-snapshot-search]').forEach(input => input.addEventListener('input', () => { input.closest('[data-snapshot-table]').dataset.page = 1; filterTables(); }));
  $$('[data-snapshot-rank]').forEach(input => input.addEventListener('change', () => { input.closest('[data-snapshot-table]').dataset.page = 1; filterTables(); }));
  $$('[data-page-size]').forEach(input => input.addEventListener('change', () => { input.closest('[data-snapshot-table]').dataset.page = 1; filterTables(); }));
  $$('[data-page-prev], [data-page-next]').forEach(button => button.addEventListener('click', () => {
    const table = button.closest('[data-snapshot-table]'); table.dataset.page = Number(table.dataset.page || 1) + (button.hasAttribute('data-page-next') ? 1 : -1); filterTables();
  }));
  $$('[data-snapshot-sort]').forEach(button => button.addEventListener('click', () => {
    const table = button.closest('table'), index = Number(button.dataset.snapshotSort), direction = button.dataset.direction === 'asc' ? -1 : 1;
    const rows = [...table.tBodies[0].rows];
    rows.sort((a, b) => {
      const x = a.cells[index].dataset.value, y = b.cells[index].dataset.value;
      if (x === '' && y === '') return 0; if (x === '') return 1; if (y === '') return -1;
      return direction * (Number.isFinite(Number(x)) && Number.isFinite(Number(y)) ? Number(x) - Number(y) : x.localeCompare(y, 'vi'));
    });
    rows.forEach(row => table.tBodies[0].append(row)); button.dataset.direction = direction === 1 ? 'asc' : 'desc';
    table.querySelectorAll('th[aria-sort]').forEach(th => th.removeAttribute('aria-sort'));
    button.closest('th').setAttribute('aria-sort', direction === 1 ? 'ascending' : 'descending');
    filterTables();
  }));
  $('#fb-sort')?.addEventListener('click', () => $('#fb-campaign-table [data-snapshot-sort]')?.click());
  $$('[data-snapshot-detail]').forEach(button => button.addEventListener('click', () => {
    const row = button.closest('tr'), headers = [...row.closest('table').tHead.rows[0].cells];
    $('#snapshot-detail .snapshot-info').textContent = `Report ${data.report_id} · Revision ${data.revision}\n` + [...row.cells].map((cell, i) => `${headers[i].textContent.trim()}: ${cell.textContent.trim()}`).join('\n');
    if (row.dataset.savedRow) {
      const saved = JSON.parse(row.dataset.savedRow);
      $('#snapshot-detail .snapshot-info').textContent = `Report ${data.report_id} · Revision ${data.revision}\nMúi giờ nguồn: ${data.dashboard.timezone}\nSnapshot: ${data.dashboard.fetched_at}\n` +
        Object.entries(saved).map(([key, cell]) => `${key}: ${cell.value === null ? 'null (chưa có dữ liệu)' : cell.value}`).join('\n');
    }
    $('#snapshot-detail').showModal();
  }));
  $('#data-source')?.addEventListener('click', () => $('#source-dialog').showModal());
  $('#date-range')?.addEventListener('click', () => $('#date-dialog').showModal());
  $('#comparison')?.addEventListener('click', () => note('Chỉ hiển thị kỳ so sánh đã được Admin chốt trong revision này.'));
  $$('[data-period]').forEach(button => {
    button.setAttribute('aria-pressed', 'false');
    button.addEventListener('click', () => button.dataset.period === 'custom' ? $('#date-dialog').showModal() : note('Snapshot cố định theo kỳ đã chốt. Dùng Tùy chỉnh để lọc các điểm/ngày hiện có.'));
  });
  $('#date-form')?.addEventListener('submit', event => {
    event.preventDefault();
    const start = $('#date-start').value, end = $('#date-end').value;
    if (!start || !end || start > end || start < data.period.start || end > data.period.end) { $('#date-error').textContent = 'Khoảng ngày phải nằm trong kỳ của snapshot.'; return; }
    $('#date-error').textContent = '';
    $$('[data-bundle-chart]').forEach(element => {
      const chart = JSON.parse(element.querySelector('script').textContent);
      if (chart.labels.every(label => /^\d{4}-\d{2}-\d{2}$/.test(label))) {
        const indices = chart.labels.map((label, i) => label >= start && label <= end ? i : -1).filter(i => i >= 0);
        element.filteredChart = {...chart, labels: indices.map(i => chart.labels[i]), values: indices.map(i => chart.values[i])};
        window.dashboardCharts.renderBundleChart(element, element.filteredChart);
      }
    });
    $$('[data-snapshot-table] tbody tr').forEach(row => {
      const date = /^\d{4}-\d{2}-\d{2}$/.test(row.dataset.rowDate || '') ? row.dataset.rowDate : '';
      row.dataset.dateHidden = String(Boolean(date && (date < start || date > end)));
    });
    $$('[data-snapshot-table]').forEach(table => { table.dataset.page = 1; });
    $('#snapshot-filter-status').textContent = `Chi tiết: ${start} → ${end}. KPI và Top K giữ nguyên toàn kỳ; hàng không có ngày không được lọc theo ngày.`;
    filterTables(); $('#date-dialog').close(); note('Đã lọc chi tiết. KPI tổng vẫn là số của toàn kỳ đã chốt.');
  });
  $('#export-report')?.addEventListener('click', () => { $('#export-menu').hidden = !$('#export-menu').hidden; $('#export-report').setAttribute('aria-expanded', String(!$('#export-menu').hidden)); });
  const print = () => window.print();
  $('#export-pdf')?.addEventListener('click', print); $('#seo-pdf')?.addEventListener('click', print); $('#print-plan')?.addEventListener('click', print);
  const exportCsv = () => {
    const rows = [['Report ID', data.report_id], ['Revision', data.revision], ['Kỳ', data.period.start, data.period.end], ['Phạm vi', 'Các hàng đang hiện trong snapshot']];
    $$('.snapshot-table table, #fb-campaign-table').forEach(table => [...table.rows].filter(row => !row.hidden).forEach(row => rows.push([...row.cells].map(cell =>
      row.dataset.savedRow ? (cell.dataset.null === 'true' ? 'null' : cell.dataset.value) : cell.textContent.trim()))));
    const escape = value => { const text = String(value); return '"' + (/^\s*[=+@\-]|^[\t\r\n]/.test(text) ? "'" : '') + text.replaceAll('"', '""') + '"'; };
    const url = URL.createObjectURL(new Blob(['\uFEFF' + rows.map(row => row.map(escape).join(',')).join('\r\n')], {type:'text/csv;charset=utf-8'}));
    const link = document.createElement('a'); link.href = url; link.download = `${data.report_id}-r${data.revision}.csv`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  $('#export-csv')?.addEventListener('click', exportCsv); $('#fc-download')?.addEventListener('click', exportCsv);
  $$('[data-open-filter], #seo-advanced, #fb-advanced, #fc-advanced').forEach(button => button.addEventListener('click', () => {
    const input = $('[data-snapshot-search]'); if (input) { input.scrollIntoView({block:'center'}); input.focus(); } else note('Snapshot chưa có bảng chi tiết để lọc.');
  }));
  $$('#seo-weekly, #fb-optimize, #fb-library, #seo-strategy').forEach(button => button.addEventListener('click', () => {
    $('#snapshot-detail .snapshot-info').textContent = 'Report ' + data.report_id + ' · Revision ' + data.revision + '\nSnapshot chưa cung cấp nội dung cho thao tác này. Cần dữ liệu và phê duyệt từ Admin.';
    $('#snapshot-detail').showModal();
  }));
  filterTables();
  const targets = {'tong-quan-hieu-qua':'seo-summary', 'hieu-qua-seo':'seo-kpis', 'thu-hang-tu-khoa':'seo-keywords',
    'hieu-qua-trang-dich':'seo-landings', 'phan-tich-luu-luong-truy-cap':'seo-trend',
    'chuyen-doi-va-khach-hang-tiem-nang':'seo-funnel', 'tang-truong-va-phan-tich':'seo-insights'};
  const view = new URLSearchParams(location.search).get('view');
  if (Object.hasOwn(targets, view)) document.getElementById(targets[view])?.scrollIntoView({block:'start'});
})();
