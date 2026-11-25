(function () {
  'use strict';
  const S = window.VioSEO, $ = selector => document.querySelector(selector);
  if (!S || !$('#seo-panel-content')) return;
  const el = S.element, num = new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 2});
  const fold = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase();
  const fmt = value => value === null || value === undefined ? '—' : num.format(value);
  const cell = value => { const td = el('td'); td.append(value?.nodeType ? value : el('span', value ?? '—')); return td; };
  const button = (label, action, cls = 'ov-button ov-secondary') => { const node = el('button', label, cls); node.type = 'button'; node.addEventListener('click', action); return node; };
  const statusNames = {met: 'Đạt mục tiêu', below_target: 'Chưa đạt', in_progress_met: 'Tạm đạt · kỳ đang mở', in_progress: 'Đang thực hiện', not_started: 'Chưa tới kỳ thực hiện', no_data: 'Chưa đủ dữ liệu', not_set: 'Chưa đặt mục tiêu', period_mismatch: 'Chọn từ ngày 1 trong cùng tháng'};
  const measurementFields = {traffic_start: 'traffic-start', traffic_end: 'traffic-end', rank_date: 'rank-date'};
  let data, editing = null, pending = null, page = 1, projectDraft = null, projectMonth = 0, reportTicket = 0, chartKey = 'accepted_new';

  function contentSummary() {
    const summary = data.content?.summary || {}, labels = [['published_new', 'Bài mới đã đăng'], ['accepted_new', 'Bài mới nghiệm thu'], ['accepted_updates', 'Cập nhật nghiệm thu'], ['awaiting_acceptance', 'Chờ nghiệm thu']];
    $('#seo-content-stats').replaceChildren(...labels.map(([key, label]) => { const card = el('div', '', 'seo-stat'); card.append(el('dt', label), el('dd', fmt(summary[key] ?? 0))); if (data.content?.previous_summary && data.comparison.mode !== 'none') { const previous = data.content.previous_summary[key], delta = (summary[key] || 0) - previous; card.append(el('small', `${delta > 0 ? '+' : ''}${fmt(delta)} so kỳ đối chiếu · trước: ${fmt(previous)}`)); } return card; }));
    const target = $('#seo-content-chart');
    if (!data.content?.ledger_count) { target.replaceChildren(el('div', 'Nhập danh sách để theo dõi tiến độ nội dung theo tháng.', 'seo-inline-empty')); return; }
    const toolbar = el('div', '', 'seo-chart-switch');
    for (const [key, label] of [['published_new', 'Đã đăng'], ['accepted_new', 'Nghiệm thu bài mới'], ['accepted_updates', 'Nghiệm thu cập nhật']]) {
      const node = button(label, () => { chartKey = key; contentSummary(); }); node.setAttribute('aria-pressed', String(chartKey === key)); toolbar.append(node);
    }
    const plot = el('div'); target.replaceChildren(toolbar, plot);
    window.VioReportCharts.renderSeries(plot, data.content.trend.map(row => ({date: row.month + '-01', label: row.month.slice(5) + '/' + row.month.slice(0, 4), full_date: 'Tháng ' + row.month.slice(5) + '/' + row.month.slice(0, 4), value: row[chartKey]})), {kind: 'bar', integer: true, maxBarWidth: 64, title: chartKey === 'published_new' ? 'Bài mới đã đăng' : chartKey === 'accepted_new' ? 'Bài mới đã nghiệm thu' : 'Cập nhật đã nghiệm thu', format: value => fmt(value) + ' bài'});
  }

  function rankComparison() {
    let section = $('#seo-rank-comparison');
    if (!section) { section = el('section', '', 'seo-card'); section.id = 'seo-rank-comparison'; $('#seo-comparison-panel').after(section); }
    section.hidden = data.comparison.mode === 'none' || !data.previous_distribution?.length;
    if (section.hidden) return;
    const head = el('div', '', 'seo-card-head'); head.append(el('h3', 'Phân bố thứ hạng · hai kỳ'));
    const legend = el('div', '', 'seo-rank-legend'); legend.append(el('span', 'Kỳ đang xem'), el('span', 'Kỳ đối chiếu'));
    const maximum = Math.max(1, ...data.distribution.map(row => row.count), ...data.previous_distribution.map(row => row.count));
    const rows = el('div', '', 'seo-rank-bars');
    const svgNode = (tag, attrs) => { const node = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value)); return node; };
    data.distribution.forEach((row, index) => { const before = data.previous_distribution[index]?.count || 0, item = el('div', '', 'seo-rank-bar-row'), label = el('div', row.label);
      label.append(el('small', `${fmt(row.count)} hiện tại / ${fmt(before)} trước`, 'seo-date'));
      const svg = svgNode('svg', {viewBox:'0 0 340 46',role:'img','aria-label':`${row.label}: ${row.count} kỳ này, ${before} kỳ trước`});
      svg.append(svgNode('rect', {x:0,y:4,width:row.count/maximum*320,height:14,rx:4,class:'current'}), svgNode('rect', {x:0,y:26,width:before/maximum*320,height:14,rx:4,class:'previous'})); item.append(label, svg); rows.append(item);
    });
    section.replaceChildren(head, legend, rows, el('p', 'Cùng bộ từ khóa đang theo dõi; chưa có phép đo được tách riêng, không suy ra thứ hạng.', 'seo-help'));
  }

  function contentRows() {
    const query = fold($('#seo-content-search').value), kind = $('#seo-content-kind').value, status = $('#seo-content-status').value;
    const rows = (data.content?.items || []).filter(row => (!query || fold(row.title + ' ' + row.topic + ' ' + row.url).includes(query))
      && (kind === 'all' || row.kind === kind) && (status === 'archived' ? row.archived : !row.archived)
      && (['all', 'archived'].includes(status) || status === 'accepted' && row.accepted_date || status === 'published' && row.publication_status === 'published'
        || status === 'pending' && row.review_status === 'pending' || status === 'draft' && row.publication_status === 'draft'));
    const pages = Math.max(1, Math.ceil(rows.length / 15)); page = Math.min(page, pages);
    $('#seo-content-count').textContent = fmt(rows.length) + ' bài / công việc';
    $('#seo-content-rows').replaceChildren(...rows.slice((page - 1) * 15, page * 15).map(row => {
      const tr = el('tr'), title = el('div', row.title, 'seo-content-name'), progress = el('div', '', 'seo-status-stack'), dates = el('div'), links = el('div', '', 'seo-row-links');
      title.append(el('small', `${row.kind === 'new' ? 'Bài mới' : 'Cập nhật bài cũ'} · Kế hoạch ${row.month}${row.topic ? ' · ' + row.topic : ''}`, 'seo-date'));
      if (row.provenance) title.append(el('small', 'Tự đồng bộ · ' + ({wordpress:'WordPress',rss_atom:'RSS / Atom',structured_data:'Dữ liệu bài viết',article_metadata:'Dữ liệu bài viết'})[row.provenance.source], 'seo-date'));
      const observed = data.effectiveness?.items?.find(item => item.id === row.id || item.ids?.includes(row.id));
      if (observed?.values.views !== null && observed?.values.views !== undefined) title.append(el('small', fmt(observed.values.views) + ' lượt xem trong kỳ · GA4', 'seo-date'));
      for (const [label, state] of [[row.publication_status === 'published' ? 'Đã đăng' : 'Bản thảo', row.publication_status], [({pending: 'Chờ duyệt', approved: 'Đã duyệt', rejected: 'Cần chỉnh sửa'})[row.review_status], row.review_status], [row.accepted_date ? 'Đã nghiệm thu' : 'Chưa nghiệm thu', row.accepted_date ? 'accepted' : 'pending']]) { const badge = el('span', label, 'seo-status'); badge.dataset.state = state; progress.append(badge); }
      dates.append(el('span', row.published_date ? 'Đăng ' + S.date(row.published_date) : 'Chưa đăng'), el('small', row.accepted_date ? 'Nghiệm thu ' + S.date(row.accepted_date) : '—', 'seo-date'));
      if (row.url) links.append(S.link(row.url, 'Mở bài viết ↗')); if (row.draft_url) links.append(S.link(row.draft_url, 'Bản thảo ↗')); if (!row.url && !row.draft_url) links.append(el('span', 'Chưa gắn liên kết', 'seo-help'));
      tr.append(cell(title), cell(progress), cell(dates), cell(links));
      if (data.permissions.edit) { const edit = button('Cập nhật', () => editContent(row)); edit.setAttribute('aria-label', 'Cập nhật ' + row.title); tr.append(cell(edit)); }
      return tr;
    }));
    $('#seo-content-empty').hidden = rows.length > 0; $('#seo-content-page').textContent = `Trang ${page}/${pages}`;
    $('#seo-content-prev').disabled = page <= 1; $('#seo-content-next').disabled = page >= pages;
    $('#seo-content-history').replaceChildren(...(data.content?.history || []).map(row => { const li = el('li'); li.append(el('span', row.filename), el('small', window.VioFormat?.timestamp?.(row.confirmed_at) || 'Đã nhập')); return li; }));
  }

  function editContent(row) {
    if (!data?.permissions.edit) return;
    editing = row;
    const values = {'title-input': row?.title || '', 'item-kind': row?.kind || 'new', month: row?.month || data.period.end.slice(0, 7), publication: row?.publication_status || 'draft', published: row?.published_date || '', review: row?.review_status || 'pending', accepted: row?.accepted_date || '', url: row?.url || '', 'draft-url': row?.draft_url || '', topic: row?.topic || ''};
    for (const [key, value] of Object.entries(values)) $('#seo-content-' + key).value = value;
    $('#seo-content-title').textContent = row?.id ? 'Cập nhật bài viết' : 'Thêm bài viết';
    $('#seo-content-attest').checked = false; $('#seo-content-archived').checked = Boolean(row?.archived); $('#seo-content-archive-label').hidden = !row;
    $('#seo-content-published').max = S.today(); $('#seo-content-accepted').max = S.today();
    S.message('', false, $('#seo-content-error')); $('#seo-content-dialog').showModal(); $('#seo-content-title-input').focus();
  }

  function downloadTemplate() {
    const columns = ['Tên bài viết', 'Loại công việc', 'Tháng kế hoạch', 'Trạng thái đăng', 'Ngày đăng', 'Trạng thái duyệt', 'Ngày nghiệm thu', 'URL bài viết', 'Link bản thảo', 'Nhóm nội dung'];
    const blob = new Blob(['\uFEFF' + columns.join(',') + '\r\n'], {type: 'text/csv;charset=utf-8;'});
    const href = URL.createObjectURL(blob), link = el('a'); link.href = href; link.download = 'Vio-Mau-danh-sach-bai-viet.csv'; link.click(); setTimeout(() => URL.revokeObjectURL(href), 1000);
    S.message('Mẫu đã tải. Điền loại “Bài mới” / “Cập nhật”, tháng YYYY-MM, trạng thái “Bản thảo” / “Đã đăng”, duyệt “Chờ duyệt” / “Đã duyệt” / “Từ chối”. Ngày dùng DD/MM/YYYY.');
  }

  function renderProject() {
    const project = data.project, plan = project?.plan;
    $('#seo-project-edit').textContent = plan ? 'Cập nhật cam kết' : 'Thiết lập cam kết 12 tháng';
    $('#seo-legacy-plan').hidden = Boolean(plan) || !data.plan?.version;
    $('#seo-project-overview').replaceChildren(); $('#seo-project-months').replaceChildren(); $('#seo-project-results').replaceChildren();
    if (!plan) {
      $('#seo-project-caption').textContent = 'Mẫu 12 tháng gồm 8 chỉ tiêu. Nhập thời hạn và mục tiêu theo hợp đồng của khách hàng.';
      $('#seo-project-note').textContent = 'Ô trống là chưa có kế hoạch hoặc kết quả.';
      return;
    }
    $('#seo-project-caption').textContent = `${plan.name} · Phiên bản ${plan.version} · ${plan.start_month} – ${plan.months.at(-1).month}`;
    const headline = el('div', '', 'seo-project-headline');
    const periodStatus = {closed: 'Kỳ đã kết thúc', in_progress: 'Kỳ đang mở', not_started: 'Chưa tới kỳ thực hiện'};
    headline.append(el('strong', project.month_number ? `Tháng ${project.month_number}/${plan.duration}` : 'Ngoài thời hạn dự án'));
    if (periodStatus[project.state]) headline.append(el('span', periodStatus[project.state]));
    $('#seo-project-overview').append(headline);
    $('#seo-project-months').replaceChildren(...plan.months.map((month, index) => { const node = button(`T${index + 1} · ${month.month.slice(5)}/${month.month.slice(0, 4)}`, () => { const range = S.monthRange(month.month); $('#seo-start').value = range.start; $('#seo-end').value = range.end; S.busy(node, S.reload); }); node.setAttribute('aria-current', month.month === project.month ? 'date' : 'false'); return node; }));
    const items = project.items.filter(goal => goal.target != null || goal.actual != null);
    $('#seo-project-results').replaceChildren(...items.map(goal => {
      const card = el('article', '', 'seo-kpi-card'), head = el('div'), value = el('strong', fmt(goal.actual) + (goal.unit === 'percent' && goal.actual !== null ? '%' : ''));
      head.append(el('h3', goal.label), el('span', goal.source)); value.append(el('small', ` / ${fmt(goal.target)}${goal.unit === 'percent' && goal.target !== null ? '%' : ''}`)); card.dataset.state = goal.status;
      const progress = el('progress'); progress.max = 100; progress.value = Math.max(0, Math.min(100, goal.achievement ?? 0)); progress.setAttribute('aria-label', 'Tiến độ ' + goal.label); progress.hidden = goal.achievement === null;
      card.append(head, el('small', 'Thực tế / Cam kết tháng', 'seo-kpi-reading'), value, progress, el('p', statusNames[goal.status] || 'Chưa đánh giá'));
      if (goal.difference !== null) card.append(el('small', `${goal.difference > 0 ? '+' : ''}${fmt(goal.difference)} ${goal.unit === 'percent' ? 'điểm phần trăm' : 'so mục tiêu'}${goal.achievement !== null ? ' · ' + fmt(goal.achievement) + '% hoàn thành' : ''}`));
      if (goal.note) card.append(el('small', goal.note));
      return card;
    }));
    $('#seo-project-note').textContent = items.length ? '' : 'Chọn tháng có cam kết hoặc kết quả để xem chi tiết.';
  }

  function monthAfter(start, offset) { const [year, month] = start.split('-').map(Number), value = year * 12 + month - 1 + offset; return `${String(Math.floor(value / 12)).padStart(4, '0')}-${String(value % 12 + 1).padStart(2, '0')}`; }
  function collectTargets() {
    const month = projectDraft?.months[projectMonth];
    if (!month) return;
    for (const input of document.querySelectorAll('[data-seo-project-target]')) month[input.dataset.seoProjectTarget] = input.value === '' ? null : Number(input.value);
    for (const [key, id] of Object.entries(measurementFields)) month[key] = $('#seo-project-' + id).value || null;
  }
  function displayTargets() {
    const month = projectDraft.months[projectMonth], definitions = data.project.definitions;
    const hints = {
      top10_percent: 'Spineditor · Tỷ lệ trên bộ từ khóa đã chốt.',
      traffic: 'Google · Tổng trong tháng hoặc chênh lệch theo cách tính đã chọn.',
      new_articles: projectDraft.template === 'monthly_seo' ? 'Đếm bài mới đã đăng và đã duyệt, theo ngày đăng.' : 'Số bài mới đã được nghiệm thu trong tháng.',
      updated_articles: 'Số lần cập nhật đã được nghiệm thu trong tháng.',
      technical_percent: 'Khối lượng kỹ thuật đã nghiệm thu / tổng checklist.',
      optimization: 'Đầu việc tối ưu có bằng chứng nghiệm thu.',
      entity: 'Số hồ sơ có bằng chứng nghiệm thu.',
      social_profile: 'Số trang mạng xã hội đã nghiệm thu.',
      social_share: projectDraft.template === 'monthly_seo' ? 'Để trống để tính từ mục tiêu bài mới × số trang đã nhập.' : 'Số lượt chia sẻ có bằng chứng nghiệm thu.'
    };
    $('#seo-project-targets').replaceChildren(...definitions.map(definition => { const label = el('label', definition.label + (definition.unit === 'percent' ? ' (%)' : ''), 'seo-field'), input = el('input'); input.type = 'number'; input.min = 0; input.max = definition.unit === 'percent' ? 100 : 1000000000; input.step = definition.unit === 'percent' ? '.01' : '1'; input.placeholder = 'Không áp dụng'; input.value = month[definition.key] ?? ''; input.dataset.seoProjectTarget = definition.key; const hint = el('small', hints[definition.key] || definition.source || 'Cam kết trong tháng'); hint.id = 'seo-project-hint-' + definition.key; input.setAttribute('aria-describedby', hint.id); label.append(input, hint); return label; }));
    for (const [key, id] of Object.entries(measurementFields)) $('#seo-project-' + id).value = month[key] || '';
  }
  function rebuildMonths() {
    const start = $('#seo-project-start').value;
    if (!/^\d{4}-\d{2}$/.test(start)) return;
    S.monthRange(start);
    const duration = Number($('#seo-project-duration').value), existing = new Map(projectDraft.months.map(row => [row.month, row]));
    projectDraft.months = Array.from({length: duration}, (_, index) => { const month = monthAfter(start, index); return existing.get(month) || {month, ...Object.fromEntries(data.project.definitions.map(row => [row.key, null]))}; });
    projectMonth = Math.min(projectMonth, duration - 1);
    $('#seo-project-month').replaceChildren(...projectDraft.months.map((row, index) => { const option = el('option', `Tháng ${index + 1} · ${row.month}`); option.value = index; return option; })); $('#seo-project-month').value = projectMonth; displayTargets();
  }
  function showBaseline() {
    $('#seo-project-baseline-field').hidden = $('#seo-project-traffic-basis').value !== 'increase';
  }
  function editProject() {
    if (!data?.permissions.edit || !data.project) return;
    const plan = data.project.plan;
    $('#seo-project-targets').replaceChildren();
    projectDraft = {
      template: plan ? plan.template || 'legacy' : data.project.template || 'legacy',
      months: plan ? plan.months.map(row => ({...row})) : []
    };
    projectMonth = Math.max(0, (data.project.month_number || 1) - 1);
    $('#seo-project-name').value = plan?.name || 'SEO Website · ' + data.client.name;
    $('#seo-project-start').value = plan?.start_month || data.period.end.slice(0, 7);
    const duration = plan?.duration || 12, select = $('#seo-project-duration');
    if (![...select.options].some(option => Number(option.value) === duration)) { const option = el('option', duration + ' tháng'); option.value = duration; select.append(option); }
    select.value = duration;
    $('#seo-project-traffic').value = plan?.traffic_metric || (projectDraft.template === 'monthly_seo' ? 'ga4_views' : 'gsc_clicks');
    $('#seo-project-traffic-basis').value = plan?.traffic_basis || 'total';
    $('#seo-project-baseline-month').value = plan?.traffic_baseline_month || '';
    $('#seo-project-share-pages').value = plan?.share_pages ?? '';
    $('#seo-project-share-pages-field').hidden = projectDraft.template !== 'monthly_seo';
    showBaseline();
    rebuildMonths(); $('#seo-project-attest').checked = false;
    $('#seo-project-scope').textContent = `${data.keywords.filter(row => row.committed).length} từ đang đánh dấu cam kết. Đặt KPI Top 10 sẽ chốt bộ này và điều kiện đo đang chọn. Bạn có thể chỉ đặt KPI nội dung khi chưa nhập từ khóa.`;
    S.message('', false, $('#seo-project-error')); $('#seo-project-dialog').showModal();
  }

  function metric(report, key) { return report?.state === 'ready' ? report.metrics.find(row => row.key === key)?.value ?? null : null; }
  function renderPerformance() {
    if (!data) return;
    const gsc = S.sourceReports?.gsc, ga4 = S.sourceReports?.ga4;
    const channels = ga4?.tables?.find(table => table.id === 'channels')?.rows || [], organic = ga4?.state === 'ready' ? channels.find(row => row.sessionDefaultChannelGroup === 'Organic Search')?.sessions ?? null : null;
    const specs = [['Lượt nhấp tìm kiếm', metric(gsc, 'clicks'), 'Google Search Console', 'gsc'], ['Lượt hiển thị', metric(gsc, 'impressions'), 'Google Search Console', 'gsc'], ['Phiên Organic Search', organic, 'Google Analytics 4 · riêng kênh tự nhiên', 'ga4']];
    $('#seo-performance').replaceChildren(...specs.map(([label, value, note, source]) => { const card = el('article', '', 'seo-performance-card'), img = el('img'); img.src = '/static/customer/platforms/' + (source === 'gsc' ? 'gsc.png' : 'ga4.svg'); img.alt = ''; const title = el('div'); title.append(img, el('span', label)); const link = el('a', value === null ? 'Kiểm tra nguồn →' : 'Xem dữ liệu →', 'ov-button ov-secondary'); link.href = value === null ? '/workspace/integrations?platform=' + source : '/workspace/reports/data?source=' + source + '&' + new URLSearchParams(data.period); card.append(title, el('strong', fmt(value)), el('small', value === null ? 'Chưa có quan sát đúng kỳ; không mặc định bằng 0.' : note), link); return card; }));
    renderQueries(gsc);
  }

  function renderQueries(report) {
    let section = $('#seo-gsc-discovery');
    if (!section) {
      section = el('section', '', 'seo-card');
      section.id = 'seo-gsc-discovery';
      $('#seo-panel-keywords').append(section);
    }
    const head = el('div', '', 'seo-card-head'), title = el('div'); title.append(el('h3', 'Khám phá từ khóa ngách từ GSC'), el('p', 'Truy vấn thực tế trong bản đồng bộ; vị trí là trung bình GSC, không phải thứ hạng Spineditor.', 'seo-help')); head.append(title); section.replaceChildren(head);
    if (window.VioSEOAutomation) { window.VioSEOAutomation.renderDiscovery(report); return; }
    const queries = report?.state === 'ready' ? report.tables.find(table => table.id === 'queries')?.rows || [] : [];
    if (!queries.length) { section.append(el('p', 'Đồng bộ GSC đúng kỳ để xem truy vấn. Bạn vẫn có thể nhập và phân loại từ khóa từ file Spineditor.', 'seo-help')); return; }
    const table = el('table', '', 'seo-table'), thead = el('thead'), tr = el('tr'); for (const label of ['Truy vấn', 'Nhấp', 'Hiển thị', 'Vị trí TB GSC', 'Theo dõi']) tr.append(el('th', label)); thead.append(tr); table.append(thead);
    const tbody = el('tbody');
    for (const row of queries.slice(0, 15)) { const tr = el('tr'); tr.append(cell(row.query), cell(fmt(row.clicks)), cell(fmt(row.impressions)), cell(fmt(row.position))); const action = button('Theo dõi từ ngách', () => S.busy(action, async () => { await S.api(S.base + '/seo/keyword-from-gsc', {client_id: S.scope.client_id, snapshot: report.snapshot.id, keyword: row.query}); await S.reload(); S.message('Đã thêm vào bộ theo dõi dạng từ khóa ngách. Chưa tự đưa vào cam kết hoặc gán thứ hạng Spineditor.'); })); action.disabled = !data.permissions.edit; tr.append(cell(action)); tbody.append(tr); }
    table.append(tbody); const wrap = el('div', '', 'seo-table-wrap'); wrap.tabIndex = 0; wrap.append(table); section.append(wrap, el('p', 'Hiển thị tối đa 15 truy vấn. GSC có thể ẩn truy vấn; tổng bảng không thay cho tổng KPI nguồn.', 'seo-help'));
  }

  async function savedReports() {
    if (!data) return;
    const ticket = ++reportTicket; $('#seo-reports-status').textContent = 'Đang tải báo cáo đã lưu…';
    try { const result = await S.api(S.base + '/compiled-reports'); if (ticket !== reportTicket) return; $('#seo-report-list').replaceChildren(...result.reports.map(row => { const link = el('a'); link.href = '/workspace/reports/combined?report=' + row.id; const title = el('span'); title.append(el('strong', row.name), el('small', S.date(row.start_date) + ' – ' + S.date(row.end_date))); link.append(title, el('span', 'Mở báo cáo →')); return link; })); $('#seo-reports-status').textContent = result.reports.length ? 'Danh sách báo cáo tổng hợp của khách hàng đang chọn.' : 'Chưa có báo cáo đã lưu. Chọn “Tạo báo cáo SEO” khi đã có dữ liệu.'; }
    catch (_) { if (ticket === reportTicket) $('#seo-reports-status').textContent = 'Chưa tải được danh sách. Chọn Cập nhật danh sách để thử lại.'; }
  }

  S.editContent = editContent;
  document.addEventListener('vio:seo-loaded', event => { data = event.detail; page = 1; contentSummary(); contentRows(); renderProject(); renderPerformance(); if ($('#seo-comparison-panel')) rankComparison(); savedReports(); });
  document.addEventListener('vio:seo-source', event => { renderPerformance(); if (data && event.detail?.source === 'ga4') contentRows(); });
  for (const id of ['seo-content-search', 'seo-content-kind', 'seo-content-status']) $('#' + id).addEventListener(id.endsWith('search') ? 'input' : 'change', () => { if (data) { page = 1; contentRows(); } });
  $('#seo-content-prev').addEventListener('click', () => { page--; contentRows(); }); $('#seo-content-next').addEventListener('click', () => { page++; contentRows(); });
  $('#seo-content-add').addEventListener('click', () => editContent(null));
  document.querySelectorAll('[data-seo-content-template]').forEach(node => node.addEventListener('click', downloadTemplate));
  $('#seo-content-form').addEventListener('submit', event => { event.preventDefault(); S.busy(event.submitter, async () => {
    const item = {title: $('#seo-content-title-input').value, kind: $('#seo-content-item-kind').value, month: $('#seo-content-month').value, publication_status: $('#seo-content-publication').value, published_date: $('#seo-content-published').value, review_status: $('#seo-content-review').value, accepted_date: $('#seo-content-accepted').value, url: $('#seo-content-url').value, draft_url: $('#seo-content-draft-url').value, topic: $('#seo-content-topic').value, archived: $('#seo-content-archived').checked};
    await S.api(S.base + '/seo/content', {client_id: S.scope.client_id, id: editing?.id || null, version: editing?.version || 0, item, acceptance_confirmed: $('#seo-content-attest').checked}); $('#seo-content-dialog').close(); await S.reload(); S.message('Đã lưu bài viết và lịch sử cập nhật.');
  }, $('#seo-content-error')); });
  $('#seo-content-import').addEventListener('click', () => { if (!data?.permissions.edit) return; pending = null; $('#seo-content-upload-form').hidden = false; $('#seo-content-preview').hidden = true; S.message('', false, $('#seo-content-upload-error')); $('#seo-content-upload-dialog').showModal(); });
  $('#seo-content-upload-form').addEventListener('submit', event => { event.preventDefault(); S.busy(event.submitter, async () => {
    const file = $('#seo-content-file').files[0]; if (!file || file.size > 2 * 1024 * 1024) throw new Error('Chọn Excel/CSV tối đa 2 MB.');
    pending = await S.api(S.base + '/seo/content-preview?' + new URLSearchParams({client_id: S.scope.client_id, filename: file.name}), file, true);
    $('#seo-content-preview-summary').replaceChildren(el('strong', fmt(pending.count) + ' bài / công việc'), el('p', `${pending.duplicates} đã có · ${pending.accepted} dòng có ngày nghiệm thu`), el('p', pending.website || 'Khách hàng chưa có website'));
    $('#seo-content-preview-rows').replaceChildren(...pending.rows.map(row => { const tr = el('tr'); tr.append(cell(row.title), cell(row.kind === 'new' ? 'Bài mới' : 'Cập nhật'), cell(S.date(row.published_date)), cell(S.date(row.accepted_date))); return tr; }));
    $('#seo-content-upload-form').hidden = true; $('#seo-content-preview').hidden = false; $('#seo-content-import-attest').checked = false; $('#seo-content-upload-confirm').disabled = true;
  }, $('#seo-content-upload-error')); });
  $('#seo-content-import-attest').addEventListener('change', () => { $('#seo-content-upload-confirm').disabled = !$('#seo-content-import-attest').checked; });
  $('#seo-content-upload-back').addEventListener('click', () => { pending = null; $('#seo-content-upload-form').hidden = false; $('#seo-content-preview').hidden = true; });
  $('#seo-content-upload-confirm').addEventListener('click', event => S.busy(event.currentTarget, async () => { if (!pending || !$('#seo-content-import-attest').checked) throw new Error('Xác nhận danh sách trước khi nhập.'); const result = await S.api(S.base + '/seo/content-confirm', {client_id: S.scope.client_id, import_id: pending.id, confirmed: true}); $('#seo-content-upload-dialog').close(); await S.reload(); S.message(result.message); }, $('#seo-content-upload-error')));
  $('#seo-website-edit').addEventListener('click', () => { if (!data?.permissions.edit) return; $('#seo-website-input').value = data.client.website || data.website || ''; S.message('', false, $('#seo-website-error')); $('#seo-website-dialog').showModal(); });
  $('#seo-website-form').addEventListener('submit', event => { event.preventDefault(); S.busy(event.submitter, async () => { await S.api(S.base + '/clients/' + data.client.id + '/update', {name: data.client.name, website: $('#seo-website-input').value, version: data.client.version}); $('#seo-website-dialog').close(); await S.reload(); S.message('Đã lưu website của khách hàng.'); }, $('#seo-website-error')); });
  $('#seo-project-edit').addEventListener('click', editProject);
  $('#seo-project-traffic-basis').addEventListener('change', showBaseline);
  for (const id of ['seo-project-start', 'seo-project-duration']) $('#' + id).addEventListener('change', () => {
    try {
      collectTargets();
      rebuildMonths();
    } catch (error) {
      S.message(error.message, true, $('#seo-project-error'));
    }
  });
  $('#seo-project-month').addEventListener('change', () => { collectTargets(); projectMonth = Number($('#seo-project-month').value); displayTargets(); });
  $('#seo-project-copy').addEventListener('click', () => {
    collectTargets();
    const values = Object.fromEntries(data.project.definitions.map(({key}) => [key, projectDraft.months[projectMonth][key]]));
    projectDraft.months = projectDraft.months.map((row, index) => index > projectMonth ? {...row, ...values} : row);
    S.message('Đã áp dụng mục tiêu cho các tháng phía sau.', false, $('#seo-project-error'));
  });
  $('#seo-project-form').addEventListener('submit', event => {
    event.preventDefault();
    S.busy(event.submitter, async () => {
      collectTargets();
      if (!$('#seo-project-attest').checked) throw new Error('Xác nhận cam kết trước khi lưu.');
      const plan = {
        name: $('#seo-project-name').value,
        start_month: $('#seo-project-start').value,
        duration: Number($('#seo-project-duration').value),
        template: projectDraft.template,
        traffic_metric: $('#seo-project-traffic').value,
        traffic_basis: $('#seo-project-traffic-basis').value,
        traffic_baseline_month: $('#seo-project-baseline-month').value || null,
        share_pages: $('#seo-project-share-pages').valueAsNumber || null,
        profile: data.profile,
        months: projectDraft.months
      };
      await S.api(S.base + '/seo/project', {client_id: S.scope.client_id, version: data.project.plan?.version || 0, plan});
      $('#seo-project-dialog').close();
      await S.reload();
      S.message('Đã chốt phiên bản cam kết dự án.');
    }, $('#seo-project-error'));
  });
  $('#seo-reports-refresh').addEventListener('click', event => S.busy(event.currentTarget, savedReports));
}());
