(() => {
  'use strict';
  const W = window.VioWorkspace, $ = (selector) => document.querySelector(selector);
  const {node, fold, date} = W;
  let activeTab = 'members', editedMember, inviteComplete = false;
  const invitationStates = {pending: 'Đang chờ', accepted: 'Đã chấp nhận', expired: 'Hết hạn', revoked: 'Đã thu hồi'};
  const roleDescriptions = {admin: 'Quản lý khách hàng, cài đặt và thành viên có vai trò Member/Viewer. Không thể thay đổi chủ sở hữu.', member: 'Xem dữ liệu và khách hàng trong Workspace. Không quản lý thành viên hoặc cài đặt.', viewer: 'Xem các trang dữ liệu đã mở cho Workspace. Không có quyền quản trị.'};
  function badge(text, className, key, value) { const item = node('span', text, className); item.dataset[key] = value; return item; }
  function rowAction(text, callback, danger = false) { const button = node('button', text, danger ? 'wa-danger' : ''); button.type = 'button'; button.disabled = W.busy || !W.ready; button.addEventListener('click', callback); return button; }
  function renderMembers() {
    const data = W.data, words = fold($('#members-search').value).split(/\s+/).filter(Boolean), role = $('#members-role').value, state = $('#members-state').value;
    const status = (item) => !item.active ? 'revoked' : !item.account_active ? 'disabled' : 'active';
    const rows = (W.ready ? data.members : []).filter((item) => words.every((word) => fold(item.name + ' ' + item.email).includes(word)) && (role === 'all' || item.role === role) && (state === 'all' || status(item) === state));
    const sort = $('#members-sort').value;
    rows.sort((a, b) => sort === 'name' ? a.name.localeCompare(b.name, 'vi') : sort === 'role' ? ['owner','admin','member','viewer'].indexOf(a.role) - ['owner','admin','member','viewer'].indexOf(b.role) : b.created_at.localeCompare(a.created_at));
    $('#members-rows').replaceChildren(...rows.map((member) => {
      const row = node('tr', ''); row.dataset.memberId = member.id;
      const nameCell = node('td', ''), name = node('div', '', 'wa-member-name'), text = node('div', ''), strong = node('strong', member.name);
      if (member.is_self) strong.append(node('span', 'Bạn', 'wa-self-tag'));
      text.append(strong, node('small', member.email_verified ? 'Email đã xác minh' : 'Email chưa xác minh'));
      name.append(node('span', member.name.slice(0,1).toUpperCase(), 'wa-avatar'), text); nameCell.append(name);
      const roleCell = node('td', ''); roleCell.append(badge(W.roles[member.role], 'wa-role-pill', 'role', member.role));
      const stateCell = node('td', ''); stateCell.append(badge({active:'Hoạt động',revoked:'Đã thu hồi',disabled:'Tài khoản bị khóa'}[status(member)], 'wa-state', 'state', status(member)));
      const actionCell = node('td', ''), actions = node('div', '', 'wa-row-actions');
      if (member.can_manage) { actions.append(rowAction('Đổi vai trò', () => openMember(member)), rowAction('Thu hồi', () => remove(member), true)); }
      else actions.append(node('span', member.is_self ? 'Tài khoản của bạn' : member.role === 'owner' ? 'Chủ sở hữu' : 'Chỉ xem', 'wa-row-lock'));
      actionCell.append(actions); row.append(nameCell, node('td', member.email, 'wa-member-email'), roleCell, stateCell, node('td', date(member.created_at)), actionCell); return row;
    }));
    $('#members-no-results').hidden = rows.length > 0 || !W.ready;
    $('#members-result-count').textContent = W.ready ? `${rows.length} / ${data.members.length} thành viên trong danh sách` : 'Đang tải danh sách thành viên…';
    $('#members-first-invite').hidden = !W.ready || data.summary.active_members > 1 || !data.permissions.manage_members;
  }
  function renderInvitations() {
    const rows = W.ready ? W.data.invitations.filter((item) => $('#invitations-state').value === 'all' || item.status === $('#invitations-state').value) : [];
    $('#invitations-rows').replaceChildren(...rows.map((invite) => {
      const row = node('tr', ''); row.dataset.invitationId = invite.id;
      const role = node('td', ''); role.append(badge(W.roles[invite.role], 'wa-role-pill', 'role', invite.role));
      const state = node('td', ''); state.append(badge(invitationStates[invite.status], 'wa-state', 'state', invite.status));
      const action = node('td', ''), actions = node('div', '', 'wa-row-actions');
      if (invite.can_revoke) actions.append(rowAction('Thu hồi mã', () => revoke(invite), true));
      else actions.append(node('span', '—', 'wa-row-lock'));
      action.append(actions); row.append(node('td', invite.email), role, state, node('td', date(invite.expires_at, true)), action); return row;
    }));
    $('#invitations-empty').hidden = rows.length > 0 || !W.ready;
  }
  function renderEvents() {
    const labels = {workspace_created:'Tạo Workspace', workspace_settings_updated:'Cập nhật cài đặt Workspace', invitation_created:'Tạo mã mời thành viên', invitation_accepted:'Tham gia qua lời mời', invitation_revoked:'Thu hồi mã mời', member_role_changed:'Thay đổi vai trò thành viên', member_access_revoked:'Thu hồi quyền thành viên', member_access_restored:'Khôi phục quyền thành viên',client_created:'Thêm khách hàng',client_updated:'Cập nhật khách hàng',client_archived:'Lưu trữ khách hàng',client_restored:'Khôi phục khách hàng'};
    const events = W.ready ? W.data.events : [];
    $('#members-events').replaceChildren(...events.map((item) => { const row = node('li', ''), icon = node('span', 'history', 'material-symbols-outlined'), text = node('div', ''); icon.setAttribute('aria-hidden','true'); text.append(node('strong', labels[item.action] || 'Cập nhật trong Workspace'), node('small', item.actor_name || 'Thành viên Workspace')); const time = node('time', date(item.created_at, true)); time.dateTime = item.created_at; row.append(icon, text, time); return row; }));
    $('#members-events-empty').hidden = events.length > 0 || !W.ready;
  }
  function render() {
    const data = W.data;
    $('#members-active-count').textContent = W.ready ? data.summary.active_members : '—';
    $('#members-invite-count').textContent = W.ready && data.summary.pending_invitations !== null ? data.summary.pending_invitations : '—';
    $('#members-invite-summary').textContent = data.permissions.view_invitations ? 'Mã mời riêng theo email, có thời hạn sử dụng.' : 'Chỉ Owner/Admin xem và quản lý lời mời.';
    $('#members-tab-count').textContent = W.ready ? data.members.length : '';
    $('#invitations-tab-count').textContent = W.ready && data.summary.pending_invitations !== null ? data.summary.pending_invitations : '';
    $('#members-verification').hidden = !W.ready || !data.permissions.manage_members || data.permissions.email_verified;
    if (activeTab !== 'members' && !data.permissions[activeTab === 'events' ? 'view_audit' : 'view_invitations']) setTab('members');
    renderMembers(); renderInvitations(); renderEvents();
  }
  function controls() {
    document.querySelectorAll('[data-open-invite]').forEach((button) => { button.disabled = W.busy || !W.ready || !W.data.permissions.invite; button.title = !W.data.permissions.manage_members ? 'Chỉ chủ sở hữu hoặc quản trị viên được mời thành viên.' : !W.data.permissions.email_verified ? 'Xác minh email trước khi mời.' : ''; });
    $('#members-send-verification').disabled = W.busy || !W.session?.capabilities?.email_delivery;
    $('#members-tab-invitations').disabled = !W.data.permissions.view_invitations;
    $('#members-tab-events').disabled = !W.data.permissions.view_audit;
    $('#invite-submit').disabled = W.busy || inviteComplete || !W.data.permissions.invite;
    $('#invite-fields').disabled = W.busy || inviteComplete;
    $('#member-editor-save').disabled = W.busy || !W.ready;
    $('#member-new-role').disabled = W.busy;
    document.querySelectorAll('.wa-row-actions button').forEach((button) => { button.disabled = W.busy || !W.ready; });
  }
  function setTab(key) {
    activeTab = key;
    document.querySelectorAll('[data-members-tab]').forEach((button) => { const selected = button.dataset.membersTab === key; button.setAttribute('aria-selected', String(selected)); button.tabIndex = selected ? 0 : -1; $('#members-panel-' + button.dataset.membersTab).hidden = !selected; });
  }
  function openInvite() {
    if (!W.ready || W.busy || !W.data.permissions.invite) return;
    inviteComplete = false; $('#members-invite-form').reset(); $('#invite-code').value = ''; $('#invite-result').hidden = true; $('#invite-error').hidden = true;
    $('#invite-role').replaceChildren(...W.data.permissions.assignable_roles.map((role) => new Option(W.roles[role], role))); $('#invite-role').value = 'member'; roleDescription(); controls();
    $('#invite-dialog').showModal(); $('#invite-email').focus();
  }
  function roleDescription() { $('#invite-role-description').textContent = roleDescriptions[$('#invite-role').value] || ''; }
  function openMember(member) { if (W.busy) return; editedMember = member; $('#member-editor-description').textContent = `${member.name} · ${member.email}`; $('#member-new-role').replaceChildren(...W.data.permissions.assignable_roles.map((role) => new Option(W.roles[role], role))); $('#member-new-role').value = member.role; $('#member-editor-error').hidden = true; $('#member-editor').showModal(); }
  async function remove(member) {
    if (W.busy || !await W.confirm('Thu hồi quyền thành viên?', `${member.name} sẽ không còn truy cập được Workspace này. Quyền tại Workspace khác của họ vẫn được giữ.`, 'Thu hồi quyền')) return;
    await W.run(async () => { W.adopt(await W.api(`${W.base}/members/${member.id}/remove`, {version:member.version})); W.notify('Đã thu hồi quyền truy cập Workspace.', 'success'); });
  }
  async function revoke(invite) {
    if (W.busy || !await W.confirm('Thu hồi mã mời?', `Mã đã tạo cho ${invite.email} sẽ không còn sử dụng được.`, 'Thu hồi mã')) return;
    await W.run(async () => { W.adopt(await W.api(`${W.base}/invitations/${invite.id}/revoke`, {})); W.notify('Đã thu hồi mã mời.', 'success'); });
  }
  $('#members-invite-form').addEventListener('submit', async (event) => {
    event.preventDefault(); if (inviteComplete) return;
    await W.run(async () => {
      $('#invite-error').hidden = true;
      const result = await W.api(W.base + '/invitations', {email:$('#invite-email').value.trim(),role:$('#invite-role').value});
      inviteComplete = true; $('#invite-code').value = result.invitation_code; $('#invite-result').hidden = false;
      await W.reload(); W.notify('Đã tạo mã mời. Hãy gửi mã riêng cho người nhận; email mời chưa được gửi.', 'success');
    }, (error) => { $('#invite-error').textContent = error.message + (inviteComplete ? '' : ' Nếu kết nối bị gián đoạn, hãy kiểm tra danh sách lời mời trước khi tạo lại.'); $('#invite-error').hidden = false; });
  });
  $('#invite-dialog').addEventListener('close', () => { $('#invite-code').value = ''; $('#invite-result').hidden = true; inviteComplete = false; controls(); });
  $('#invite-copy').addEventListener('click', () => W.copy($('#invite-code').value, $('#invite-code')));
  $('#invite-role').addEventListener('change', roleDescription);
  $('#member-editor-form').addEventListener('submit', async (event) => { event.preventDefault(); if (!editedMember) return; await W.run(async () => { W.adopt(await W.api(`${W.base}/members/${editedMember.id}/role`, {version:editedMember.version,role:$('#member-new-role').value})); $('#member-editor').close(); W.notify('Đã cập nhật vai trò thành viên.', 'success'); }, (error) => { $('#member-editor-error').textContent = error.message; $('#member-editor-error').hidden = false; }); });
  document.querySelectorAll('[data-open-invite]').forEach((button) => button.addEventListener('click', openInvite));
  const tabs = [...document.querySelectorAll('[data-members-tab]')];
  tabs.forEach((button) => { button.addEventListener('click', () => setTab(button.dataset.membersTab)); button.addEventListener('keydown', (event) => { if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return; event.preventDefault(); const allowed = tabs.filter((b) => !b.disabled), index = allowed.indexOf(button); const next = event.key === 'Home' ? allowed[0] : event.key === 'End' ? allowed.at(-1) : allowed[(index + (event.key === 'ArrowRight' ? 1 : -1) + allowed.length) % allowed.length]; next.click(); next.focus(); }); });
  for (const selector of ['#members-search','#members-role','#members-state','#members-sort']) $(selector).addEventListener(selector.endsWith('search') ? 'input' : 'change', renderMembers);
  $('#invitations-state').addEventListener('change', renderInvitations);
  document.addEventListener('keydown', (event) => { if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !document.querySelector('dialog[open]') && !/INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName)) { event.preventDefault(); setTab('members'); $('#members-search').focus(); } });
  $('#members-send-verification').addEventListener('click', () => W.run(async () => { const result = await W.api('auth/email/verify', {}); W.notify(result.message || 'Đã tiếp nhận yêu cầu gửi email xác minh.'); }));
  W.mount(render, controls, () => W.info('Quản lý đội ngũ', 'Chủ sở hữu và quản trị viên có thể mời thành viên bằng mã riêng sau khi xác minh email.\n\nNgười nhận đăng nhập bằng đúng email được mời, xác minh email và nhập mã ở trang thiết lập Workspace. Mã có hạn 7 ngày, chỉ dùng một lần.\n\nQuản trị viên quản lý vai trò Member/Viewer. Không thể tự đổi quyền hoặc thay đổi chủ sở hữu.'));
})();
