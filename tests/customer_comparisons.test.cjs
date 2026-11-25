const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {test}=require('node:test');
const {JSDOM}=require('../../VioAgencyAnalytics-Admin/node_modules/jsdom');

function setup(query=''){
  const dom=new JSDOM(`<select id="compare"><option value="previous">Kỳ trước</option><option value="custom">Tùy chỉnh</option><option value="none">Không so sánh</option></select><form id="test-custom-comparison" hidden><label>Từ<input type="date" data-comparison-start></label><label>Đến<input type="date" data-comparison-end></label><button>Áp dụng</button><p data-comparison-feedback hidden></p></form>`,{url:'https://customer.example.test/workspace/dashboard'+query,runScripts:'outside-only'});
  for(const file of ['data-format','saved-analytics'])dom.window.eval(readFileSync('static/js/customer/'+file+'.js','utf8'));
  const w=dom.window,api=w.VioSavedAnalytics;let applied=0;
  if(query)w.document.querySelector('#compare').value='custom';
  const controls=api.bindComparison('test','#compare',()=>({start:'2026-11-01',end:'2026-11-30',data_start:'2026-11-01',data_end:'2026-11-10'}),()=>({latest_closed_date:'2026-11-10'}),()=>{applied++;});
  return {dom,w,api,controls,applied:()=>applied,select:w.document.querySelector('#compare'),form:w.document.querySelector('form'),start:w.document.querySelector('[data-comparison-start]'),end:w.document.querySelector('[data-comparison-end]')};
}

test('Custom comparison starts from elapsed days and draft edits do not silently change the applied period',()=>{
  const s=setup();
  assert.equal(s.form.hidden,true);assert.equal(s.start.disabled,true);
  s.select.value='custom';s.select.dispatchEvent(new s.w.Event('change'));
  assert.equal(s.form.hidden,false);assert.equal(s.start.required,true);
  assert.equal(s.start.value,'2026-10-22');assert.equal(s.end.value,'2026-10-31');assert.equal(s.applied(),1);
  s.start.value='2026-09-01';
  assert.equal(s.controls.range().start,'2026-10-22');
  s.form.dispatchEvent(new s.w.Event('submit',{cancelable:true}));
  assert.equal(s.controls.range().start,'2026-09-01');assert.equal(s.applied(),2);
  s.select.value='none';s.select.dispatchEvent(new s.w.Event('change'));
  assert.equal(s.controls.range(),null);assert.equal(s.start.disabled,true);assert.equal(s.start.required,false);
  s.dom.window.close();
});

test('Future and over-90-day comparisons show an error and retain the last applied dates',()=>{
  const s=setup();s.select.value='custom';s.select.dispatchEvent(new s.w.Event('change'));
  for(const [start,end] of [['2026-01-01','2026-04-01'],['2026-11-01','2026-11-30']]){
    s.start.value=start;s.end.value=end;s.form.dispatchEvent(new s.w.Event('submit',{cancelable:true}));
    assert.equal(s.controls.range().start,'2026-10-22');assert.equal(s.applied(),1);
    assert.equal(s.form.querySelector('[data-comparison-feedback]').hidden,false);
  }
  s.dom.window.close();
});

test('Deep links restore the applied comparison and API requests keep the explicit dates',async()=>{
  const s=setup('?comparison=custom&comparison_start=2026-09-01&comparison_end=2026-09-30');
  assert.equal(s.start.value,'2026-09-01');assert.equal(s.controls.range().end,'2026-09-30');
  let captured;
  s.w.fetch=async(url)=>{captured=new URL(url,s.w.location.origin);return {ok:true,json:async()=>({scope:{workspace_id:'a',client_id:'b'}})};};
  await s.api.read('a','b','gsc',{start:'2026-10-01',end:'2026-10-31'},'custom',null,'day',s.controls.range());
  assert.equal(captured.searchParams.get('comparison_start'),'2026-09-01');
  assert.equal(captured.searchParams.get('comparison_end'),'2026-09-30');
  s.dom.window.close();
});

test('Changes preserve server decimal/percentage-point semantics and do not turn missing or stock into growth',()=>{
  const s=setup(),api=s.api;
  assert.equal(api.changeText({value:.25,previous:.20,unit:'percent'}),'+5 điểm phần trăm');
  assert.equal(api.changeText({value:5,previous:null}), '');
  assert.equal(api.changeText({value:5,previous:0}), 'Kỳ đối chiếu bằng 0');
  assert.equal(api.changeText({value:8,previous:4,grain:'snapshot'}),'');
  assert.equal(api.changeText({comparison:{status:'ready',summary:'+1,25%'}}),'+1,25%');
  const text=api.comparisonText({mode:'previous_month',label:'Cùng kỳ tháng trước',period:{start:'2026-10-01',end:'2026-10-10'},current_days:10,comparison_days:10,matched_elapsed:true,status:'missing',message:'Chưa có bản lưu'});
  assert.match(text,/10 ngày đang xem/);assert.match(text,/10 ngày đối chiếu/);assert.match(text,/Chưa có bản lưu/);
  s.dom.window.close();
});
