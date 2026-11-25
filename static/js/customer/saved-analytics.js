/* Saved-data dashboard utilities. No provider transport or cross-source sums. */
(() => {
  'use strict';
  const measured = (value) => typeof value === 'number' && Number.isFinite(value) && value >= 0
    || typeof value === 'string' && /^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(value);
  const number = (value) => measured(value) && Number.isFinite(Number(value)) ? Number(value) : null;
  const format = (value,meta={}) => window.VioDataFormat.format(value,meta.unit || 'number',meta.currency);
  function href(value) {
    if (typeof value !== 'string') return '';
    try {
      const url=new URL(value,location.origin);
      if (url.origin!==location.origin || !['/workspace/reports/data','/workspace/reports/facebook-content'].includes(url.pathname)) return '';
      return url.pathname+url.search;
    } catch { return ''; }
  }
  async function read(workspaceId,clientId,source,period,comparison,signal,granularity='day',comparisonPeriod=null) {
    const query=new URLSearchParams({source,comparison,granularity});
    if (period) { query.set('start',period.start); query.set('end',period.end); }
    if (comparison==='custom' && comparisonPeriod) {
      query.set('comparison_start',comparisonPeriod.start); query.set('comparison_end',comparisonPeriod.end);
    }
    const response=await fetch(`/api/customer/workspaces/${workspaceId}/analytics?`+query,{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'},signal});
    const data=await response.json();
    if (!response.ok) {
      if (response.status===401) location.replace('/workspace/login');
      throw new Error(data.error || 'Chưa tải được dữ liệu đã lưu. Hãy thử lại.');
    }
    if (data.scope?.workspace_id!==workspaceId || data.scope?.client_id!==clientId) throw new Error('Khách hàng đã thay đổi. Hãy cập nhật lại.');
    return data;
  }
  function goalText(goal) {
    if (!goal || goal.value===null || goal.value===undefined) return '';
    const labels={met:'Đạt KPI',below_target:'Chưa đạt KPI',within_limit:'Trong giới hạn',over_limit:'Vượt giới hạn',no_data:'KPI chưa có số liệu',currency_mismatch:'KPI khác tiền tệ'};
    return (goal.assessment?.label || labels[goal.status] || '')+(goal.ratio!==null && goal.ratio!==undefined ? ' · '+window.VioDataFormat.fraction(goal.ratio)+(goal.direction==='at_most' ? ' giới hạn' : '') : '');
  }
  function caption(data) {
    if (!data?.focus) return 'Chưa có báo cáo đã đồng bộ. Chọn nguồn để bắt đầu.';
    const period=data.period, snapshot=data.snapshot;
    let value=data.source_name+(data.asset_name ? ' · '+data.asset_name : '');
    if (period) value+=' · '+period.start+' → '+period.end;
    if (snapshot && period?.is_open) value+=' · dữ liệu đến '+period.data_end;
    return value+(snapshot ? ' · Bản lưu #'+snapshot.id.slice(0,8) : ' · Chưa có dữ liệu đúng kỳ');
  }
  function periodRange(key,calendar,fallbackToday) {
    const today=calendar?.today || fallbackToday,iso=(value)=>value.toISOString().slice(0,10);
    const shift=(value,days)=>iso(new Date(new Date(value+'T00:00:00Z').getTime()+days*86400000));
    const closed=calendar?.latest_closed_date || shift(today,-1),first=today.slice(0,8)+'01';
    if(key==='this_month'){const next=new Date(first+'T00:00:00Z');next.setUTCMonth(next.getUTCMonth()+1);return {start:first,end:shift(iso(next),-1)};}
    if(key==='previous_month'){const end=shift(first,-1);return {start:end.slice(0,8)+'01',end};}
    return {start:shift(closed,key==='last7' ? -6 : key==='last90' ? -89 : -29),end:closed};
  }
  function preferredPeriod(preferences) {
    return preferences?.updated_at && ['last7','last30','last90','this_month','previous_month'].includes(preferences.default_period) ? preferences.default_period : 'latest';
  }
  function comparisonText(value) {
    if (!value || value.mode==='none') return '';
    let text=value.label;
    if(value.period) text+=` · ${value.period.start} → ${value.period.end} · ${value.current_days} ngày đang xem / ${value.comparison_days} ngày đối chiếu`;
    if(value.matched_elapsed) text+=' · Cùng phần thời gian đã kết thúc';
    if(value.status!=='ready' && value.message) text+=' · '+value.message;
    return text;
  }
  function changeText(item) {
    if(item.comparison) return item.comparison.status==='ready' ? item.comparison.summary+(item.comparison.relation!=='equal' && item.comparison.effect_label ? ' · '+item.comparison.effect_label : '') : '';
    const current=number(item.value),prior=number(item.previous);
    if(current===null || prior===null || item.grain==='snapshot')return '';
    if(current===prior)return 'Không thay đổi';
    const delta=current-prior,sign=delta>0 ? '+' : '−';
    if(item.unit==='percent')return sign+window.VioDataFormat.format(Math.abs(delta)*100,'number')+' điểm phần trăm';
    return prior===0 ? 'Kỳ đối chiếu bằng 0' : sign+window.VioDataFormat.format(Math.abs(delta)/prior,'percent');
  }
  function bindComparison(prefix,selector,getPeriod,getCalendar,onApply) {
    const select=document.querySelector(selector),form=document.querySelector('#'+prefix+'-custom-comparison');
    if(!select || !form)return {range:()=>null,update:()=>{}};
    const start=form.querySelector('[data-comparison-start]'),end=form.querySelector('[data-comparison-end]');
    const feedback=form.querySelector('[data-comparison-feedback]');let applied=null;
    const stamp=(value)=>typeof value==='string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value+'T00:00:00Z')) && new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value;
    const valid=(first,last)=>stamp(first)&&stamp(last)&&first<=last&&(Date.parse(last)-Date.parse(first))/86400000<=89;
    const show=(text)=>{feedback.textContent=text;feedback.hidden=!text;};
    function update(){
      const custom=select.value==='custom';form.hidden=!custom;
      start.disabled=end.disabled=!custom;start.required=end.required=custom;
      const closed=getCalendar()?.latest_closed_date;
      if(closed){start.max=end.max=closed;}
    }
    function apply(){
      const closed=getCalendar()?.latest_closed_date;
      if(!valid(start.value,end.value) || closed && end.value>closed){show('Chọn kỳ đối chiếu tối đa 90 ngày, chỉ gồm ngày nguồn đã kết thúc.');return false;}
      applied={start:start.value,end:end.value};show('');return true;
    }
    const params=new URLSearchParams(location.search);
    if(valid(params.get('comparison_start'),params.get('comparison_end'))){
      start.value=params.get('comparison_start');end.value=params.get('comparison_end');applied={start:start.value,end:end.value};
    }
    select.addEventListener('change',()=>{
      update();show('');
      if(select.value==='custom'){
        if(!start.value || !end.value){
          const period=getPeriod(),first=period?.data_start||period?.start,last=period?.data_end||period?.end;
          if(valid(first,last)){
            const days=(Date.parse(last)-Date.parse(first))/86400000+1;
            start.value=new Date(Date.parse(first+'T00:00:00Z')-days*86400000).toISOString().slice(0,10);
            end.value=new Date(Date.parse(first+'T00:00:00Z')-86400000).toISOString().slice(0,10);
          }
        }
        if(!apply())return;
      }
      onApply();
    });
    form.addEventListener('submit',(event)=>{event.preventDefault();if(apply())onApply();});
    update();
    return {range:()=>select.value==='custom' ? applied : null,update};
  }
  window.VioSavedAnalytics=Object.freeze({measured,number,format,href,read,goalText,caption,periodRange,preferredPeriod,comparisonText,changeText,bindComparison});
})();
