/* Report navigation reads snapshots; only the explicit sync button queues work. */
(() => {
  'use strict';
  const dayMs = 86400000;
  function stamp(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
    const parsed = new Date(value+'T00:00:00Z');
    return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0,10) === value ? parsed : null;
  }
  const iso = (date) => date.toISOString().slice(0,10);
  function valid(start,end) {
    const first = stamp(start), last = stamp(end);
    return Boolean(first && last && last >= first && last-first < 90*dayMs);
  }
  function monthRange(value) {
    if (!/^\d{4}-\d{2}$/.test(value || '')) return null;
    const first = stamp(value+'-01'); if (!first) return null;
    const last = new Date(first); last.setUTCMonth(last.getUTCMonth()+1); last.setUTCDate(0);
    return {start:iso(first),end:iso(last)};
  }
  function range(preset,calendar,month) {
    const closed = stamp(calendar?.latest_closed_date), today = stamp(calendar?.today);
    if (!closed || !today) return null;
    if (['last7','last30','last90'].includes(preset)) return {start:iso(new Date(closed.getTime()-(Number(preset.slice(4))-1)*dayMs)),end:iso(closed)};
    if (preset === 'month') return monthRange(month);
    if (preset === 'this_month') return monthRange(iso(today).slice(0,7));
    if (preset === 'last_month') { today.setUTCDate(0); return monthRange(iso(today).slice(0,7)); }
    return null;
  }
  function goalInput(value,unit) {
    const text = value.trim().replace(',','.');
    if (!text) return null;
    if (!/^(?:0|[1-9]\d{0,17})(?:\.\d{1,8})?$/.test(text)) throw new Error('Dùng số không âm, tối đa 18 chữ số và 8 số lẻ; không có dấu hàng nghìn.');
    const [whole,fraction=''] = text.split('.');
    if (unit === 'count' && /[1-9]/.test(fraction)) throw new Error('Chỉ số đếm cần mục tiêu là số nguyên.');
    if (unit === 'percent' && (BigInt(whole) > 100n || whole === '100' && /[1-9]/.test(fraction))) throw new Error('Nhập mục tiêu tỷ lệ từ 0 đến 100%.');
    const trimmed = fraction.replace(/0+$/,'');
    return whole+(trimmed ? '.'+trimmed : '');
  }
  window.VioReportControls = Object.freeze({range,valid,goalInput});
  const $ = (selector) => document.querySelector(selector), tag = $('#connector-report-data') || $('#facebook-content-data');
  if (!tag || !$('#report-period-form')) return;
  const data = JSON.parse(tag.textContent), details = JSON.parse($('#library-data').textContent);
  const preset = $('#report-preset'), start = $('#report-start'), end = $('#report-end'), month = $('#report-month');
  const comparison = $('#report-comparison'), compareStart = $('#report-comparison-start'), compareEnd = $('#report-comparison-end');
  let busy = false;
  const dialog = $('#report-goals-dialog'), targets = data.targets;
  function message(element,text,success=false) { if (!element) return; element.textContent = text; element.hidden = !text; element.dataset.success = String(success); }
  function setBusy(value) {
    busy = value;
    document.querySelectorAll('#report-period-form input,#report-period-form select,#report-period-form button,#report-sync,#report-sync-comparison,#report-goals-edit,#report-goals-dialog button,#report-goals-dialog input,#report-goals-dialog select').forEach((element) => { element.disabled = value; });
    updateComparison();
    if ($('#report-sync')) $('#report-sync').textContent = value ? 'Đang xử lý…' : data.snapshot ? 'Đồng bộ lại kỳ này' : 'Đồng bộ kỳ này';
  }
  function navigate(first,last) {
    const url = new URL(location.href), previous = new URLSearchParams(url.search); url.search = ''; url.hash = '';
    for (const key of ['style', 'palette', 'order', 'hidden', 'template']) if (previous.has(key)) url.searchParams.set(key, previous.get(key));
    if (data.connector && url.pathname === '/workspace/reports/data') url.searchParams.set('source',data.source);
    url.searchParams.set('start',first); url.searchParams.set('end',last);
    if (comparison && comparison.value !== 'none') {
      url.searchParams.set('comparison',comparison.value);
      if (comparison.value === 'custom') {
        url.searchParams.set('comparison_start',compareStart.value);
        url.searchParams.set('comparison_end',compareEnd.value);
      }
    }
    location.assign(url.pathname+url.search);
  }
  function updateComparison() {
    const custom = comparison?.value === 'custom';
    for (const key of ['start','end']) {
      const input = key === 'start' ? compareStart : compareEnd;
      if (!input) continue;
      $('#report-comparison-'+key+'-label').hidden = !custom;
      input.disabled = busy || !custom; input.required = custom;
    }
    if (custom && !compareStart.value && !compareEnd.value) {
      const first = stamp(data.period.data_start || start.value), last = stamp(data.period.data_end || end.value);
      if (first && last) {
        compareStart.value = iso(new Date(first.getTime()-(last-first+dayMs)));
        compareEnd.value = iso(new Date(first.getTime()-dayMs));
      }
    }
  }
  comparison?.addEventListener('change',updateComparison);
  updateComparison();
  function updateRange() {
    $('#report-month-label').hidden = preset.value !== 'month';
    const value = range(preset.value,data.calendar,month.value);
    if (value) { start.value = value.start; end.value = value.end; }
  }
  for (const value of ['last30','last7','last90','this_month','last_month']) {
    const selected = range(value,data.calendar);
    if (selected?.start === start.value && selected.end === end.value) { preset.value = value; break; }
  }
  preset.addEventListener('change',updateRange); month.addEventListener('change',updateRange);
  [start,end].forEach((element) => element.addEventListener('input',() => { preset.value = 'custom'; $('#report-month-label').hidden = true; }));
  $('#report-period-form').addEventListener('submit',(event) => {
    event.preventDefault(); if (busy) return;
    if (!valid(start.value,end.value)) { message($('#report-control-feedback'),'Chọn ngày bắt đầu và kết thúc hợp lệ, tối đa 90 ngày.'); return; }
    if (comparison?.value === 'custom' && (!valid(compareStart.value,compareEnd.value) || compareEnd.value > data.calendar.latest_closed_date)) {
      message($('#report-control-feedback'),'Chọn kỳ đối chiếu hợp lệ, tối đa 90 ngày và chỉ gồm ngày nguồn đã kết thúc.'); return;
    }
    navigate(start.value,end.value);
  });
  async function api(path,body) {
    const response = await fetch('/api/customer/'+path,{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json',...(body ? {'Content-Type':'application/json','X-CSRF-Token':body.csrf} : {})},
      ...(body ? {method:'POST',body:JSON.stringify(body.data)} : {})});
    const value = await response.json();
    if (!response.ok) {
      if (response.status === 401) location.replace('/workspace/login');
      const error = new Error(value.error || 'Chưa thực hiện được. Vui lòng thử lại.'); error.code = value.code; throw error;
    }
    return value;
  }
  async function mutation(path,body) {
    const session = await api('session');
    if (session.workspace?.id !== details.workspace.id) throw new Error('Workspace đã thay đổi. Hãy tải lại trang.');
    return api(`workspaces/${details.workspace.id}/`+path,{data:body,csrf:session.csrf});
  }
  $('#report-sync')?.addEventListener('click',async () => {
    if (busy) return; setBusy(true); message($('#report-control-feedback'),'');
    try {
      await mutation(`connections/${data.connection.id}/sync`,{client_id:data.scope.client_id,version:data.connection.version,
        start:data.period.data_start,end:data.period.data_end,request_key:crypto.randomUUID()});
      navigate(data.period.start,data.period.end);
    } catch (error) { message($('#report-control-feedback'),error.message); setBusy(false); }
  });
  $('#report-sync-comparison')?.addEventListener('click',async () => {
    if (busy || !data.comparison?.period) return;
    setBusy(true); message($('#report-control-feedback'),'');
    try {
      await mutation(`connections/${data.connection.id}/sync`,{client_id:data.scope.client_id,version:data.connection.version,
        start:data.comparison.period.start,end:data.comparison.period.end,request_key:crypto.randomUUID()});
      navigate(data.period.start,data.period.end);
    } catch (error) { message($('#report-control-feedback'),error.message); setBusy(false); }
  });
  $('#report-comparison-retry')?.addEventListener('click',() => location.reload());
  function close() { if (!busy) dialog?.close(); }
  dialog?.addEventListener('cancel',(event) => { if (busy) event.preventDefault(); });
  $('#report-goals-close')?.addEventListener('click',close); $('#report-goals-cancel')?.addEventListener('click',close);
  $('#report-goals-edit')?.addEventListener('click',() => {
    if (busy) return;
    for (const field of document.querySelectorAll('[data-goal]')) {
      const goal = targets.items.find((item) => item.key === field.dataset.goal);
      field.querySelector('[data-goal-value]').value = goal.input_value ?? '';
      field.querySelector('[data-goal-direction]').value = goal.direction;
    }
    message($('#report-goals-feedback'),''); dialog.showModal();
  });
  $('#report-goals-form')?.addEventListener('submit',async (event) => {
    event.preventDefault(); if (busy) return;
    const changed = [];
    try {
      for (const field of document.querySelectorAll('[data-goal]')) {
        const goal = targets.items.find((item) => item.key === field.dataset.goal), input = field.querySelector('[data-goal-value]');
        let value;
        try { value = goalInput(input.value,goal.unit); } catch (error) { input.focus(); throw new Error(goal.label+': '+error.message); }
        const direction = field.querySelector('[data-goal-direction]').value;
        if (value !== goal.input_value || direction !== goal.direction) changed.push({key:goal.key,input_value:value,direction,version:goal.version});
      }
      if (!changed.length) { close(); return; }
      setBusy(true); message($('#report-goals-feedback'),'');
      await mutation('targets/'+data.source,{client_id:data.scope.client_id,asset_id:targets.asset_id,start:targets.start,end:targets.end,items:changed});
      location.reload();
    } catch (error) {
      setBusy(false); message($('#report-goals-feedback'),error.message);
      if (error.code === 'target_version') {
        const reload = document.createElement('button'); reload.type = 'button'; reload.className = 'ov-button ov-secondary'; reload.textContent = 'Tải lại mục tiêu mới'; reload.addEventListener('click',() => location.reload()); $('#report-goals-feedback').append(document.createElement('br'),reload);
      }
    }
  });
})();
