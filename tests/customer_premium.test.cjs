const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {test} = require('node:test');
const {JSDOM} = require('../../VioAgencyAnalytics-Admin/node_modules/jsdom');

test('Navigation preference is reversible, accessible and works without browser storage', () => {
  const dom = new JSDOM('<button id="workspace-nav-toggle"><span></span></button>', {url:'https://customer.example.test/workspace',runScripts:'outside-only'});
  const w = dom.window;
  Object.defineProperty(w,'localStorage',{get(){throw new Error('Storage blocked');}});
  w.eval(readFileSync('static/js/customer/premium.js','utf8'));
  const button = w.document.querySelector('button');
  assert.equal(button.getAttribute('aria-expanded'),'true');
  button.click();
  assert.equal(w.document.body.dataset.navCompact,'true');
  assert.equal(button.getAttribute('aria-pressed'),'true');
  assert.equal(button.getAttribute('aria-label'),'Mở rộng thanh điều hướng');
  button.click();
  assert.equal(w.document.body.dataset.navCompact,'false');
  assert.equal(button.getAttribute('aria-expanded'),'true');
  dom.window.close();
});

test('Changing provider replaces its identity and a broken local image has an honest fallback', () => {
  const brands={ga4:{file:'ga4.svg',short:'GA4'},gsc:{file:'gsc.png',short:'GSC'}};
  const dom = new JSDOM('<script id="platform-brands-data" type="application/json">'+JSON.stringify(brands)+'</script><div id="dialog"></div>',{url:'https://customer.example.test',runScripts:'outside-only'});
  const w=dom.window;
  w.eval(readFileSync('static/js/customer/platform-brands.js','utf8'));
  const api=w.VioPlatformBrand,dialog=w.document.querySelector('div'),mark=api.logo('ga4');
  dialog.append(mark);api.setTheme(dialog,'ga4');
  assert.equal(mark.querySelector('img').getAttribute('src'),'/static/customer/platforms/ga4.svg');
  api.setLogo(mark,'gsc');api.setTheme(dialog,'gsc');
  assert.equal(mark.querySelectorAll('img').length,1);
  assert.equal(dialog.dataset.platformBrand,'gsc');
  mark.querySelector('img').dispatchEvent(new w.Event('error'));
  assert.equal(mark.querySelector('img').hidden,true);
  assert.equal(mark.querySelector('.platform-logo-fallback').hidden,false);
  assert.equal(mark.querySelector('.platform-logo-fallback').textContent,'GSC');
  api.setLogo(mark,'https://foreign.example/logo');api.setTheme(dialog,'__proto__');
  assert.equal(mark.querySelector('img'),null);
  assert.equal(dialog.dataset.platformBrand,undefined);
  dom.window.close();
});
