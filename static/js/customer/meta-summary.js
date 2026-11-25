/* Independent latest-source card. Never merges Content into advertising KPI. */
(() => {
  'use strict';
  const root = document.querySelector('#meta-summary'); if (!root) return;
  const details = JSON.parse(document.querySelector('#overview-data, #marketing-data').textContent);
  const workspaceId = details.workspace.id;
  let selected = details.selected_client?.id || null, generation = 0;
  const note = document.querySelector('#meta-summary-note'), metric = document.querySelector('#meta-summary-metric');
  async function refresh() {
    const ticket = ++generation, clientId = selected;
    metric.hidden = true; root.hidden = true; root.setAttribute('aria-busy','true');
    document.querySelector('#meta-summary-title').textContent = 'Nội dung Fanpage';
    note.textContent = clientId ? 'Đang tải lần đồng bộ gần nhất…' : 'Chọn khách hàng để xem Fanpage.';
    if (!clientId) { root.setAttribute('aria-busy','false'); return; }
    try {
      const response = await fetch(`/api/customer/workspaces/${workspaceId}/channels/facebook-content`,{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}});
      const data = await response.json();
      if (ticket !== generation || clientId !== selected) return;
      if (!response.ok || data.scope?.workspace_id !== workspaceId || data.scope?.client_id !== clientId) throw new Error();
      root.hidden = ['not_connected', 'no_client'].includes(data.state);
      if (data.state === 'ready') {
        const value = data.metrics.find((item) => item.key === 'posts_published')?.value;
        if (typeof value === 'number' && Number.isFinite(value)) { document.querySelector('#meta-summary-posts').textContent = new Intl.NumberFormat('vi-VN').format(value); metric.hidden = false; }
        document.querySelector('#meta-summary-title').textContent = data.asset.name;
        const stamp = new Date(data.snapshot.fetched_at);
        const fetched = Number.isNaN(stamp.getTime()) ? 'chưa rõ thời điểm' : new Intl.DateTimeFormat('vi-VN',{dateStyle:'short',timeStyle:'short',timeZone:'Asia/Ho_Chi_Minh'}).format(stamp);
        note.textContent = `Kỳ ${data.snapshot.start_date} → ${data.snapshot.end_date} UTC · Cập nhật ${fetched} GMT+7.`;
      } else {
        document.querySelector('#meta-summary-title').textContent = 'Nội dung Fanpage';
        note.textContent = ({select_asset:'Đã cấp quyền · Chọn Fanpage tại Kết nối nền tảng.',syncing:'Đang đồng bộ Fanpage…',sync_error:'Đồng bộ cần kiểm tra tại Kết nối nền tảng.',empty:'Chưa có dữ liệu đã đồng bộ.'})[data.state] || 'Chọn khách hàng để bắt đầu.';
      }
    } catch { if (ticket === generation) { root.hidden = false; document.querySelector('#meta-summary-title').textContent = 'Nội dung Fanpage'; note.textContent = 'Chưa tải được dữ liệu. Mở Fanpage để kiểm tra.'; } }
    finally { if (ticket === generation) root.setAttribute('aria-busy','false'); }
  }
  document.addEventListener('customer:workspace-detail',(event) => { selected = event.detail.selected_client?.id || null; refresh(); });
  document.addEventListener('customer:marketing-context',(event) => { const id = event.detail.scope?.client_id || null; if (id !== selected) { selected = id; refresh(); } });
  refresh();
})();
