/* One local brand catalogue for server-rendered and dynamic customer components. */
(() => {
  'use strict';
  const data = document.getElementById('platform-brands-data');
  if (!data) return;
  const brands = JSON.parse(data.textContent);
  const known = (source) => Object.hasOwn(brands, source);
  function setTheme(element, source) {
    if (!element) return;
    if (known(source)) element.dataset.platformBrand = source;
    else delete element.dataset.platformBrand;
  }
  function fallback(image) {
    image.hidden = true;
    const label = image.parentElement?.querySelector('.platform-logo-fallback');
    if (label) label.hidden = false;
  }
  function watch(image) {
    image.addEventListener('error', () => fallback(image), {once: true});
    if (image.complete && !image.naturalWidth) fallback(image);
  }
  function setLogo(element, source) {
    if (!element) return;
    element.classList.remove('material-symbols-outlined');
    element.classList.add('platform-logo');
    element.setAttribute('aria-hidden', 'true');
    element.replaceChildren();
    if (!known(source)) {
      delete element.dataset.platformLogo;
      const symbol = document.createElement('span');
      symbol.className = 'material-symbols-outlined'; symbol.textContent = 'query_stats';
      element.append(symbol); return;
    }
    const brand = brands[source];
    element.dataset.platformLogo = source;
    const image = document.createElement('img');
    image.alt = ''; image.width = 32; image.height = 32; image.decoding = 'async';
    const label = document.createElement('span');
    label.className = 'platform-logo-fallback'; label.hidden = true; label.textContent = brand.short;
    element.append(image, label);
    image.addEventListener('error', () => fallback(image), {once: true});
    image.src = '/static/customer/platforms/' + brand.file;
  }
  function logo(source, className = '') {
    const element = document.createElement('span'); element.className = className;
    setLogo(element, source); return element;
  }
  document.querySelectorAll('[data-platform-logo] img').forEach(watch);
  window.VioPlatformBrand = Object.freeze({logo, setLogo, setTheme, known});
})();
