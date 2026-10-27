/* Customer design workspace. Local drafts/preferences never create server identity. */
(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const page = document.body.dataset.customerPage;
  const prefix = 'vio.customer-preview.v1.';
  const read = (key, fallback) => {
    try { return JSON.parse(sessionStorage.getItem(prefix + key)) ?? fallback; }
    catch { return fallback; }
  };
  const write = (key, value) => {
    try { sessionStorage.setItem(prefix + key, JSON.stringify(value)); return true; }
    catch { info('Không thể lưu', 'Trình duyệt đang chặn lưu trữ hoặc đã hết dung lượng. Thay đổi chưa được lưu.'); return false; }
  };
  const normalized = value => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').toLowerCase();
  const dialog = $('#customer-dialog');
  function info(title, message) {
    $('#customer-dialog-title').textContent = title;
    $('#customer-dialog-message').textContent = message;
    if (!dialog.open) dialog.showModal();
  }
  let toastTimer;
  function toast(message) {
    const node = $('#customer-toast');
    node.textContent = message;
    node.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { node.hidden = true; }, 4500);
  }
  let activeModal = null;
  let previousFocus = null;
  function openModal(id) {
    const modal = $('#' + id);
    if (!modal) return;
    previousFocus = document.activeElement;
    activeModal = modal;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    const heading = $('h3', modal);
    if (heading) { heading.id ||= id + '-heading'; modal.setAttribute('aria-labelledby', heading.id); }
    ($('input:not([type=checkbox]):not([type=radio]),button', modal) || modal).focus();
    document.body.style.overflow = 'hidden';
  }
  function closeModal() {
    if (!activeModal) return;
    activeModal.classList.add('hidden');
    activeModal.classList.remove('flex');
    activeModal = null;
    document.body.style.overflow = '';
    previousFocus?.focus();
  }
  const workspace = read('workspace', {});
  if (typeof workspace.name === 'string' && workspace.name.trim()) {
    $$('[data-workspace-name]').forEach(n => { n.textContent = workspace.name; });
  }

  function menu(open) {
    document.body.classList.toggle('customer-menu-open', open);
    if ($('#customer-backdrop')) $('#customer-backdrop').hidden = !open;
    $('#customer-menu')?.setAttribute('aria-expanded', String(open));
    if (open) $('#customer-sidebar a')?.focus();
  }
  $('#customer-menu')?.addEventListener('click', () => menu(!document.body.classList.contains('customer-menu-open')));
  $('#customer-backdrop')?.addEventListener('click', () => menu(false));
  $('#customer-channel-toggle')?.addEventListener('click', e => {
    const expanded = e.currentTarget.getAttribute('aria-expanded') !== 'true';
    e.currentTarget.setAttribute('aria-expanded', String(expanded));
    $('#customer-channel-links').hidden = !expanded;
  });

  const search = $('#customer-search');
  const results = $('#customer-search-results');
  search?.addEventListener('input', () => {
    const query = normalized(search.value.trim());
    results.replaceChildren();
    results.hidden = !query;
    if (!query) return;
    const links = $$('#customer-sidebar nav a').filter(a => normalized(a.textContent).includes(query));
    links.forEach(a => {
      const item = document.createElement('a');
      item.href = a.getAttribute('href');
      item.textContent = a.querySelector('span:last-child')?.textContent || a.textContent;
      results.append(item);
    });
    if (!links.length) { const p = document.createElement('p'); p.textContent = 'Không tìm thấy trang hoặc báo cáo.'; results.append(p); }
  });
  search?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !results.hidden) $('a', results)?.click();
  });
  document.addEventListener('click', e => {
    if (results && !e.target.closest('.customer-topbar')) results.hidden = true;
  });
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k' && search) { e.preventDefault(); search.focus(); }
    if (e.key === 'Escape' && !dialog.open) {
      closeModal(); menu(false);
      if (results) results.hidden = true;
    }
    if (e.key === 'Tab' && activeModal && !dialog.open) {
      const nodes = $$('button,a[href],input,select,textarea,[tabindex="0"]', activeModal).filter(n => !n.disabled && n.getClientRects().length);
      const first = nodes[0], last = nodes[nodes.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    }
  });
  $$('#createReportModal,#inviteModal').forEach(modal => modal.addEventListener('click', e => { if (e.target === modal) closeModal(); }));

  function configureFilter({cards, buttons, input, status, categoryAttribute = 'category'}) {
    if (!cards.length) return;
    let category = 'all';
    const empty = document.createElement('p');
    empty.className = 'customer-no-results'; empty.hidden = true; empty.textContent = 'Không tìm thấy kết quả phù hợp. Thử từ khóa hoặc bộ lọc khác.';
    cards[0].parentElement.append(empty);
    function filter() {
      const query = normalized(input?.value || '');
      let count = 0;
      cards.forEach(card => {
        const match = (category === 'all' || card.dataset.category === category) && normalized(card.textContent).includes(query) && (!status || status.selectedIndex < 2);
        card.hidden = !match;
        count += Number(match);
      });
      empty.hidden = count > 0;
    }
    buttons.forEach(button => button.addEventListener('click', () => {
      category = button.dataset[categoryAttribute] || 'all';
      buttons.forEach(b => { b.classList.toggle('customer-filter-active', b === button); b.setAttribute('aria-pressed', String(b === button)); });
      filter();
    }));
    input?.addEventListener('input', filter);
    status?.addEventListener('change', filter);
    filter();
  }
  configureFilter({ cards: $$('.channel-card'), buttons: $$('.category-btn'), input: $('#channelSearch'), status: $('#statusFilter') });
  configureFilter({ cards: $$('[data-report-card]'), buttons: $$('#reportFilterBar .filter-btn') });
  configureFilter({ cards: $$('[data-platform-card]'), buttons: $$('[data-platform-category]'), input: $('[data-platform-search]'), categoryAttribute:'platformCategory' });

  $$('.tab-btn').forEach(tab => {
    tab.setAttribute('role','tab');
    tab.addEventListener('click', () => {
      $$('.tab-btn').forEach(b => { b.setAttribute('aria-selected', String(b === tab)); b.classList.toggle('customer-filter-active', b === tab); });
      ['members','pending','logs'].forEach(name => $('#panel-' + name)?.classList.toggle('hidden', tab.dataset.tab !== 'tab-' + name));
    });
  });
  const memberFilters = $$('[data-member-filter]');
  function filterMembers() {
    const [query, role, status] = memberFilters;
    const matching = (!role || role.selectedIndex < 2) && (!status || status.selectedIndex < 2);
    $$('[data-member-row]').forEach(row => { row.hidden = !matching || !normalized(row.textContent).includes(normalized(query?.value || '')); });
    let empty = $('#customer-members-empty');
    if (!empty && $('#panel-members')) {
      empty = document.createElement('p'); empty.id = 'customer-members-empty'; empty.className = 'customer-no-results'; empty.textContent = 'Không có thành viên phù hợp.'; $('#panel-members').append(empty);
    }
    if (empty) empty.hidden = $$('[data-member-row]').some(row => !row.hidden);
  }
  memberFilters.forEach(field => field.addEventListener(field.tagName === 'SELECT' ? 'change' : 'input', filterMembers));

  const settingsFields = $$('[data-setting]:not([type=file])');
  function settingsValues() {
    return Object.fromEntries(settingsFields.map(field => [field.id, {value: field.value, checked:field.checked}]));
  }
  function applySettings(values) {
    if (!values || typeof values !== 'object') return;
    settingsFields.forEach(field => {
      const value = values[field.id];
      if (!value || typeof value !== 'object') return;
      if (typeof value.value === 'string' && !['radio','checkbox'].includes(field.type)) field.value = value.value;
      if (typeof value.checked === 'boolean') field.checked = value.checked;
    });
  }
  const settingsDefaults = settingsValues();
  if (page === 'settings') {
    applySettings(read('settings', settingsDefaults));
    if (workspace.name) { const name = $('input[readonly]'); if (name) name.value = workspace.name; }
    const savedLogo = read('logo', '');
    if (typeof savedLogo === 'string' && /^data:image\/(png|jpeg|webp);base64,/.test(savedLogo)) $$('[data-logo-preview]').forEach(img => { img.src = savedLogo; });
    const upload = $('input[type=file]');
    upload?.addEventListener('change', () => {
      const file = upload.files[0];
      if (!file) return;
      if (!['image/png','image/jpeg','image/webp'].includes(file.type) || file.size > 2 * 1024 * 1024) {
        info('Logo chưa phù hợp', 'Chọn ảnh PNG, JPG hoặc WebP dung lượng tối đa 2 MB.'); upload.value = ''; return;
      }
      const reader = new FileReader();
      reader.addEventListener('load', () => {
        $$('[data-logo-preview]').forEach(img => { img.src = reader.result; });
        upload.dataset.pendingLogo = reader.result;
        toast('Đã xem trước logo. Bấm Lưu thay đổi để giữ lại trên trình duyệt.');
      });
      reader.readAsDataURL(file);
    });
  }

  let draftFilter = 'Tất cả';
  function getDrafts() {
    const drafts = read('drafts', []);
    return Array.isArray(drafts) ? drafts.filter(d => d && typeof d.name === 'string' && typeof d.id === 'string').slice(0,50) : [];
  }
  function renderDrafts() {
    const list = $('#local-report-list');
    if (!list) return;
    list.replaceChildren();
    const drafts = getDrafts();
    const query = normalized($('input[placeholder*="báo cáo"]', $('#customer-content'))?.value || '');
    $$('[data-draft-tab]').forEach(tab => {
      const label = tab.dataset.draftTab;
      tab.textContent = label + ' ' + (['Tất cả','Bản nháp'].includes(label) ? drafts.length : 0);
      tab.setAttribute('aria-pressed', String(label === draftFilter));
    });
    // Hide the original empty state only when a local draft exists.
    const emptyTitle = $$('h3').find(h => h.textContent.includes('Chưa có báo cáo tùy chỉnh'));
    if (emptyTitle) emptyTitle.parentElement.hidden = drafts.length > 0;
    if (!['Tất cả','Bản nháp'].includes(draftFilter)) {
      const p=document.createElement('p'); p.className='customer-no-results'; p.textContent='Chưa có báo cáo thuộc trạng thái này.'; list.append(p); return;
    }
    drafts.filter(d => normalized(d.name).includes(query)).forEach(draft => {
      const row = document.createElement('article'); row.className='customer-local-draft';
      const text = document.createElement('div'), heading = document.createElement('h3'), meta = document.createElement('p');
      heading.textContent=draft.name; meta.textContent='Bản nháp trên trình duyệt · '+(draft.period || 'Chưa chọn kỳ')+' · Chưa phát hành';
      text.append(heading,meta); row.append(text);
      const open=document.createElement('button'); open.className='customer-secondary'; open.textContent='Mở bản nháp';
      open.addEventListener('click',()=>info(draft.name,'Kỳ báo cáo: '+draft.period+'\nMẫu: '+draft.template+'\nNội dung: '+(draft.sections?.join(', ') || 'Chưa chọn')+'\n\nĐây là bản nháp lưu trên trình duyệt. Kết nối dữ liệu và lưu báo cáo trên máy chủ chưa được kích hoạt.'));
      const remove=document.createElement('button'); remove.className='customer-back-link'; remove.textContent='Xóa bản nháp';
      remove.addEventListener('click',()=>{ if(write('drafts',getDrafts().filter(d=>d.id!==draft.id))) renderDrafts(); });
      row.append(open,remove); list.append(row);
    });
  }
  $$('[data-draft-tab]').forEach(tab=>tab.addEventListener('click',()=>{draftFilter=tab.dataset.draftTab;renderDrafts();}));
  if (page==='reports') {
    $('input[placeholder*="báo cáo"]', $('#customer-content'))?.addEventListener('input',renderDrafts);
    renderDrafts();
    if (new URLSearchParams(location.search).get('create') === '1') openModal('createReportModal');
  }
  $('#createReportForm')?.addEventListener('submit', e => {
    e.preventDefault();
    const form=e.currentTarget;
    if (!form.reportValidity()) return;
    const name=$('#reportNameInput').value.trim();
    if (!name || name.length>120) { info('Tên báo cáo', 'Nhập tên báo cáo từ 1 đến 120 ký tự.'); return; }
    const selects=$$('select',form);
    const drafts=getDrafts();
    if(drafts.length>=50){info('Đã đủ bản nháp','Bản xem thử lưu tối đa 50 bản nháp. Xóa bản không còn dùng trước khi tạo thêm.');return;}
    const draft={id:crypto.randomUUID(),name,period:selects[0]?.value||'',template:selects[1]?.value||'',sections:$$('input[type=checkbox]:checked',form).map(f=>f.closest('label')?.textContent.trim()||f.value)};
    if(write('drafts',[draft,...drafts])) { closeModal(); renderDrafts(); form.reset(); toast('Đã lưu bản nháp trên trình duyệt. Chưa phát hành hoặc gửi báo cáo.'); }
  });
  $('#auth-form')?.addEventListener('submit', e => { e.preventDefault(); info('Đăng nhập chưa được kích hoạt','Bản giao diện này chưa tạo phiên đăng nhập. Chọn Khám phá giao diện mới để xem các trang.'); });

  document.addEventListener('click', event => {
    const button=event.target.closest('[data-action]');
    if(!button)return;
    const action=button.dataset.action;
    if(action==='save-report')return; // Native form validation and submit handler.
    event.preventDefault();
    switch(action) {
      case 'create-workspace': {
        const name=$('#agency-name'), website=$('#agency-website');
        if(!name.reportValidity()||!website.reportValidity())return;
        const value=name.value.trim();
        if(!value||value.length>100){info('Tên Workspace','Nhập tên Workspace từ 1 đến 100 ký tự.');return;}
        if(write('workspace',{name:value,website:website.value,country:$('#agency-country').value,timezone:$('#agency-timezone').value,currency:$('#agency-currency').value}))location.assign('/workspace');
        break;
      }
      case 'create-mode': $('#agency-name')?.focus(); break;
      case 'join-workspace': info('Tham gia Workspace','Bạn cần lời mời hợp lệ từ quản trị Workspace. Bản xem thử chưa nhận hoặc xác thực lời mời.'); break;
      case 'create-report': openModal('createReportModal'); break;
      case 'invite-open': openModal('inviteModal'); break;
      case 'close-modal': closeModal(); break;
      case 'invite-send': {
        const email=$('#inviteEmail');
        email.required=true;
        if(!email.reportValidity())return;
        info('Chưa gửi lời mời','Chức năng gửi lời mời và phân quyền cần tài khoản Workspace đã đăng nhập. Không có email nào được gửi từ bản xem thử này.');break;
      }
      case 'matrix': $('#permissionsMatrixSection')?.scrollIntoView({behavior:'smooth',block:'start'}); break;
      case 'save-settings': {
        if(settingsFields.some(field=>!field.reportValidity()))return;
        if(write('settings',settingsValues())) {
          const pending=$('input[type=file]')?.dataset.pendingLogo;
          if(pending!==undefined&&!write('logo',pending))return;
          toast('Đã lưu tùy chọn trên trình duyệt này. Chưa cập nhật máy chủ.');
        } break;
      }
      case 'reset-settings': {
        applySettings(read('settings',settingsDefaults));
        const logo=read('logo','');
        $$('[data-logo-preview]').forEach(img=>{img.src=/^data:image\/(png|jpeg|webp);base64,/.test(logo)?logo:'/static/img/analytics-mark.svg';});
        const upload=$('input[type=file]'); if(upload){upload.value='';delete upload.dataset.pendingLogo;}
        toast('Đã khôi phục các tùy chọn đã lưu.');break;
      }
      case 'remove-logo':
        $$('[data-logo-preview]').forEach(img=>{img.src='/static/img/analytics-mark.svg';});
        if($('input[type=file]'))$('input[type=file]').dataset.pendingLogo='';
        toast('Đã gỡ logo khỏi bản xem trước. Bấm Lưu thay đổi để giữ lại.');break;
      case 'metric-tab':
        $$('[data-action=metric-tab]',button.parentElement).forEach(b=>{b.classList.toggle('customer-filter-active',b===button);b.setAttribute('aria-pressed',String(b===button));});
        toast('Đã chọn '+button.textContent.trim()+'. Chưa có dữ liệu kết nối cho biểu đồ này.');break;
      case 'connect-unavailable': info('Kết nối nền tảng','Bản giao diện này chưa thực hiện OAuth hoặc đồng bộ tài khoản. Các trạng thái kết nối hiển thị là ví dụ thiết kế; chưa có tài khoản nào được kết nối mới.'); break;
      case 'auth-unavailable': info('Đăng nhập tài khoản','Google Sign-in và đăng nhập email chưa được tích hợp vào giao diện mới. Chọn Khám phá giao diện mới để tiếp tục xem thử mà không nhập mật khẩu.'); break;
      case 'password': { const field=$('#password'); if(field&&!field.disabled)field.type=field.type==='password'?'text':'password';break; }
      case 'export-history': info('Lịch sử xuất file','Chưa có lịch sử xuất file cho Workspace xem thử. Bạn có thể mở báo cáo hiện có trong Phân tích kênh để dùng chức năng xuất của từng báo cáo.');break;
      case 'export-empty': info('Chưa có dữ liệu để xuất','Dashboard này chưa nhận dữ liệu kết nối. Các báo cáo mẫu hiện có trong Phân tích kênh vẫn hỗ trợ xuất file.');break;
      case 'report-unavailable': info('Báo cáo chưa sẵn sàng','Chưa có báo cáo đã phát hành cho kênh này. Xem các báo cáo hiện có trong Phân tích kênh.');break;
      case 'period': info('Kỳ báo cáo','Trang tổng hợp đang hiển thị trạng thái minh họa tháng 10/2026. Mở báo cáo chi tiết trong Phân tích kênh để đổi kỳ và so sánh dữ liệu mẫu.');break;
      case 'notifications': info('Thông báo','Chưa có thông báo mới trong bản xem thử.');break;
      case 'help': info('VioAgencyAnalytics','Bắt đầu từ Thiết lập Workspace, xem Kết nối nền tảng, Dashboard và Phân tích kênh. Các báo cáo cũ nằm trong Phân tích kênh. Tùy chọn và bản nháp ở đây chỉ được lưu trên trình duyệt.');break;
      default: info('Chức năng đang được chuẩn bị','Thao tác này cần dữ liệu và quyền từ Workspace trên máy chủ. Bản xem thử chưa thực hiện thay đổi này.');
    }
  });
})();
