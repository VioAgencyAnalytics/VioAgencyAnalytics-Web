const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {test} = require('node:test');
const vm = require('node:vm');
const context = vm.createContext({window:{},document:{querySelector:()=>null},Date,BigInt});
vm.runInContext(readFileSync('static/js/customer/report-controls.js','utf8'),context);
const {range,valid,goalInput} = context.window.VioReportControls;
const calendar = {today:'2026-11-10',latest_closed_date:'2026-11-09'};
const plain = (value) => JSON.parse(JSON.stringify(value));

test('Presets use the source calendar, closed days and full requested months',() => {
  assert.deepEqual(plain(range('last7',calendar)),{start:'2026-11-03',end:'2026-11-09'});
  assert.deepEqual(plain(range('last30',calendar)),{start:'2026-10-11',end:'2026-11-09'});
  assert.deepEqual(plain(range('this_month',calendar)),{start:'2026-11-01',end:'2026-11-30'});
  assert.deepEqual(plain(range('last_month',calendar)),{start:'2026-10-01',end:'2026-10-31'});
});
test('Month picker handles leap years and January rollover without local clock drift',() => {
  assert.deepEqual(plain(range('month',calendar,'2024-02')),{start:'2024-02-01',end:'2024-02-29'});
  assert.deepEqual(plain(range('last_month',{today:'2027-01-01',latest_closed_date:'2026-12-31'})),{start:'2026-12-01',end:'2026-12-31'});
  assert.equal(range('month',calendar,'2026-13'),null);
});
test('Custom window permits at most 90 inclusive days and rejects normalized invalid dates',() => {
  assert.equal(valid('2026-01-01','2026-03-31'),true);
  assert.equal(valid('2026-01-01','2026-04-01'),false);
  assert.equal(valid('2026-02-30','2026-03-01'),false);
  assert.equal(valid('2026-11-10','2026-11-09'),false);
});
test('Goals retain exact decimals, allow Vietnamese decimal comma and explicit zero',() => {
  assert.equal(goalInput('9007199254740993.25000000','currency'),'9007199254740993.25');
  assert.equal(goalInput('2,500','percent'),'2.5');
  assert.equal(goalInput('0','count'),'0');
  assert.equal(goalInput('','count'),null);
  for (const [value,unit] of [['1.000.000','currency'],['-1','count'],['0.5','count'],['100.00000001','percent'],['NaN','number']]) assert.throws(()=>goalInput(value,unit));
});
