const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('../../VioAgencyAnalytics-Admin/node_modules/jsdom');
const tick = () => new Promise(resolve => setImmediate(resolve));

function setup() {
  const html = fs.readFileSync('templates/customer/live/components/seo-automation.html', 'utf8') +
    '<input id="seo-start"><input id="seo-end"><select id="seo-client-select"><option value="client">Client</option></select><section id="seo-gsc-discovery"></section>';
  const dom = new JSDOM(html, {url:'http://127.0.0.1/workspace/seo', runScripts:'outside-only', pretendToBeVisual:true});
  const w = dom.window, d = w.document, calls = [], messages = [];
  w.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
  w.HTMLDialogElement.prototype.close = function () { this.open = false; };
  const q = {dom, w, d, calls, messages};
  q.discovery = {snapshot:{id:'snapshot'}, items:[], page_grouping:true};
  q.handler = async path => path.includes('/discovery?') ? q.discovery : {id:'job', status:'queued'};
  const S = {
    base:'workspaces/workspace', sourceReports:{gsc:{state:'ready', snapshot:{id:'snapshot'}}},
    element(tag, text = '', cls = '') { const node = d.createElement(tag); node.textContent = text; node.className = cls; return node; },
    link(url, text) { const node = d.createElement('a'); node.href = url; node.textContent = text; return node; },
    date:value => value, message(text, error, target) { messages.push({text, error}); if (target) target.textContent = text; },
    async api(path, body) { calls.push({path, body}); return q.handler(path, body); },
    async busy(button, action, target) { try { await action(); } catch (error) { S.message(error.message, true, target); } },
    async reload() { q.load(); }, async refreshSources() {}, editContent(value) { q.edit = value; }
  };
  q.S = S;
  q.data = {scope:{client_id:'client'}, period:{start:'2026-10-01', end:'2026-10-31'}, website:'https://example.test',
    permissions:{edit:true}, keywords:[], automation:{website_job:null}};
  q.load = () => {
    d.querySelector('#seo-start').value = q.data.period.start;
    d.querySelector('#seo-end').value = q.data.period.end;
    d.dispatchEvent(new w.CustomEvent('vio:seo-loaded', {detail:q.data}));
  };
  w.VioSEO = S;
  w.eval(fs.readFileSync('static/js/customer/seo-automation.js', 'utf8'));
  q.load();
  return q;
}

test('website sync requires the applied scope and reuses the request key after an ambiguous failure', async () => {
  const q = setup();
  q.d.querySelector('#seo-start').value = '2026-09-01';
  q.d.querySelector('#seo-website-sync-open').click(); await tick();
  assert.equal(q.d.querySelector('#seo-website-sync-dialog').open, false);
  assert.match(q.messages.at(-1).text, /Xem dữ liệu/);
  q.load();
  q.d.querySelector('#seo-website-sync-open').click(); await tick();
  assert.equal(q.d.querySelector('#seo-website-sync-dialog').open, true);
  q.handler = async path => { if (path.endsWith('/website-sync')) throw Error('Timeout'); return q.discovery; };
  const submit = () => q.d.querySelector('#seo-website-sync-form').dispatchEvent(new q.w.Event('submit', {cancelable:true}));
  submit(); await tick(); submit(); await tick();
  const writes = q.calls.filter(call => call.path.endsWith('/website-sync'));
  assert.equal(writes.length, 2);
  assert.equal(writes[0].body.request_key, writes[1].body.request_key);
  assert.equal(writes[0].body.client_id, 'client');
  assert.equal(writes[0].body.start, '2026-10-01');
  assert.equal(writes[0].body.mode, 'auto');
  q.dom.window.close();
});

test('discovery paginates and escapes queries, preserves zero and unknown, and confirms the saved role', async () => {
  const q = setup();
  q.discovery.items = Array.from({length:26}, (_, i) => ({keyword:i ? 'keyword '+i : '<img onerror=alert(1)>',
    page:'https://example.test/'+i, role:'primary', reason:'Query', clicks:0, impressions:1, position:null, tracked:i ? null : {id:'tracked'}}));
  q.data.keywords = [{id:'tracked', version:4, role:'secondary', role_reviewed:0, topic:'Lead chọn', segment:'niche', committed:true}];
  q.load(); await tick();
  const rows = q.d.querySelectorAll('#seo-auto-keyword-rows tr');
  assert.equal(rows.length, 25); assert.equal(q.d.querySelector('#seo-auto-keyword-rows img'), null);
  assert.equal(rows[0].children[2].textContent, '0'); assert.equal(rows[0].children[4].textContent, '—');
  rows[0].querySelector('button').click(); await tick();
  const write = q.calls.find(call => call.path.endsWith('/seo/keywords')).body.changes[0];
  assert.equal(write.role, 'secondary'); assert.equal(write.committed, true);
  assert.equal(write.version, 4); assert.equal(write.segment, 'niche');
  q.d.querySelector('#seo-auto-keywords-next').click(); await tick();
  assert.equal(q.d.querySelectorAll('#seo-auto-keyword-rows tr').length, 1);
  q.dom.window.close();
});

test('a slow discovery response from the previous period never replaces the new period', async () => {
  const q = setup(); await tick();
  const pending = [];
  q.handler = () => new Promise(resolve => pending.push(resolve));
  q.load();
  q.data.period = {start:'2026-09-01', end:'2026-09-30'}; q.load();
  const result = keyword => ({snapshot:{id:keyword}, page_grouping:true, items:[{keyword, page:'', role:'secondary', clicks:1, impressions:2, position:1}]});
  pending[0](result('OLD PERIOD')); await tick();
  assert.doesNotMatch(q.d.querySelector('#seo-auto-keyword-rows').textContent, /OLD PERIOD/);
  pending[1](result('NEW PERIOD')); await tick();
  assert.match(q.d.querySelector('#seo-auto-keyword-rows').textContent, /NEW PERIOD/);
  q.dom.window.close();
});

test('undated articles prefill a pending review and never claim acceptance', async () => {
  const q = setup();
  q.data.automation.website_job = {status:'succeeded', added:1, duplicates:0, without_date:1,
    needs_review:[{title:'Article', url:'https://example.test/article'}]};
  q.load();
  q.d.querySelector('#seo-website-review button').click(); await tick();
  assert.equal(q.edit.title, 'Article'); assert.equal(q.edit.review_status, 'pending');
  assert.equal(q.edit.accepted_date, undefined); assert.equal(q.edit.published_date, undefined);
  q.dom.window.close();
});
