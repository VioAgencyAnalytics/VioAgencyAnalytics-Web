const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {test} = require('node:test');
const {JSDOM} = require('../../VioAgencyAnalytics-Admin/node_modules/jsdom');

function setup() {
  const dom = new JSDOM('<div id="chart"></div>',{runScripts:'outside-only'});
  for (const file of ['data-format','report-charts']) dom.window.eval(readFileSync('static/js/customer/'+file+'.js','utf8'));
  const report = {metrics:[{key:'views',label:'Lượt xem',unit:'count'}],snapshot:{start_date:'2026-10-01',end_date:'2026-10-04'},
    daily:[{date:'2026-10-01',values:{views:0}},{date:'2026-10-02',values:{views:10}},{date:'2026-10-04',values:{views:2}}]};
  return {dom,report,api:dom.window.VioReportCharts,target:dom.window.document.querySelector('#chart')};
}

test('Line chart never joins across missing days, distinguishes zero and retains keyboard values', () => {
  const {dom,report,api,target} = setup();
  let reading;
  api.render(target,report,'views',{kind:'line',onRead:(value) => { reading = value; }});
  assert.equal(target.querySelectorAll('.pr-line').length,1);
  assert.equal(target.querySelectorAll('.pr-line')[0].getAttribute('points').split(' ').length,2);
  assert.equal(target.querySelectorAll('[data-value=""]').length,1);
  assert.equal(target.querySelectorAll('.pr-zero-dot').length,1);
  const zero = target.querySelector('[data-value="0"]');
  zero.dispatchEvent(new dom.window.Event('focus'));
  assert.match(reading,/01\/10: 0/);
  assert.match(zero.getAttribute('aria-label'),/01\/10: 0/);
  dom.window.close();
});

test('Comparisons use the same metric and real prior dates; different lengths do not fabricate days', () => {
  const {dom,report,api,target} = setup();
  report.comparison = {status:'ready',period:{start:'2026-09-01',end:'2026-09-05'},items:[{key:'views',status:'ready'}],
    daily:[{date:'2026-09-01',values:{views:1}},{date:'2026-09-02',values:{views:0}},{date:'2026-09-05',values:{views:7}}]};
  assert.equal(api.render(target,report,'views',{kind:'line'}),true);
  assert.equal(target.querySelectorAll('.pr-line-previous').length,1);
  assert.equal(target.querySelectorAll('[data-date=""]').length,1);
  assert.match(target.textContent,/Đối chiếu 05\/09: 7/);
  report.comparison.items[0].status = 'not_comparable';
  assert.equal(api.render(target,report,'views',{kind:'line'}),false);
  assert.equal(target.querySelector('.pr-line-previous'),null);
  dom.window.close();
});

test('Unavailable series does not invent bars from period totals, including currency totals', () => {
  const {dom,report,api,target} = setup();
  report.daily = [];
  report.metrics[0].value = 600;
  api.render(target,report,'views');
  assert.equal(target.querySelector('svg'),null);
  assert.match(target.textContent,/chưa cung cấp chuỗi ngày/);
  dom.window.close();
});

test('Search position starts at rank 1, uses a line, and leaves missing or invalid ranks as gaps', () => {
  const {dom,api,target} = setup();
  api.renderSeries(target,[{date:'2026-10-01',value:9},{date:'2026-10-02',value:3.25},
    {date:'2026-10-03',value:0.4},{date:'2026-10-04',value:1}],
    {kind:'bar',position:true,previous:[{date:'2026-09-01',value:10},{date:'2026-09-02',value:1}]});
  const points=target.querySelectorAll('.pr-line-dot');
  assert.equal(points.length,3);
  assert.ok(Number(points[1].getAttribute('cy')) < Number(points[0].getAttribute('cy')));
  assert.equal(points[2].getAttribute('cy'),target.querySelector('.viz-baseline').getAttribute('y1'));
  assert.equal(points[2].getAttribute('cy'),target.querySelectorAll('.pr-zero-previous')[1].getAttribute('cy'));
  assert.equal(target.querySelectorAll('.pr-line').length,1);
  assert.equal(target.querySelectorAll('.pr-line')[0].getAttribute('points').split(' ').length,2);
  assert.equal(target.querySelector('[data-date="2026-10-03"]').getAttribute('data-value'),'');
  assert.equal(target.querySelector('.cr-axis title').textContent,'1');
  assert.match(target.querySelector('.viz-rank-guide').textContent,/Hạng 1/);
  assert.equal(target.querySelector('.viz-area'),null);
  assert.equal(target.querySelector('.viz-toggle button, .cr-bar, .viz-previous-bar'),null);
  dom.window.close();
});

test('Small fractional steps retain their scale labels', () => {
  const {dom,api,target} = setup();
  api.renderSeries(target,[{date:'2026-10-01',value:0.18},{date:'2026-10-02',value:0.83}]);
  const ticks = [...target.querySelectorAll('.cr-axis:has(title)')].map((node) => node.firstChild.textContent);
  assert.deepEqual(ticks,['0','0,25','0,5','0,75','1']);
  dom.window.close();
});

test('Chart type switch preserves current and comparison observations including zero', () => {
  const {dom, report, api, target} = setup();
  report.comparison = {status:'ready', period:{start:'2026-09-01',end:'2026-09-04'}, items:[{key:'views',status:'ready'}],
    daily:[{date:'2026-09-01',values:{views:0}},{date:'2026-09-02',values:{views:8}}]};
  api.render(target, report, 'views', {kind:'bar'});
  assert.equal(target.querySelectorAll('.cr-bar').length, 2);
  assert.equal(target.querySelectorAll('.viz-previous-bar').length, 1);
  const toggle = target.querySelectorAll('.viz-toggle button')[1];
  toggle.click();
  assert.equal(toggle.getAttribute('aria-pressed'), 'true');
  assert.equal(target.querySelectorAll('.cr-bar').length, 0);
  assert.equal(target.querySelectorAll('[data-value=""]').length, 1);
  assert.equal(target.querySelectorAll('.pr-zero-dot').length, 1);
  dom.window.close();
});

test('Donut labels keep the loaded denominator and group small categories without losing their values', () => {
  const {dom, api, target} = setup();
  api.renderDonut(target, Array.from({length:7}, (_,index) => ({label:'Nhóm '+index, value:index+1})), {label:'phiên đã tải'});
  assert.equal(target.querySelectorAll('.viz-slice').length, 5);
  assert.equal(target.querySelector('.viz-donut-value').textContent, '28');
  assert.match(target.textContent, /Các nhóm còn lại/);
  assert.equal([...target.querySelectorAll('.viz-legend-item strong')].reduce((total,item)=>total+Number(item.textContent),0),28);
  api.renderDonut(target, [{label:'Có số liệu',value:7},{label:'Chưa biết',value:null}]);
  assert.equal(target.querySelector('svg'),null);
  api.renderDonut(target, [{label:'A',value:0},{label:'B',value:0}]);
  assert.equal(target.querySelector('svg'),null);
  assert.match(target.textContent,/giá trị 0/);
  dom.window.close();
});

test('Donut text is inert and blank strings cannot become measured zero', () => {
  const {dom, api, target} = setup();
  api.renderDonut(target, [{label:'<img src=x onerror=alert(1)>',value:5}]);
  assert.equal(target.querySelector('img'),null);
  assert.match(target.textContent,/<img src=x/);
  api.renderDonut(target, [{label:'A',value:' '}]);
  assert.equal(target.querySelector('svg'),null);
  assert.deepEqual(JSON.parse(JSON.stringify(api.points([{date:'2026-10-01',values:{v:''}}],'2026-10-01','2026-10-01','v'))),[{date:'2026-10-01',value:null}]);
  dom.window.close();
});

test('Donut currency legends and totals preserve exact decimal strings above the safe integer boundary', () => {
  const {dom, api, target} = setup();
  api.renderDonut(target,[{label:'A',value:'9007199254740993.25'},{label:'B',value:'0.50'}],{
    label:'chi phí đã tải',format:(value)=>dom.window.VioDataFormat.format(value,'currency','USD'),
  });
  assert.match(target.querySelector('.viz-donut').getAttribute('aria-label'),/9\.007\.199\.254\.740\.993,75 USD/);
  assert.match(target.querySelector('.viz-donut-legend').textContent,/9\.007\.199\.254\.740\.993,25 USD/);
  dom.window.close();
});

test('SEO keeps missing ranks separate from confirmed outside Top 100', () => {
  const {api,target}=setup();
  const rows=['Top 3','Hạng 4–10','Hạng 11–30','Hạng 31–100','Ngoài Top 100','Chưa đo'].map((label,index)=>({label,value:6-index}));
  api.renderDonut(target,rows,{maxSlices:6,label:'từ khóa'});
  assert.equal(target.querySelectorAll('.viz-slice').length,6);
  assert.match(target.textContent,/Ngoài Top 100/);
  assert.match(target.textContent,/Chưa đo/);
  assert.doesNotMatch(target.textContent,/Các nhóm còn lại/);
});
