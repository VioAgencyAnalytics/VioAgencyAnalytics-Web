(() => {
  'use strict';
  const sidebar = document.getElementById('dashboard-sidebar');
  const toggle = document.getElementById('sidebar-toggle');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (!sidebar || !toggle || !backdrop) return;
  const mobile = matchMedia('(max-width: 1023px)');
  const groups = [...sidebar.querySelectorAll('[data-report-group]')];
  function setGroup(group, open) {
    group.querySelector('.report-nav-toggle').setAttribute('aria-expanded', String(open));
    group.querySelector('.report-submenu').hidden = !open;
  }
  groups.forEach((group) => {
    const button = group.querySelector('.report-nav-toggle');
    button.addEventListener('click', () => {
      const open = button.getAttribute('aria-expanded') !== 'true';
      groups.forEach((other) => setGroup(other, other === group && open));
    });
  });
  function setSidebar(open, restoreFocus = true) {
    sidebar.classList.toggle('is-open', open);
    sidebar.inert = mobile.matches && !open;
    backdrop.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';
    if (open) sidebar.querySelector('a').focus();
    else if (mobile.matches && restoreFocus) toggle.focus();
  }
  toggle.addEventListener('click', () => setSidebar(!sidebar.classList.contains('is-open')));
  backdrop.addEventListener('click', () => setSidebar(false));
  mobile.addEventListener('change', () => setSidebar(false, false));
  sidebar.inert = mobile.matches;
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !document.querySelector('dialog[open]')) {
      if (sidebar.classList.contains('is-open')) setSidebar(false);
      const menu = document.getElementById('export-menu');
      if (menu && !menu.hidden) {
        menu.hidden = true;
        const button = document.getElementById('export-report');
        button.setAttribute('aria-expanded', 'false'); button.focus();
      }
    }
    if (event.key === 'Tab' && sidebar.classList.contains('is-open')) {
      const links = [...sidebar.querySelectorAll('a, button')].filter((el) => el.getClientRects().length);
      const first = links[0], last = links.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  const sectionLinks = [...sidebar.querySelectorAll('[data-section]')];
  function markSection(view) {
    const active = sectionLinks.filter((link) => document.getElementById(link.dataset.section));
    const selected = active.find((link) => link.dataset.path === view) || active[0];
    sectionLinks.forEach((link) => {
      if (link === selected) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    return selected;
  }
  sectionLinks.forEach((link) => link.addEventListener('click', (event) => {
    const section = document.getElementById(link.dataset.section);
    if (!section || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (mobile.matches) setSidebar(false);
    const url = new URL(location.href);
    url.searchParams.set('view', link.dataset.path);
    history.replaceState(null, '', url);
    markSection(link.dataset.path);
    for (let parent = section.parentElement; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
    section.scrollIntoView({ block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }));
  markSection(new URLSearchParams(location.search).get('view'));
})();
