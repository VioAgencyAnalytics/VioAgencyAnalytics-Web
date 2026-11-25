(function () {
  'use strict';
  const print = document.querySelector('#compiled-print');
  if (print) {
    print.addEventListener('click', () => window.VioReportNotes ? window.VioReportNotes.print(print) : window.print());
    window.VioSEO?.ready().catch(error => window.VioSEO.message(error.message, true));
    return;
  }
  const S = window.VioSEO, form = document.querySelector('#compiled-builder-form');
  if (!S || !form) return;
  const builderUrl = location.pathname + location.search;
  const $ = selector => document.querySelector(selector);
  const templateData = $('#compiled-preset-data');
  const template = templateData ? JSON.parse(templateData.textContent) : null;
  let readySources = [], requestKey = null, requestFingerprint = null;
  let statusTicket = 0, catalogue, selectionEdited = false, wrongSearchSite = false;
  const comparison = S.comparisonControls('compiled', () => ({start:$('#compiled-start').value,end:$('#compiled-end').value}));
  const selected = name => [...document.querySelectorAll(`input[name="${name}"]:checked`)].map(input => input.value);
  function describeSelection() {
    $('#compiled-selection-note').textContent = `${selected('compiled-source').length} nguồn · ${selected('compiled-section').length} phần nội dung · Báo cáo riêng tư`;
    $('#compiled-profile-field').hidden = !selected('compiled-source').includes('seo');
    const params = new URLSearchParams({tab: 'reports'});
    try {
      const period = S.validPeriod($('#compiled-start').value, $('#compiled-end').value);
      for (const [key, value] of Object.entries({...period, ...comparison.value()})) params.set(key, value);
      if ($('#compiled-profile').value) params.set('profile', $('#compiled-profile').value);
    } catch (_) {
      // Incomplete date edits should not be passed back to the SEO page.
    }
    $('#compiled-seo-return').href = '/workspace/seo?' + params;
  }
  async function list() {
    const index = await S.api(S.base + '/compiled-reports');
    $('#compiled-saved-list').replaceChildren(...index.reports.map(row => { const a = S.element('a'); a.href = '/workspace/reports/combined?report=' + row.id; const body = S.element('div'); body.append(S.element('strong', row.name), S.element('small', `${S.date(row.start_date)} – ${S.date(row.end_date)} · ${new Date(row.created_at).toLocaleString('vi-VN', {timeZone: S.scope.timezone})}`)); a.append(body, S.element('span', 'Mở báo cáo →')); return a; }));
    $('#compiled-saved-empty').textContent = index.reports.length ? '' : 'Chưa có báo cáo tổng hợp đã lưu cho khách hàng này.';
    form.hidden = !index.permissions.create;
    if (!index.permissions.create) S.message('Bạn có quyền xem các báo cáo đã lưu. Owner, Admin hoặc Thành viên có thể tạo bản mới.');
  }
  function pickReadySources() {
    for (const input of document.querySelectorAll('input[name="compiled-source"]')) {
      if (!input.disabled) input.checked = readySources.includes(input.value);
    }
    describeSelection();
  }
  function renderSeoStatus(seo) {
    const node = $('[data-source-status="seo"]');
    if (!seo) { node.textContent = 'Chưa kiểm tra được dữ liệu SEO'; return; }
    const measured = seo.comparison?.coverage?.current?.observed ?? seo.keywords.filter(row => row.observed_date).length;
    const hasData = seo.import_ids.length || seo.work.length || seo.content?.items?.length || seo.keywords.length || seo.project?.plan;
    if (hasData) readySources.push('seo');
    node.textContent = measured ? `${measured} từ có ngày đo trong kỳ`
      : hasData ? 'Có dữ liệu SEO đã lưu · chưa có ngày đo thứ hạng trong kỳ' : 'Chưa có dữ liệu SEO đã lưu trong kỳ';
    const select = $('#compiled-profile');
    const options = seo.profiles.map(profile => {
      const label = {desktop: 'Máy tính', mobile: 'Điện thoại', unspecified: 'Chưa rõ thiết bị'}[profile.device];
      const option = S.element('option', [label, profile.location, profile.language].filter(Boolean).join(' · '));
      option.value = profile.id;
      return option;
    });
    select.replaceChildren(...(options.length ? options : [new Option('Chưa có bản thứ hạng', '')]));
    select.value = seo.profile || '';
  }
  async function sourceStatus() {
    const ticket = ++statusTicket, picker = $('#compiled-select-ready');
    for (const node of document.querySelectorAll('[data-source-status]')) node.textContent = 'Đang kiểm tra kỳ đã chọn…';
    picker.disabled = true;
    readySources = [];
    let period;
    try { period = S.validPeriod($('#compiled-start').value, $('#compiled-end').value); }
    catch (_) {
      for (const node of document.querySelectorAll('[data-source-status]')) node.textContent = 'Chọn đủ ngày hợp lệ để kiểm tra';
      return;
    }
    if (!catalogue) catalogue = S.api(S.base + '/data').catch(() => { catalogue = null; return null; });
    const query = new URLSearchParams(location.search);
    const profile = $('#compiled-profile').value || query.get('seo_profile');
    const seoParams = new URLSearchParams(period);
    if (profile) seoParams.set('profile', profile);
    const results = await Promise.allSettled([catalogue,
      S.api(S.base + '/data/ga4?' + new URLSearchParams(period)), S.api(S.base + '/data/gsc?' + new URLSearchParams(period)),
      S.api(S.base + '/seo?' + seoParams)]);
    if (ticket !== statusTicket) return;
    const [index, ga4, gsc, seo] = results.map(result => result.status === 'fulfilled' ? result.value : null);
    wrongSearchSite = seo?.effectiveness?.sources?.gsc?.state === 'wrong_website';
    for (const node of document.querySelectorAll('[data-source-status]')) {
      const source = node.dataset.sourceStatus;
      if (source === 'seo') continue;
      if (source === 'gsc' && wrongSearchSite) {
        node.textContent = 'Website đã chọn khác website báo cáo';
        continue;
      }
      const google = ['ga4', 'gsc'].includes(source);
      const row = google ? (source === 'ga4' ? ga4 : gsc) : index?.sources.find(row => row.source === source);
      if (!row) { node.textContent = 'Chưa kiểm tra được dữ liệu nguồn'; continue; }
      const snapshot = row.state === 'ready' ? row.snapshot : null;
      const matches = snapshot && (google || snapshot.start_date === period.start && snapshot.end_date === period.end);
      if (matches) readySources.push(source);
      if (snapshot) node.textContent = `${matches ? 'Có bản lưu' : 'Bản lưu gần nhất'} ${S.date(snapshot.start_date)} – ${S.date(snapshot.end_date)}`;
      else node.textContent = row.asset ? 'Chưa đồng bộ kỳ này' : 'Chưa chọn tài sản để đồng bộ';
    }
    renderSeoStatus(seo);
    picker.disabled = !readySources.length;
    if (!query.has('sources') && !template?.sources.length && !selectionEdited) pickReadySources();
    describeSelection();
  }
  form.addEventListener('change', event => {
    if (event.target.name === 'compiled-source') selectionEdited = true;
    describeSelection();
    if (['compiled-start', 'compiled-end', 'compiled-profile', 'compiled-month', 'compiled-range'].includes(event.target.id)) sourceStatus();
  });
  $('#compiled-select-ready').addEventListener('click', () => { selectionEdited = true; pickReadySources(); });
  $('#compiled-month').addEventListener('change', () => { try { const period = S.monthRange($('#compiled-month').value); $('#compiled-start').value = period.start; $('#compiled-end').value = period.end; $('#compiled-range').value = 'custom'; } catch (error) { S.message(error.message, true); } });
  $('#compiled-range').addEventListener('change', () => {
    if ($('#compiled-range').value === 'custom') return;
    const today = new Date(S.today() + 'T00:00:00Z');
    if ($('#compiled-range').value === 'last30') { const end = new Date(today); end.setUTCDate(end.getUTCDate() - 1); const start = new Date(end); start.setUTCDate(start.getUTCDate() - 29); $('#compiled-start').value = start.toISOString().slice(0, 10); $('#compiled-end').value = end.toISOString().slice(0, 10); }
    else { today.setUTCDate(0); const period = S.monthRange(today.toISOString().slice(0, 7)); $('#compiled-start').value = period.start; $('#compiled-end').value = period.end; }
  });
  $('#compiled-client-select').addEventListener('change', () => S.busy(null, async () => { await S.api(S.base + '/clients/' + $('#compiled-client-select').value + '/select', {}); location.assign(builderUrl); }));
  $('#compiled-refresh').addEventListener('click', event => S.busy(event.currentTarget, list));
  form.addEventListener('submit', event => { event.preventDefault(); S.busy(event.submitter, async () => {
    const period = S.validPeriod($('#compiled-start').value, $('#compiled-end').value), sources = selected('compiled-source'), sections = selected('compiled-section');
    if (!sources.length || !sections.length) throw new Error('Chọn ít nhất một nguồn và một phần nội dung.');
    if (wrongSearchSite && sources.includes('seo') && sources.includes('gsc')) {
      throw new Error('Chọn lại website Search Console hoặc bỏ chọn nguồn này khi tạo báo cáo SEO.');
    }
    const body = {client_id: S.scope.client_id, name: $('#compiled-name').value.trim(), ...period, ...comparison.value(), sources, sections};
    if (template) body.presentation = template.id;
    if (form.dataset.style) { body.style = form.dataset.style; body.palette = form.dataset.palette; }
    if (form.dataset.order) body.order = form.dataset.order;
    if (form.dataset.hidden) body.hidden = form.dataset.hidden;
    if (sources.includes('seo') && $('#compiled-profile').value) body.seo_profile = $('#compiled-profile').value;
    const fingerprint = JSON.stringify(body);
    if (fingerprint !== requestFingerprint) { requestKey = crypto.randomUUID().replaceAll('-', ''); requestFingerprint = fingerprint; }
    const response = await S.api(S.base + '/compiled-reports', {...body, request_key: requestKey});
    if (!/^\/workspace\/reports\/combined\?report=[a-f0-9]{32}$/.test(response.href)) throw new Error('Địa chỉ báo cáo không hợp lệ.');
    location.assign(response.href);
  }); });
  async function start() {
    await S.ready();
    if (!S.scope.client_id) { const clients = [...$('#compiled-client-select').options].filter(option => option.value); if (clients.length === 1) { await S.api(S.base + '/clients/' + clients[0].value + '/select', {}); location.replace(builderUrl); return; } form.hidden = true; throw new Error('Chọn khách hàng ở phía trên trước khi tạo báo cáo.'); }
    const query = new URLSearchParams(location.search), current = S.today(), range = S.monthRange(current.slice(0, 7));
    $('#compiled-start').value = query.get('start') || range.start; $('#compiled-end').value = query.get('end') || current;
    $('#compiled-month').value = $('#compiled-end').value.slice(0, 7);
    const sources = query.has('sources') ? query.get('sources').split(',') : template?.sources || [];
    document.querySelectorAll('input[name="compiled-source"]').forEach(input => { input.checked = sources.includes(input.value); });
    if (template?.source === 'seo') $('input[name="compiled-source"][value="seo"]').checked = true;
    if (template && !template.sections.includes('comparison')) $('#compiled-comparison').value = 'none';
    if (template?.sections.length === 1 && template.sections[0] === 'comparison') {
      $('#compiled-comparison option[value="none"]').disabled = true;
      if ($('#compiled-comparison').value === 'none') $('#compiled-comparison').value = 'previous';
    }
    $('#compiled-name').value = `${template?.name || (sources.includes('seo') ? 'Báo cáo SEO' : 'Báo cáo Marketing')} · ${S.scope.client_name} · ${$('#compiled-month').value}`;
    comparison.update(); await Promise.all([list(), sourceStatus()]); describeSelection();
  }
  S.busy(null, start);
}());
