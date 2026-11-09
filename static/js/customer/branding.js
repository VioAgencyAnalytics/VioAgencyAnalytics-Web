/* Workspace identity uses same-origin, authenticated raster images only. */
(() => {
  'use strict';
  const initials = (name) => {
    const words = String(name || '').trim().split(/\s+/).filter(Boolean);
    return words.length ? (Array.from(words[0])[0] + (words.length > 1 ? Array.from(words.at(-1))[0] : '')).toLocaleUpperCase('vi-VN') : 'W';
  };
  function setName(avatar, name) {
    avatar.dataset.brandName = String(name || '');
    avatar.querySelector('.ws-avatar-initials').textContent = initials(name);
  }
  function setImage(avatar, url, lazy = true) {
    avatar.querySelector('img')?.remove();
    const fallback = avatar.querySelector('.ws-avatar-initials'); fallback.hidden = false;
    avatar.classList.remove('has-image');
    if (!url) return;
    const image = document.createElement('img'); image.alt = '';
    image.loading = lazy ? 'lazy' : 'eager'; image.decoding = 'async'; image.referrerPolicy = 'no-referrer';
    image.addEventListener('load', () => {
      if (image.isConnected && image.naturalWidth > 0) { image.hidden = false; fallback.hidden = true; avatar.classList.add('has-image'); }
    });
    image.addEventListener('error', () => { image.remove(); fallback.hidden = false; avatar.classList.remove('has-image'); });
    avatar.append(image); image.src = url;
  }
  function avatar(name, workspaceId = '') {
    const item = document.createElement('span'); item.className = 'ws-avatar'; item.setAttribute('aria-hidden','true');
    const fallback = document.createElement('span'); fallback.className = 'ws-avatar-initials'; item.append(fallback);
    setName(item, name);
    if (/^[a-f0-9]{32}$/.test(workspaceId)) setImage(item, '/api/customer/workspaces/' + workspaceId + '/logo');
    if (/^[a-f0-9]{32}$/.test(workspaceId)) item.dataset.workspaceId = workspaceId;
    return item;
  }
  document.querySelectorAll('[data-workspace-logo]').forEach((image) => {
    const parent = image.closest('.ws-avatar'), id = image.dataset.workspaceLogo;
    if (!parent || !/^[a-f0-9]{32}$/.test(id)) return;
    parent.dataset.workspaceId = id;
    setName(parent, parent.dataset.brandName);
    setImage(parent, '/api/customer/workspaces/' + id + '/logo');
  });
  function refresh(workspace) {
    document.querySelectorAll('.ws-avatar[data-workspace-id]').forEach((item) => {
      if (item.dataset.workspaceId !== workspace.id) return;
      setName(item, workspace.name); setImage(item, '/api/customer/workspaces/' + workspace.id + '/logo');
    });
  }
  window.VioWorkspaceBranding = Object.freeze({avatar, setName, setImage, refresh});
})();
