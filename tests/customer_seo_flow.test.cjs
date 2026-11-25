const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('../../VioAgencyAnalytics-Admin/node_modules/jsdom');

function setup() {
  const dom=new JSDOM('<section id="seo-panel-content"></section><input id="seo-start" value="2026-10-01"><input id="seo-end" value="2026-10-31"><div data-seo-flow-sources="ga4,gsc"></div><div id="seo-kpi-required-source"></div><div id="seo-article-performance"></div><div id="seo-report-readiness"></div><div id="seo-project-timeline"></div>', {url:'http://localhost/workspace/seo',runScripts:'outside-only'});
  const w=dom.window,d=w.document,calls=[];
  const S={sourceReports:{},element(tag,text='',cls=''){const node=d.createElement(tag);node.textContent=text;node.className=cls;return node;},
    link(url,text){const a=d.createElement('a');a.href=url;a.textContent=text;return a;},date:x=>x,
    async busy(node,fn){await fn();},async syncSeoSource(source){calls.push(source);},setTab(){}};
  w.VioSEO=S;w.VioDataFormat={format(value,unit){return value===null||value===undefined?'—':unit==='percent'?value*100+'%':String(value);}};
  w.eval(fs.readFileSync('static/js/customer/seo-flow.js','utf8'));
  const data={period:{start:'2026-10-01',end:'2026-10-31'},comparison:{mode:'previous'},keywords:[],content:{items:[]},project:{plan:null},effectiveness:{sources:{},items:[]}};
  const load=()=>d.dispatchEvent(new w.CustomEvent('vio:seo-loaded',{detail:data}));
  load();return {dom,w,d,S,data,load,calls};
}

test('SEO source cards identify the required connector and never sync on read',()=>{
  const q=setup();
  assert.ok(q.d.querySelector('a[href="/workspace/integrations?platform=ga4"]'));
  assert.ok(q.d.querySelector('a[href="/workspace/integrations?platform=gsc"]'));
  assert.equal(q.calls.length,0);
  q.S.sourceReports.ga4={state:'empty',connection:{status:'connected'},asset:{id:'asset',name:'<img src=x>'},permissions:{sync:true}};
  q.load();
  assert.equal(q.d.querySelectorAll('.seo-flow-source img').length,2);
  const button=[...q.d.querySelectorAll('.seo-flow-source button')].find(node=>node.textContent==='Đồng bộ kỳ này');
  button.click();
  assert.deepEqual(q.calls,['ga4']);q.dom.window.close();
});

test('report preparation counts saved data in the selected period and keeps the import in that period', () => {
  const q = setup(), prep = q.d.querySelector('[data-seo-flow-sources]'), imports = [];
  prep.dataset.seoFlowSources = 'spineditor,gsc,ga4';
  const status = q.d.createElement('p');
  status.id = 'seo-report-source-status';
  q.d.body.append(status);
  q.data.permissions = {edit: true};
  q.data.keywords = [{observed_date:null, previous_observed_date:'2026-09-15'}];
  q.data.effectiveness.sources.gsc = {state:'wrong_website'};
  q.S.sourceIssue = source => source === 'gsc' ? 'wrong_website' : null;
  q.S.openImport = (...args) => imports.push(args);
  q.S.sourceReports.ga4 = {state:'empty', connection:{status:'connected'}, asset:{name:'GA4 site'}};
  q.S.sourceReports.gsc = {state:'ready', connection:{status:'connected'}, asset:{name:'Another site'},
    snapshot:{start_date:'2026-10-01', end_date:'2026-10-31'}, permissions:{sync:true}};
  q.load();
  assert.match(status.textContent, /0\/3/);
  assert.match(prep.textContent, /Website đang chọn khác website báo cáo/);
  assert.equal(prep.querySelectorAll('.seo-flow-status[data-state="ready"]').length, 0);
  const importButton = [...prep.querySelectorAll('button')].find(button => button.textContent === 'Nhập thứ hạng');
  importButton.click();
  assert.deepEqual(imports, [['current', 'reports']]);
  q.data.keywords[0].observed_date = '2026-10-19';
  q.S.sourceReports.ga4 = {...q.S.sourceReports.ga4, state:'ready', snapshot:{start_date:'2026-10-01', end_date:'2026-10-31'}};
  q.load();
  assert.match(status.textContent, /2\/3/);
  assert.match(q.d.querySelector('#seo-report-readiness').textContent, /Chưa có cặp thứ hạng để đối chiếu/);
  q.dom.window.close();
});

test('per-article values keep unknown separate from measured zero and expose the previous observation',()=>{
  const q=setup();
  q.data.effectiveness.items=[{id:'article',title:'<script>article</script>',url:'https://example.test/a',
    values:{views:0,clicks:null,impressions:10,ctr:0,position:2},previous:{views:0,clicks:null,impressions:8,ctr:0,position:3}}];
  q.load();
  const cells=q.d.querySelectorAll('#seo-article-performance tbody td');
  assert.equal(cells[1].querySelector('strong').textContent,'0');
  assert.equal(cells[2].querySelector('strong').textContent,'—');
  assert.match(cells[1].textContent,/Trước: 0/);
  assert.equal(q.d.querySelector('#seo-article-performance script'),null);q.dom.window.close();
});

test('monthly KPI matrix keeps the observed zero, blank future cells and plan-only total',()=>{
  const q=setup();
  q.data.project.timeline={totals:{new_articles:{target:10,actual:0}},metrics:[{key:'new_articles',label:'Bài mới',unit:'count'}],months:[
    {month:'2026-10',items:[{key:'new_articles',target:0,actual:0,status:'met'}]},
    {month:'2026-11',items:[{key:'new_articles',target:10,actual:null,status:'not_started'}]}]};
  q.load();
  const plan=q.d.querySelectorAll('.seo-matrix-plan td'), actual=q.d.querySelectorAll('.seo-matrix-actual td');
  assert.equal(q.d.querySelector('.seo-matrix-banner th').colSpan, 5);
  assert.deepEqual([...q.d.querySelectorAll('.seo-kpi-matrix thead tr:last-child th')].map(th=>th.textContent), ['STT', 'Tháng', '1', '2', 'Tổng']);
  assert.equal(q.d.querySelector('.seo-matrix-plan > th').textContent, 'Bài mới');
  assert.equal(q.d.querySelector('.seo-matrix-actual > th').textContent, 'Đã thực hiện');
  assert.equal(plan[1].textContent,'0');
  assert.equal(plan[3].textContent,'10');
  assert.equal(actual[0].textContent,'0');
  assert.equal(actual[1].textContent,'');
  assert.match(actual[1].title,/Chưa tới kỳ/);
  assert.equal(actual[2].textContent,'');
  q.dom.window.close();
});
