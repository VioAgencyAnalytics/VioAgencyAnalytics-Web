(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];
  const initial = $('#seo-data');
  if (!initial) return;
  let data = JSON.parse(initial.textContent);
  let rank = 'all';
  let search = '';
  let compare = true;
  let mode = 'traffic';
  let pending;
  let toastTimer;
  const number = new Intl.NumberFormat('vi-VN');
  const date = (iso) => iso.split('-').reverse().join('/');
  const range = (start, end) => `${date(start)} – ${date(end)}`;
  const escape = (text) => String(text).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const trafficPaths = Object.fromEntries($$('[data-chart-line]').map((path) => [path.dataset.chartLine, path.getAttribute('d')]));
  const ratesPaths = {
    primary: 'M 0 190 Q 150 170, 300 180 T 600 95 T 900 65 L 1000 45',
    secondary: 'M 0 45 Q 150 80, 300 75 T 600 130 T 900 165 L 1000 190',
    previous: 'M 0 230 Q 150 200, 300 210 T 600 165 T 900 135 L 1000 120',
  };
  const metricsMarkup = (items) => items.map(([label, value]) => `<div><dt>${escape(label)}</dt><dd>${escape(value)}</dd></div>`).join('');

  function toast(text) {
    clearTimeout(toastTimer);
    $('#dashboard-toast').textContent = text;
    $('#dashboard-toast').hidden = false;
    toastTimer = setTimeout(() => { $('#dashboard-toast').hidden = true; }, 4200);
  }
  function detail(title, html) {
    $('#seo-detail-title').textContent = title;
    $('#seo-detail-content').innerHTML = html;
    $('#seo-detail-dialog').showModal();
  }
  function renderChart() {
    const paths = mode === 'traffic' ? trafficPaths : ratesPaths;
    $$('[data-chart-line]').forEach((path) => {
      path.setAttribute('d', paths[path.dataset.chartLine]);
      path.style.display = path.dataset.chartLine === 'previous' && !compare ? 'none' : '';
    });
    $$('[data-chart-mode]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.chartMode === mode)));
    $('#seo-primary-legend').textContent = mode === 'traffic' ? 'Lượt Click (Kỳ này)' : 'CTR (Kỳ này)';
    $('#seo-secondary-legend').textContent = mode === 'traffic' ? 'Lượt Hiển Thị (Kỳ này)' : 'Vị trí trung bình';
    $('#seo-chart-dates').innerHTML = data.chart_dates.map((label) => `<span>${escape(label)}</span>`).join('');
    $('#seo-chart-description').textContent = `${mode === 'traffic' ? 'So sánh Lượt Click & Lượt Hiển Thị' : 'Theo dõi CTR & Vị trí trung bình'} trong ${data.period.days} ngày${compare ? ' so với kỳ trước' : ''} (GSC Data)`;
    $('#seo-chart').setAttribute('aria-label', `Đường xu hướng minh họa ${mode === 'traffic' ? 'clicks và lượt hiển thị' : 'CTR và vị trí trung bình'}, ${range(data.period.start, data.period.end)}.`);
    $('#seo-chart').title = 'Đường xu hướng minh họa từ thiết kế mẫu; các chỉ số sử dụng thang đo riêng.';
  }
  function matches(row) {
    const term = search.trim().toLocaleLowerCase('vi');
    if (term && !(row.keyword + ' ' + row.landing).toLocaleLowerCase('vi').includes(term)) return false;
    if (/^top(5|10|20|30|50|100)$/.test(rank)) return row.position >= 1 && row.position <= Number(rank.slice(3));
    return ({ all: true, top3: row.position >= 1 && row.position <= 3,
      new: row.previous > 10 && row.position <= 10, risers: row.previous - row.position >= 5 })[rank];
  }
  const applied = document.createElement('div');
  applied.className = 'seo-applied-filters';
  applied.hidden = true;
  applied.innerHTML = '<span id="seo-filter-status" role="status" aria-live="polite"></span><button type="button" id="seo-clear-filters">Xóa bộ lọc</button>';
  $('#seo-keyword-table').parentElement.before(applied);
  const empty = document.createElement('tr');
  empty.className = 'seo-empty-row';
  empty.hidden = true;
  empty.innerHTML = '<td colspan="8">Không tìm thấy từ khóa phù hợp. Hãy thử nội dung khác hoặc xóa bộ lọc.</td>';
  $('#seo-keyword-table tbody').appendChild(empty);
  function filterRows() {
    let visible = 0;
    $$('[data-keyword-index]').forEach((row) => {
      row.hidden = !matches(data.keywords[Number(row.dataset.keywordIndex)]);
      if (!row.hidden) visible++;
    });
    empty.hidden = visible > 0;
    $$('[data-rank]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.rank === rank)));
    applied.hidden = rank === 'all' && !search;
    $('#seo-filter-status').textContent = `Hiển thị ${visible}/${data.keywords.length} từ khóa minh họa${search ? ` · “${search}”` : ''}`;
  }
  function resetFilters() { rank = 'all'; search = ''; filterRows(); }
  $('#seo-clear-filters').addEventListener('click', resetFilters);
  $$('[data-rank]').forEach((button) => button.addEventListener('click', () => { rank = button.dataset.rank; filterRows(); }));
  $('#seo-advanced').addEventListener('click', () => {
    $('#seo-search').value = search;
    $('#seo-rank-select').value = rank;
    $('#seo-filter-dialog').showModal();
  });
  $('#seo-filter-form').addEventListener('submit', (event) => {
    event.preventDefault();
    search = $('#seo-search').value.trim();
    rank = $('#seo-rank-select').value;
    filterRows();
    $('#seo-filter-dialog').close();
    $('#seo-keywords').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  $('#seo-reset-filters').addEventListener('click', () => {
    resetFilters(); $('#seo-search').value = ''; $('#seo-rank-select').value = 'all';
  });
  $$('[data-chart-mode]').forEach((button) => button.addEventListener('click', () => { mode = button.dataset.chartMode; renderChart(); }));

  const sampleNote = document.createElement('p');
  sampleNote.className = 'seo-sample-note';
  sampleNote.hidden = true;
  sampleNote.textContent = 'Số liệu kỳ này được mô phỏng theo độ dài khoảng thời gian. Nhận định và kế hoạch tham chiếu mẫu tháng 9/2026.';
  $('#seo-details').before(sampleNote);
  function render() {
    $$('[data-seo-field]').forEach((element) => { element.textContent = data.fields[element.dataset.seoField]; });
    const p = data.period;
    $('#date-range-label').textContent = range(p.start, p.end);
    $('#comparison > span:first-child').textContent = compare ? 'Kỳ trước' : 'Không so sánh';
    $('#comparison-label').textContent = compare ? `(${range(p.previous_start, p.previous_end)})` : '';
    $('#comparison').setAttribute('aria-pressed', String(compare));
    $$('[data-seo-comparison]').forEach((element) => { element.hidden = !compare; });
    const baseline = p.start === '2026-09-01' && p.end === '2026-09-30';
    sampleNote.hidden = baseline;
    $('#seo-result h4').textContent = baseline ? 'Hiệu Suất SEO Tháng 09/2026 Đạt 128% Mục Tiêu Đề Ra' : `Hiệu Suất SEO · ${range(p.start, p.end)}`;
    $('#seo-result p').textContent = `Lưu lượng tự nhiên tiếp tục duy trì đà tăng trưởng ổn định, đóng góp ${data.fields.leads} Leads chất lượng cao cho phòng khám KinderHealth.`;
    renderChart();
    filterRows();
  }
  async function loadPeriod(start, end, selected = 'custom') {
    pending?.abort();
    const controller = new AbortController();
    pending = controller;
    $('#main-content').setAttribute('aria-busy', 'true');
    try {
      const query = new URLSearchParams({ start, end });
      const response = await fetch(`/api/v1/reports/seo?${query}`, { signal: controller.signal });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(typeof error.detail === 'string' ? error.detail : 'Khoảng thời gian không hợp lệ.');
      }
      data = await response.json();
      $$('#period-switcher button').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.period === selected)));
      render();
      const url = new URL(location.href);
      url.searchParams.set('start', start); url.searchParams.set('end', end);
      history.replaceState(null, '', url);
      toast('Đã cập nhật báo cáo SEO với dữ liệu mẫu.');
      return true;
    } catch (error) {
      if (error.name !== 'AbortError') toast(error.message || 'Không tải được báo cáo SEO. Vui lòng thử lại.');
      return false;
    } finally {
      if (pending === controller) { pending = null; $('#main-content').setAttribute('aria-busy', 'false'); }
    }
  }
  function openDates() {
    $('#date-start').value = data.period.start; $('#date-end').value = data.period.end;
    $('#date-error').hidden = true; $('#date-dialog').showModal();
  }
  $('#date-range').addEventListener('click', openDates);
  $$('#period-switcher button').forEach((button) => button.addEventListener('click', () => {
    if (button.dataset.period === 'custom') return openDates();
    loadPeriod({ '7': '2026-09-24', '30': '2026-09-01', '90': '2026-07-01', '180': '2026-04-01' }[button.dataset.period], '2026-09-30', button.dataset.period);
  }));
  $('#date-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const start = $('#date-start').value, end = $('#date-end').value;
    if (start > end) {
      $('#date-error').textContent = 'Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.';
      $('#date-error').hidden = false; return;
    }
    const submit = $('#date-form button[type="submit"]');
    submit.disabled = true;
    try { if (await loadPeriod(start, end)) $('#date-dialog').close(); }
    finally { submit.disabled = false; }
  });
  $('#comparison').addEventListener('click', () => { compare = !compare; render(); });
  $('#data-source').addEventListener('click', () => $('#source-dialog').showModal());
  $$('[data-close-dialog]').forEach((button) => button.addEventListener('click', () => button.closest('dialog').close()));

  $$('[data-keyword-detail]').forEach((button) => button.addEventListener('click', () => {
    const row = data.keywords[Number(button.dataset.keywordDetail)];
    detail(row.keyword, `<p class="seo-detail-url">${escape(row.landing)}</p><dl class="seo-detail-metrics">${metricsMarkup([
      ['Vị trí hiện tại', `Top ${row.position}`], ['Thay đổi', `↑ ${row.previous - row.position} hạng`], ['Lượt click', number.format(row.clicks)], ['Lượt hiển thị', number.format(row.impressions)], ['CTR', row.ctr], ['Kỳ báo cáo', range(data.period.start, data.period.end)],
    ])}</dl><p>Dữ liệu minh họa Google Search Console.</p>`);
  }));
  function landingMarkup(row) {
    return `<p class="seo-detail-url">${escape(row.url)}</p><dl class="seo-detail-metrics">${metricsMarkup([['Organic Users', number.format(row.users)], ['Clicks', number.format(row.clicks)], ['Leads', number.format(row.leads)], ['CR', row.cr]])}</dl>`;
  }
  $$('[data-landing-detail]').forEach((button) => button.addEventListener('click', () => {
    detail('Hiệu quả trang đích', landingMarkup(data.landings[Number(button.dataset.landingDetail)]));
  }));
  $('#seo-all-pages').addEventListener('click', () => {
    detail('Danh sách trang đích', '<p>Mẫu thiết kế ghi nhận 24 trang đích và cung cấp số liệu chi tiết cho 4 trang bên dưới.</p>' + data.landings.map((row) => `<section class="seo-detail-page">${landingMarkup(row)}</section>`).join(''));
  });
  $('#seo-strategy').addEventListener('click', () => {
    const cards = $$('#seo-insights .space-y-4 > div');
    detail('Chiến lược SEO kỳ tiếp theo', cards.map((card) => `<section class="seo-detail-page"><h3>${escape(card.querySelector('h4').textContent.trim())}</h3><p>${escape(card.querySelector('p').textContent.trim())}</p></section>`).join('') + '<p class="seo-sample-note">Đề xuất theo bộ dữ liệu mẫu tháng 9/2026 · KDH SEO Team.</p>');
  });
  $('#seo-weekly').addEventListener('click', async () => {
    const button = $('#seo-weekly'); button.disabled = true;
    try {
      if (!(await loadPeriod('2026-09-24', '2026-09-30', '7'))) return;
      $('#seo-weekly-period').textContent = range(data.period.start, data.period.end);
      $('#seo-weekly-metrics').innerHTML = metricsMarkup(data.metrics.map((m) => [m.label, `${number.format(m.value)} ${m.unit}`]));
      $('#seo-weekly-dialog').showModal();
    } finally { button.disabled = false; }
  });

  function closeExport() { $('#export-menu').hidden = true; $('#export-report').setAttribute('aria-expanded', 'false'); }
  $('#export-report').addEventListener('click', () => {
    const open = $('#export-menu').hidden;
    $('#export-menu').hidden = !open;
    $('#export-report').setAttribute('aria-expanded', String(open));
    if (open) $('#export-pdf').focus();
  });
  document.addEventListener('click', (event) => { if (!event.target.closest('#export-menu, #export-report')) closeExport(); });
  function print() {
    closeExport();
    $$('dialog[open]').forEach((dialog) => dialog.close());
    window.print();
  }
  ['#seo-pdf', '#export-pdf', '#seo-weekly-print'].forEach((selector) => $(selector).addEventListener('click', print));
  $('#export-csv').addEventListener('click', async () => {
    closeExport();
    try {
      const query = new URLSearchParams({ start: data.period.start, end: data.period.end, rank, query: search });
      const response = await fetch(`/api/v1/reports/seo/export?${query}`);
      if (!response.ok) throw new Error('Không xuất được báo cáo. Vui lòng thử lại.');
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = `KDH-SEO-${data.period.start}-${data.period.end}.csv`;
      document.body.appendChild(anchor); anchor.click(); anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast('Đã xuất báo cáo SEO, gồm bảng từ khóa theo bộ lọc hiện tại.');
    } catch (error) { toast(error.message); }
  });



  render();
  const params = new URLSearchParams(location.search);
  const targets = {
    'tong-quan-hieu-qua': 'seo-summary', 'hieu-qua-seo': 'seo-kpis', 'thu-hang-tu-khoa': 'seo-keywords',
    'hieu-qua-trang-dich': 'seo-landings', 'phan-tich-luu-luong-truy-cap': 'seo-trend',
    'chuyen-doi-va-khach-hang-tiem-nang': 'seo-funnel', 'tang-truong-va-phan-tich': 'seo-insights',
  };
  async function restoreView() {
    if (params.has('start') && params.has('end')) await loadPeriod(params.get('start'), params.get('end'));
    const view = params.get('view');
    if (Object.hasOwn(targets, view)) {
      const link = $(`.seo-submenu a[data-path="${view}"]`);
      link?.setAttribute('aria-current', 'location');
      await document.fonts.ready;
      document.getElementById(targets[view]).scrollIntoView({ block: 'start' });
    }
  }
  restoreView();
})();
