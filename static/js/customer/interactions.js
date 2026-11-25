/* Reveal the section a client chooses, including fields inside closed disclosures. */
(() => {
  'use strict';
  function reveal(target) {
    if (!target) return;
    for (let item = target; item; item = item.parentElement) if (item.tagName === 'DETAILS') item.open = true;
  }
  function fragment(hash) {
    try { return hash.length > 1 ? document.getElementById(decodeURIComponent(hash.slice(1))) : null; }
    catch { return null; }
  }
  function update() {
    const target = fragment(location.hash); reveal(target);
    if (target) requestAnimationFrame(() => target.scrollIntoView({block:'start'}));
    document.querySelectorAll('.wa-settings-nav a').forEach((link) => {
      if (link.hash === location.hash) link.setAttribute('aria-current', 'location'); else link.removeAttribute('aria-current');
    });
  }
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
    const url = new URL(link.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname || url.search !== location.search) return;
    const target = fragment(url.hash); reveal(target);
    if (target && link.classList.contains('customer-skip')) requestAnimationFrame(() => target.focus({preventScroll:true}));
  });
  let invalidField;
  document.addEventListener('invalid', (event) => {
    reveal(event.target);
    if (invalidField) return;
    invalidField = event.target;
    requestAnimationFrame(() => { invalidField.focus(); invalidField = null; });
  }, true);
  window.addEventListener('hashchange', update); update();
})();
