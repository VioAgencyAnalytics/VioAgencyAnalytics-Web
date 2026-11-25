(function () {
  'use strict';
  const S = window.VioSEO, $ = selector => document.querySelector(selector);
  if (!S || !$('#seo-panel-content')) return;
  const el = S.element;
  let data, articlePage=1;
  const names = {ga4:'Google Analytics 4', gsc:'Search Console'};
  const sourceNotes = {ga4:'Người dùng, phiên truy cập và lượt xem trang.', gsc:'Lượt nhấp, hiển thị và truy vấn trên Google.'};
  const numbers = new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 2});
  const wholeNumbers = new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 0});
  const states = {
    not_started: 'Chưa tới kỳ', no_data: 'Thiếu dữ liệu', met: 'Đạt', below_target: 'Chưa đạt',
    in_progress: 'Đang thực hiện', in_progress_met: 'Tạm đạt'
  };
  function link(label, url) { const a=el('a',label,'ov-button ov-secondary'); a.href=url; return a; }
  function action(label, handler) {
    const node=el('button',label,'ov-button ov-secondary'); node.type='button';
    node.addEventListener('click',()=>S.busy(node,handler)); return node;
  }
  function sourceCard(title, icon, description) {
    const card = el('article', '', 'seo-flow-source'), head = el('div', '', 'seo-flow-title');
    head.append(icon, el('strong', title));
    card.append(head, el('small', description));
    return card;
  }
  function sourceStatus(card, label, state) {
    const badge = el('span', label, 'seo-flow-status');
    badge.dataset.state = state;
    card.append(badge);
  }
  function hasGoogleData(source) {
    const report = S.sourceReports?.[source];
    return report?.state === 'ready' && Boolean(report.snapshot) && data.effectiveness?.sources?.[source]?.state !== 'wrong_website';
  }
  function requireApplied() {
    if (!S.seoPeriodPending?.()) return true;
    $('#seo-period-submit')?.focus();
    S.message('Nhấn Xem dữ liệu để áp dụng kỳ mới.');
    return false;
  }
  function googleCard(source) {
    const report = S.sourceReports?.[source], error = S.sourceErrors?.[source];
    const issue = S.sourceIssue?.(source), detail = data.effectiveness?.sources?.[source];
    const connected = report?.connection?.status === 'connected', asset = report?.asset;
    const saved = hasGoogleData(source), pending = ['queued', 'running'].includes(report?.latest_sync?.status);
    const failed = report?.latest_sync?.status === 'failed', future = report?.state === 'future_period';
    const property = source === 'gsc' ? 'website' : 'tài sản GA4';
    const logo = el('img');
    logo.src = '/static/customer/platforms/' + (source === 'gsc' ? 'gsc.png' : 'ga4.svg'); logo.alt = '';
    const card = sourceCard(names[source], logo, sourceNotes[source]);
    const issueLabel = {wrong_website:'Website đang chọn khác website báo cáo', reauth:'Cần kết nối lại',
      scopes:'Cần cấp quyền đọc tài sản', setup:'VIO cần kiểm tra cấu hình Google'}[issue];
    let status = 'Chưa đồng bộ kỳ này', state = 'attention';
    if (saved) { status = 'Đã đồng bộ'; state = 'ready'; }
    else if (!report && !error) { status = 'Đang kiểm tra…'; state = 'pending'; }
    else if (issueLabel) status = issueLabel;
    else if (error) status = 'Chưa đọc được trạng thái';
    else if (pending) { status = 'Đang đồng bộ'; state = 'pending'; }
    else if (!connected) status = 'Chưa kết nối';
    else if (!asset) status = 'Chưa chọn ' + property;
    else if (future) { status = 'Kỳ này chưa có ngày hoàn tất'; state = 'pending'; }
    else if (failed) status = 'Đồng bộ chưa thành công';
    sourceStatus(card, status, state);
    if (asset) card.append(el('small', asset.external_id && source === 'gsc' ? asset.external_id : asset.name));
    if (saved) {
      const {start_date, end_date, timezone} = report.snapshot;
      card.append(el('small', `${S.date(start_date)} – ${S.date(end_date)}${timezone ? ' · ' + timezone : ''}`));
    }
    if (error) card.append(el('small', error));
    if (saved && pending) card.append(el('small', 'Đang cập nhật. Bản đã lưu dùng được.'));
    else if (saved && issueLabel) card.append(el('small', issueLabel + ' để đồng bộ mới.'));
    else if (saved && failed) card.append(el('small', 'Lần cập nhật mới chưa thành công. Có thể đồng bộ lại.'));
    if (detail?.snapshot && !detail.detail_ready) card.append(el('small', 'Đồng bộ lại nếu cần chi tiết từng bài viết.'));
    const actions = el('div', '', 'seo-flow-actions');
    if (saved) actions.append(link('Xem số liệu', '/workspace/reports/data?' + new URLSearchParams({source, ...data.period})));
    if (!issue && !future && connected && asset && report.permissions?.sync) {
      const sync = action(pending ? 'Đang đồng bộ…' : saved ? 'Đồng bộ lại kỳ này' : 'Đồng bộ kỳ này', async () => {
        if (requireApplied()) await S.syncSeoSource(source);
      });
      sync.disabled = pending;
      actions.append(sync);
    }
    const label = issue === 'wrong_website' ? 'Chọn lại website' : issue === 'reauth' || issue === 'scopes' ? 'Kết nối lại'
      : report && !connected ? 'Kết nối ' + (source === 'ga4' ? 'GA4' : names[source]) : report && !asset ? 'Chọn ' + property : 'Quản lý kết nối';
    const manage = link((data.permissions?.edit === false ? 'Xem kết nối' : label) + ' ↗', '/workspace/integrations?platform=' + source);
    manage.target = '_blank'; manage.rel = 'noopener';
    actions.append(manage);
    card.append(actions);
    return card;
  }
  function rankEntry() {
    return data.comparison.coverage?.current?.observed ?? data.keywords.filter(row => row.observed_date).length;
  }
  function rankCard() {
    const icon = el('span', 'format_list_numbered', 'material-symbols-outlined');
    icon.setAttribute('aria-hidden', 'true');
    const card = sourceCard('Thứ hạng Spineditor', icon, 'File Excel hoặc CSV có ngày đo thuộc kỳ báo cáo.');
    const count = rankEntry();
    sourceStatus(card, count ? `Đã nhập ${wholeNumbers.format(count)} từ có ngày đo` : 'Chưa có thứ hạng trong kỳ', count ? 'ready' : 'attention');
    const actions = el('div', '', 'seo-flow-actions');
    if (data.permissions.edit) {
      const download = link('Mở Spineditor ↗', 'https://spineditor.com/kiem-tra-thu-hang-tu-khoa');
      download.target = '_blank'; download.rel = 'noopener noreferrer';
      actions.append(action(count ? 'Nhập thêm thứ hạng' : 'Nhập thứ hạng', () => {
        if (requireApplied()) S.openImport('current', 'reports');
      }), download);
    }
    if (count || !data.permissions.edit) actions.append(action('Xem từ khóa', () => S.showTab('keywords')));
    card.append(actions);
    return card;
  }
  function renderSources() {
    if(!data)return;
    document.querySelectorAll('[data-seo-flow-sources]').forEach(target=>{
      const sources=target.dataset.seoFlowSources.split(',').filter(Boolean);
      target.replaceChildren(...sources.map(source => source === 'spineditor' ? rankCard() : googleCard(source)));
    });
    const kpi=$('#seo-kpi-required-source');
    if(kpi){
      kpi.replaceChildren();
      const metric=data.project?.plan?.traffic_metric;
      if(metric){
        const source = metric === 'gsc_clicks' ? 'gsc' : 'ga4';
        const plan = data.project.plan;
        kpi.append(el('p', 'Chỉ số lưu lượng · ' + (data.project.traffic_options?.[metric] || metric), 'seo-help'), googleCard(source));
        const measured = plan.months?.find(row => row.month === data.project.month);
        const rangeLink = (label, range) => link(label, '/workspace/reports/data?' + new URLSearchParams({source, ...range}));
        const actions = el('div', '', 'seo-flow-actions');
        if (measured?.traffic_start) actions.append(rangeLink(`Mở nguồn kỳ đo ${S.date(measured.traffic_start)} – ${S.date(measured.traffic_end)}`, {start: measured.traffic_start, end: measured.traffic_end}));
        if (plan.traffic_basis === 'increase' && plan.traffic_baseline_month) actions.append(rangeLink(`Mở nguồn tháng gốc ${plan.traffic_baseline_month}`, S.monthRange(plan.traffic_baseline_month)));
        if (actions.childElementCount) kpi.append(actions);
      }else kpi.append(el('p','Mẫu mặc định dùng lượt xem GA4. Chọn chỉ số theo hợp đồng khi thiết lập cam kết.','seo-help'));
    }
    renderArticlePerformance(); renderReadiness();
  }
  function renderArticlePerformance() {
    const target=$('#seo-article-performance');if(!target)return;
    const performance=data.effectiveness;
    target.replaceChildren();
    const head=el('div','','seo-card-head'), title=el('div');
    title.append(el('h3','Hiệu quả từng bài viết'),el('p','Lượt xem GA4 và tìm kiếm Google theo URL trong kỳ đang xem.','seo-help'));
    head.append(title);target.append(head);
    if(!performance?.items?.length){target.append(el('p','Đồng bộ bài viết từ website trước, sau đó đồng bộ GA4/GSC cùng kỳ.','seo-help'));return;}
    const wrap=el('div','','seo-table-wrap');wrap.tabIndex=0;wrap.setAttribute('aria-label','Hiệu quả bài viết; cuộn ngang để xem đủ chỉ số');
    const table=el('table','','seo-table'),thead=el('thead'),tr=el('tr');
    for(const text of ['Bài viết','Lượt xem · GA4','Nhấp · GSC','Hiển thị · GSC','CTR · GSC','Vị trí TB · GSC'])tr.append(el('th',text));
    thead.append(tr);const body=el('tbody');
    const pages=Math.max(1,Math.ceil(performance.items.length/15));
    articlePage=Math.min(articlePage,pages);
    for(const item of performance.items.slice((articlePage-1)*15,articlePage*15)){
      const row=el('tr'),name=el('td');name.append(S.link(item.url,item.title));row.append(name);
      for(const key of ['views','clicks','impressions','ctr','position']){
        const td=el('td'),unit=key==='ctr'?'percent':key==='position'?'number':'count';
        td.append(el('strong',window.VioDataFormat.format(item.values[key],unit)));
        if(data.comparison.mode!=='none' && item.previous[key]!==null && item.previous[key]!==undefined){
          td.append(el('small','Trước: '+window.VioDataFormat.format(item.previous[key],unit),'seo-date'));
        }
        row.append(td);
      }
      body.append(row);
    }
    table.append(thead,body);wrap.append(table);target.append(wrap,el('p',performance.note,'seo-help'));
    if(pages>1){
      const nav=el('div','','seo-pagination'),previous=action('← Trước',()=>{articlePage--;renderArticlePerformance();}),next=action('Sau →',()=>{articlePage++;renderArticlePerformance();});
      previous.disabled=articlePage<=1;next.disabled=articlePage>=pages;
      nav.append(previous,el('span',`Trang ${articlePage}/${pages} · ${performance.items.length} bài`),next);target.append(nav);
    }
    for(const source of Object.values(performance.sources||{})){
      if(source.limited)target.append(el('p',names[source.source]+': bảng nguồn có giới hạn; bài không có dòng quan sát giữ dấu —.','seo-help'));
    }
  }
  function renderReadiness() {
    const target=$('#seo-report-readiness');if(!target)return;
    const scope = $('#seo-report-period'), status = $('#seo-report-source-status');
    if (scope) scope.textContent = [data.client?.name, data.website, `${S.date(data.period.start)} – ${S.date(data.period.end)}`].filter(Boolean).join(' · ');
    if (status) {
      const available = Number(rankEntry() > 0) + Number(hasGoogleData('gsc')) + Number(hasGoogleData('ga4'));
      status.textContent = `${available}/3 nguồn chính có dữ liệu đã lưu trong kỳ. ${available === 3 ? 'Kiểm tra thêm nội dung cần trình bày.' : 'Bản xuất ghi rõ nguồn còn thiếu.'}`;
    }
    const articles = data.content?.summary?.published_new || 0;
    const accepted = (data.content?.summary?.accepted_new || 0) + (data.content?.summary?.accepted_updates || 0);
    const goals = (data.project?.items || []).filter(item => item.target != null);
    const readings = goals.filter(item => item.actual != null).length;
    const verifiedTerms = data.keywords.filter(row => ['primary', 'secondary'].includes(row.role) && (row.role_origin !== 'gsc' || row.role_reviewed)).length;
    const parts = [
      ['Bài viết', `${wholeNumbers.format(articles)} bài mới đã đăng · ${wholeNumbers.format(accepted)} lượt nghiệm thu`,
        'Đồng bộ từ website hoặc nhập danh sách. Kiểm tra trạng thái duyệt và ngày nghiệm thu.', 'Mở Bài viết', () => S.showTab('content', '#seo-auto-title')],
      ['KPI & Công việc', goals.length ? `${readings}/${goals.length} chỉ tiêu tháng có số thực tế` : 'Chưa có mục tiêu trong tháng',
        'Đặt mục tiêu theo hợp đồng. Gắn bằng chứng và xác nhận nghiệm thu công việc.', 'Mở KPI & Công việc', () => S.showTab('kpi')],
      ['Từ khóa chính, phụ và ngách', verifiedTerms ? `${wholeNumbers.format(verifiedTerms)} từ đã phân loại` : 'Chưa duyệt phân loại',
        'Dùng truy vấn GSC để tìm từ khóa. Duyệt chính/phụ, phạm vi ngách và bộ cam kết trong tab Từ khóa.', 'Mở Từ khóa', () => S.showTab('keywords')]
    ];
    if (data.comparison.mode !== 'none') {
      const comparable = data.analysis?.movement?.comparable || 0;
      parts.push(['Đối chiếu hai kỳ', comparable ? `${wholeNumbers.format(comparable)} từ đủ hai kỳ` : 'Chưa có cặp thứ hạng để đối chiếu',
        'Nhập các ngày đo của cả hai kỳ và đồng bộ kỳ đối chiếu cho từng nguồn Google.', 'Kiểm tra kỳ đối chiếu',
        () => S.showTab('overview', '#seo-comparison-title')]);
    }
    target.replaceChildren(...parts.map(([name, status, description, label, handler]) => {
      const row = el('article', '', 'seo-flow-readiness');
      row.append(el('strong', name), el('span', status, 'seo-prep-detail-status'), el('small', description), action(label, handler));
      return row;
    }));
  }
  function kpiValue(value, unit, actual = false) {
    if (value == null) return '';
    const formatter = actual && unit === 'percent' ? wholeNumbers : numbers;
    return (value < 0 ? '−' : '') + formatter.format(Math.abs(value)) + (unit === 'percent' ? '%' : '');
  }

  function matrixLabel(metric, project, labels) {
    const plan = project.plan;
    if (plan && plan.template !== 'monthly_seo') return metric.label;
    if (metric.key === 'traffic' && labels.traffic) {
      const measure = ['ga4_sessions', 'ga4_organic_sessions'].includes(plan?.traffic_metric) ? 'phiên/tháng' : 'lượt/tháng';
      return labels.traffic + (plan?.traffic_basis === 'increase' ? ' tăng thêm ' : ' ') + measure;
    }
    const pages = project.timeline?.totals?.social_profile?.target;
    if (metric.key === 'social_profile' && pages) return `Xây dựng hệ thống ${pages} trang MXH`;
    if (metric.key === 'social_share' && plan?.share_pages) return `Chia sẻ ${plan.share_pages} trang MXH`;
    return labels[metric.key] || metric.label;
  }

  function timelineMetric(table, metric, label, months, total, index) {
    const body = el('tbody'), plan = el('tr', '', 'seo-matrix-plan'), actual = el('tr', '', 'seo-matrix-actual');
    const order = el('td', String(index + 1));
    order.rowSpan = 2;
    const planLabel = el('th', label), actualLabel = el('th', 'Đã thực hiện');
    planLabel.scope = actualLabel.scope = 'row';
    if (metric.source) planLabel.title = metric.source;
    plan.append(order, planLabel);
    actual.append(actualLabel);
    for (const month of months) {
      const item = month.items.find(({key}) => key === metric.key);
      const goal = el('td', kpiValue(item?.target, metric.unit));
      const reading = el('td', kpiValue(item?.actual, metric.unit, true));
      const detail = [states[item?.status], item?.note].filter(Boolean).join(' · ');
      if (detail) reading.title = detail;
      plan.append(goal);
      actual.append(reading);
    }
    if (total) {
      plan.append(el('td', kpiValue(total.target, metric.unit), 'seo-matrix-total'));
      actual.append(el('td'));
    }
    body.append(plan, actual);
    table.append(body);
  }

  function renderTimeline() {
    const target = $('#seo-project-timeline');
    if (!target) return;
    target.replaceChildren();
    const project = data.project, timeline = project?.timeline;
    const preview = !project?.plan && !timeline?.months?.length;
    const metrics = preview ? project?.definitions : timeline?.metrics;
    if (!metrics?.length) return;
    const labels = JSON.parse(target.dataset.kpiLabels || '{}');
    const months = preview ? Array.from({length: 12}, () => ({items: []})) : timeline.months;
    for (let offset = 0; offset < months.length; offset += 12) {
      const batch = months.slice(offset, offset + 12);
      const showTotal = offset + batch.length === months.length;
      const wrap = el('div', '', 'seo-table-wrap seo-matrix-wrap');
      wrap.tabIndex = 0;
      wrap.setAttribute('role', 'region');
      wrap.setAttribute('aria-label', `Bảng KPI từ tháng ${offset + 1} đến tháng ${offset + batch.length}`);
      const table = el('table', '', 'seo-kpi-matrix');
      const columns = el('colgroup');
      columns.append(el('col', '', 'seo-matrix-order'), el('col', '', 'seo-matrix-topic'));
      for (let column = 0; column < batch.length + Number(showTotal); column++) columns.append(el('col'));
      const banner = el('tr', '', 'seo-matrix-banner');
      const heading = el('th', target.dataset.kpiHeading);
      heading.colSpan = columns.children.length;
      banner.append(heading);
      const head = el('tr');
      head.append(el('th', 'STT'), el('th', 'Tháng'));
      batch.forEach((month, index) => {
        const th = el('th', String(offset + index + 1));
        if (month.month) th.title = month.month;
        head.append(th);
      });
      if (showTotal) head.append(el('th', 'Tổng'));
      for (const th of head.children) th.scope = 'col';
      const thead = el('thead');
      thead.append(banner, head);
      table.append(columns, thead);
      metrics.forEach((metric, index) => {
        const totals = showTotal ? timeline?.totals?.[metric.key] || {} : null;
        timelineMetric(table, metric, matrixLabel(metric, project, labels), batch, totals, index);
      });
      wrap.append(table);
      target.append(wrap);
    }
    if (timeline?.months?.length) {
      target.append(el('p', 'Ô trống là chưa có kế hoạch hoặc kết quả. Xem chi tiết từng tháng bên dưới.', 'seo-help seo-matrix-note'));
    }
  }
  $('#seo-report-refresh')?.addEventListener('click', event => S.busy(event.currentTarget, async () => {
    if (requireApplied()) await S.reload();
  }));
  $('#seo-report-continue')?.addEventListener('click', event => { if (!requireApplied()) event.preventDefault(); });
  document.addEventListener('vio:seo-loaded',event=>{data=event.detail;articlePage=1;renderSources();renderTimeline();});
  document.addEventListener('vio:seo-source',renderSources);
}());
