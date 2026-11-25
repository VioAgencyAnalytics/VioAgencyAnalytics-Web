(() => {
  'use strict';

  const $ = (selector) => document.querySelector(selector);
  const search = $('#rt-search'), count = $('#rt-count'), empty = $('#rt-empty');
  const list = $('#rt-platforms'), grid = $('#rt-grid'), hero = $('#rt-hero'), title = $('#rt-results-title'), all = $('#rt-all');
  const palettePanel = $('#rt-palettes'), colors = [...palettePanel.querySelectorAll('[data-template-palette]')];
  const filters = [...document.querySelectorAll('[data-template-group]')];
  const platforms = new Map([...list.querySelectorAll('[data-collection]')].map((link) => [link.dataset.collection, link]));
  const fold = (value) => value.normalize('NFD').replace(/\p{M}/gu, '').replace(/[đĐ]/g, 'd').toLowerCase();
  const cards = [...grid.querySelectorAll('[data-template-card]')].map((card) => ({
    card, text: fold([card.dataset.search, card.querySelector('h3').textContent, card.querySelector('p').textContent].join(' ')),
    preview: card.querySelector('[data-template-preview]'), use: card.querySelector('[data-template-use]'), image: card.querySelector('.rt-thumbnail img'),
  }));
  let group = 'all', platform = '', palette = 'brand';

  function render(historyMode = 'replaceState') {
    const query = search.value.trim(), words = fold(query).split(/\s+/).filter(Boolean);
    const chosen = platforms.get(platform);
    const showCards = Boolean(chosen || words.length);
    const matchesGroup = (element) => group === 'all' || element.dataset.group === group;
    const params = new URLSearchParams();
    if (group !== 'all') params.set('category', group);
    if (platform) params.set('platform', platform);
    if (palette !== 'brand') params.set('palette', palette);
    if (query) params.set('q', query);
    const suffix = params.size ? '?' + params : '';
    let matches = 0, available = 0, total = 0;
    for (const [key, link] of platforms) {
      link.hidden = !matchesGroup(link);
      if (!link.hidden) available += 1;
      const destination = new URLSearchParams(params);
      destination.set('platform', key);
      link.href = '?' + destination;
    }
    for (const {card, text, preview, use, image} of cards) {
      if (matchesGroup(card)) total += 1;
      const visible = showCards && matchesGroup(card) && (!platform || card.dataset.collectionId === platform) && words.every((word) => text.includes(word));
      card.hidden = !visible;
      if (!visible) continue;
      matches += 1;
      preview.href = preview.pathname + suffix;
      const destination = new URL(use.href);
      if (palette !== 'brand') destination.searchParams.set('palette', palette);
      else destination.searchParams.delete('palette');
      use.href = destination.pathname + destination.search;
      if (!image.hasAttribute('src')) {
        if (matches <= 3) image.loading = 'eager';
        image.src = image.dataset.src;
      }
    }
    for (const button of filters) button.setAttribute('aria-pressed', String(button.dataset.templateGroup === group));
    for (const button of colors) button.setAttribute('aria-pressed', String(button.dataset.templatePalette === palette));
    grid.dataset.reportPalette = palette;
    palettePanel.hidden = !showCards;
    title.textContent = chosen?.dataset.name || (showCards ? 'Mẫu phù hợp' : 'Chọn nền tảng');
    count.textContent = showCards ? matches + ' mẫu báo cáo' : available + ' nhóm · ' + total + ' mẫu';
    list.hidden = showCards;
    hero.hidden = showCards;
    grid.hidden = !showCards || matches === 0;
    empty.hidden = !showCards || matches > 0;
    all.hidden = !showCards;
    if (historyMode) history[historyMode](null, '', location.pathname + suffix + location.hash);
  }

  function readAddress() {
    const params = new URLSearchParams(location.search);
    const initialGroup = params.get('category');
    group = filters.some((button) => button.dataset.templateGroup === initialGroup) ? initialGroup : 'all';
    platform = platforms.has(params.get('platform')) ? params.get('platform') : '';
    palette = colors.some((button) => button.dataset.templatePalette === params.get('palette')) ? params.get('palette') : 'brand';
    if (platform && group !== 'all' && platforms.get(platform).dataset.group !== group) group = 'all';
    search.value = (params.get('q') || '').slice(0, search.maxLength);
  }

  for (const button of filters) button.addEventListener('click', () => {
    group = button.dataset.templateGroup;
    if (group !== 'all' && platforms.get(platform)?.dataset.group !== group) platform = '';
    render('pushState');
  });
  for (const button of colors) button.addEventListener('click', () => { palette = button.dataset.templatePalette; render(); });
  const openInNewTab = (event) => event.ctrlKey || event.metaKey || event.altKey || event.shiftKey;
  for (const [key, link] of platforms) link.addEventListener('click', (event) => {
    if (openInNewTab(event)) return;
    event.preventDefault();
    platform = key;
    render('pushState');
    all.focus({preventScroll: true});
  });
  search.addEventListener('input', () => render());
  all.addEventListener('click', (event) => {
    if (openInNewTab(event)) return;
    event.preventDefault();
    const previous = platforms.get(platform);
    platform = '';
    group = 'all';
    search.value = '';
    render('pushState');
    (previous || search).focus({preventScroll: true});
  });
  $('#rt-reset').addEventListener('click', () => {
    group = 'all';
    platform = '';
    search.value = '';
    render('pushState');
    search.focus();
  });
  window.addEventListener('popstate', () => { readAddress(); render(null); });
  readAddress();
  render();
  const session = window.VioSEO;
  session.ready().catch((error) => session.message(error.message, true));
})();
