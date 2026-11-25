/* Customer forms use the BFF. Credentials and sessions never enter browser storage. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];
  let session = null;
  let mode = 'login';
  let emailAction = null;
  let emailToken = '';
  let step = 1;
  let requestKey = crypto.randomUUID();
  let loginBusy = false;
  let selectingWorkspace = false, logoTicket = 0, logoTimer, logoImage = '', logoWebsite = '';
  const Brand = window.VioWorkspaceBranding;
  const roles = {owner: 'Chủ sở hữu', admin: 'Quản trị Workspace', member: 'Thành viên', viewer: 'Chỉ xem'};
  window.addEventListener('pageshow', (event) => { if (event.persisted) location.reload(); });

  function status(message, tone = 'error') {
    const target = $('#join-workspace-dialog')?.open ? $('#join-feedback') : $('#identity-status');
    if (!target) return;
    target.textContent = message;
    target.dataset.tone = tone;
    target.hidden = !message;
    if (message && tone === 'error') target.scrollIntoView({block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  }

  async function api(path, data) {
    const options = {credentials: 'same-origin', cache: 'no-store', headers: {Accept: 'application/json'}};
    if (data !== undefined) {
      options.method = 'POST';
      options.headers['Content-Type'] = 'application/json';
      options.headers['X-CSRF-Token'] = session?.csrf || '';
      options.body = JSON.stringify(data);
    }
    let response;
    try { response = await fetch('/api/customer/' + path, options); }
    catch { throw new Error('Mất kết nối. Kiểm tra mạng rồi thử lại; dữ liệu bạn nhập vẫn được giữ trên trang.'); }
    let payload;
    try { payload = await response.json(); }
    catch { throw new Error('Dịch vụ tạm thời không khả dụng. Vui lòng thử lại.'); }
    if (!response.ok) {
      const error = new Error(payload.error || 'Không thể hoàn tất yêu cầu.');
      error.status = response.status;
      error.code = payload.code;
      throw error;
    }
    return payload;
  }

  async function action(button, task) {
    if (button?.disabled) return;
    status('');
    const labelTarget = button?.querySelector('[data-action-label]') || button;
    const label = labelTarget?.textContent;
    if (button) { button.disabled = true; labelTarget.textContent = button.dataset.loadingLabel || 'Đang xử lý…'; button.setAttribute('aria-busy', 'true'); }
    try { await task(); }
    catch (error) { status(error.message); }
    finally {
      if (button) { button.disabled = false; labelTarget.textContent = label; button.removeAttribute('aria-busy'); }
    }
  }

  async function loginAction(button, task) {
    if (loginBusy || button.disabled) return;
    loginBusy = true;
    const controls = [$('#auth-fields'), $('#google-login'), ...$$('[data-mode]')];
    const disabled = controls.map((control) => control.disabled);
    try {
      await action(button, async () => {
        controls.forEach((control) => { control.disabled = true; });
        await task();
      });
    } finally {
      controls.forEach((control, index) => { control.disabled = disabled[index]; });
      loginBusy = false;
    }
  }

  async function refresh() {
    session = await api('session');
    return session;
  }

  function setMode(next, focus = false) {
    mode = next;
    const register = mode === 'register';
    $('#name-field').hidden = !register;
    $('#name-field input').required = register;
    $('#auth-password').minLength = register ? 12 : 1;
    $('#auth-password').autocomplete = register ? 'new-password' : 'current-password';
    $('#password-guidance').hidden = !register;
    $('#auth-heading').textContent = register ? 'Tạo tài khoản của bạn' : 'Đăng nhập vào Workspace';
    $('#auth-submit').textContent = register ? 'Tạo tài khoản' : 'Đăng nhập';
    $('#auth-description').textContent = register ? 'Tạo tài khoản để bắt đầu với Workspace của bạn.' : 'Tiếp tục công việc, kết nối những góc nhìn.';
    $('.entry-form-intro .entry-form-eyebrow').textContent = register ? 'BẮT ĐẦU CÙNG VIO' : 'CHÀO MỪNG TRỞ LẠI';
    $('.identity-login-card').setAttribute('aria-labelledby', 'auth-heading');
    $$('[data-mode]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
    status('');
    if (focus) $(register ? '#name-field input' : '#identity-auth-form [name=email]').focus();
  }

  function showEmailAction(kind, token = '') {
    emailAction = kind;
    emailToken = token;
    $('#auth-main').hidden = true;
    $('#signed-in').hidden = true;
    $('#email-sent').hidden = true;
    $('#email-action-form').hidden = false;
    $('.identity-login-card').setAttribute('aria-labelledby', 'email-action-heading');
    const request = kind === 'request';
    const reset = kind === 'reset';
    $('#email-action-heading').textContent = request ? 'Quên mật khẩu?' : reset ? 'Đặt lại mật khẩu' : 'Xác minh địa chỉ email';
    $('#recovery-email-label').hidden = !request;
    $('#recovery-email-label input').required = request;
    $('#new-password-label').hidden = !reset;
    $('#new-password-label input').required = reset;
    $('#confirm-password-label').hidden = !reset;
    $('#reset-password-confirm').required = reset;
    $('#reset-password-guidance').hidden = !reset;
    $('#request-new-reset').hidden = true;
    $('#email-action-submit').hidden = false;
    $('#email-action-description').textContent = request
      ? 'Nhập email của tài khoản để nhận liên kết đặt lại mật khẩu.'
      : reset ? 'Tạo mật khẩu mới để truy cập lại tài khoản của bạn.' : 'Xác nhận email để sử dụng đầy đủ tính năng Workspace.';
    for (const input of $$('#email-action-form input')) {
      input.disabled = input.closest('label').hidden;
      input.setCustomValidity('');
    }
    $('#email-action-submit').textContent = request ? 'Gửi hướng dẫn' : reset ? 'Lưu mật khẩu mới' : 'Xác minh email';
    status('');
  }

  function passwordToggle(inputSelector, buttonSelector, name) {
    const input = $(inputSelector), button = $(buttonSelector);
    const update = () => {
      const visible = input.type === 'text';
      const label = (visible ? 'Ẩn ' : 'Hiện ') + name;
      button.setAttribute('aria-label', label);
      button.setAttribute('aria-pressed', String(visible));
      button.title = label;
      button.querySelector('.material-symbols-outlined').textContent = visible ? 'visibility' : 'visibility_off';
    };
    button.addEventListener('click', () => { input.type = input.type === 'password' ? 'text' : 'password'; update(); });
    update();
  }

  function initLogin() {
    $('#auth-fields').disabled = false;
    $('#google-login').disabled = !session.capabilities.google;
    $('#google-availability').textContent = session.capabilities.google ? '' : 'Đăng nhập Google chưa khả dụng. Bạn có thể sử dụng email.';
    $('#google-availability').hidden = session.capabilities.google;
    if (session.user) {
      $('#signed-in').hidden = false;
      $('#signed-in-label').textContent = 'Bạn đang đăng nhập với ' + session.user.email;
      $('#auth-main').hidden = true;
      $('.identity-login-card').setAttribute('aria-labelledby', 'signed-in-heading');
    }
    $$('[data-mode]').forEach((button) => button.addEventListener('click', () => setMode(button.dataset.mode, true)));
    passwordToggle('#auth-password', '#toggle-password', 'mật khẩu');
    $('#identity-auth-form').addEventListener('submit', (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const data = {email: form.get('email'), password: form.get('password'), remember: form.has('remember')};
      if (mode === 'register') data.name = form.get('name');
      loginAction($('#auth-submit'), async () => {
        await api('auth/' + mode, data);
        $('#auth-password').value = '';
        await refresh();
        location.assign(session.workspace ? '/workspace' : '/workspace/onboarding');
      });
    });
    $('#google-login').addEventListener('click', () => loginAction($('#google-login'), async () => {
      const data = await api('auth/google/start', {remember: $('#identity-auth-form [name=remember]').checked});
      const url = new URL(data.authorization_url);
      if (url.origin !== 'https://accounts.google.com' || url.username || url.password || url.hash
          || url.pathname !== '/o/oauth2/v2/auth'
          || url.searchParams.get('redirect_uri') !== location.origin + '/auth/customer/google/callback') throw new Error('Địa chỉ đăng nhập không hợp lệ.');
      location.assign(url.href);
    }));
    $('#forgot-password').addEventListener('click', () => {
      if (!session.capabilities.email_delivery) {
        status('Khôi phục qua email hiện chưa khả dụng. Vui lòng liên hệ VIO Agency để được hỗ trợ.');
        return;
      }
      showEmailAction('request');
      $('#recovery-email-label input').value = $('#identity-auth-form [name=email]').value;
      $('#recovery-email-label input').focus();
    });
    passwordToggle('#reset-password', '#toggle-reset-password', 'mật khẩu mới');
    for (const input of [$('#reset-password'), $('#reset-password-confirm')]) {
      input.addEventListener('input', () => $('#reset-password-confirm').setCustomValidity(''));
    }
    $('#recovery-retry').addEventListener('click', () => showEmailAction('request'));
    $('#request-new-reset').addEventListener('click', () => {
      $('#email-action-form').reset();
      showEmailAction('request');
    });
    $('#back-to-login').addEventListener('click', () => location.assign('/workspace/login'));
    $('#email-action-form').addEventListener('submit', (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      if (emailAction === 'reset' && form.get('password') !== form.get('password_confirm')) {
        $('#reset-password-confirm').setCustomValidity('Mật khẩu nhập lại chưa khớp.');
        $('#reset-password-confirm').reportValidity();
        return;
      }
      action($('#email-action-submit'), async () => {
        let result;
        try {
          result = emailAction === 'request'
            ? await api('auth/email/reset', {email: String(form.get('email')).trim()})
            : await api('auth/email/confirm', {kind: emailAction, token: emailToken, ...(emailAction === 'reset' ? {password: form.get('password')} : {})});
        } catch (error) {
          if (emailAction === 'reset' && error.code === 'email_token') {
            emailToken = '';
            $('#email-action-submit').hidden = true;
            $('#request-new-reset').hidden = !session.capabilities.email_delivery;
          }
          throw error;
        }
        $('#email-action-form').reset();
        if (emailAction === 'request') {
          $('#email-action-form').hidden = true;
          $('#email-sent').hidden = false;
          $('.identity-login-card').setAttribute('aria-labelledby', 'email-sent-heading');
          $('#email-sent-heading').setAttribute('tabindex', '-1');
          $('#email-sent-heading').focus();
        } else {
          emailToken = '';
          $('#email-action-form').hidden = true;
          await refresh();
          setMode('login');
          $('#auth-main').hidden = !!session.user;
          $('#signed-in').hidden = !session.user;
          if (session.user) $('.identity-login-card').setAttribute('aria-labelledby', 'signed-in-heading');
          if (session.user) $('#signed-in-label').textContent = 'Email đã xác minh: ' + session.user.email;
        }
        if (emailAction !== 'request') status(result.message, 'success');
      });
    });
    function consumeEmailLink() {
      const fragment = new URLSearchParams(location.hash.slice(1));
      const token = fragment.get('verify') || fragment.get('reset');
      if (!token) return false;
      history.replaceState(null, '', location.pathname);
      $('#email-action-form').reset();
      showEmailAction(fragment.has('verify') ? 'verify' : 'reset', token);
      return true;
    }
    window.addEventListener('hashchange', consumeEmailLink);
    if (!consumeEmailLink()) {
      const errors = {google_cancelled: 'Bạn đã hủy đăng nhập Google. Bạn có thể chọn lại tài khoản hoặc dùng email.', oauth_state: 'Phiên đăng nhập Google đã hết hạn hoặc thay đổi. Bấm Google để bắt đầu lại.', account_link_required: 'Email này đã đăng ký bằng mật khẩu. Hãy đăng nhập bằng email; chọn Quên mật khẩu nếu cần khôi phục.', google_failed: 'Chưa thể đăng nhập Google. Thử lại hoặc dùng email và mật khẩu đã đăng ký.'};
      Object.assign(errors, {
        google_configuration: 'Đăng nhập Google tạm chưa sẵn sàng. Vui lòng dùng email hoặc liên hệ VIO.',
        google_unavailable: 'Chưa kết nối được với Google. Vui lòng thử lại.',
        google_clock: 'Chưa xác minh được phiên Google. Vui lòng thử lại sau ít phút.',
        google_identity: 'Chưa xác minh được tài khoản Google. Vui lòng chọn lại tài khoản.'
      });
      const code = new URLSearchParams(location.search).get('error');
      if (errors[code]) {
        status(errors[code], code === 'google_cancelled' ? 'info' : 'error');
        history.replaceState(null, '', location.pathname);
        if (code === 'account_link_required') $('#identity-auth-form [name=email]').focus();
      }
    }
  }

  function workspaceData() {
    return {...Object.fromEntries(new FormData($('#workspace-form')).entries()), request_key: requestKey};
  }

  function review() {
    const data = workspaceData();
    const brand = Brand.avatar(data.name); Brand.setImage(brand, logoImage, false);
    const heading = document.createElement('strong'); heading.textContent = data.name;
    $('#workspace-review-brand').replaceChildren(brand, heading);
    const values = [['Loại hình', data.kind === 'agency' ? 'Agency' : 'Doanh nghiệp'], ['Website', data.website || 'Chưa thêm'], ['Quốc gia', $('#workspace-form [name=country]').selectedOptions[0].textContent], ['Múi giờ', data.timezone], ['Tiền tệ', data.currency], [data.kind === 'business' ? 'Thương hiệu' : 'Khách hàng', data.first_client || (data.kind === 'business' ? data.name : 'Thêm sau')]];
    $('#workspace-review').replaceChildren(...values.map(([label, value]) => {
      const row = document.createElement('div');
      const dt = document.createElement('dt');
      const dd = document.createElement('dd');
      dt.textContent = label; dd.textContent = value; row.append(dt, dd);
      return row;
    }));
  }

  function showStep(next, focus = true) {
    step = next;
    $$('[data-step]').forEach((section) => { section.hidden = Number(section.dataset.step) !== step; });
    $$('[data-step-indicator]').forEach((item) => {
      if (Number(item.dataset.stepIndicator) === step) item.setAttribute('aria-current', 'step');
      else item.removeAttribute('aria-current');
      item.dataset.completed = String(Number(item.dataset.stepIndicator) < step);
    });
    $('#step-back').hidden = step === 1;
    $('#step-next').hidden = step === 3;
    $('#workspace-submit').hidden = step !== 3;
    if (step === 3) review();
    if (focus) $(`[data-step="${step}"]`).querySelector('input:not([type=radio]), h3[tabindex]')?.focus();
  }

  function showWorkspaceCreation(open, focus = true) {
    const hasWorkspaces = session.workspaces.length > 0;
    document.body.dataset.entryCreating = String(open);
    $('#workspace-create-section').hidden = !open;
    $('#workspace-picker').hidden = open;
    $('#workspace-create-open').hidden = open;
    $('#workspace-create-cancel').hidden = !hasWorkspaces;
    $('#workspace-page-heading').textContent = open ? hasWorkspaces ? 'Tạo Workspace mới' : 'Tạo Workspace đầu tiên' : 'Chọn Workspace của bạn';
    $('#workspace-page-description').textContent = open ? 'Thiết lập không gian riêng cho dữ liệu, thương hiệu và đội ngũ.' : 'Một nơi riêng cho thương hiệu, dữ liệu và đội ngũ của bạn.';
    status('');
    if (open) showStep(1, false);
    if (focus) {
      if (open) $('#create-heading').focus();
      else $('#workspace-create-open').focus();
    }
  }

  function updateWorkspaceType() {
    const business = $('#workspace-form [name=kind]:checked').value === 'business';
    $('#first-client-heading').textContent = business ? 'Thương hiệu của bạn' : 'Khách hàng đầu tiên';
    $('#first-client-description').textContent = business ? 'Dữ liệu các nền tảng sẽ được gom theo thương hiệu này.' : 'Thêm khách hàng để tổ chức dữ liệu ngay từ đầu.';
    $('#first-client-label').textContent = business ? 'Tên thương hiệu' : 'Tên khách hàng / thương hiệu';
    $('#first-client-help').textContent = business ? 'Để trống để dùng tên Workspace. Bạn có thể cập nhật sau.' : 'Bạn có thể để trống và thêm khách hàng sau.';
    $('#workspace-client-step-label').textContent = business ? 'Thương hiệu' : 'Khách hàng';
    $('#workspace-form [name=first_client]').placeholder = business ? $('#workspace-form [name=name]').value.trim() || 'Tên thương hiệu của bạn' : 'VD: Thương hiệu ABC';
  }

  function searchWorkspaces() {
    const normalize = (value) => value.toLocaleLowerCase('vi').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd');
    const query = normalize($('#workspace-search').value.trim());
    let visible = 0;
    $$('#workspace-list button').forEach((button) => { button.hidden = !normalize(button.textContent).includes(query); if (!button.hidden) visible += 1; });
    $('#workspace-search-empty').hidden = visible > 0;
    $('#workspace-count').textContent = query ? `${visible}/${session.workspaces.length}` : String(session.workspaces.length);
  }

  function validStep() {
    if (step === 1) normalizeWebsite();
    return $$(`[data-step="${step}"] input, [data-step="${step}"] select`).every((input) => input.reportValidity());
  }

  function websiteOrigin(value) {
    try {
      const url = new URL(/^https?:\/\//i.test(value) ? value : 'https://' + value);
      return ['https:','http:'].includes(url.protocol) && url.hostname.includes('.') && !url.username && !url.password ? url.origin : '';
    } catch { return ''; }
  }
  function normalizeWebsite() {
    const input = $('#workspace-form [name=website]'), value = input.value.trim();
    if (value && !/^[a-z][a-z0-9+.-]*:/i.test(value) && websiteOrigin(value)) input.value = 'https://' + value;
  }
  function updateBrandPreview() {
    const name = $('#workspace-form [name=name]').value.trim() || 'Workspace của bạn';
    const website = websiteOrigin($('#workspace-form [name=website]').value.trim());
    $('#workspace-brand-name').textContent = name;
    $('#workspace-brand-website').textContent = website ? new URL(website).hostname : 'Thêm website để tự lấy logo';
    const avatar = $('#workspace-preview-avatar .ws-avatar');
    Brand.setName(avatar, name);
    if (website === logoWebsite) return;
    clearTimeout(logoTimer);
    logoTicket += 1; logoImage = ''; logoWebsite = website; Brand.setImage(avatar, '');
    $('#workspace-brand-status').textContent = '';
    if (!website) return;
    const ticket = logoTicket;
    logoTimer = setTimeout(async () => {
      $('#workspace-brand-status').textContent = 'Đang tìm logo…';
      try {
        const result = await api('branding/preview', {website});
        if (ticket !== logoTicket) return;
        if (result.available && typeof result.image === 'string' && /^data:image\/(png|jpeg|gif|x-icon);base64,[A-Za-z0-9+/]+=*$/.test(result.image)) {
          logoImage = result.image; Brand.setImage(avatar, logoImage, false);
          $('#workspace-brand-status').textContent = 'Logo lấy từ website';
          if (step === 3) review();
        } else $('#workspace-brand-status').textContent = 'Chưa tìm thấy logo · Dùng chữ viết tắt';
      } catch {
        if (ticket === logoTicket) $('#workspace-brand-status').textContent = 'Dùng chữ viết tắt · Bạn vẫn có thể tạo Workspace';
      }
    }, 650);
  }

  async function renderWorkspaces() {
    $('#account-name').textContent = session.user.name;
    $('#account-avatar').textContent = Array.from(session.user.name.trim())[0]?.toLocaleUpperCase('vi') || 'V';
    $('#verification-note').hidden = !!session.user.email_verified;
    $('#verify-email').disabled = !session.capabilities.email_delivery;
    if (!session.capabilities.email_delivery) $('#verification-text').textContent = 'Bạn có thể tạo Workspace. Xác minh email và lời mời sẽ khả dụng khi dịch vụ email được bật.';
    $('#workspace-list-section').hidden = !session.workspaces.length;
    $('#workspace-count').textContent = String(session.workspaces.length);
    $('#workspace-search-label').hidden = session.workspaces.length < 4;
    $('#workspace-list').replaceChildren(...session.workspaces.map((workspace) => {
      const button = document.createElement('button');
      button.className = 'identity-workspace-option'; button.type = 'button';
      const chosen = workspace.id === session.workspace?.id;
      button.setAttribute('aria-pressed', String(chosen)); button.setAttribute('aria-label', 'Mở Workspace ' + workspace.name);
      const body = document.createElement('span'); body.className = 'workspace-choice-body';
      const name = document.createElement('strong'); name.className = 'workspace-choice-title'; name.textContent = workspace.name;
      const detail = document.createElement('span'); detail.className = 'workspace-choice-meta';
      const role = document.createElement('span'); role.className = 'workspace-role'; role.textContent = roles[workspace.role] || 'Thành viên'; detail.append(role);
      const kind = document.createElement('span'); kind.className = 'workspace-kind'; kind.textContent = workspace.kind === 'business' ? 'Doanh nghiệp' : 'Agency'; detail.append(kind);
      if (chosen) { const current = document.createElement('span'); current.className = 'workspace-current'; current.textContent = 'Đang chọn'; detail.append(current); }
      body.append(name, detail);
      if (workspace.website) {
        const site = document.createElement('small'); site.className = 'workspace-choice-site';
        try { site.textContent = new URL(workspace.website).hostname; } catch { site.textContent = workspace.website; }
        body.append(site);
      }
      if (Number.isInteger(workspace.client_count)) {
        const clients = document.createElement('span'); clients.className = 'workspace-choice-clients';
        const count = document.createElement('strong'); count.textContent = `${workspace.client_count} ${workspace.kind === 'business' ? 'thương hiệu' : 'khách hàng'}`; clients.append(count);
        (workspace.client_preview || []).slice(0,2).forEach((value) => { const tag = document.createElement('span'); tag.className = 'workspace-client-chip'; tag.textContent = value; clients.append(tag); });
        if (workspace.client_count > 2) { const extra = document.createElement('span'); extra.className = 'workspace-client-chip'; extra.textContent = '+' + (workspace.client_count - 2); clients.append(extra); }
        body.append(clients);
      }
      const arrow = document.createElement('span'); arrow.className = 'workspace-choice-arrow'; arrow.textContent = '→'; arrow.setAttribute('aria-hidden','true');
      button.append(Brand.avatar(workspace.name, workspace.id), body, arrow);
      button.addEventListener('click', () => action(null, async () => {
        if (selectingWorkspace) return;
        selectingWorkspace = true; $$('#workspace-list button').forEach((item) => { item.disabled = true; }); button.setAttribute('aria-busy','true');
        try { await api(`workspaces/${workspace.id}/select`, {}); location.assign('/workspace'); }
        finally { selectingWorkspace = false; $$('#workspace-list button').forEach((item) => { item.disabled = false; }); button.removeAttribute('aria-busy'); }
      }));
      return button;
    }));
    const current = session.workspace;
    $('#workspace-success').hidden = !current;
    $('#invite-panel').hidden = !current || !['owner', 'admin'].includes(current.role) || !session.user.email_verified;
    $('#invitation-result').hidden = true;
    if (current) {
      $('#workspace-active-avatar').replaceChildren(Brand.avatar(current.name, current.id));
      $('#workspace-success-heading').textContent = current.name;
      $('#workspace-success-detail').textContent = `${roles[current.role]} · ${current.kind === 'agency' ? 'Agency' : 'Doanh nghiệp'} · ${current.currency} · ${current.timezone}`;
      $('#invite-admin-option').disabled = current.role !== 'owner';
      $('#invite-form [name=role]').value = 'member';
      try {
        const details = await api(`workspaces/${current.id}`);
        $('#workspace-client-detail').textContent = details.clients.length ? `${details.clients.length} khách hàng / thương hiệu` : 'Chưa thêm khách hàng / thương hiệu.';
        const tags = details.clients.slice(0,3).map((client) => { const tag = document.createElement('span'); tag.className = 'workspace-client-chip'; tag.textContent = client.name; return tag; });
        if (details.clients.length > 3) { const more = document.createElement('span'); more.className = 'workspace-client-chip'; more.textContent = '+' + (details.clients.length - 3); tags.push(more); }
        $('#workspace-client-tags').replaceChildren(...tags);
      } catch { /* Workspace selection remains available if its optional preview fails. */ }
    }
  }

  async function initOnboarding() {
    if (!session.user) { location.replace('/workspace/login'); return; }
    await renderWorkspaces();
    showWorkspaceCreation(session.workspaces.length === 0, false);
    $('#workspace-create-open').disabled = false;
    $('#workspace-join-open').disabled = false;
    $('#workspace-create-open').addEventListener('click', () => showWorkspaceCreation(true));
    $('#workspace-create-cancel').addEventListener('click', () => showWorkspaceCreation(false));
    $('#workspace-join-open').addEventListener('click', () => {
      $('#join-feedback').hidden = true;
      $('#join-workspace-dialog').showModal();
      $('#join-form [name=invitation_code]').focus();
    });
    $('#workspace-join-close').addEventListener('click', () => $('#join-workspace-dialog').close());
    $('#workspace-search').addEventListener('input', searchWorkspaces);
    $('#workspace-search-clear').addEventListener('click', () => { $('#workspace-search').value = ''; searchWorkspaces(); $('#workspace-search').focus(); });
    $('#workspace-preview-avatar').replaceChildren(Brand.avatar('Workspace của bạn'));
    $('#workspace-form [name=name]').addEventListener('input', () => {
      const name = $('#workspace-form [name=name]').value.trim() || 'Workspace của bạn';
      $('#workspace-brand-name').textContent = name; Brand.setName($('#workspace-preview-avatar .ws-avatar'), name);
      updateWorkspaceType();
    });
    $$('#workspace-form [name=kind]').forEach((input) => input.addEventListener('change', updateWorkspaceType));
    updateWorkspaceType();
    for (const name of ['country', 'currency', 'timezone']) $('#workspace-form [name=' + name + ']').addEventListener('change', () => {
      const form = $('#workspace-form');
      $('#workspace-locale-summary').textContent = form.elements.country.selectedOptions[0].textContent + ' · ' + form.elements.currency.value + ' · ' + form.elements.timezone.value;
    });
    $('#workspace-form [name=website]').addEventListener('input', updateBrandPreview);
    $('#workspace-form [name=website]').addEventListener('blur', () => { normalizeWebsite(); updateBrandPreview(); });
    $('#workspace-fields').disabled = false;
    $('#join-submit').disabled = false;
    $('#step-next').addEventListener('click', () => { if (validStep()) showStep(Math.min(3, step + 1)); });
    $('#step-back').addEventListener('click', () => showStep(Math.max(1, step - 1)));
    $('#workspace-form').addEventListener('submit', (event) => {
      event.preventDefault();
      if (step !== 3) { if (validStep()) showStep(step + 1); return; }
      const data = workspaceData();
      action($('#workspace-submit'), async () => {
        await api('workspaces', data);
        location.assign('/workspace');
      });
    });
    $('#join-form').addEventListener('submit', (event) => {
      event.preventDefault();
      const data = Object.fromEntries(new FormData(event.currentTarget));
      action($('#join-submit'), async () => {
        await api('workspaces/join', data);
        location.assign('/workspace');
      });
    });
    $('#verify-email').addEventListener('click', () => action($('#verify-email'), async () => {
      const data = await api('auth/email/verify', {});
      status(data.message, 'success');
    }));
    $('#invite-form').addEventListener('submit', (event) => {
      event.preventDefault();
      const data = Object.fromEntries(new FormData(event.currentTarget));
      action($('#invite-form button[type=submit]'), async () => {
        const result = await api(`workspaces/${session.workspace.id}/invitations`, data);
        $('#invitation-code').value = result.invitation_code;
        $('#invitation-result').hidden = false;
      });
    });
  }

  $$('[data-logout]').forEach((button) => button.addEventListener('click', () => action(button, async () => {
    await api('auth/logout', {});
    location.assign('/workspace/login');
  })));
  async function start() {
    if (!['login', 'onboarding'].includes(document.body.dataset.customerPage)) return;
    try {
      await refresh();
      if (document.body.dataset.customerPage === 'login') initLogin();
      else await initOnboarding();
    } catch (error) { status(error.message); }
  }
  start();
})();
