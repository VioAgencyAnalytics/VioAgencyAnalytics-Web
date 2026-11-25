/* A reversible local navigation preference; no account or data state changes. */
(() => {
  'use strict';
  const toggle = document.getElementById('workspace-nav-toggle');
  if (!toggle) return;
  let compact = false;
  try { compact = localStorage.getItem('vio.customer.nav.compact') === 'true'; } catch { /* Storage can be unavailable. */ }
  function render() {
    document.body.dataset.navCompact = String(compact);
    toggle.setAttribute('aria-pressed', String(compact));
    toggle.setAttribute('aria-expanded', String(!compact));
    const label = compact ? 'Mở rộng thanh điều hướng' : 'Thu gọn thanh điều hướng';
    toggle.setAttribute('aria-label', label); toggle.title = label;
    toggle.querySelector('span').textContent = compact ? 'menu' : 'menu_open';
  }
  toggle.addEventListener('click', () => {
    compact = !compact; render();
    try { localStorage.setItem('vio.customer.nav.compact', String(compact)); } catch { /* Keep the preference for this page. */ }
  });
  document.getElementById('nav-channels')?.addEventListener('click', (event) => {
    if (compact && window.matchMedia('(min-width:1100px)').matches && !event.target.closest('a')) {
      event.preventDefault(); window.location.assign('/workspace/channels');
    }
  });
  render();
})();
