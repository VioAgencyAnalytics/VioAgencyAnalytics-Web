const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {test} = require('node:test');
const {JSDOM} = require('../../VioAgencyAnalytics-Admin/node_modules/jsdom');

function setup() {
  const scope = {workspace_id:'a'.repeat(32),client_id:'b'.repeat(32),timezone:'Asia/Ho_Chi_Minh'};
  const component = readFileSync('templates/customer/live/components/seo-comparison.html', 'utf8');
  const dom = new JSDOM(`<script id="seo-context-data" type="application/json">${JSON.stringify(scope)}</script>
    <input id="seo-start" value="2026-10-01"><input id="seo-end" value="2026-10-31">
    <input id="seo-comparison-start"><input id="seo-comparison-end">
    <select id="seo-profile"><option value="profile">Profile</option></select>
    <select id="seo-client-select"><option value="${scope.client_id}">Client</option></select>
    <select id="seo-comparison"><option value="previous_month">Month</option><option value="none">None</option><option value="previous">Previous</option></select>
    <p id="seo-comparison-preview"></p>${component}`, {url:'https://customer.example.test/workspace/seo',runScripts:'outside-only',pretendToBeVisual:true});
  const w = dom.window, calls = [], opened = [];
  w.eval(readFileSync('static/js/customer/seo-common.js', 'utf8'));
  const S = w.VioSEO;
  S.sourceReports = {}; S.sourceErrors = {};
  S.api = async (path, body) => { calls.push({path, body}); return {id:'job'}; };
  S.refreshSources = async () => {};
  S.reload = async () => {};
  S.openImport = target => opened.push(target);
  w.VioDataFormat = {format(value, unit) { return value === undefined || value === null ? '—' : unit === 'percent' ? value * 100 + '%' : String(value); }};
  w.eval(readFileSync('static/js/customer/seo-comparison.js', 'utf8'));
  const data = {scope, profile:'profile',period:{start:'2026-10-01',end:'2026-10-31'},
    comparison:{mode:'previous_month',current_start:'2026-10-01',current_end:'2026-10-31',start:'2026-09-01',end:'2026-09-30'},
    keywords:[{rank:4,state:'ranked',observed_date:'2026-10-22',previous_period_rank:null,previous_period_state:'not_measured',previous_observed_date:null}],
    analysis:{movement:{comparable:0,total:1}},permissions:{edit:true}};
  const load = () => w.document.dispatchEvent(new w.CustomEvent('vio:seo-loaded', {detail:data}));
  const source = (key, report) => { S.sourceReports[key] = report; w.document.dispatchEvent(new w.CustomEvent('vio:seo-source', {detail:{source:key,report}})); };
  load();
  return {dom,w,S,data,calls,opened,load,source};
}
function report(source = 'gsc') {
  return {source,period:{data_start:'2026-10-01',data_end:'2026-10-31'},snapshot:{id:'snapshot'},
    connection:{id:'c'.repeat(32),version:7,status:'connected'},asset:{id:'d'.repeat(32)},permissions:{sync:true},
    metrics:[{key:'clicks',value:40,unit:'count'}],tables:[],calendar:{timezone:'America/Los_Angeles'},
    comparison:{status:'missing',period:{start:'2026-09-01',end:'2026-09-30'},current_days:31,comparison_days:30,items:[]}};
}
const tick = () => new Promise(resolve => setImmediate(resolve));

test('SEO exposes the actual two periods, dated rank imports and source-specific missing data', async () => {
  const s = setup();
  assert.match(s.w.document.querySelector('#seo-comparison-preview').textContent, /01\/09\/2026 – 30\/09\/2026/);
  s.source('gsc', report());
  assert.match(s.w.document.querySelector('#seo-comparison-sources').textContent, /31 \/ 30 ngày/);
  assert.equal(s.w.document.querySelector('#seo-comparison-sync').hidden, false);
  const imported = [...s.w.document.querySelectorAll('button')].find(node => node.textContent === 'Nhập file kỳ đối chiếu');
  imported.click(); assert.deepEqual(s.opened, ['previous']);
  assert.equal(s.calls.length, 0);
  s.dom.window.close();
});

test('the explicit missing-data action syncs the exact source, client, version and comparison dates once', async () => {
  const s = setup(); s.source('gsc', report());
  const button = s.w.document.querySelector('#seo-comparison-sync');
  button.click(); button.click(); await tick();
  assert.equal(s.calls.length, 1);
  assert.equal(s.calls[0].path, 'workspaces/' + 'a'.repeat(32) + '/connections/' + 'c'.repeat(32) + '/sync');
  assert.equal(s.calls[0].body.client_id, 'b'.repeat(32));
  assert.equal(s.calls[0].body.version, 7);
  assert.equal(s.calls[0].body.start, '2026-09-01');
  assert.equal(s.calls[0].body.end, '2026-09-30');
  assert.ok(s.calls[0].body.request_key);
  s.dom.window.close();
});

test('both missing windows use separate idempotency keys and an existing baseline is reused', async () => {
  const s = setup(), missing = report(); missing.snapshot = null;
  s.source('gsc', missing); s.w.document.querySelector('#seo-comparison-sync').click(); await tick();
  assert.equal(s.calls.length, 2);
  assert.deepEqual(s.calls.map(call => call.body.start), ['2026-10-01', '2026-09-01']);
  assert.notEqual(s.calls[0].body.request_key, s.calls[1].body.request_key);
  s.calls.length = 0;
  missing.comparison.snapshot = {id: 'baseline'};
  s.source('gsc', missing); s.w.document.querySelector('#seo-comparison-sync').click(); await tick();
  assert.equal(s.calls.length, 1); assert.equal(s.calls[0].body.start, '2026-10-01');
  s.dom.window.close();
});

test('editing an unapplied period disables sync against the old selection and none hides comparison', async () => {
  const s = setup(); s.source('gsc', report());
  const input = s.w.document.querySelector('#seo-start'); input.value = '2026-10-05';
  input.dispatchEvent(new s.w.Event('input'));
  const button = s.w.document.querySelector('#seo-comparison-sync');
  assert.equal(button.disabled, true); button.click(); await tick(); assert.equal(s.calls.length, 0);
  assert.match(s.w.document.querySelector('#seo-comparison-preview').textContent, /Nhấn Xem dữ liệu/);
  s.data.comparison.mode = 'none'; s.w.document.querySelector('#seo-comparison').value = 'none'; s.load();
  assert.equal(s.w.document.querySelector('#seo-comparison-data').hidden, true);
  s.dom.window.close();
});

test('viewers see data with no mutation controls and organic traffic never falls back to all sessions', async () => {
  const s = setup(); s.data.permissions.edit = false; s.load();
  const ga4 = report('ga4'); ga4.permissions.sync = false;
  ga4.metrics = [{key:'sessions',value:9999,unit:'count'}];
  ga4.tables = [{id:'channels',rows:[{sessionDefaultChannelGroup:'Direct',sessions:9999}]}];
  s.source('ga4', ga4);
  assert.equal(s.w.document.querySelector('#seo-comparison-sync').hidden, true);
  assert.equal(s.w.document.querySelectorAll('#seo-comparison-sources button').length, 0);
  const card = [...s.w.document.querySelectorAll('.seo-compare-source')].find(node => node.textContent.includes('Google Analytics 4'));
  assert.match(card.textContent, /Phiên Organic Search/); assert.doesNotMatch(card.textContent, /9999/);
  assert.match(card.textContent, /—/); assert.equal(s.calls.length, 0);
  s.dom.window.close();
});

test('a saved snapshot does not make an expired connection eligible for another sync', () => {
  const s = setup();
  s.S.sourceIssue = source => source === 'gsc' ? 'reauth' : null;
  s.source('gsc', report());
  assert.equal(s.w.document.querySelector('#seo-comparison-sync').hidden, true);
  const card = [...s.w.document.querySelectorAll('.seo-compare-source')].find(node => node.textContent.includes('Search Console'));
  assert.match(card.textContent, /Đã có dữ liệu/);
  assert.match(card.textContent, /Kết nối lại Search Console/);
  assert.equal(card.querySelector('button'), null);
  s.dom.window.close();
});

test('server errors remain text and every Google date range keeps its source calendar', () => {
  const s = setup();
  s.S.sourceErrors.gsc = '<img src=x onerror=alert(1)> Quyền truy cập đã thay đổi';
  s.source('gsc', null);
  assert.match(s.w.document.querySelector('#seo-comparison-sources').textContent, /Quyền truy cập đã thay đổi/);
  assert.equal(s.w.document.querySelector('#seo-comparison-sources img[onerror]'), null);
  const data = report(); data.period.data_end = '2026-10-29';
  data.comparison.period.end = '2026-09-29'; s.source('gsc', data);
  const card = [...s.w.document.querySelectorAll('.seo-compare-source')].find(node => node.textContent.includes('Search Console'));
  assert.match(card.textContent, /29\/10\/2026/); assert.match(card.textContent, /29\/09\/2026/);
  s.dom.window.close();
});

test('refreshing an existing snapshot remains polling until the queued job completes', async () => {
  const s=setup(), source=report();
  let refreshes=0,reloads=0,scheduled;
  s.w.setTimeout=handler=>{scheduled=handler;return 1;};
  s.S.refreshSources=async()=>{refreshes++;source.latest_sync={status:'succeeded'};};
  s.S.reload=async()=>{reloads++;};
  source.latest_sync={status:'queued'};
  source.comparison.snapshot={id:'baseline'};
  s.source('gsc',source);
  assert.match(s.w.document.querySelector('#seo-comparison-sources').textContent,/Đang đồng bộ/);
  assert.equal(typeof scheduled,'function');
  await scheduled();
  assert.equal(refreshes,1);assert.equal(reloads,1);
  s.dom.window.close();
});
