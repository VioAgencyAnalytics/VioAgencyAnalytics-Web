(() => {
  'use strict';
  const quiet = matchMedia('(prefers-reduced-motion: reduce)');
  const pointer = matchMedia('(hover: hover) and (pointer: fine)');
  const bell = document.getElementById('workspace-bell');
  const icon = bell?.querySelector('.material-symbols-outlined');
  const badge = document.getElementById('workspace-bell-count');
  let bellMotion, badgeMotion, toastMotion;

  document.addEventListener('vio:notification-arrived', () => {
    if (quiet.matches) return;
    bellMotion?.cancel();
    badgeMotion?.cancel();
    toastMotion?.cancel();
    bellMotion = icon?.animate?.([
      {rotate: '0deg'}, {rotate: '-13deg'}, {rotate: '10deg'}, {rotate: '-5deg'}, {rotate: '0deg'},
    ], {duration: 480, easing: 'ease-out'});
    badgeMotion = badge?.animate?.([{scale: '1'}, {scale: '1.24'}, {scale: '1'}], {duration: 340, easing: 'ease-out'});
    toastMotion = document.getElementById('workspace-notice-toast')?.animate?.([
      {opacity: 0, translate: '0 10px'}, {opacity: 1, translate: '0 0'},
    ], {duration: 230, easing: 'cubic-bezier(.22,.8,.3,1)'});
  });

  const cover = document.querySelector('.pr-cover');
  const art = cover?.querySelector('.pr-cover-art');
  if (!art) return;
  let frame, x, y;
  function reset() {
    cancelAnimationFrame(frame);
    frame = 0;
    art.style.removeProperty('--vio-cover-x');
    art.style.removeProperty('--vio-cover-y');
  }
  cover.addEventListener('pointermove', event => {
    if (!pointer.matches || quiet.matches || event.pointerType !== 'mouse') return;
    x = event.clientX;
    y = event.clientY;
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      const box = cover.getBoundingClientRect();
      const fraction = (value, start, size) => Math.min(1, Math.max(0, (value - start) / size)) - .5;
      art.style.setProperty('--vio-cover-x', `${(-12 * fraction(y, box.top, box.height)).toFixed(2)}deg`);
      art.style.setProperty('--vio-cover-y', `${(16 * fraction(x, box.left, box.width)).toFixed(2)}deg`);
    });
  }, {passive: true});
  cover.addEventListener('pointerleave', reset);
  cover.addEventListener('pointercancel', reset);
  window.addEventListener('resize', reset, {passive: true});
  window.addEventListener('scroll', reset, {passive: true});
  quiet.addEventListener('change', reset);
})();
