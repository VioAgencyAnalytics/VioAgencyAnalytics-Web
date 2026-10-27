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
  const roles = {owner: 'Chủ sở hữu', admin: 'Quản trị Workspace', member: 'Thành viên', viewer: 'Chỉ xem'};
  window.addEventListener('pageshow', (event) => { if (event.persisted) location.reload(); });

  function status(message, tone = 'error') {
    const target = $('#identity-status');
    if (!target) return;
    target.textContent = message;
    target.dataset.tone = tone;
    target.hidden = !message;
    if (message && tone === 'error') target.scrollIntoView({block: 'nearest', behavior: 'smooth'});
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
    const label = button?.textContent;
    if (button) { button.disabled = true; button.textContent = 'Đang xử lý…'; button.setAttribute('aria-busy', 'true'); }
    try { await task(); }
    catch (error) { status(error.message); }
    finally {
      if (button) { button.disabled = false; button.textContent = label; button.removeAttribute('aria-busy'); }
    }
  }

  async function refresh() {
    session = await api('session');
    return session;
  }

  function setMode(next) {
    mode = next;
    const register = mode === 'register';
    $('#name-field').hidden = !register;
    $('#name-field input').required = register;
    $('#auth-password').minLength = register ? 12 : 1;
    $('#auth-password').autocomplete = register ? 'new-password' : 'current-password';
    $('#password-guidance').hidden = !register;
    $('#auth-heading').textContent = register ? 'Tạo tài khoản của bạn' : 'Đăng nhập vào Workspace';
    $('#auth-submit').textContent = register ? 'Tạo tài khoản' : 'Đăng nhập';
    $$('[data-mode]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
    status('');
  }

  function showEmailAction(kind, token = '') {
    emailAction = kind;
    emailToken = token;
    $('#auth-main').hidden = true;
    $('#signed-in').hidden = true;
    $('#email-sent').hidden = true;
    $('#email-action-form').hidden = false;
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

  function initLogin() {
    $('#auth-fields').disabled = false;
    $('#google-login').disabled = !session.capabilities.google;
    $('#google-availability').textContent = session.capabilities.google ? '' : 'Đăng nhập Google chưa khả dụng. Bạn có thể sử dụng email.';
    if (session.user) {
      $('#signed-in').hidden = false;
      $('#signed-in-label').textContent = 'Bạn đang đăng nhập với ' + session.user.email;
      $('#auth-main').hidden = true;
    }
    $$('[data-mode]').forEach((button) => button.addEventListener('click', () => setMode(button.dataset.mode)));
    $('#toggle-password').addEventListener('click', () => {
      const visible = $('#auth-password').type === 'password';
      $('#auth-password').type = visible ? 'text' : 'password';
      $('#toggle-password').setAttribute('aria-label', visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu');
      $('#toggle-password').setAttribute('aria-pressed', String(visible));
    });
    $('#identity-auth-form').addEventListener('submit', (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const data = {email: form.get('email'), password: form.get('password'), remember: form.has('remember')};
      if (mode === 'register') data.name = form.get('name');
      action($('#auth-submit'), async () => {
        await api('auth/' + mode, data);
        $('#auth-password').value = '';
        await refresh();
        location.assign(session.workspace ? '/workspace' : '/workspace/onboarding');
      });
    });
    $('#google-login').addEventListener('click', () => action($('#google-login'), async () => {
      const data = await api('auth/google/start', {remember: $('#identity-auth-form [name=remember]').checked});
      const url = new URL(data.authorization_url);
      if (url.origin !== 'https://accounts.google.com' || url.pathname !== '/o/oauth2/v2/auth') throw new Error('Địa chỉ đăng nhập không hợp lệ.');
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
    $('#toggle-reset-password').addEventListener('click', () => {
      const visible = $('#reset-password').type === 'password';
      $('#reset-password').type = visible ? 'text' : 'password';
      $('#toggle-reset-password').setAttribute('aria-label', visible ? 'Ẩn mật khẩu mới' : 'Hiện mật khẩu mới');
      $('#toggle-reset-password').setAttribute('aria-pressed', String(visible));
    });
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
        } else {
          emailToken = '';
          $('#email-action-form').hidden = true;
          await refresh();
          setMode('login');
          $('#auth-main').hidden = !!session.user;
          $('#signed-in').hidden = !session.user;
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
      const errors = {google_cancelled: 'Bạn đã hủy đăng nhập Google.', oauth_state: 'Phiên đăng nhập Google đã hết hạn. Vui lòng thử lại.', account_link_required: 'Email đã có tài khoản. Hãy đăng nhập bằng phương thức đã đăng ký.', google_failed: 'Không thể hoàn tất đăng nhập Google. Hãy thử lại hoặc đăng nhập bằng email.'};
      const code = new URLSearchParams(location.search).get('error');
      if (errors[code]) { status(errors[code]); history.replaceState(null, '', location.pathname); }
    }
  }

  function workspaceData() {
    return {...Object.fromEntries(new FormData($('#workspace-form')).entries()), request_key: requestKey};
  }

  function review() {
    const data = workspaceData();
    const values = [['Workspace', data.name], ['Loại hình', data.kind === 'agency' ? 'Agency' : 'Doanh nghiệp'], ['Website', data.website || 'Chưa thêm'], ['Quốc gia', $('#workspace-form [name=country]').selectedOptions[0].textContent], ['Múi giờ', data.timezone], ['Tiền tệ', data.currency], ['Khách hàng', data.first_client || (data.kind === 'business' ? data.name : 'Thêm sau')]];
    $('#workspace-review').replaceChildren(...values.map(([label, value]) => {
      const row = document.createElement('div');
      const dt = document.createElement('dt');
      const dd = document.createElement('dd');
      dt.textContent = label; dd.textContent = value; row.append(dt, dd);
      return row;
    }));
  }

  function showStep(next) {
    step = next;
    $$('[data-step]').forEach((section) => { section.hidden = Number(section.dataset.step) !== step; });
    $$('[data-step-indicator]').forEach((item) => {
      if (Number(item.dataset.stepIndicator) === step) item.setAttribute('aria-current', 'step');
      else item.removeAttribute('aria-current');
    });
    $('#step-back').hidden = step === 1;
    $('#step-next').hidden = step === 3;
    $('#workspace-submit').hidden = step !== 3;
    if (step === 3) review();
  }

  function validStep() {
    return $$(`[data-step="${step}"] input, [data-step="${step}"] select`).every((input) => input.reportValidity());
  }

  async function renderWorkspaces() {
    $('#account-name').textContent = session.user.name;
    $('#verification-note').hidden = !!session.user.email_verified;
    $('#verify-email').disabled = !session.capabilities.email_delivery;
    if (!session.capabilities.email_delivery) $('#verification-text').textContent = 'Bạn có thể tạo Workspace. Xác minh email và lời mời sẽ khả dụng khi dịch vụ email được bật.';
    $('#workspace-list-section').hidden = !session.workspaces.length;
    $('#workspace-list').replaceChildren(...session.workspaces.map((workspace) => {
      const button = document.createElement('button');
      button.className = 'identity-workspace-option'; button.type = 'button';
      button.setAttribute('aria-pressed', String(workspace.id === session.workspace?.id));
      const name = document.createElement('strong'); name.textContent = workspace.name;
      const detail = document.createElement('span'); detail.textContent = `${roles[workspace.role]} · ${workspace.currency} · ${workspace.timezone}`;
      button.append(name, detail);
      button.addEventListener('click', () => action(null, async () => {
        if (button.disabled) return;
        button.disabled = true;
        try { await api(`workspaces/${workspace.id}/select`, {}); location.assign('/workspace'); }
        finally { button.disabled = false; }
      }));
      return button;
    }));
    const current = session.workspace;
    $('#workspace-success').hidden = !current;
    $('#invite-panel').hidden = !current || !['owner', 'admin'].includes(current.role) || !session.user.email_verified;
    $('#invitation-result').hidden = true;
    if (current) {
      $('#workspace-success-heading').textContent = current.name;
      $('#workspace-success-detail').textContent = `${roles[current.role]} · ${current.kind === 'agency' ? 'Agency' : 'Doanh nghiệp'} · ${current.currency} · ${current.timezone}`;
      $('#invite-admin-option').disabled = current.role !== 'owner';
      $('#invite-form [name=role]').value = 'member';
      const details = await api(`workspaces/${current.id}`);
      $('#workspace-client-detail').textContent = details.clients.length ? 'Khách hàng / thương hiệu: ' + details.clients.map((client) => client.name).join(', ') : 'Chưa thêm khách hàng / thương hiệu.';
    }
  }

  async function initOnboarding() {
    if (!session.user) { location.replace('/workspace/login'); return; }
    await renderWorkspaces();
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
