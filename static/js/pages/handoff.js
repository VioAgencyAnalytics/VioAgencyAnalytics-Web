(async () => {
  'use strict';
  const params = new URLSearchParams(location.hash.slice(1));
  history.replaceState(null, '', '/auth/handoff/callback');
  const reset = document.getElementById('handoff-reset');
  reset.addEventListener('submit', async event => {
    event.preventDefault();
    // Fetch preserves Origin under this callback's no-referrer policy. Never
    // forward the reset form or its CSRF value across the redirect to Admin.
    try {
      const response = await fetch('/logout', {method: 'POST', redirect: 'manual',
        body: new URLSearchParams(new FormData(reset))});
      if (response.type === 'opaqueredirect') location.replace('/reports');
      else document.getElementById('handoff-status').textContent = 'Chưa kết thúc được phiên xem. Tải lại trang rồi thử lại.';
    } catch { document.getElementById('handoff-status').textContent = 'Chưa kết nối được hệ thống. Vui lòng thử lại.'; }
  });
  try {
    if (['transaction', 'state', 'code'].some(key => params.getAll(key).length !== 1) || [...params].length !== 3) throw new Error('Mã chuyển phiên không hợp lệ. Mở lại báo cáo từ Admin.');
    const response = await fetch('/auth/handoff/callback', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(Object.fromEntries(params))});
    const data = await response.json();
    if (response.status === 409) document.getElementById('handoff-reset').hidden = false;
    if (!response.ok) throw new Error(data.error || 'Chưa mở được báo cáo.');
    if (!/^\/(reports\/rpt_[a-f0-9]{32}\?revision=[1-9][0-9]*|internal-preview\/[a-f0-9]{32})$/.test(data.location)) throw new Error('Đường dẫn báo cáo không hợp lệ.');
    location.replace(data.location);
  } catch (error) { document.getElementById('handoff-status').textContent = error.message; }
})();
