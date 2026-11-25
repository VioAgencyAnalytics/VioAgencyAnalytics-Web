(function () {
  'use strict';
  const S = window.VioSEO, $ = selector => document.querySelector(selector);
  if (!S || !$('#seo-auto-website')) return;
  const el = S.element, number = new Intl.NumberFormat('vi-VN', {maximumFractionDigits:2});
  const methods = {wordpress:'WordPress',rss_atom:'RSS / Atom',sitemap_metadata:'Sitemap & dữ liệu bài viết'};
  const labels = {queued:'Đang chờ đồng bộ',running:'Đang lấy bài từ website',succeeded:'Đã đồng bộ',failed:'Đồng bộ chưa hoàn tất',cancelled:'Website hoặc quyền truy cập đã thay đổi'};
  const errors = {worker_interrupted:'Tác vụ bị gián đoạn. Bạn có thể thử lại.',website_unavailable:'Website chưa phản hồi hoặc chưa có nguồn bài viết phù hợp. Thử lại hoặc chọn nguồn đọc khác.',website_source_unavailable:'Website chưa cung cấp danh sách bài viết công khai phù hợp. Thử nguồn khác hoặc nhập file.',sync_cancelled:'Website hoặc quyền truy cập đã thay đổi. Tải lại để kiểm tra.'};
  let data, discovery, page = 1, search = '', role = 'all', generation = 0, timer, keywordJob, discoveryLoading = false, discoveryOpen = false;
  const requestKeys = new Map();
  const format = value => value === null || value === undefined ? '—' : number.format(value);
  const cell = value => { const td = el('td'); td.append(value?.nodeType ? value : el('span', value)); return td; };
  const button = (label, handler, style = 'ov-button ov-secondary') => {
    const value = el('button', label, style); value.type = 'button'; value.addEventListener('click', () => S.busy(value, handler)); return value;
  };
  function requireApplied() {
    if (!data || $('#seo-start').value !== data.period.start || $('#seo-end').value !== data.period.end || $('#seo-client-select').value !== data.scope.client_id) {
      throw new Error('Nhấn Xem dữ liệu để áp dụng khách hàng và kỳ mới trước khi đồng bộ.');
    }
  }
  function post(action, extra = {}) {
    requireApplied();
    const key = action + '/' + contextKey() + '/' + (extra.mode || '') + '/' + (extra.resume_id || '');
    if (!requestKeys.has(key)) requestKeys.set(key, crypto.randomUUID());
    return S.api(S.base + '/seo/' + action, {client_id:data.scope.client_id,...data.period,request_key:requestKeys.get(key),...extra})
      .then(value => { requestKeys.delete(key); return value; });
  }
  function contextKey(value = data) {
    return value.scope.client_id + '/' + value.period.start + '/' + value.period.end;
  }
  function renderWebsite() {
    const job = data.automation?.website_job, target = $('#seo-website-sync-status'), review = $('#seo-website-review');
    target.replaceChildren(); review.replaceChildren();
    if (!job) {
      target.append(el('p', 'Tự nhận diện WordPress, RSS hoặc sitemap. Kết quả được gắn với khách hàng và kỳ đang xem.', 'seo-help')); return;
    }
    const status = el('div', '', 'seo-auto-status'); status.dataset.state = job.status;
    status.append(el('strong', labels[job.status] || job.status));
    if (job.method) status.append(el('span', methods[job.method] || job.method, 'seo-auto-origin'));
    if (job.finished_at) status.append(el('small', S.timestamp?.(job.finished_at) || new Date(job.finished_at).toLocaleString('vi-VN', {timeZone:S.scope?.timezone || 'Asia/Ho_Chi_Minh'})));
    target.append(status);
    if (job.status === 'succeeded') {
      const counts = el('div', '', 'seo-auto-kpis');
      for (const [label, value] of [['bài mới thêm',job.added],['bài đã có',job.duplicates],['cần kiểm tra ngày',job.without_date]]) {
        const node = el('span'); node.append(el('strong', format(value || 0)), el('span', label)); counts.append(node);
      }
      target.append(counts);
      if (job.remaining_count && data.permissions.edit) {
        status.append(button('Lấy tiếp ' + format(job.remaining_count) + ' trang còn lại', async () => {
          await post('website-sync', {mode:'sitemap',resume_id:job.id}); await S.reload(); schedule();
        }));
      }
      if (job.partial) target.append(el('p', 'Nguồn trả danh sách giới hạn hoặc còn trang chưa đọc. Số bài thể hiện phần đã xác minh.', 'seo-help'));
      for (const note of job.notes || []) target.append(el('p', note, 'seo-help'));
      if (job.needs_review?.length) {
        review.className = 'seo-auto-review-list'; review.append(el('h3','Bài cần xác nhận ngày đăng'));
        for (const item of job.needs_review) {
          const row = el('div', '', 'seo-auto-review-item'), name = el('div'); name.append(el('strong',item.title),S.link(item.url,'Mở bài viết ↗')); row.append(name);
          if (data.permissions.edit) row.append(button('Bổ sung ngày đăng', () => {
            S.editContent({title:item.title,url:item.url,publication_status:'published',review_status:'pending',month:data.period.end.slice(0,7)});
          }));
          review.append(row);
        }
      }
    } else if (job.error_code) target.append(el('p',errors[job.error_code] || 'Chưa lấy được bài viết. Kiểm tra website và thử lại.','seo-help'));
  }
  async function syncKeywords() {
    const result = await post('keywords-sync');
    discoveryOpen = true;
    keywordJob = result.sync ? {...result.sync, context:contextKey()} : null;
    await S.reload();
    S.message(keywordJob ? 'Đang đồng bộ GSC và lấy từ khóa theo trang. Kết quả sẽ tự cập nhật.' : 'Đã đưa các truy vấn GSC vào bộ từ khóa. Kiểm tra gợi ý chính/phụ.');
    schedule();
  }
  async function loadDiscovery() {
    if (!data || discoveryLoading) return;
    const ticket = generation; discoveryLoading = true;
    try {
      const result = await S.api(S.base + '/seo/discovery?' + new URLSearchParams(data.period));
      if (ticket !== generation) return;
      discovery = result; page = 1; renderDiscoveryRows();
    } catch (error) {
      if (ticket === generation) { discovery = {items:[],error:error.message}; renderDiscoveryRows(); }
    } finally { if (ticket === generation) discoveryLoading = false; }
  }
  function renderDiscovery(report) {
    const target = $('#seo-gsc-discovery');
    if (!data || !target) return;
    const pending = report?.latest_sync;
    if (data.automation?.keywords_enabled && ['queued', 'running'].includes(pending?.status)) {
      keywordJob = {...pending, context:contextKey()};
      schedule();
    }
    target.classList.add('seo-auto-discovery');
    const head = el('div','','seo-card-head'), title = el('div');
    title.append(el('h3','Từ khóa tự lấy từ Google'),el('p','Gợi ý chính/phụ theo truy vấn nổi bật của từng trang trong kỳ.','seo-help')); head.append(title);
    if (data.permissions.edit) head.append(button(keywordJob ? 'Kiểm tra đồng bộ GSC' : 'Đồng bộ từ khóa GSC', async () => {
      if (keywordJob) { await S.refreshSources(); await S.reload(); } else await syncKeywords();
    }, 'ov-button seo-primary'));
    target.replaceChildren(head);
    const help = el('p', 'Đang đọc dữ liệu GSC đã lưu…', 'seo-help'); help.id = 'seo-auto-keyword-status'; target.append(help);
    const summary = data.automation?.keywords;
    if (summary) help.textContent = `${format(summary.added)} từ mới · ${format(summary.existing)} từ đã có · phân loại gợi ý chờ duyệt.`;
    const details = el('details', '', 'seo-auto-query-details');
    details.open = discoveryOpen;
    details.append(el('summary', 'Xem truy vấn và gợi ý chính/phụ'));
    details.addEventListener('toggle', () => { if (details.isConnected) discoveryOpen = details.open; });
    target.append(details);
    const controls = el('div','','seo-toolbar'), input = document.createElement('input'), select = document.createElement('select');
    input.type='search'; input.placeholder='Tìm từ khóa hoặc URL…'; input.value=search; input.setAttribute('aria-label','Tìm truy vấn Google');
    input.addEventListener('input', () => { search=input.value; page=1; renderDiscoveryRows(); });
    select.setAttribute('aria-label','Lọc gợi ý chính phụ');
    for (const [key,label] of [['all','Tất cả gợi ý'],['primary','Gợi ý từ chính'],['secondary','Gợi ý từ phụ']]) { const option=el('option',label); option.value=key; select.append(option); }
    select.value=role; select.addEventListener('change',()=>{role=select.value;page=1;renderDiscoveryRows();});
    controls.append(input,select);details.append(controls);
    const wrap=el('div','','seo-table-wrap'); wrap.tabIndex=0;
    const table=el('table','','seo-table'),thead=el('thead'),titles=el('tr');
    for(const label of ['Từ khóa / trang đích','Gợi ý vai trò','Nhấp','Hiển thị','Vị trí TB GSC','Phân loại'])titles.append(el('th',label));
    const body=el('tbody'); body.id='seo-auto-keyword-rows';thead.append(titles);table.append(thead,body);wrap.append(table);details.append(wrap);
    const navigation=el('div','','seo-pagination');
    const previous=button('← Trước',()=>{page--;renderDiscoveryRows();}),next=button('Sau →',()=>{page++;renderDiscoveryRows();}),count=el('span');
    previous.id='seo-auto-keywords-prev';next.id='seo-auto-keywords-next';count.id='seo-auto-keywords-page';navigation.append(previous,count,next);details.append(navigation);
    if (report?.state !== 'ready') {
      help.textContent='Kết nối Search Console và đồng bộ đúng kỳ để lấy từ khóa của website.';
      const link=el('a','Kết nối / quản lý Search Console','ov-button ov-secondary');link.href='/workspace/integrations?platform=gsc';target.append(link);
    }
    if (keywordJob) help.textContent = 'Đang đồng bộ GSC. Từ khóa sẽ tự được thêm khi nguồn hoàn tất.';
    if (discovery) renderDiscoveryRows();
    if(report?.snapshot)loadDiscovery();
  }
  function renderDiscoveryRows() {
    const target = $('#seo-auto-keyword-rows');
    if (!target || !data) return;
    const term = search.toLocaleLowerCase('vi-VN');
    const rows = (discovery?.items || []).filter(row =>
      (role === 'all' || row.role === role) && (!term || (row.keyword + ' ' + row.page).toLocaleLowerCase('vi-VN').includes(term)));
    const pages = Math.max(1, Math.ceil(rows.length / 25));
    page = Math.max(1, Math.min(page, pages));
    target.replaceChildren(...rows.slice((page - 1) * 25, page * 25).map(row => {
      const tr = el('tr'), name = el('div', '', 'seo-auto-query-title');
      name.append(el('strong', row.keyword));
      if (row.page) name.append(S.link(row.page, 'Mở trang đích ↗'));
      const suggested = el('div', '', 'seo-auto-query-role');
      suggested.append(el('span', row.role === 'primary' ? 'Gợi ý từ chính' : 'Gợi ý từ phụ', 'seo-auto-origin'), el('small', row.reason));
      const state = el('div', '', 'seo-auto-query-role');
      const tracked = data.keywords.find(item => item.id === row.tracked?.id);
      if (tracked) {
        state.append(el('small', tracked.role_reviewed ? 'Đã duyệt phân loại' : 'Chờ duyệt gợi ý'));
        if (data.permissions.edit && !tracked.role_reviewed) {
          state.append(button('Duyệt ' + (tracked.role === 'primary' ? 'từ chính' : 'từ phụ'), async () => {
            await S.api(S.base + '/seo/keywords', {client_id:data.scope.client_id, changes:[{
              id:tracked.id, version:tracked.version, role:tracked.role, segment:tracked.segment || 'general',
              committed:Boolean(tracked.committed), topic:tracked.topic
            }]});
            await S.reload();
          }));
        }
      } else state.append(el('small', 'Nhấn Đồng bộ từ khóa GSC để thêm vào bộ theo dõi.'));
      tr.append(cell(name), cell(suggested), cell(format(row.clicks)), cell(format(row.impressions)), cell(format(row.position)), cell(state));
      return tr;
    }));
    if (!rows.length) {
      const row = el('tr'), empty = el('td', discoveryLoading ? 'Đang đọc dữ liệu GSC…' : 'Chưa có truy vấn phù hợp trong bản dữ liệu của kỳ này.');
      empty.colSpan = 6; row.append(empty); target.append(row);
    }
    $('#seo-auto-keywords-prev').disabled = page <= 1;
    $('#seo-auto-keywords-next').disabled = page >= pages;
    $('#seo-auto-keywords-page').textContent = `Trang ${page}/${pages} · ${format(rows.length)} từ`;
    if (discovery?.error) $('#seo-auto-keyword-status').textContent = discovery.error;
    else if (discovery?.snapshot && !keywordJob) {
      $('#seo-auto-keyword-status').textContent = `${format(discovery.items.length)} truy vấn trong bản GSC · ${discovery.page_grouping ? 'Có trang đích để gợi ý chính/phụ' : 'Bản cũ chưa có trang đích, đồng bộ lại để bổ sung'}. Vị trí GSC được giữ riêng với thứ hạng Spineditor.`;
    }
  }
  function schedule() {
    if (timer || document.hidden || !data) return;
    if (!['queued','running'].includes(data.automation?.website_job?.status) && !keywordJob) return;
    timer = window.setTimeout(async () => {
      timer = null;
      let feedback;
      try {
        if (keywordJob) {
          await S.refreshSources();
          const job = S.sourceReports?.gsc?.latest_sync;
          if (job?.id === keywordJob.id && !['queued', 'running'].includes(job.status)) {
            keywordJob = null;
            if (job.status !== 'succeeded') feedback = 'GSC chưa đồng bộ xong. Kiểm tra kết nối và thử lại.';
          }
        }
        await S.reload();
        if (feedback) S.message(feedback, true);
      } catch (error) { S.message(error.message, true); }
      schedule();
    }, 6000);
  }
  $('#seo-website-sync-open').addEventListener('click',()=>S.busy(null,async()=>{
    requireApplied();if(!data.website)throw new Error('Nhấn Thiết lập website trước khi đồng bộ bài viết.');
    $('#seo-website-sync-site').textContent=data.website;
    $('#seo-website-sync-period').textContent=`Lấy bài đăng từ ${S.date(data.period.start)} đến ${S.date(data.period.end)}.`;
    S.message('',false,$('#seo-website-sync-error'));$('#seo-website-sync-dialog').showModal();
  }));
  $('#seo-website-sync-form').addEventListener('submit',event=>{
    event.preventDefault();S.busy(event.submitter,async()=>{
      await post('website-sync',{mode:$('#seo-website-sync-mode').value});$('#seo-website-sync-dialog').close();await S.reload();schedule();
    },$('#seo-website-sync-error'));
  });
  document.addEventListener('vio:seo-loaded',event=>{
    const next = event.detail;
    if (keywordJob && keywordJob.context !== contextKey(next)) keywordJob = null;
    clearTimeout(timer); timer = null;
    data = next; generation++; discovery = null; discoveryLoading = false;
    renderWebsite(); renderDiscovery(S.sourceReports?.gsc); schedule();
  });
  document.addEventListener('visibilitychange',()=>{if(document.hidden){clearTimeout(timer);timer=null;}else schedule();});
  window.addEventListener('pagehide',()=>clearTimeout(timer));
  window.VioSEOAutomation={renderDiscovery};
}());
