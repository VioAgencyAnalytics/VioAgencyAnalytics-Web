(async () => {
  'use strict';
  const params = new URLSearchParams(location.hash.slice(1));
  history.replaceState(null, '', '/auth/handoff/callback');
  try {
    if (['transaction', 'state', 'code'].some(key => params.getAll(key).length !== 1) || [...params].length !== 3) throw new Error('Mã chuyển phiên không hợp lệ. Mở lại báo cáo từ Admin.');
    const response = await fetch('/auth/handoff/callback', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(Object.fromEntries(params))});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Chưa mở được báo cáo.');
    if (!/^\/(reports\/rpt_[a-f0-9]{32}\?revision=[1-9][0-9]*|internal-preview\/[a-f0-9]{32})$/.test(data.location)) throw new Error('Đường dẫn báo cáo không hợp lệ.');
    location.replace(data.location);
  } catch (error) { document.getElementById('handoff-status').textContent = error.message; }
})();
