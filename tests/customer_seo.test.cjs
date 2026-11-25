const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const code = fs.readFileSync(require('node:path').join(__dirname, '../static/js/customer/seo-common.js'), 'utf8');
function setup(payload) {
  const context = {workspace_id:'a'.repeat(32),client_id:'b'.repeat(32),timezone:'Asia/Ho_Chi_Minh'};
  const document = {querySelector(selector) { return selector === '#seo-context-data' ? {textContent:JSON.stringify(context)} : null; },createElement(tag) { return {tag}; }};
  const window = {};
  const sandbox = {document,window,Intl,Date,URL,AbortSignal,fetch:async () => ({ok:true,json:async () => payload}),location:{assign() {}}};
  vm.runInNewContext(code,sandbox);
  return window.VioSEO;
}
test('report periods reject invalid leap dates, reversed ranges and more than ninety days', () => {
  const S = setup();
  assert.equal(S.monthRange('2024-02').end,'2024-02-29');
  assert.equal(S.monthRange('2026-02').end,'2026-02-28');
  assert.throws(() => S.validPeriod('2026-02-30','2026-03-02'));
  assert.throws(() => S.validPeriod('2026-10-02','2026-10-01'));
  assert.throws(() => S.validPeriod('2026-01-01','2026-04-01'));
  assert.equal(S.validPeriod('2026-01-01','2026-03-31').end,'2026-03-31');
});
test('links never promote script schemes or credentials into clickable report URLs', () => {
  const S = setup();
  assert.equal(S.link('javascript:alert(1)').tag,'span');
  assert.equal(S.link('https://user:pass@example.com').tag,'span');
  assert.equal(S.link('https://example.com/a').rel,'noopener noreferrer');
});
test('API results must match both selected workspace and client', async () => {
  const S = setup({scope:{workspace_id:'a'.repeat(32),client_id:'c'.repeat(32)}});
  await assert.rejects(S.api('workspaces/seo'),/Khách hàng đã thay đổi/);
});
