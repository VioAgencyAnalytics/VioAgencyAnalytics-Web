(function () {
  'use strict';
  const S = window.VioSEO;
  if (!S || !document.querySelector('#seo-period-form')) return;
  const $ = selector => document.querySelector(selector);
  let data, preview, page = 1, workEditing = null, generation = 0, importTarget = null;
  const states = {not_set: 'Chưa chốt bộ cam kết', met: 'Đã đủ số từ đạt mục tiêu', below_target: 'Chưa đạt mục tiêu', in_progress: 'Đang thực hiện', partial_period: 'Chọn trọn tháng để nghiệm thu', insufficient_data: 'Chưa đủ dữ liệu nghiệm thu', period_mismatch: 'Chọn từ ngày 1 để đối chiếu mục tiêu tháng', profile_mismatch: 'Điều kiện đo khác điều kiện đã chốt KPI'};
  const roleNames = {unclassified: 'Chưa phân loại', primary: 'Từ khóa chính', secondary: 'Từ khóa phụ'};
  const counts = new Intl.NumberFormat('vi-VN');
  const text = (tag, value, cls) => S.element(tag, value ?? '—', cls);
  const cell = value => { const td = text('td', ''); td.append(value?.nodeType ? value : text('span', value)); return td; };
  function period() { return S.validPeriod($('#seo-start').value, $('#seo-end').value); }
  const comparison = S.comparisonControls('seo', period);
  function profileName(profile) { return `${({desktop: 'Máy tính', mobile: 'Điện thoại', unspecified: 'Chưa rõ thiết bị'})[profile.device]}${profile.location ? ' · ' + profile.location : ''}${profile.language ? ' · ' + profile.language : ''}`; }
  function tab(key, update = true) {
    if (key === 'work') key = 'kpi';
    if (!['overview', 'keywords', 'content', 'kpi', 'reports'].includes(key)) key = 'overview';
    document.querySelectorAll('[data-seo-tab]').forEach(button => { button.setAttribute('aria-selected', String(button.dataset.seoTab === key)); button.tabIndex = button.dataset.seoTab === key ? 0 : -1; });
    document.querySelectorAll('.seo-tabpanel').forEach(panel => { panel.hidden = panel.id !== 'seo-panel-' + key; });
    if (update) { const url = new URL(location.href); url.searchParams.set('tab', key); history.replaceState(null, '', url); }
  }
  function showTab(key, selector = '#seo-tab-' + key) {
    tab(key);
    const target = $(selector);
    if (!target) return;
    if (!target.matches('button, a, input, select')) target.tabIndex = -1;
    target.focus({preventScroll: true});
    target.scrollIntoView({block: 'center'});
  }
  function reportLinks() {
    const applied = data?.comparison;
    const query = new URLSearchParams({sources: 'seo,ga4,gsc', ...(data?.period || period()), comparison: applied?.mode || 'previous'});
    if (applied?.mode === 'custom') { query.set('comparison_start', applied.start); query.set('comparison_end', applied.end); }
    if (data?.profile) query.set('seo_profile', data.profile);
    document.querySelectorAll('[data-seo-report-link]').forEach(link => {
      link.href = '/workspace/reports/combined?' + query;
      link.hidden = !data.permissions.create_report;
    });
  }
  function renderRankOverview() {
    const panel = $('#seo-rank-overview'), summary = data.rank_overview;
    if (!panel || !summary) return;
    const hasKeywords = summary.total > 0;
    panel.querySelector('[data-rank-overview-title]').textContent = summary.title;
    const scope = panel.querySelector('[data-rank-overview-scope]');
    scope.textContent = 'Spineditor · ' + counts.format(summary.total) + ' từ đang theo dõi';
    scope.hidden = !hasKeywords;
    panel.querySelector('[data-rank-overview-list]').hidden = !hasKeywords;
    panel.querySelector('[data-rank-overview-empty]').hidden = hasKeywords;
    panel.querySelector('[data-rank-overview-link]').hidden = !hasKeywords;
    panel.querySelector('[data-rank-overview-group="outside"]').hidden = !summary.counts.outside;
    panel.querySelectorAll('[data-rank-overview-count]').forEach(node => {
      node.textContent = counts.format(summary.counts[node.dataset.rankOverviewCount]);
    });
    panel.hidden = false;
  }
  function renderOverview() {
    document.querySelectorAll('[data-seo-stat]').forEach(node => { node.textContent = counts.format(data.stats[node.dataset.seoStat]); });
    $('#seo-website-label').textContent = data.website || 'Chưa có website';
    const caption = $('#seo-period-caption'); if (caption) caption.textContent = 'Đang xem: ' + S.date(data.period.start) + ' – ' + S.date(data.period.end);
    $('#seo-month').value = data.period.end.slice(0, 7);
    window.VioReportCharts.renderDonut($('#seo-distribution'), data.distribution.map(row => ({label: row.label, value: row.count})), {
      label: 'từ khóa', format: value => counts.format(value), maxSlices: 6,
      emptyText: 'Nhập bộ từ khóa để xem phân bố thứ hạng.',
    });
    $('#seo-rank-note').textContent = data.stats.total ? `${data.stats.ranked}/${data.stats.total} từ có vị trí trong kỳ. Ngày đo của từng dòng được ghi tại tab Từ khóa.` : 'Chưa có bộ từ khóa. Nhập file đầu tiên tại tab Từ khóa.';
    const select = $('#seo-profile'); select.replaceChildren(...data.profiles.map(profile => { const option = text('option', profileName(profile)); option.value = profile.id; return option; }));
    if (!data.profiles.length) { const option = text('option', 'Chưa có bản thứ hạng'); option.value = ''; select.append(option); }
    select.value = data.profile;
    renderRankOverview();
    renderAnalysis();
  }
  function renderAnalysis() {
    const analysis = data.analysis, compare = data.comparison;
    $('#seo-comparison-panel').hidden = !analysis || compare.mode === 'none';
    if (!analysis) return;
    const model = analysis.movement;
    $('#seo-movement-scope').textContent = `${compare.label || 'Kỳ liền trước'}: ${S.date(compare.current_start || data.period.start)} – ${S.date(compare.current_end || data.period.end)} / ${S.date(compare.start)} – ${S.date(compare.end)}${compare.current_days !== compare.comparison_days ? ' · Khác số ngày' : ''}`;
    $('#seo-movement-coverage').textContent = `${model.comparable}/${model.total} từ đủ hai kỳ`;
    $('#seo-movement-cards').replaceChildren(...[['up','Lên hạng'],['down','Xuống hạng'],['stable','Giữ hạng'],['entered_top10','Vào Top 10'],['left_top10','Rời Top 10'],['unavailable','Thiếu dữ liệu đối chiếu']].map(([key,label]) => {
      const card = text('article', '', 'seo-movement-card'); card.dataset.movement = key; card.append(text('strong', counts.format(model[key])), text('span', label)); return card;
    }));
    $('#seo-role-cards').replaceChildren(...analysis.roles.map(role => {
      const card = text('article', '', 'seo-role-card'), bar = text('div', '', 'seo-role-bar');
      bar.style.setProperty('--seo-role-share', (role.total ? role.top10 / role.total * 100 : 0) + '%');
      card.append(text('h3', role.label), text('strong', `${role.top10}/${role.total} từ Top 10`), bar, text('small', `${role.measured}/${role.total} có phép đo · ${role.committed} đánh dấu cam kết`)); return card;
    }));
  }
  function filtered() {
    const search = $('#seo-keyword-search').value.trim().toLocaleLowerCase('vi');
    const rank = $('#seo-rank-filter').value, movement = $('#seo-change-filter').value, sort = $('#seo-sort').value;
    return data.keywords.filter(row => (!search || (row.keyword + ' ' + row.topic).toLocaleLowerCase('vi').includes(search))
      && ($('#seo-role-filter').value === 'all' || row.role === $('#seo-role-filter').value)
      && ($('#seo-segment-filter').value === 'all' || (row.segment || 'general') === $('#seo-segment-filter').value)
      && ($('#seo-commit-filter').value === 'all' || Boolean(row.committed) === ($('#seo-commit-filter').value === 'yes'))
      && (rank === 'all' || rank === 'unknown' && ['unknown','not_measured'].includes(row.state) || rank === 'outside' && (row.state === 'outside_top100' || row.rank > 100) || rank.startsWith('top') && row.rank !== null && row.rank <= Number(rank.slice(3)))
      && (movement === 'all' || movement === row.movement || movement === 'entered_top10' && row.rank !== null && row.rank <= 10 && (row.previous_period_rank > 10 || row.previous_period_state === 'outside_top100')
        || movement === 'left_top10' && row.previous_period_rank !== null && row.previous_period_rank <= 10 && (row.rank > 10 || row.state === 'outside_top100')))
      .sort((a,b) => (sort === 'rank' ? (a.rank ?? Infinity) - (b.rank ?? Infinity) : sort === 'up' ? (b.change ?? -Infinity) - (a.change ?? -Infinity) : sort === 'down' ? (a.change ?? Infinity) - (b.change ?? Infinity) : 0) || a.keyword.localeCompare(b.keyword, 'vi'));
  }
  function roleSelect(row) {
    const select = document.createElement('select'); select.setAttribute('aria-label', 'Vai trò của ' + row.keyword);
    for (const [key, label] of Object.entries(roleNames)) { const option = text('option', label); option.value = key; select.append(option); }
    select.value = row.role; select.disabled = !data.permissions.edit; return select;
  }
  async function saveKeywords(changes) { await S.api(S.base + '/seo/keywords', {client_id: S.scope.client_id, changes}); await load(); S.message('Đã lưu phân loại. Để cập nhật bộ KPI, chốt phiên bản mới trong Cam kết KPI.'); }
  function renderKeywords() {
    const rows = filtered(), pages = Math.max(1, Math.ceil(rows.length / 20)); page = Math.min(page, pages);
    const nodes = rows.slice((page - 1) * 20, page * 20).map(row => {
      const tr = document.createElement('tr'), name = text('div', row.keyword, 'seo-keyword');
      const topic = document.createElement('input'); topic.type = 'text'; topic.maxLength = 160; topic.value = row.topic; topic.placeholder = 'Nhóm chủ đề'; topic.setAttribute('aria-label', 'Nhóm của ' + row.keyword); topic.disabled = !data.permissions.edit; name.append(topic);
      const role = roleSelect(row), roleGroup = text('div', '', 'seo-keyword-types'), segment = document.createElement('select');
      if (row.role_origin === 'gsc') name.append(text('small', row.role_reviewed ? 'GSC · Đã duyệt phân loại' : 'GSC · Phân loại gợi ý, chờ duyệt', 'seo-date'));
      segment.setAttribute('aria-label', 'Phạm vi của ' + row.keyword);
      for (const [key, label] of [['general', 'Tổng quát'], ['niche', 'Từ khóa ngách']]) { const option = text('option', label); option.value = key; segment.append(option); }
      segment.value = row.segment || 'general'; segment.disabled = !data.permissions.edit; roleGroup.append(role, segment);
      const committed = document.createElement('input'); committed.type = 'checkbox'; committed.checked = Boolean(row.committed); committed.disabled = !data.permissions.edit; committed.setAttribute('aria-label', 'Cam kết: ' + row.keyword);
      const rank = text('div', row.rank === null ? (row.state === 'outside_top100' ? '>100' : '—') : row.rank, 'seo-rank'); rank.append(text('small', row.observed_date ? S.date(row.observed_date) : 'Chưa đo trong kỳ', 'seo-date'));
      const change = text('div', data.comparison.mode === 'none' ? 'Đang tắt đối chiếu' : row.change === null ? ({entered_top100:'Vào Top 100',left_top100:'Rời Top 100',outside_top100:'Cả hai kỳ ngoài Top 100'})[row.movement] || 'Chưa đủ hai kỳ' : row.change === 0 ? 'Giữ hạng' : (row.change > 0 ? '↑ ' : '↓ ') + Math.abs(row.change) + ' bậc', row.change > 0 || row.movement === 'entered_top100' ? 'seo-up' : row.change < 0 || row.movement === 'left_top100' ? 'seo-down' : '');
      if (row.previous_period_rank !== null) change.append(text('small', 'Kỳ trước: ' + row.previous_period_rank, 'seo-date'));
      if (row.previous_observed_date) change.append(text('small', 'Đo ' + S.date(row.previous_observed_date), 'seo-date'));
      tr.append(cell(name), cell(roleGroup), cell(committed), cell(rank), cell(change), cell(S.link(row.url, 'Xem trang ↗')));
      if (data.permissions.edit) { const save = text('button', 'Lưu', 'ov-button ov-secondary'); save.type = 'button'; save.setAttribute('aria-label', 'Lưu ' + row.keyword); save.addEventListener('click', () => S.busy(save, () => saveKeywords([{id: row.id, role: role.value, segment: segment.value, committed: committed.checked, topic: topic.value, version: row.version}]))); tr.append(cell(save)); }
      return tr;
    });
    $('#seo-keywords-rows').replaceChildren(...nodes); $('#seo-keywords-empty').hidden = rows.length > 0;
    $('#seo-page-label').textContent = `Trang ${page}/${pages} · ${rows.length} từ`; $('#seo-prev').disabled = page <= 1; $('#seo-next').disabled = page >= pages;
    $('#seo-compare-label').textContent = data.comparison.mode === 'none' ? 'Đang tắt đối chiếu.' : `${S.date(data.period.start)} – ${S.date(data.period.end)} so với ${S.date(data.comparison.start)} – ${S.date(data.comparison.end)} · Cùng điều kiện đo; ngày đo được ghi ở từng dòng.`;
    $('#seo-import-history').replaceChildren(...data.imports.map(row => { const li = text('li', ''); const main = text('span', row.filename); main.append(text('small', profileName(row.metadata), 'seo-date')); li.append(main, text('span', window.VioFormat?.timestamp?.(row.confirmed_at) || new Date(row.confirmed_at).toLocaleString('vi-VN', {timeZone: S.scope.timezone}))); return li; }));
  }
  function renderPlan() {
    const plan = data.plan;
    $('#seo-plan-version').textContent = plan.version ? 'Phiên bản ' + plan.version : 'Chưa thiết lập';
    const actual = plan.top10 === null ? '—' : counts.format(plan.top10), measured = plan.measured === null ? '—' : counts.format(plan.measured);
    $('#seo-plan-result').replaceChildren(text('strong', plan.keyword_count ? `${actual}/${counts.format(plan.required)} từ cần đạt` : 'Chưa chốt mục tiêu'),
      text('p', states[plan.status] || 'Đang kiểm tra'),
      text('p', plan.keyword_count ? `Bộ đã chốt: ${plan.keyword_count} từ · Mục tiêu ${plan.top10_percent}% · Có phép đo: ${measured}/${plan.keyword_count}.` : 'Đánh dấu từ thuộc cam kết tại tab Từ khóa, rồi chốt mục tiêu cho tháng.'));
    if (plan.keyword_count) {
      const progress = text('div', '', 'seo-plan-progress'), fill = text('span');
      const ratio = plan.top10 !== null && plan.required > 0 ? plan.top10 / plan.required : null;
      fill.style.width = (ratio === null ? 0 : Math.min(100, ratio * 100)) + '%'; progress.append(fill); $('#seo-plan-result').append(progress);
      $('#seo-plan-result').append(text('small', ratio === null ? plan.required === 0 ? 'Mục tiêu 0%; không tính tỷ lệ hoàn thành.' : 'Chưa đánh giá trong kỳ/điều kiện đang chọn.' : new Intl.NumberFormat('vi-VN',{style:'percent',maximumFractionDigits:2}).format(ratio) + ' số từ cần đạt' + (plan.period_complete === false ? ' · Kết quả tạm thời, chưa chốt trọn tháng.' : '')));
    }
    $('#seo-plan-detail').hidden = !(plan.keywords || []).length;
    $('#seo-plan-keywords').replaceChildren(...(plan.keywords || []).map(row => {
      const tr = document.createElement('tr'), known = row.rank !== null || row.state === 'outside_top100';
      tr.append(cell(row.keyword), cell(row.rank ?? (row.state === 'outside_top100' ? '>100' : '—')), cell(S.date(row.observed_date)), cell(!known ? 'Chưa có phép đo' : row.rank !== null && row.rank <= 10 ? 'Đạt Top 10' : 'Chưa vào Top 10')); return tr;
    }));
    $('#seo-plan-month').value = plan.month; $('#seo-plan-percent').value = plan.top10_percent ?? '';
    $('#seo-plan-context').textContent = `Danh sách hiện tại có ${data.keywords.filter(row => row.committed).length} từ thuộc cam kết. Chốt lại sẽ tạo phiên bản mới cho tháng ${plan.month}; báo cáo đã lưu giữ nguyên.`;
  }
  function shareSuggestion() {
    const plan = data?.project?.plan;
    if (plan?.template !== 'monthly_seo' || !plan.share_pages || $('#seo-work-kind').value !== 'social_share') return null;
    const month = data.project.timeline?.months.find(row => row.month === $('#seo-work-month').value);
    const articles = month?.items.find(row => row.key === 'new_articles');
    if (articles?.actual == null || articles.actual * plan.share_pages > Number($('#seo-work-actual').max)) return null;
    const share = month.items.find(row => row.key === 'social_share');
    return {articles: articles.actual, pages: plan.share_pages, planned: share?.target};
  }

  function renderShareSuggestion() {
    const hint = $('#seo-share-hint');
    if (!hint) return;
    const suggestion = shareSuggestion();
    hint.hidden = !suggestion;
    if (suggestion) {
      const {articles, pages} = suggestion;
      $('#seo-share-reading').textContent = `${articles} bài đã đăng và duyệt × ${pages} trang = ${articles * pages} lượt dự kiến. Kiểm tra số lượt thực tế trước khi nghiệm thu.`;
    }
  }

  function editWork(row) {
    workEditing = row; $('#seo-work-name').value = row?.title || ''; $('#seo-work-month').value = row?.month || data.period.end.slice(0, 7); $('#seo-work-category').value = row?.category || 'technical'; $('#seo-work-target').value = row?.target ?? 1; $('#seo-work-actual').value = row?.actual ?? 0; $('#seo-work-evidence').value = row?.evidence || ''; $('#seo-work-kind').value = row?.kind || 'other'; $('#seo-work-verified').checked = Boolean(row?.verified); $('#seo-work-accepted-date').value = row?.accepted_date || ''; S.message('', false, $('#seo-work-error'));
    renderShareSuggestion();
    $('#seo-work-dialog').showModal();
  }
  function renderWork() {
    $('#seo-work-rows').replaceChildren(...data.work.map(row => { const tr = document.createElement('tr'), title = text('div', row.title); title.append(text('small', row.verified ? 'Đã nghiệm thu · ' + S.date(row.accepted_date) : 'Chưa nghiệm thu · chưa tính KPI', 'seo-date')); tr.append(cell(title), cell(row.month), cell(counts.format(row.target)), cell(counts.format(row.actual)), cell(S.link(row.evidence))); if (data.permissions.edit) { const button = text('button', 'Cập nhật', 'ov-button ov-secondary'); button.type = 'button'; button.addEventListener('click', () => editWork(row)); tr.append(cell(button)); } return tr; })); $('#seo-work-empty').hidden = data.work.length > 0;
  }
  async function sources(ticket) {
    const query = new URLSearchParams({...data.period, comparison: data.comparison.mode});
    if (data.comparison.mode === 'custom') {
      query.set('comparison_start', data.comparison.start); query.set('comparison_end', data.comparison.end);
    }
    await Promise.all(['ga4', 'gsc'].map(async source => {
      const link = document.querySelector(`[data-seo-source-report="${source}"]`);
      link.hidden = true;
      try {
        const report = await S.api(S.base + '/data/' + source + '?' + query);
        if (ticket !== generation) return;
        S.sourceReports[source] = report; document.dispatchEvent(new CustomEvent('vio:seo-source', {detail: {source, report}}));
        const label = $('#seo-source-' + source), metric = report.metrics.find(row => row.key === (source === 'ga4' ? 'active_users' : 'clicks'));
        label.textContent = report.state === 'ready' ? `${metric?.label || 'Dữ liệu đã lưu'}: ${window.VioDataFormat.format(metric?.value, metric?.unit || 'count', metric?.currency)}` : 'Chưa có bản dữ liệu trong kỳ';
        if (report.state === 'ready') { link.hidden = false; link.href = '/workspace/reports/data?source=' + source + '&' + query; }
      } catch (error) { if (ticket === generation) { $('#seo-source-' + source).textContent = error.message; S.sourceReports[source] = null; S.sourceErrors[source] = error.message; document.dispatchEvent(new CustomEvent('vio:seo-source', {detail: {source, report: null}})); } }
    }));
  }
  async function sourceConnections(ticket) {
    try {
      const result = await S.api(S.base + '/integrations');
      if (ticket !== generation || result.workspace.id !== S.scope.workspace_id || result.selected_client?.id !== S.scope.client_id) return;
      S.sourceConnections = Object.fromEntries(result.connections.filter(row => ['ga4', 'gsc'].includes(row.platform_id)
        && row.workspace_id === S.scope.workspace_id && row.client_id === S.scope.client_id).map(row => [row.platform_id, row]));
      document.dispatchEvent(new CustomEvent('vio:seo-source'));
    } catch (_) {
      // The exact-period report states still work if the connection catalogue is unavailable.
    }
  }
  function sourceIssue(source) {
    const report = S.sourceReports?.[source], connection = S.sourceConnections?.[source];
    const error = report?.latest_sync?.error_code;
    if (data?.effectiveness?.sources?.[source]?.state === 'wrong_website') return 'wrong_website';
    if (report?.availability === 'not_configured' || error === 'provider_setup_required') return 'setup';
    if (report?.connection?.status === 'reauth_required' || error === 'provider_reauth'
        || connection?.state === 'expired' && connection.id === report?.connection?.id && connection.version === report.connection.version) return 'reauth';
    if (error === 'provider_scopes') return 'scopes';
    return null;
  }
  async function load() {
    if (!S.scope.client_id) { S.message('Chọn hoặc tạo khách hàng tại Tổng quan trước khi sử dụng SEO.', true); return; }
    const ticket = ++generation, query = new URLSearchParams({...period(), ...comparison.value(), client_id: S.scope.client_id});
    if ($('#seo-profile').value) query.set('profile', $('#seo-profile').value);
    S.message('Đang tải dữ liệu SEO…');
    const next = await S.api(S.base + '/seo?' + query);
    if (ticket !== generation) return;
    data = next; S.data = next; S.sourceReports = {}; S.sourceErrors = {}; S.sourceConnections = {}; renderOverview(); renderKeywords(); renderPlan(); renderWork(); reportLinks();
    const url = new URL(location.href);
    for (const key of ['start','end','profile','comparison','comparison_start','comparison_end']) { const value = query.get(key); if (value) url.searchParams.set(key, value); else url.searchParams.delete(key); }
    history.replaceState(null, '', url.pathname + url.search);
    document.querySelectorAll('.seo-edit').forEach(node => { node.hidden = !data.permissions.edit; });
    S.message(''); document.dispatchEvent(new CustomEvent('vio:seo-loaded', {detail: data}));
    await Promise.all([sources(ticket), sourceConnections(ticket)]);
  }
  document.querySelectorAll('[data-seo-tab]').forEach(button => button.addEventListener('click', () => tab(button.dataset.seoTab)));
  document.querySelectorAll('[data-seo-goto]').forEach(link => link.addEventListener('click', event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    showTab(link.dataset.seoGoto, link.dataset.seoGoto === 'reports' ? '#seo-report-prep-title' : undefined);
  }));
  $('#seo-rank-overview a')?.addEventListener('click', event => {
    event.preventDefault();
    tab('overview');
    const chart = $('#seo-distribution');
    chart.tabIndex = -1;
    chart.focus({preventScroll: true});
    chart.scrollIntoView({block: 'center'});
  });
  document.querySelector('.seo-tabs').addEventListener('keydown', event => { const tabs = [...document.querySelectorAll('[data-seo-tab]')], index = tabs.indexOf(document.activeElement); if (index >= 0 && ['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) { event.preventDefault(); const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length; tabs[next].focus(); tab(tabs[next].dataset.seoTab); } });
  $('#seo-period-form').addEventListener('submit', event => { event.preventDefault(); S.busy(event.submitter, load); });
  $('#seo-month').addEventListener('change', () => { try { const range = S.monthRange($('#seo-month').value); $('#seo-start').value = range.start; $('#seo-end').value = range.end; S.busy(null, load); } catch (error) { S.message(error.message, true); } });
  $('#seo-client-select').addEventListener('change', () => S.busy(null, async () => { await S.api(S.base + '/clients/' + $('#seo-client-select').value + '/select', {}); location.assign('/workspace/seo'); }));
  for (const id of ['seo-keyword-search', 'seo-role-filter', 'seo-segment-filter', 'seo-commit-filter', 'seo-rank-filter', 'seo-change-filter', 'seo-sort']) $('#' + id).addEventListener(id === 'seo-keyword-search' ? 'input' : 'change', () => { if (data) { page = 1; renderKeywords(); } });
  $('#seo-prev').addEventListener('click', () => { page--; renderKeywords(); }); $('#seo-next').addEventListener('click', () => { page++; renderKeywords(); });
  $('#seo-commit-page').addEventListener('click', event => S.busy(event.currentTarget, async () => { const rows = filtered().slice((page - 1) * 20, page * 20); if (!rows.length) throw new Error('Chưa có từ khóa để chọn.'); await saveKeywords(rows.map(row => ({id: row.id, role: row.role, segment: row.segment || 'general', committed: true, topic: row.topic, version: row.version}))); }));
  let importReturnTab = 'keywords';
  function openImport(target = null, returnTab = 'keywords') {
    if (!data || !data.permissions.edit) return;
    const profile = data.profiles.find(row => row.id === data.profile);
    importTarget = target === 'previous' ? {start: data.comparison.start, end: data.comparison.end} : target === 'current' ? data.period : null;
    importReturnTab = returnTab;
    preview = null; $('#seo-upload-website').value = data.website || S.scope.website || '';
    $('#seo-upload-file').value = '';
    $('#seo-upload-device').value = profile?.device || 'unspecified';
    $('#seo-upload-location').value = profile?.location || ''; $('#seo-upload-language').value = profile?.language || '';
    $('#seo-import-context').textContent = importTarget ? `Kỳ cần bổ sung ${S.date(importTarget.start)} – ${S.date(importTarget.end)}. Giữ cùng website, thiết bị, địa điểm và ngôn ngữ để so sánh.` : 'Dùng ngày đo thực tế trong file Spineditor.';
    $('#seo-import-preview').hidden = true; $('#seo-upload-form').hidden = false;
    S.message('', false, $('#seo-import-error')); $('#seo-import-dialog').showModal();
  }
  document.querySelectorAll('[data-seo-import]').forEach(button => button.addEventListener('click', () => openImport()));
  function importOutsidePeriod() {
    return importTarget && (preview.end < importTarget.start || preview.start > importTarget.end);
  }
  $('#seo-upload-form').addEventListener('submit', event => {
    event.preventDefault();
    S.busy(event.submitter, async () => {
      const file = $('#seo-upload-file').files[0];
      if (!file || file.size > 2 * 1024 * 1024) throw new Error('Chọn Excel/CSV tối đa 2 MB.');
      const query = new URLSearchParams({client_id: S.scope.client_id, filename: file.name, website: $('#seo-upload-website').value,
        device: $('#seo-upload-device').value, location: $('#seo-upload-location').value, language: $('#seo-upload-language').value});
      preview = await S.api(S.base + '/seo/import-preview?' + query, file, true);
      const summary = $('#seo-preview-summary');
      summary.replaceChildren(text('strong', preview.count + ' dòng từ khóa'),
        text('p', `${preview.ranked} có vị trí · ${preview.unknown} chưa xác định`),
        text('p', `Ngày đo trong file ${S.date(preview.start)} – ${S.date(preview.end)}`),
        text('p', preview.metadata.website));
      if (importOutsidePeriod()) summary.append(text('p', 'Ngày đo trong file nằm ngoài kỳ cần bổ sung. Hãy chọn file đúng kỳ hoặc đổi kỳ xem sau khi nhập.', 'seo-help'));
      $('#seo-preview-rows').replaceChildren(...preview.rows.map(row => {
        const tr = document.createElement('tr'); tr.append(cell(row.keyword), cell(row.rank ?? (row.state === 'outside_top100' ? '>100' : '—')),
          cell(row.previous_rank ?? '—'), cell(S.date(row.observed_date))); return tr;
      }));
      $('#seo-upload-form').hidden = true; $('#seo-import-preview').hidden = false;
      $('#seo-dates-confirmed').checked = false; $('#seo-import-confirm').disabled = true;
      S.message('', false, $('#seo-import-error'));
    }, $('#seo-import-error'));
  });
  $('#seo-dates-confirmed').addEventListener('change', () => { $('#seo-import-confirm').disabled = !$('#seo-dates-confirmed').checked; });
  $('#seo-preview-back').addEventListener('click', () => { preview = null; $('#seo-upload-form').hidden = false; $('#seo-import-preview').hidden = true; });
  $('#seo-import-confirm').addEventListener('click', event => S.busy(event.currentTarget, async () => {
    if (!preview || !$('#seo-dates-confirmed').checked) throw new Error('Xác nhận ngày đo trước khi nhập.');
    const response = await S.api(S.base + '/seo/confirm', {client_id: S.scope.client_id, import_id: preview.id, dates_confirmed: true});
    $('#seo-import-dialog').close();
    if (!importTarget) {
      $('#seo-profile').value = ''; const earliest = new Date(preview.end + 'T00:00:00Z'); earliest.setUTCDate(earliest.getUTCDate() - 89);
      $('#seo-start').value = preview.start > earliest.toISOString().slice(0, 10) ? preview.start : earliest.toISOString().slice(0, 10); $('#seo-end').value = preview.end;
    }
    const note = importOutsidePeriod() ? ' Ngày đo thuộc kỳ khác. Chỉnh khoảng ngày để xem file vừa nhập.' : '';
    await load();
    showTab(importReturnTab);
    S.message(response.message + note); preview = null; importTarget = null;
  }, $('#seo-import-error')));
  $('#seo-plan-form').addEventListener('submit', event => { event.preventDefault(); S.busy(event.submitter, async () => { if ($('#seo-plan-month').value !== data.plan.month) throw new Error('Chọn đúng tháng ở bộ lọc đầu trang để đọc phiên bản và chốt KPI.'); await S.api(S.base + '/seo/plan', {client_id: S.scope.client_id, month: $('#seo-plan-month').value, top10_percent: Number($('#seo-plan-percent').value), version: data.plan.version, profile: data.profile}); await load(); S.message('Đã chốt phiên bản mục tiêu theo bộ từ khóa cam kết hiện tại.'); }); });
  $('#seo-add-work').addEventListener('click', () => editWork(null));
  $('#seo-work-kind')?.addEventListener('change', renderShareSuggestion);
  $('#seo-work-month')?.addEventListener('change', renderShareSuggestion);
  $('#seo-share-suggest')?.addEventListener('click', () => {
    const suggestion = shareSuggestion();
    if (!suggestion) return;
    $('#seo-work-actual').value = suggestion.articles * suggestion.pages;
    if (suggestion.planned != null && suggestion.planned <= Number($('#seo-work-target').max)) $('#seo-work-target').value = suggestion.planned;
    $('#seo-work-verified').checked = false;
  });
  $('#seo-work-form').addEventListener('submit', event => { event.preventDefault(); S.busy(event.submitter, async () => { await S.api(S.base + '/seo/work', {client_id: S.scope.client_id, id: workEditing?.id || null, version: workEditing?.version || 0, month: $('#seo-work-month').value, title: $('#seo-work-name').value, category: $('#seo-work-category').value, target: Number($('#seo-work-target').value), actual: Number($('#seo-work-actual').value), evidence: $('#seo-work-evidence').value, kind: $('#seo-work-kind').value, verified: $('#seo-work-verified').checked, accepted_date: $('#seo-work-accepted-date').value || null}); $('#seo-work-dialog').close(); await load(); S.message('Đã lưu công việc SEO.'); }, $('#seo-work-error')); });
  async function start() { await S.ready(); if (!S.scope.client_id) { const clients = [...$('#seo-client-select').options].filter(option => option.value); if (clients.length === 1) { await S.api(S.base + '/clients/' + clients[0].value + '/select', {}); location.replace('/workspace/seo'); return; } } const query = new URLSearchParams(location.search), today = S.today(), range = S.monthRange(today.slice(0, 7)); $('#seo-start').value = query.get('start') || range.start; $('#seo-end').value = query.get('end') || today; $('#seo-month').value = $('#seo-end').value.slice(0, 7); if (query.get('profile')) { const option = text('option', 'Đang tải điều kiện đo'); option.value = query.get('profile'); $('#seo-profile').append(option); $('#seo-profile').value = option.value; } comparison.update(); tab(query.get('tab'), false); await load(); }
  S.reload = load; S.setTab = tab; S.showTab = showTab; S.openImport = openImport;
  S.sourceIssue = sourceIssue; S.refreshSources = () => sources(generation);
  S.busy(null, start);
}());
