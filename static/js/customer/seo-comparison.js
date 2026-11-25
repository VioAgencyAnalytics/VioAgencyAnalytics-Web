(function () {
  'use strict';
  const S = window.VioSEO, $ = selector => document.querySelector(selector);
  const panel = $('#seo-comparison-data');
  if (!S || !panel) return;
  const el = S.element, sources = {gsc: 'Search Console', ga4: 'Google Analytics 4'};
  const requests = new Map();
  let data, busy = false, timer = null, polling = false;

  function range(value) {
    return value?.start && value?.end ? `${S.date(value.start)} – ${S.date(value.end)}` : 'Chưa có ngày nguồn đã hoàn tất';
  }
  function inputs() {
    return {start: $('#seo-start').value, end: $('#seo-end').value, comparison: $('#seo-comparison').value,
      comparison_start: $('#seo-comparison-start').value, comparison_end: $('#seo-comparison-end').value};
  }
  function pending() {
    if (!data) return true;
    const value = inputs();
    return value.start !== data.period.start || value.end !== data.period.end || value.comparison !== data.comparison.mode
      || $('#seo-profile').value !== data.profile || $('#seo-client-select').value !== data.scope.client_id
      || value.comparison === 'custom' && (value.comparison_start !== data.comparison.start || value.comparison_end !== data.comparison.end);
  }
  function preview() {
    const target = $('#seo-comparison-preview');
    const unapplied = pending();
    try {
      const value = inputs(), previous = S.comparisonWindow(value, value.comparison, {start: value.comparison_start, end: value.comparison_end});
      const label = previous ? `Kỳ đối chiếu ${range(previous)}` : value.comparison === 'none' ? 'Đang tắt đối chiếu.' : 'Kỳ đang xem chưa bắt đầu.';
      target.textContent = label + (unapplied ? ' Nhấn Xem dữ liệu để áp dụng.' : '');
      target.dataset.pending = String(unapplied);
    } catch (error) { target.textContent = error.message; target.dataset.pending = 'true'; }
    panel.dataset.pending = String(unapplied);
    panel.querySelectorAll('button').forEach(node => { node.disabled = busy || unapplied; });
    const exportNote = $('#seo-report-filter-note');
    if (exportNote) exportNote.hidden = !unapplied;
  }
  function action(label, handler) {
    const button = el('button', label, 'ov-button ov-secondary'); button.type = 'button';
    button.disabled = busy || pending(); button.addEventListener('click', handler); return button;
  }
  function feedback(message = '', error = false) {
    S.message(message, error, $('#seo-comparison-feedback'));
  }
  function googlePeriod(source, kind) {
    const report = S.sourceReports?.[source];
    if (!report || kind === 'previous' && data.comparison.mode === 'none') return null;
    const comparison = report.comparison || {}, current = kind === 'current';
    const period = current ? {start: report.period?.data_start, end: report.period?.data_end} : comparison.period;
    const snapshot = current ? report.snapshot : comparison.snapshot;
    const job = current ? report.latest_sync : comparison.latest_sync;
    const syncing = ['queued', 'running'].includes(job?.status) || !current && comparison.status === 'syncing';
    const state = syncing ? 'syncing' : snapshot ? 'ready' : job?.status === 'failed' ? 'failed' : 'missing';
    return {source, kind, report, period, snapshot, job, state,
      canSync: report.permissions?.sync === true && report.connection?.status === 'connected'
        && !S.sourceIssue?.(source) && Boolean(report.asset?.id && period?.start && period?.end)};
  }
  function missingGoogle() {
    return Object.keys(sources).flatMap(source => ['current', 'previous'].map(kind => googlePeriod(source, kind)))
      .filter(value => value?.canSync && ['missing', 'failed'].includes(value.state));
  }
  function hasJobs() {
    return Object.keys(sources).some(source => ['current', 'previous'].some(kind => googlePeriod(source, kind)?.state === 'syncing'));
  }
  function schedule() {
    if (timer || polling || document.hidden || !hasJobs()) return;
    timer = window.setTimeout(poll, 6000);
  }
  async function poll() {
    timer = null;
    if (document.hidden || !data || busy) { schedule(); return; }
    const active = data; polling = true;
    try {
      await S.refreshSources();
      if (active === data && !hasJobs()) await S.reload();
    } catch (error) { feedback(error.message, true); }
    finally { polling = false; schedule(); }
  }
  async function sync(targets) {
    if (busy || pending() || !targets.length) return;
    const active = data, errors = [];
    busy = true; feedback('Đang gửi yêu cầu đồng bộ…'); render();
    try {
      for (const target of targets) {
        if (active !== data || pending()) break;
        const connection = target.report.connection;
        const key = [data.scope.client_id, connection.id, connection.version, target.report.asset.id, target.period.start, target.period.end].join('/');
        if (!requests.has(key)) requests.set(key, crypto.randomUUID());
        try {
          await S.api(S.base + '/connections/' + connection.id + '/sync', {client_id: data.scope.client_id,
            version: connection.version, start: target.period.start, end: target.period.end, request_key: requests.get(key)});
          requests.delete(key);
        } catch (error) {
          if (error.status && error.status < 500) requests.delete(key);
          errors.push(`${sources[target.source]} · ${target.kind === 'current' ? 'kỳ đang xem' : 'kỳ đối chiếu'} · ${error.message}`);
          if ([401, 403, 409].includes(error.status)) break;
        }
      }
      if (active === data) {
        feedback(errors.length ? errors.join(' ') : 'Đã xếp lịch đồng bộ. Kết quả sẽ tự cập nhật khi hoàn tất.', errors.length > 0);
        await S.refreshSources();
      }
    } finally { busy = false; if (active === data) render(); schedule(); }
    return errors;
  }
  function periodRow(title, period, label, state, note = '') {
    const node = el('div', '', 'seo-compare-period'), head = el('div');
    const status = el('span', label, 'seo-compare-status'); status.dataset.state = state;
    head.append(el('strong', title), status); node.append(head, el('small', range(period)));
    if (note) node.append(el('small', note));
    return node;
  }
  function rankSource() {
    const card = el('article', '', 'seo-compare-source'); card.append(el('h3', 'Thứ hạng Spineditor'));
    const coverage = data.comparison.coverage || {};
    for (const kind of ['current', 'previous']) {
      const current = kind === 'current', measured = coverage[kind];
      const observed = measured?.observed ?? data.keywords.filter(row => current ? row.observed_date : row.previous_observed_date).length;
      const known = measured?.measured ?? data.keywords.filter(row => current ? row.rank !== null || row.state === 'outside_top100' : row.previous_period_rank !== null || row.previous_period_state === 'outside_top100').length;
      const dates = measured?.last_date ? `Ngày đo ${S.date(measured.first_date)}${measured.first_date !== measured.last_date ? ' – ' + S.date(measured.last_date) : ''}` : '';
      const period = current ? {start: data.comparison.current_start, end: data.comparison.current_end} : data.comparison;
      const row = periodRow(current ? 'Kỳ đang xem' : 'Kỳ đối chiếu', period,
        observed ? `${known}/${data.keywords.length} từ có vị trí` : 'Cần nhập file', observed ? known === data.keywords.length ? 'ready' : 'partial' : 'missing', dates);
      if (data.permissions.edit) row.append(action((observed ? 'Bổ sung file ' : 'Nhập file ') + (current ? 'kỳ đang xem' : 'kỳ đối chiếu'), () => S.openImport(kind)));
      card.append(row);
    }
    const movement = data.analysis?.movement;
    card.append(el('p', `${movement?.comparable ?? 0}/${data.keywords.length} từ đủ hai kỳ, cùng điều kiện đo.`, 'seo-help'));
    return card;
  }
  function metricTable(items) {
    const table = el('table', '', 'seo-compare-metrics'), head = el('thead'), titles = el('tr'), body = el('tbody');
    for (const title of ['Chỉ số', 'Hiện tại', 'Đối chiếu']) titles.append(el('th', title));
    head.append(titles);
    for (const item of items) {
      const row = el('tr'), title = el('td', item.label);
      const value = (number) => window.VioDataFormat.format(number, item.unit, item.currency);
      const change = el('small', item.status === 'ready' ? item.summary : 'Chưa đủ dữ liệu hai kỳ');
      change.dataset.effect = item.effect || 'unavailable'; title.append(change);
      row.append(title, el('td', value(item.actual)), el('td', value(item.previous))); body.append(row);
    }
    table.append(head, body); return table;
  }
  function googleSource(source) {
    const card = el('article', '', 'seo-compare-source'), head = el('h3'), logo = document.createElement('img');
    logo.src = '/static/customer/platforms/' + (source === 'gsc' ? 'gsc.png' : 'ga4.svg'); logo.alt = '';
    head.append(logo, el('span', sources[source])); card.append(head);
    const report = S.sourceReports?.[source];
    const issue = S.sourceIssue?.(source);
    const manage = label => {
      const link = el('a', label + ' ↗', 'ov-button ov-secondary');
      link.href = '/workspace/integrations?platform=' + source;
      link.target = '_blank'; link.rel = 'noopener'; card.append(link);
    };
    if (issue === 'wrong_website') {
      card.append(el('p', 'Chọn tài sản Search Console khớp website báo cáo.', 'seo-help'));
      manage('Chọn lại website');
      return card;
    }
    if (!report) {
      card.append(el('p', S.sourceErrors?.[source] || 'Đang kiểm tra bản dữ liệu hai kỳ…', 'seo-help'));
    } else {
      for (const kind of ['current', 'previous']) {
        const value = googlePeriod(source, kind);
        const label = {ready: 'Đã có dữ liệu', syncing: 'Đang đồng bộ', failed: 'Cần thử lại', missing: 'Chưa có bản lưu'}[value.state];
        const row = periodRow(kind === 'current' ? 'Kỳ đang xem' : 'Kỳ đối chiếu', value.period, label, value.state);
        if (value.canSync && ['missing', 'failed'].includes(value.state)) {
          row.append(action(kind === 'current' ? 'Lấy dữ liệu kỳ đang xem' : 'Lấy dữ liệu kỳ đối chiếu', () => sync([value])));
        }
        card.append(row);
      }
      const comparison = report.comparison || {}, selected = source === 'gsc' ? ['clicks', 'impressions', 'ctr', 'position'] : ['organic_sessions'];
      const organic = report.tables.find(table => table.id === 'channels')?.rows.filter(row => row.sessionDefaultChannelGroup === 'Organic Search') || [];
      const items = selected.map(key => {
        const metric = report.metrics.find(row => row.key === key);
        return comparison.items?.find(item => item.key === key) || {
          key, label: ({clicks: 'Lượt nhấp', impressions: 'Hiển thị', ctr: 'CTR', position: 'Vị trí TB', organic_sessions: 'Phiên Organic Search'})[key],
          unit: metric?.unit || (key === 'ctr' ? 'percent' : key === 'position' ? 'number' : 'count'),
          actual: report.snapshot ? key === 'organic_sessions' ? organic.length === 1 ? organic[0].sessions : null : metric?.value ?? null : null, previous: null,
        };
      });
      card.append(metricTable(items));
      if (comparison.current_days !== comparison.comparison_days && comparison.period) {
        card.append(el('p', `${comparison.current_days} / ${comparison.comparison_days} ngày. Tổng hai kỳ giữ theo số ngày thực tế.`, 'seo-help'));
      }
      if (report.calendar?.timezone) card.append(el('p', 'Ngày báo cáo theo ' + report.calendar.timezone, 'seo-help'));
      if (comparison.status === 'unavailable') card.append(el('p', comparison.message, 'seo-help'));
    }
    if (issue === 'reauth' || issue === 'scopes') manage('Kết nối lại ' + sources[source]);
    else if (!report?.asset) manage('Quản lý kết nối ' + sources[source]);
    return card;
  }
  function render() {
    if (!data) return;
    panel.hidden = data.comparison.mode === 'none';
    $('#seo-comparison-dates').textContent = `${range({start: data.comparison.current_start, end: data.comparison.current_end})} so với ${range(data.comparison)}`;
    if (!panel.hidden) $('#seo-comparison-sources').replaceChildren(rankSource(), ...Object.keys(sources).map(googleSource));
    $('#seo-comparison-sync').hidden = !missingGoogle().length;
    preview(); schedule();
  }
  $('#seo-comparison-sync').addEventListener('click', () => S.busy(null, () => sync(missingGoogle()), $('#seo-comparison-feedback')));
  for (const id of ['seo-start', 'seo-end', 'seo-profile', 'seo-comparison', 'seo-comparison-start', 'seo-comparison-end']) {
    $('#' + id).addEventListener('input', preview); $('#' + id).addEventListener('change', preview);
  }
  document.addEventListener('vio:seo-loaded', event => {
    window.clearTimeout(timer); timer = null; data = event.detail; feedback(); render();
  });
  document.addEventListener('vio:seo-source', render);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { window.clearTimeout(timer); timer = null; } else schedule();
  });
  window.addEventListener('pagehide', () => window.clearTimeout(timer));
  S.seoPeriodPending = pending;
  S.syncSeoSource = async (source, kind = 'current') => {
    const target = googlePeriod(source, kind);
    if (busy) throw new Error('Đang gửi yêu cầu đồng bộ. Vui lòng chờ hoàn tất.');
    if (pending()) throw new Error('Nhấn Xem dữ liệu để áp dụng kỳ mới trước khi đồng bộ.');
    if (!target?.canSync) throw new Error('Kết nối và chọn đúng tài sản trước khi đồng bộ.');
    if (target.state === 'syncing') throw new Error('Nguồn này đang đồng bộ. Kết quả sẽ tự cập nhật khi hoàn tất.');
    const errors = await sync([target]);
    S.message(errors?.length ? errors.join(' ') : 'Đã xếp lịch đồng bộ. Dữ liệu sẽ tự cập nhật khi hoàn tất.', Boolean(errors?.length));
  };
}());
