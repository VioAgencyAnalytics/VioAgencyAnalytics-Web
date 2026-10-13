(() => {
  'use strict';
  const root = document.getElementById('published-report');
  if (!root) return;
  const links = [...document.querySelectorAll('[data-published-section]')];
  const sections = [...root.querySelectorAll('[data-section-key]')];
  const sidebar = document.getElementById('published-sidebar');
  const button = document.getElementById('pb-menu');
  const backdrop = document.getElementById('sidebar-backdrop');
  const mobile = matchMedia('(max-width:1023px)');
  function menu(open, focus = true) {
    sidebar.classList.toggle('is-open', open); sidebar.inert = mobile.matches && !open;
    button.setAttribute('aria-expanded', String(open)); backdrop.hidden = !open;
    document.body.style.overflow = open ? 'hidden' : '';
    if (focus && open) sidebar.querySelector('a')?.focus();
    else if (focus && mobile.matches) button.focus();
  }
  button.addEventListener('click', () => menu(!sidebar.classList.contains('is-open')));
  backdrop.addEventListener('click', () => menu(false));
  mobile.addEventListener('change', () => menu(false, false));
  sidebar.inert = mobile.matches;
  document.addEventListener('keydown', event => {
    if (!sidebar.classList.contains('is-open')) return;
    if (event.key === 'Escape') menu(false);
    if (event.key === 'Tab') {
      const focusable = [...sidebar.querySelectorAll('a, button:not([disabled])')], first = focusable[0], last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  function activate(key) {
    const chosen = sections.find(s => s.dataset.sectionKey === key) || sections.find(s => s.dataset.sectionKey === root.dataset.selected);
    sections.forEach(section => { section.hidden = section !== chosen; });
    links.forEach(link => link.dataset.publishedSection === chosen?.dataset.sectionKey ? link.setAttribute('aria-current', 'page') : link.removeAttribute('aria-current'));
  }
  links.forEach(link => link.addEventListener('click', event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault(); history.pushState(null, '', link.href); activate(link.dataset.publishedSection);
    if (mobile.matches) menu(false);
    document.getElementById(link.dataset.target)?.scrollIntoView({ block:'start' });
  }));
  window.addEventListener('popstate', () => activate(new URLSearchParams(location.search).get('section')));
  root.querySelectorAll('[data-number]').forEach(element => {
    const raw = element.textContent.trim();
    if (/^-?\d+(?:\.\d+)?(?:e[+-]?\d+)?$/i.test(raw) && Number.isFinite(Number(raw))) {
      element.textContent = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 12 }).format(Number(raw));
    }
  });
  root.querySelectorAll('[data-bundle-chart]').forEach(element => {
    try { window.dashboardCharts.renderBundleChart(element, JSON.parse(element.querySelector('script').textContent)); }
    catch { element.querySelector('.pb-chart-surface').textContent = 'Không thể hiển thị biểu đồ. Số liệu nguồn vẫn có trong bảng chi tiết nếu được cung cấp.'; }
  });
})();
