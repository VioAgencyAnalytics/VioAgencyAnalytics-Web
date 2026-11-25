const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('../../VioAgencyAnalytics-Admin/node_modules/jsdom');

function setup() {
  let html = ['seo-content', 'seo-project', 'seo-reports'].map(name => fs.readFileSync(`templates/customer/live/components/${name}.html`, 'utf8')).join('');
  html = html.replace(/\{% for n in \[1,3,6,9,12,18,24\] %\}[\s\S]*?\{% endfor %\}/, '<option value="12">12 tháng</option>');
  html += '<div id="seo-legacy-plan"></div><section id="seo-performance"></section><section id="seo-panel-keywords"></section><button id="seo-website-edit"></button><dialog id="seo-website-dialog"></dialog><form id="seo-website-form"><input id="seo-website-input"><p id="seo-website-error"></p></form>';
  const dom = new JSDOM(html, {url:'http://127.0.0.1/workspace/seo',runScripts:'outside-only'});
  const w = dom.window, d = w.document, calls = [], messages = [];
  w.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
  w.HTMLDialogElement.prototype.close = function () { this.open = false; };
  const S = {scope:{workspace_id:'a'.repeat(32),client_id:'b'.repeat(32)},base:'workspaces/'+'a'.repeat(32),sourceReports:{},
    element(tag, text='', cls='') { const node=d.createElement(tag);node.textContent=text;if(cls)node.className=cls;return node; },
    message(text,error,target) { messages.push({text,error});if(target){target.textContent=text;target.hidden=!text;} },
    date:value=>value||'—',today:()=> '2026-11-13',monthRange:month=>({start:month+'-01',end:month+'-31'}),
    link(url,label) { const a=d.createElement('a');a.href=url;a.textContent=label;return a; },
    async api(path,body) { calls.push({path,body});return {reports:[],message:'OK'}; },
    async reload() {},async busy(button,fn,target) { try { await fn(); } catch(error) { S.message(error.message,true,target); } }};
  w.VioSEO=S;w.VioReportCharts={renderSeries(){}};
  w.eval(fs.readFileSync('static/js/customer/seo-delivery.js','utf8'));
  const data={client:{id:S.scope.client_id,name:'Khách hàng'},period:{start:'2026-10-01',end:'2026-10-31'},comparison:{mode:'previous_month'},permissions:{edit:true},keywords:[],profile:'',
    content:{items:[],summary:{},previous_summary:null,ledger_count:0,history:[],trend:[]},
    project:{plan:null,items:[],definitions:[{key:'new_articles',label:'Bài mới',unit:'count'},{key:'traffic',label:'Lưu lượng',unit:'count'}]}};
  function load() { d.dispatchEvent(new w.CustomEvent('vio:seo-loaded',{detail:data})); }
  load();return {dom,w,d,S,data,calls,messages,load};
}

test('website content is rendered as text and archived records stay outside active list',async()=>{
  const q=setup();q.data.content.items=[{id:'x',title:'<img src=x onerror=alert(1)>',kind:'new',month:'2026-10',publication_status:'published',review_status:'approved',published_date:'2026-10-01',accepted_date:'2026-10-02',url:'https://example.test/a',archived:false},
    {id:'y',title:'Archived',kind:'new',month:'2026-10',publication_status:'draft',review_status:'pending',archived:true}];q.load();
  assert.equal(q.d.querySelectorAll('#seo-content-rows tr').length,1);
  assert.equal(q.d.querySelector('#seo-content-rows img'),null);
  assert.match(q.d.querySelector('#seo-content-rows').textContent,/<img/);
  q.d.querySelector('#seo-content-status').value='archived';q.d.querySelector('#seo-content-status').dispatchEvent(new q.w.Event('change'));
  assert.match(q.d.querySelector('#seo-content-rows').textContent,/Archived/);await new Promise(resolve=>setImmediate(resolve));q.dom.window.close();
});

test('article form preserves pending acceptance and passes the version on edits',async()=>{
  const q=setup();const row={id:'x',version:4,title:'Nội dung',kind:'update',month:'2026-10',publication_status:'published',review_status:'approved',published_date:'2026-09-01',accepted_date:'2026-10-02',url:'https://example.test/a',archived:false};
  q.data.content.items=[row];q.load();q.d.querySelector('#seo-content-rows button').click();
  assert.equal(q.d.querySelector('#seo-content-attest').checked,false);
  q.d.querySelector('#seo-content-accepted').value='';
  q.d.querySelector('#seo-content-form').dispatchEvent(new q.w.Event('submit',{bubbles:true,cancelable:true}));
  await new Promise(resolve=>setImmediate(resolve));
  const sent=q.calls.find(row=>row.path.endsWith('/seo/content')).body;
  assert.equal(sent.version,4);assert.equal(sent.item.kind,'update');assert.equal(sent.item.accepted_date,'');assert.equal(sent.acceptance_confirmed,false);q.dom.window.close();
});

test('monthly contract editor preserves zero versus unset and different month targets',async()=>{
  const q=setup();q.data.project.plan={version:2,name:'SEO',start_month:'2026-10',duration:2,traffic_metric:'gsc_clicks',months:[{month:'2026-10',new_articles:0,traffic:null},{month:'2026-11',new_articles:12,traffic:100}]};
  q.load();q.d.querySelector('#seo-project-edit').click();
  assert.equal(q.d.querySelector('[data-seo-project-target=new_articles]').value,'0');
  assert.equal(q.d.querySelector('[data-seo-project-target=traffic]').value,'');
  q.d.querySelector('#seo-project-month').value='1';q.d.querySelector('#seo-project-month').dispatchEvent(new q.w.Event('change'));
  assert.equal(q.d.querySelector('[data-seo-project-target=new_articles]').value,'12');
  q.d.querySelector('#seo-project-attest').checked=true;q.d.querySelector('#seo-project-form').dispatchEvent(new q.w.Event('submit',{bubbles:true,cancelable:true}));
  await new Promise(resolve=>setImmediate(resolve));
  const sent=q.calls.find(row=>row.path.endsWith('/seo/project')).body;
  assert.equal(sent.version,2);assert.equal(sent.plan.months[0].new_articles,0);assert.equal(sent.plan.months[0].traffic,null);assert.equal(sent.plan.months[1].new_articles,12);q.dom.window.close();
});

test('missing Organic Search row never becomes zero in SEO overview',async()=>{
  const q=setup();q.S.sourceReports.ga4={state:'ready',metrics:[],tables:[{id:'channels',rows:[{sessionDefaultChannelGroup:'Direct',sessions:30}]}]};
  q.d.dispatchEvent(new q.w.CustomEvent('vio:seo-source'));
  assert.equal(q.d.querySelectorAll('#seo-performance strong')[2].textContent,'—');await new Promise(resolve=>setImmediate(resolve));q.dom.window.close();
});

test('KPI cards identify actual versus commitment and keep overachievement visible',async()=>{
  const q=setup();q.data.project.plan={version:1,name:'SEO',start_month:'2026-10',duration:1,months:[{month:'2026-10'}]};
  q.data.project.items=[{key:'top10_percent',label:'Top 10',source:'Spineditor',unit:'percent',actual:30,target:25,
    difference:5,achievement:120,status:'met',note:'12/40 từ đã chốt'},
    {key:'traffic',label:'Lưu lượng',source:'GSC',unit:'count',actual:null,target:100,difference:null,
      achievement:null,status:'no_data',note:'Chưa có bản đúng kỳ'}];q.load();
  const cards=q.d.querySelectorAll('#seo-project-results article');
  assert.match(cards[0].textContent,/Thực tế \/ Cam kết tháng/);
  assert.match(cards[0].textContent,/120% hoàn thành/);
  assert.match(cards[0].textContent,/5 điểm phần trăm/);
  assert.equal(cards[0].querySelector('progress').value,100);
  assert.equal(cards[1].querySelector('progress').hidden,true);
  assert.match(cards[1].querySelector('strong').textContent,/— \/ 100/);
  await new Promise(resolve=>setImmediate(resolve));q.dom.window.close();
});

test('monthly target inputs explain their data source through accessible descriptions',async()=>{
  const q=setup();q.d.querySelector('#seo-project-edit').click();
  const field=q.d.querySelector('[data-seo-project-target=new_articles]');
  assert.match(q.d.getElementById(field.getAttribute('aria-describedby')).textContent,/nghiệm thu/);
  const traffic=q.d.querySelector('[data-seo-project-target=traffic]');
  assert.match(q.d.getElementById(traffic.getAttribute('aria-describedby')).textContent,/Tổng trong tháng/);
  await new Promise(resolve=>setImmediate(resolve));q.dom.window.close();
});
