const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {test} = require('node:test');
const vm = require('node:vm');
const context=vm.createContext({window:{},Intl,BigInt,URL,location:{origin:'https://customer.example.test'}});
for(const file of ['data-format','saved-analytics']) vm.runInContext(readFileSync('static/js/customer/'+file+'.js','utf8'),context);
const api=context.window.VioSavedAnalytics;

test('Native source formatting keeps money exact, zero true and fractional KPI semantics',()=>{
  assert.equal(api.format('9007199254740993.25',{unit:'currency',currency:'USD'}),'9.007.199.254.740.993,25 USD');
  assert.equal(api.format(.25,{unit:'number',currency:'VND'}),'0,25');
  assert.equal(api.format(null,{unit:'count'}),'—');
  assert.equal(api.format(0,{unit:'count'}),'0');
  assert.equal(api.format(.25,{unit:'percent'}),'25%');
});
test('Dashboard report navigation remains on allowlisted private report routes',()=>{
  assert.equal(api.href('/workspace/reports/data?source=ga4&snapshot=abc'),'/workspace/reports/data?source=ga4&snapshot=abc');
  for(const link of ['https://evil.test/','//evil.test/workspace/reports/data','javascript:alert(1)','/api/customer/auth/logout','/workspace/integrations']) assert.equal(api.href(link),'');
});
test('Budget ratios use limits terminology, absent/zero-ratio goals remain honest',()=>{
  assert.equal(api.goalText({value:'100',direction:'at_most',status:'within_limit',ratio:'0.5'}),'Trong giới hạn · 50% giới hạn');
  assert.equal(api.goalText({value:'0',direction:'at_least',status:'met',ratio:null}),'Đạt KPI');
  assert.equal(api.goalText({value:null,status:'not_set'}),'');
  assert.equal(api.goalText({value:'10',status:'no_data',ratio:null}),'KPI chưa có số liệu');
  assert.equal(api.goalText({value:'10',status:'below_target',ratio:'0.0000001',assessment:{label:'Đang thực hiện'}}),'Đang thực hiện · <0,01%');
  assert.equal(context.window.VioDataFormat.fraction('90071992547409.9325'),'9.007.199.254.740.993,25%');
});
test('Source calendar presets keep full monthly targets and closed-day last30',()=>{
  const calendar={today:'2026-11-10',latest_closed_date:'2026-11-09'};
  assert.equal(JSON.stringify(api.periodRange('this_month',calendar,'2099-01-01')),JSON.stringify({start:'2026-11-01',end:'2026-11-30'}));
  assert.equal(JSON.stringify(api.periodRange('last30',calendar,'2099-01-01')),JSON.stringify({start:'2026-10-11',end:'2026-11-09'}));
});
test('Monthly presets follow the selected source clock and leap-year boundary',()=>{
  const calendar={today:'2024-03-01',latest_closed_date:'2024-02-28'};
  assert.equal(JSON.stringify(api.periodRange('previous_month',calendar,'2026-11-10')),JSON.stringify({start:'2024-02-01',end:'2024-02-29'}));
  assert.equal(JSON.stringify(api.periodRange('last7',calendar,'2026-11-10')),JSON.stringify({start:'2024-02-22',end:'2024-02-28'}));
});

test('Saved Workspace period preferences apply; initial or invalid preferences use latest',()=>{
  assert.equal(api.preferredPeriod(undefined),'latest');
  assert.equal(api.preferredPeriod({default_period:'last30',updated_at:null}),'latest');
  for(const period of ['last7','last30','last90','this_month','previous_month']) assert.equal(api.preferredPeriod({default_period:period,updated_at:'2026-11-10T00:00:00Z'}),period);
  assert.equal(api.preferredPeriod({default_period:'custom',updated_at:'2026-11-10T00:00:00Z'}),'latest');
});
