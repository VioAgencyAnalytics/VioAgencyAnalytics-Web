const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {test} = require('node:test');
const {JSDOM} = require('../../VioAgencyAnalytics-Admin/node_modules/jsdom');

function setup(query='') {
  const dom=new JSDOM(`<script id="seo-context-data" type="application/json">{"workspace_id":"${'a'.repeat(32)}","client_id":"${'b'.repeat(32)}","timezone":"Asia/Ho_Chi_Minh"}</script><select id="seo-comparison"><option value="previous">Kỳ trước</option><option value="previous_month">Tháng trước</option><option value="custom">Tùy chỉnh</option><option value="none">Không</option></select><label><input id="seo-comparison-start" type="date"></label><label><input id="seo-comparison-end" type="date"></label>`,{url:'https://customer.example.test/workspace/seo'+query,runScripts:'outside-only'});
  dom.window.eval(readFileSync('static/js/customer/seo-common.js','utf8'));
  const controls=dom.window.VioSEO.comparisonControls('seo',()=>({start:'2026-10-01',end:'2026-10-31'}));
  controls.update();
  return {dom,window:dom.window,controls,select:dom.window.document.querySelector('select')};
}
test('SEO comparison hides inactive dates and restores explicit deep-linked custom windows',()=>{
  const s=setup('?comparison=custom&comparison_start=2026-08-01&comparison_end=2026-08-31');
  assert.equal(s.select.value,'custom');
  assert.equal(s.window.document.querySelector('#seo-comparison-start').disabled,false);
  assert.deepEqual(JSON.parse(JSON.stringify(s.controls.value())),{comparison:'custom',comparison_start:'2026-08-01',comparison_end:'2026-08-31'});
  s.select.value='previous_month';s.select.dispatchEvent(new s.window.Event('change'));
  assert.equal(s.window.document.querySelector('#seo-comparison-start').disabled,true);
  assert.deepEqual(JSON.parse(JSON.stringify(s.controls.value())),{comparison:'previous_month'});
  s.dom.window.close();
});
test('SEO comparison rejects missing, reversed and future ranges instead of reusing stale values',()=>{
  const s=setup('?comparison=custom');
  const a=s.window.document.querySelector('#seo-comparison-start'),b=s.window.document.querySelector('#seo-comparison-end');
  a.value='';b.value='';assert.throws(()=>s.controls.value(),/ngày hợp lệ/);
  a.value='2026-10-31';b.value='2026-10-01';assert.throws(()=>s.controls.value(),/ngày hợp lệ/);
  a.value='2099-01-01';b.value='2099-01-31';assert.throws(()=>s.controls.value(),/chưa kết thúc/);
  s.select.value='none';s.select.dispatchEvent(new s.window.Event('change'));
  assert.deepEqual(JSON.parse(JSON.stringify(s.controls.value())),{comparison:'none'});
  s.dom.window.close();
});

test('comparison preview matches closed months, leap years, elapsed days and ninety-day validation', () => {
  const s = setup(), resolve = s.window.VioSEO.comparisonWindow;
  const plain = value => JSON.parse(JSON.stringify(value));
  const cases = [
    ['2026-10-01', '2026-10-31', 'previous', '2026-12-01', '2026-08-31', '2026-09-30'],
    ['2026-10-01', '2026-10-31', 'previous_month', '2026-12-01', '2026-09-01', '2026-09-30'],
    ['2024-03-01', '2024-03-31', 'previous_month', '2026-12-01', '2024-02-01', '2024-02-29'],
    ['2026-03-29', '2026-03-31', 'previous_month', '2026-12-01', '2026-02-28', '2026-02-28'],
    ['2026-11-01', '2026-11-30', 'previous', '2026-11-16', '2026-10-16', '2026-10-31'],
    ['2026-11-01', '2026-11-30', 'previous_month', '2026-11-16', '2026-10-01', '2026-10-16'],
    ['2026-01-01', '2026-01-31', 'previous_month', '2026-12-01', '2025-12-01', '2025-12-31'],
  ];
  for (const [start, end, mode, closed, first, last] of cases) {
    assert.deepEqual(plain(resolve({start, end}, mode, null, closed)), {start: first, end: last});
  }
  assert.equal(resolve({start:'2026-11-01',end:'2026-11-30'}, 'none'), null);
  assert.equal(resolve({start:'2099-11-01',end:'2099-11-30'}, 'previous', null, '2026-11-16'), null);
  assert.throws(() => resolve({start:'2026-10-01',end:'2026-10-31'}, 'custom', {start:'2025-01-01',end:'2025-04-01'}));
  s.dom.window.close();
});
