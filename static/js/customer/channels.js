(() => {
  'use strict';
  const W = window.VioLibrary, {$, node} = W, initial = W.initial, params = new URLSearchParams(location.search);
  let group = initial.groups.some((g) => g.id === params.get('category')) ? params.get('category') : 'all', deepLink = params.get('channel');
  let sources = null, loading = true, loadError = false, generation = 0, controller;
  const focused = {facebook_content:['posts_published','reactions_lifetime','comments_lifetime'], facebook_ads:['spend','clicks','leads'],
    google_ads:['spend','clicks','conversions'],tiktok_ads:['spend','clicks','conversions'],ga4:['active_users','sessions','engagement_rate'],
    gsc:['clicks','impressions','position'],youtube:['views','watch_minutes','subscribers_gained'],business_profile:['call_clicks','directions','website_clicks']};
  function source(id) { return sources?.find((row) => row.source === id); }
  function savedChannel(original) {
    if (W.snapshot?.channels) return W.channel(original.id); // Scoped presentation fixtures/legacy adapter.
    const rows = original.source_ids.map(source).filter(Boolean), row = rows[0];
    const state = rows.some((s) => s.state === 'ready') ? 'ready' : rows.some((s) => ['sync_error','invalid'].includes(s.state)) ? 'attention'
      : rows.some((s) => s.state === 'syncing') ? 'syncing' : rows.some((s) => s.asset || s.state === 'select_asset') ? 'empty' : W.channel(original.id).state;
    const metrics = original.id === 'seo' ? [] : (focused[original.id] || []).map((key) => row?.metrics?.find((m) => m.key === key)).filter(Boolean);
    return {...original, state:loadError ? 'attention' : state, metrics, saved:row};
  }
  function reportHref(id) {
    const row = source(id), target = new URL(id === 'facebook_content' ? '/workspace/channels/facebook-content' : '/workspace/reports/data',location.origin);
    if (id !== 'facebook_content') target.searchParams.set('source',id);
    if ($('#library-period').value === 'latest') { if (row?.snapshot) target.searchParams.set('snapshot',row.snapshot.id); }
    else { const period = W.context().period; target.searchParams.set('start',period.start); target.searchParams.set('end',period.end); }
    return target.pathname+target.search;
  }
  async function loadSaved() {
    const ticket = ++generation, context = W.context(), clientId = context.scope.client_id;
    controller?.abort(); controller = new AbortController(); const signal = AbortSignal.any([controller.signal,AbortSignal.timeout(20000)]); sources = null; loading = true; loadError = false; render();
    if (!W.ready || !clientId) { loading = false; render(); return; }
    async function get(path) {
      const response = await fetch('/api/customer/'+path,{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'},signal});
      const data = await response.json();
      if (response.status === 401) { location.replace('/workspace/login'); throw new Error(); }
      if (!response.ok || data.scope?.workspace_id !== context.scope.workspace_id || data.scope?.client_id !== clientId) throw new Error();
      return data;
    }
    try {
      const index = await get(`workspaces/${context.scope.workspace_id}/data`);
      if (ticket !== generation || W.context().request_id !== context.request_id) return;
      if (!Array.isArray(index.sources)) throw new Error();
      let rows = index.sources;
      if ($('#library-period').value !== 'latest') {
        const query = new URLSearchParams({start:context.period.start,end:context.period.end});
        rows = await Promise.all(rows.map(async (row) => {
          if (!row.asset) return row;
          try { const value = await get(`workspaces/${context.scope.workspace_id}/data/${row.source}?${query}`); if (value.source !== row.source) throw new Error(); return value; }
          catch (error) { if (error.name === 'AbortError') throw error; return {...row,state:'invalid',snapshot:null,metrics:[],read_error:true}; }
        }));
      }
      if (ticket !== generation || W.context().request_id !== context.request_id || !W.ready) return;
      sources = rows;
    } catch (error) { if (ticket !== generation || error.name === 'AbortError') return; loadError = true; }
    finally { if (ticket === generation) { loading = false; render(); } }
  }
  $('#library-search').value = (params.get('q') || '').slice(0, 150);
  if ([...$('#channels-status').options].some((o) => o.value === params.get('status'))) $('#channels-status').value = params.get('status');
  function open(id) {
    const channel = W.channel(id); if (!channel || !W.ready || loading) return;
    if (loadError || source(id)?.read_error) { loadSaved(); return; }
    if (id !== 'seo') {
      const row = source(id);
      location.assign(row?.asset || row?.state === 'ready' ? reportHref(id) : '/workspace/integrations?platform='+encodeURIComponent(id)); return;
    }
    const target = new URL('/workspace/seo', location.origin);
    if ($('#library-period').value !== 'latest') { const period = W.context().period; target.searchParams.set('start', period.start); target.searchParams.set('end', period.end); }
    location.assign(target.pathname + target.search);
  }
  function render() {
    const channels = initial.channels.map(savedChannel), counts = Object.fromEntries(Object.keys(W.labels).map((s) => [s, 0]));
    const words = W.fold($('#library-search').value.trim()).split(/\s+/).filter(Boolean), status = $('#channels-status').value;
    let shown = 0;
    for (const channel of channels) {
      const card = document.querySelector(`[data-channel-card="${channel.id}"]`);
      counts[channel.state] += 1; card.dataset.state = channel.state;
      card.querySelector('[data-card-state]').textContent = loading ? 'Đang tải…' : loadError ? 'Chưa tải được' : W.labels[channel.state];
      const metrics = card.querySelector('.lb-card-metrics'); metrics.replaceChildren();
      for (const metric of channel.metrics) {
        const value = channel.state === 'ready' ? W.snapshot?.channels ? W.format(metric.value,metric.unit) : window.VioDataFormat.format(metric.value,metric.unit,metric.currency) : '—';
        const cell = node('dd',value); cell.dataset.value = metric.key; cell.setAttribute('aria-label',value === '—' ? 'Chưa có dữ liệu' : value);
        const label = node('dt',metric.label);
        if (metric.grain === 'snapshot') label.append(node('small',metric.aggregation === 'latest_observation' ? 'Tại lần đồng bộ' : 'Tích lũy'));
        const box = node('div',''); box.append(label,cell); metrics.append(box);
      }
      metrics.hidden = !channel.metrics.length;
      const row = channel.saved, snapshot = row?.snapshot;
      card.querySelector('[data-card-period]').textContent = loading ? 'Đang kiểm tra dữ liệu đã lưu.' : loadError || row?.read_error ? 'Chưa đọc được kỳ này. Bấm Tải lại để thử lại.'
        : channel.id === 'seo' ? 'Quản lý thứ hạng, cam kết KPI và công việc SEO theo website.'
        : snapshot ? `${snapshot.start_date} → ${snapshot.end_date} · ${snapshot.timezone}`
        : row?.asset ? 'Chưa có dữ liệu đã lưu cho kỳ này. Mở báo cáo để chọn kỳ hoặc đặt KPI.' : row?.state === 'select_asset' ? 'Đã cấp quyền. Chọn tài khoản để hoàn tất.' : 'Kết nối tài khoản để bắt đầu.';
      const button = card.querySelector('[data-open-channel]'); button.disabled = !W.ready || loading;
      button.textContent = loadError || row?.read_error ? 'Thử tải lại' : channel.id === 'seo' ? 'Mở SEO & Từ khóa →' : row?.asset || channel.state === 'ready' ? 'Xem phân tích →' : row?.state === 'select_asset' ? 'Chọn tài khoản →' : 'Kết nối →';
      button.setAttribute('aria-label',button.textContent.replace(' →','')+' '+channel.name);
      const haystack = W.fold([channel.id.replaceAll('_', ' '), channel.name, channel.description, ...channel.topics].join(' '));
      const matches = (group === 'all' || channel.group === group) && (status === 'all' || channel.state === status) && words.every((q) => haystack.includes(q));
      card.hidden = !matches; if (matches) shown += 1;
    }
    $('#channels-health-counts').replaceChildren(...Object.entries(counts).filter(([, count]) => count > 0).map(([state, count]) => { const item = node('span', `${W.labels[state]} (${count})`); item.dataset.state = state; return item; }));
    $('#channels-health-description').textContent = loading ? 'Đang đọc dữ liệu đã đồng bộ…' : loadError ? 'Chưa tải được trạng thái. Bấm Tải lại để thử lại.'
      : `${counts.ready}/${channels.length} mục có dữ liệu ${$('#library-period').value === 'latest' ? 'đã lưu. Kỳ của từng nguồn được ghi trên thẻ.' : 'trong kỳ đã chọn. “—” là chưa có số liệu, không phải 0.'}`;
    $('#library-no-results').hidden = shown > 0; $('#library-result-count').textContent = `Hiển thị ${shown} / ${channels.length} kênh`;
    document.querySelectorAll('[data-library-group]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.libraryGroup === group)));
    if (deepLink && W.ready && !loading && !loadError) { const id = deepLink; deepLink = null; if (initial.channels.some((c) => c.id === id)) open(id); }
  }
  function filter() { W.url({q: $('#library-search').value.trim(), category: group === 'all' ? '' : group, status: $('#channels-status').value === 'all' ? '' : $('#channels-status').value}); render(); }
  $('#library-search').addEventListener('input', filter); $('#channels-status').addEventListener('change', filter);
  document.querySelectorAll('[data-library-group]').forEach((b) => b.addEventListener('click', () => { group = b.dataset.libraryGroup; filter(); }));
  document.querySelectorAll('[data-open-channel]').forEach((b) => b.addEventListener('click', () => open(b.dataset.openChannel)));
  document.querySelectorAll('[data-channel-link]').forEach((link) => link.addEventListener('click', (event) => {
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault(); open(link.dataset.channelLink);
  }));
  $('#library-reset').addEventListener('click', () => { group = 'all'; $('#library-search').value = ''; $('#channels-status').value = 'all'; filter(); $('#library-search').focus(); });
  $('#library-preview').addEventListener('close', () => { W.url({channel: ''}); document.querySelectorAll('[data-channel-link]').forEach((a) => a.removeAttribute('aria-current')); });
  $('#channels-seo-dialog').addEventListener('close', () => W.url({channel:''}));
  document.addEventListener('customer:library-context',()=>{sources=null;loadError=false;loading=true;controller?.abort();generation+=1;render();if(W.ready)loadSaved();});
  document.addEventListener('customer:library-ready',loadSaved);
  window.addEventListener('pagehide',()=>{controller?.abort();generation+=1;});
  window.VioChannels = Object.freeze({getContext: W.context, render: W.accept});
  W.mount(render);
})();
