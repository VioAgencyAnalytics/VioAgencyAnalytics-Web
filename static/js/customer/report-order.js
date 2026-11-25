(() => {
  'use strict';

  const scope = document.querySelector('[data-report-order]');
  if (!scope) return;
  const container = scope.querySelector('[data-order-container]') || scope;
  const groups = new Map();
  for (const block of scope.querySelectorAll('[data-order-key]')) {
    const key = block.dataset.orderKey;
    if (!groups.has(key)) groups.set(key, {label: block.dataset.orderLabel, blocks: []});
    groups.get(key).blocks.push(block);
  }
  const original = [...groups.keys()];
  if (original.length < 2) return;
  const requested = scope.dataset.reportOrder.split(',').filter((key) => groups.has(key));
  const active = [...new Set([...requested, ...original])];
  const hidden = new Set((scope.dataset.reportHidden || '').split(',').filter((key) => groups.has(key)));
  if (hidden.size === original.length) hidden.clear();

  if (requested.length || hidden.size) {
    const last = [...container.children].findLast((node) => node.matches('[data-order-key]') || node.querySelector('[data-order-key]'));
    const tail = container.querySelector(':scope > [data-order-tail]');
    const boundary = container.insertBefore(document.createComment('report sections end'), tail || last.nextSibling);
    for (const key of active) {
      for (const block of groups.get(key).blocks) {
        boundary.before(block);
        block.hidden = hidden.has(key);
      }
    }
    for (const extra of scope.querySelectorAll('[data-order-extra]')) {
      extra.hidden = extra.dataset.orderExtra.split(',').some((key) => hidden.has(key));
    }
    for (const link of scope.querySelectorAll('a[href^="#"]')) {
      const target = document.getElementById(link.getAttribute('href').slice(1));
      if (target?.closest('[data-order-key][hidden]')) link.hidden = true;
    }
    const seo = scope.querySelector('#chapter-seo-website.sc-report');
    if (seo && !seo.querySelector('.sc-page:not([hidden])')) {
      scope.querySelector('a[href="#chapter-seo-website"]')?.setAttribute('hidden', '');
    }
  }

  if (document.body.dataset.pdfRender === 'true') return;
  const dialog = document.querySelector('#vt-order-dialog');
  if (!dialog) return;
  const list = dialog.querySelector('#vt-order-list');
  const status = dialog.querySelector('#vt-order-status');
  let keys = [], stagedHidden = new Set(), dragged = null, dropTarget = null, opener = null;

  function clearDropTarget() {
    dropTarget?.removeAttribute('data-drop-side');
    dropTarget = null;
  }

  function afterMiddle(row, pointerY) {
    const rect = row.getBoundingClientRect();
    return pointerY > rect.top + rect.height / 2;
  }

  function move(key, index) {
    const source = keys.indexOf(key);
    if (source < 0 || index < 0 || index >= keys.length || index === source) return;
    keys.splice(source, 1);
    keys.splice(index, 0, key);
    render();
    list.querySelector(`[data-order-row="${key}"]`).focus();
    status.textContent = groups.get(key).label + ' ở vị trí ' + (index + 1) + '.';
  }

  function render() {
    list.replaceChildren(...keys.map((key, index) => {
      const row = document.createElement('li');
      row.dataset.orderRow = key;
      row.draggable = true;
      row.tabIndex = -1;
      const handle = document.createElement('span');
      handle.className = 'material-symbols-outlined';
      handle.setAttribute('aria-hidden', 'true');
      handle.textContent = 'drag_indicator';
      const label = document.createElement('strong');
      label.textContent = groups.get(key).label;
      const toggle = document.createElement('label');
      toggle.className = 'vt-section-toggle';
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.checked = !stagedHidden.has(key);
      input.setAttribute('aria-label', 'Hiện ' + label.textContent);
      const state = document.createElement('span');
      state.textContent = input.checked ? 'Hiện' : 'Ẩn';
      input.addEventListener('change', () => {
        if (input.checked) stagedHidden.delete(key);
        else stagedHidden.add(key);
        state.textContent = input.checked ? 'Hiện' : 'Ẩn';
        status.textContent = label.textContent + (input.checked ? ' sẽ hiển thị.' : ' sẽ được ẩn.');
      });
      toggle.append(input, state);
      row.append(handle, label, toggle);
      for (const [delta, caption] of [[-1, 'Lên'], [1, 'Xuống']]) {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = caption;
        button.disabled = index + delta < 0 || index + delta >= keys.length;
        button.setAttribute('aria-label', 'Đưa ' + label.textContent + ' ' + caption.toLowerCase());
        button.addEventListener('click', () => move(key, index + delta));
        row.append(button);
      }
      return row;
    }));
  }

  for (const button of document.querySelectorAll('[data-report-order-open]')) {
    button.hidden = false;
    button.addEventListener('click', () => {
      opener = button;
      keys = [...active];
      stagedHidden = new Set(hidden);
      status.textContent = '';
      render();
      dialog.showModal();
    });
  }
  list.addEventListener('dragstart', (event) => {
    const row = event.target.closest('[data-order-row]');
    if (!row) return;
    dragged = row.dataset.orderRow;
    event.dataTransfer.setData('text/plain', dragged);
    event.dataTransfer.effectAllowed = 'move';
    row.classList.add('vt-dragging');
  });
  list.addEventListener('dragover', (event) => {
    const row = event.target.closest('[data-order-row]');
    if (!dragged || !row) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    if (dropTarget !== row) clearDropTarget();
    if (dragged === row.dataset.orderRow) return;
    dropTarget = row;
    dropTarget.dataset.dropSide = afterMiddle(row, event.clientY) ? 'after' : 'before';
  });
  list.addEventListener('drop', (event) => {
    const row = event.target.closest('[data-order-row]');
    if (!dragged || !row) return;
    event.preventDefault();
    const from = keys.indexOf(dragged), target = keys.indexOf(row.dataset.orderRow);
    const insertion = target + Number(afterMiddle(row, event.clientY));
    move(dragged, insertion - Number(from < insertion));
    dragged = null;
    clearDropTarget();
    list.querySelector('.vt-dragging')?.classList.remove('vt-dragging');
  });
  list.addEventListener('dragleave', (event) => {
    if (!list.contains(event.relatedTarget)) clearDropTarget();
  });
  list.addEventListener('dragend', () => {
    dragged = null;
    clearDropTarget();
    list.querySelector('.vt-dragging')?.classList.remove('vt-dragging');
  });
  dialog.querySelector('[data-order-close]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => opener?.focus());
  dialog.querySelector('#vt-order-reset').addEventListener('click', () => {
    keys = [...original]; stagedHidden.clear(); render(); status.textContent = 'Đã về thứ tự gốc và hiện tất cả các mục.';
  });
  dialog.querySelector('#vt-order-apply').addEventListener('click', () => {
    if (stagedHidden.size === keys.length) { status.textContent = 'Chọn hiển thị ít nhất một mục.'; return; }
    const url = new URL(location.href);
    const reordered = keys.some((key, index) => key !== original[index]);
    url.searchParams.set('order', reordered ? keys.join(',') : '');
    url.searchParams.set('hidden', keys.filter((key) => stagedHidden.has(key)).join(','));
    location.assign(url.pathname + url.search + url.hash);
  });
})();
