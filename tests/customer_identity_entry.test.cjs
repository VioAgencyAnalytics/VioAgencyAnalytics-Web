const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {test} = require('node:test');
const {JSDOM, VirtualConsole} = require('../../VioAgencyAnalytics-Admin/node_modules/jsdom');

const workspace = (id, name) => ({id:id.repeat(32),name,kind:'business',role:'owner',client_count:1,client_preview:[name]});
async function page(kind, workspaces=[]) {
  const template=readFileSync('templates/customer/live/'+kind+'.html','utf8');
  const dom=new JSDOM('<!doctype html><body data-customer-page="'+kind+'">'+template+'</body>',{url:'https://customer.example.test/workspace/'+kind,runScripts:'outside-only',virtualConsole:new VirtualConsole()});
  const w=dom.window,requests=[];
  w.matchMedia=()=>({matches:true});w.HTMLElement.prototype.scrollIntoView=()=>{};
  if(w.HTMLDialogElement) {
    w.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
    w.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
  }
  w.fetch=async(url,options={})=>{
    requests.push({url,options});
    if(url.endsWith('/session'))return {ok:true,json:async()=>({user:kind==='login'?null:{id:'qa',name:'Minh Anh',email:'qa@example.test',email_verified:1},workspaces,workspace:null,csrf:'qa-only',capabilities:{google:true,email_delivery:true}})};
    if(url.endsWith('/workspaces/join'))return {ok:false,status:400,json:async()=>({error:'Mã mời đã hết hạn.',code:'invitation_invalid'})};
    return {ok:true,json:async()=>({available:false,message:'OK'})};
  };
  w.eval(readFileSync('static/js/customer/branding.js','utf8'));
  w.eval(readFileSync('static/js/customer/identity.js','utf8'));
  await new Promise(resolve=>setImmediate(resolve));
  return {dom,w,d:w.document,requests};
}

test('Existing users choose a Workspace first; creation is explicit and preserves a draft', async()=>{
  const {dom,w,d}=await page('onboarding',[workspace('a','Vio Agency'),workspace('b','Sàn gỗ Á Châu')]);
  assert.equal(d.querySelector('#workspace-create-section').hidden,true);
  assert.equal(d.querySelectorAll('#workspace-list button').length,2);
  d.querySelector('#workspace-create-open').click();
  assert.equal(d.querySelector('#workspace-picker').hidden,true);
  const name=d.querySelector('[name=name]');name.value='Thương hiệu mới';name.dispatchEvent(new w.Event('input'));
  d.querySelector('#workspace-create-cancel').click();
  assert.equal(d.querySelector('#workspace-picker').hidden,false);
  d.querySelector('#workspace-create-open').click();assert.equal(name.value,'Thương hiệu mới');
  dom.window.close();
});

test('New users see creation immediately and business wording matches the submitted model', async()=>{
  const {dom,w,d}=await page('onboarding');
  assert.equal(d.querySelector('#workspace-create-section').hidden,false);
  assert.equal(d.querySelector('#workspace-create-cancel').hidden,true);
  d.querySelector('#step-next').click();assert.equal(d.querySelector('[data-step="1"]').hidden,false);
  d.querySelector('[name=name]').value='Sàn gỗ Á Châu';
  const business=d.querySelector('[name=kind][value=business]');business.checked=true;business.dispatchEvent(new w.Event('change'));
  d.querySelector('[name=website]').value='example.test';d.querySelector('#step-next').click();
  assert.equal(d.querySelector('[name=website]').value,'https://example.test');
  assert.equal(d.querySelector('#first-client-heading').textContent,'Thương hiệu của bạn');
  d.querySelector('#step-next').click();
  const rows=[...d.querySelectorAll('#workspace-review>div')].map(row=>row.textContent);
  assert.ok(rows.includes('Thương hiệuSàn gỗ Á Châu'));
  assert.equal(d.querySelector('#workspace-submit').hidden,false);
  dom.window.close();
});

test('Workspace search handles Vietnamese accents and renders names as text', async()=>{
  const {dom,w,d}=await page('onboarding',[workspace('a','Sàn gỗ Á Châu'),workspace('b','Vio Agency'),workspace('c','Studio Việt'),workspace('d','<img src=x onerror=alert(1)>')]);
  assert.equal(d.querySelector('#workspace-search-label').hidden,false);
  assert.equal(d.querySelector('.workspace-choice-title img'),null);
  const search=d.querySelector('#workspace-search');search.value='san go a chau';search.dispatchEvent(new w.Event('input'));
  assert.equal([...d.querySelectorAll('#workspace-list button')].filter(row=>!row.hidden).length,1);
  assert.equal(d.querySelector('#workspace-count').textContent,'1/4');
  search.value='Không tồn tại';search.dispatchEvent(new w.Event('input'));
  assert.equal(d.querySelector('#workspace-search-empty').hidden,false);
  d.querySelector('#workspace-search-clear').click();assert.equal(d.querySelector('#workspace-count').textContent,'4');
  dom.window.close();
});

test('Invitation errors remain inside the open dialog and allow retry with CSRF', async()=>{
  const {dom,w,d,requests}=await page('onboarding',[workspace('a','Vio Agency')]);
  d.querySelector('#workspace-join-open').click();
  d.querySelector('[name=invitation_code]').value='expired-qa-only';
  d.querySelector('#join-form').dispatchEvent(new w.Event('submit',{cancelable:true}));
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(d.querySelector('#join-feedback').textContent,'Mã mời đã hết hạn.');
  assert.equal(d.querySelector('#join-feedback').hidden,false);
  assert.equal(d.querySelector('#join-submit').disabled,false);
  assert.equal(requests.find(row=>row.url.endsWith('/workspaces/join')).options.headers['X-CSRF-Token'],'qa-only');
  assert.equal(d.querySelector('#identity-status').hidden,true);
  dom.window.close();
});

test('Login keeps Google available across register mode and password visibility stays accessible', async()=>{
  const {dom,w,d}=await page('login');
  assert.equal(d.querySelector('#google-login').disabled,false);
  d.querySelector('[data-mode=register]').click();
  assert.equal(d.querySelector('#name-field input').required,true);
  assert.equal(d.querySelector('#auth-password').autocomplete,'new-password');
  d.querySelector('#toggle-password').click();assert.equal(d.querySelector('#auth-password').type,'text');
  assert.equal(d.querySelector('#toggle-password').getAttribute('aria-label'),'Ẩn mật khẩu');
  d.querySelector('[data-mode=login]').click();assert.equal(d.querySelector('#auth-password').autocomplete,'current-password');
  d.querySelector('#forgot-password').click();assert.equal(d.querySelector('#email-action-form').hidden,false);
  assert.equal(d.querySelector('.identity-login-card').getAttribute('aria-labelledby'),'email-action-heading');
  dom.window.close();
});
