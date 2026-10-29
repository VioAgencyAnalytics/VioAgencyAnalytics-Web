"""Live Members/Settings UX and tenant denial. Only named QA accounts are modified."""
import json
from pathlib import Path
import secrets
import subprocess
import time

from playwright.sync_api import sync_playwright

ORIGIN = 'http://127.0.0.1:8084'
OUT = Path(__file__).resolve().parents[1] / '.work/customer-workspace-admin-qa'


def verify_qa(account_id, email):
    # No email is sent; never modify a real account or expose an Admin test endpoint.
    script = """import sys
from kdh.customer_server import create_customer_app
account,email=sys.argv[1:]
assert email.startswith('workspace-ui-') and email.endswith('@example.invalid')
app=create_customer_app(); store=app.extensions['store']
assert store.one('SELECT id FROM customer_accounts WHERE id=? AND email=?',(account,email))
store.execute('UPDATE customer_accounts SET email_verified=1 WHERE id=? AND email=?',(account,email))
print('QA verification fixture applied')
"""
    result = subprocess.run(['docker','exec','VioAgencyAnalytics-Customer-Admin','python','-c',script,account_id,email],capture_output=True,text=True)
    assert result.returncode == 0, result.stderr[-600:]


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    errors, external, results = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
        owner_context = browser.new_context(viewport={'width':1440,'height':1000})
        other_context = browser.new_context(viewport={'width':1440,'height':1000})
        owner, other = owner_context.new_page(), other_context.new_page()
        for page in (owner,other):
            page.on('pageerror',lambda error: errors.append(str(error)))
            page.on('request',lambda r: external.append(r.url) if not r.url.startswith(ORIGIN+'/') else None)

        def register(page, suffix):
            email = f'workspace-ui-{suffix.lower()}-{time.time_ns()}@example.invalid'
            page.goto(ORIGIN+'/workspace/login'); page.locator('#auth-fields:not([disabled])').wait_for()
            page.locator('[data-mode=register]').click(); page.locator('#name-field input').fill('QA '+suffix)
            page.locator('#identity-auth-form [name=email]').fill(email); page.locator('#auth-password').fill(secrets.token_urlsafe(24)); page.locator('#auth-submit').click()
            page.wait_for_url('**/workspace/onboarding'); page.locator('#workspace-fields:not([disabled])').wait_for()
            return email, page.request.get(ORIGIN+'/api/customer/session').json()['user']['id']

        def post(page, path, payload):
            csrf = page.request.get(ORIGIN+'/api/customer/session').json()['csrf']
            return page.request.post(ORIGIN+path,data=payload,headers={'Origin':ORIGIN,'X-CSRF-Token':csrf})

        def skip_tour(page):
            page.locator('#product-tour[open]').wait_for(); page.locator('#tour-skip:not([disabled])').click()
            page.locator('#product-tour:not([open])').wait_for(state='attached')

        def ready(page):
            page.locator('#workspace-page-select:not([disabled])').wait_for()

        owner_email, owner_id = register(owner,'Owner')
        owner.locator('#workspace-form [name=name]').fill('VIO Agency · QA Workspace')
        owner.locator('#step-next').click(); owner.locator('#workspace-form [name=first_client]').fill('QA Brand')
        owner.locator('#step-next').click(); owner.locator('#workspace-submit').click(); owner.wait_for_url('**/workspace'); skip_tour(owner)
        session = owner.request.get(ORIGIN+'/api/customer/session').json(); workspace_id=session['workspace']['id']
        base='/api/customer/workspaces/'+workspace_id
        owner.locator('#nav-members').click(); owner.wait_for_url('**/workspace/members'); ready(owner)
        owner.keyboard.press('Control+k'); owner.locator('#workspace-search-input').fill('Cai dat Workspace')
        owner.locator('#workspace-search-results a[href="/workspace/settings"]').click(); ready(owner)
        owner.locator('#nav-members').click(); ready(owner)
        assert owner.locator('#members-active-count').inner_text()=='1'
        assert owner.locator('#members-verification').is_visible()
        assert owner.locator('[data-open-invite]').first.is_disabled()
        verify_qa(owner_id,owner_email)
        owner.locator('#workspace-page-refresh').click(); ready(owner)
        assert not owner.locator('#members-verification').is_visible()
        other_email, other_id = register(other,'Member'); verify_qa(other_id,other_email)
        owner.locator('[data-open-invite]').first.click(); owner.locator('#invite-email').fill(other_email)
        owner.locator('#invite-role').select_option('member'); owner.locator('#invite-submit').click()
        owner.locator('#invite-result:not([hidden])').wait_for()
        code=owner.locator('#invite-code').input_value()
        assert code and len(code)>40
        owner.locator('#invite-dialog [data-close-dialog]').first.click()
        assert owner.locator('#invite-code').input_value()==''
        other.locator('#join-form [name=invitation_code]').fill(code); other.locator('#join-submit').click()
        other.wait_for_url('**/workspace'); skip_tour(other)
        other.goto(ORIGIN+'/workspace/members'); ready(other)
        assert other.locator('[data-open-invite]').first.is_disabled()
        assert other.locator('#members-tab-events').is_disabled()
        assert other.request.get(ORIGIN+base+'/members').json()['invitations']==[]
        owner.locator('#workspace-page-refresh').click(); ready(owner)
        target=owner.locator(f'[data-member-id="{other_id}"]')
        target.get_by_role('button',name='Đổi vai trò').click()
        owner.locator('#member-new-role').select_option('viewer'); owner.locator('#member-editor-save').click()
        owner.locator('#member-editor:not([open])').wait_for(state='attached'); ready(owner)
        assert 'Người xem' in target.inner_text()
        other.goto(ORIGIN+'/workspace/settings'); ready(other)
        assert other.locator('#settings-permission-note').is_visible()
        assert other.locator('#settings-name').is_disabled()
        assert post(other,base+'/settings',{}).status==422  # Schema rejection does not authorize a write.
        valid=owner.request.get(ORIGIN+base+'/settings').json()
        payload={**{k:valid['workspace'][k] for k in ('name','website','country','timezone','currency')},**{k:v for k,v in valid['profile'].items() if k!='updated_at'}}
        assert post(other,base+'/settings',payload).status==403
        owner.locator('#members-search').fill('no-such-person'); assert owner.locator('#members-no-results').is_visible()
        owner.locator('#members-search').fill(''); owner.locator('#members-role').select_option('viewer')
        assert owner.locator('#members-rows tr').count()==1
        owner.locator('#members-role').select_option('all')
        owner.locator('[data-open-invite]').first.click(); owner.locator('#invite-email').fill(f'workspace-ui-pending-{time.time_ns()}@example.invalid')
        owner.locator('#invite-submit').click(); owner.locator('#invite-result:not([hidden])').wait_for(); owner.locator('#invite-dialog [data-close-dialog]').first.click()
        owner.locator('#members-tab-invitations').click()
        owner.locator('#invitations-rows button').click(); owner.locator('#workspace-confirm-accept').click(); ready(owner)
        owner.wait_for_function("document.querySelector('#members-invite-count').textContent==='0'")
        owner.locator('#members-tab-events').click(); assert owner.locator('#members-events li').count()>0
        owner.locator('#members-tab-members').click()
        assert owner.request.post(ORIGIN+base+'/members/'+other_id+'/remove',data={'version':2}).status==403
        assert not owner.evaluate('localStorage.length || sessionStorage.length')

        for width in (1440,1024,390):
            owner.set_viewport_size({'width':width,'height':1000 if width>700 else 844}); owner.evaluate('document.activeElement.blur(); scrollTo(0,0)'); owner.wait_for_timeout(80)
            assert not owner.evaluate('document.documentElement.scrollWidth>innerWidth'),('members',width)
            owner.screenshot(path=str(OUT/f'members-{width}.png'),full_page=True); owner.screenshot(path=str(OUT/f'members-{width}-viewport.png'))
            if width>700:
                owner.evaluate('scrollTo(0,document.body.scrollHeight)'); assert abs(owner.locator('.workspace-topbar').bounding_box()['y'])<2; assert abs(owner.locator('.ov-sidebar').bounding_box()['y'])<2
            results.append({'page':'members','width':width,'status':'PASS'})

        owner.goto(ORIGIN+'/workspace/settings'); ready(owner)
        owner.locator('#settings-name').fill('VIO Agency · QA Settings')
        owner.locator('[name=company_name]').fill('VIO Company')
        owner.locator('#settings-report-name').fill('QA <img src=x>')
        assert owner.locator('#preview-title img').count()==0
        owner.locator('#settings-accent').fill('#2563EB')
        owner.locator('.wa-period-options label').filter(has=owner.locator('input[value=last7]')).click()
        owner.locator('#settings-compare').uncheck()
        assert owner.locator('#settings-save-bar').is_visible()
        owner.keyboard.press('Control+s')
        owner.wait_for_function("document.querySelector('#workspace-page-status').textContent.includes('Đã lưu cài đặt')")
        assert owner.locator('#settings-save').is_disabled()
        assert owner.request.get(ORIGIN+base+'/settings').json()['profile']['default_period']=='last7'
        owner.goto(ORIGIN+'/workspace/dashboard'); owner.locator('#marketing-client:not([disabled])').wait_for()
        assert owner.locator('#marketing-period').input_value()=='last7'
        assert owner.locator('#marketing-comparison').input_value()=='none'
        owner.goto(ORIGIN+'/workspace'); owner.locator('#overview-logout:not([disabled])').wait_for()
        assert owner.locator('#overview-period').input_value()=='last7'
        assert owner.locator('#overview-comparison').is_hidden()
        owner.goto(ORIGIN+'/workspace/settings'); ready(owner)
        owner.locator('#settings-name').fill('Draft unsaved')
        owner.locator('#nav-members').click(); owner.locator('#workspace-confirm[open]').wait_for()
        owner.locator('#workspace-confirm-cancel').click(); assert owner.locator('#settings-name').input_value()=='Draft unsaved'
        current=owner.request.get(ORIGIN+base+'/settings').json()
        payload={**{k:current['workspace'][k] for k in ('name','website','country','timezone','currency')},**{k:v for k,v in current['profile'].items() if k!='updated_at'},'company_name':'Updated elsewhere'}
        assert post(owner,base+'/settings',payload).status==200
        owner.locator('#settings-save').click()
        owner.wait_for_function("document.querySelector('#workspace-page-status').textContent.includes('đối chiếu')")
        assert owner.locator('#settings-name').input_value()=='Draft unsaved'
        owner.locator('#workspace-page-refresh').click(); owner.locator('#workspace-confirm-accept').click(); ready(owner)
        assert owner.locator('[name=company_name]').input_value()=='Updated elsewhere'
        assert owner.locator('#settings-name').input_value()=='VIO Agency · QA Settings'
        for width in (1440,1024,390):
            owner.set_viewport_size({'width':width,'height':1000 if width>700 else 844}); owner.evaluate('document.activeElement.blur(); scrollTo(0,0)'); owner.wait_for_timeout(80)
            assert not owner.evaluate('document.documentElement.scrollWidth>innerWidth'),('settings',width)
            if width<=700:
                assert owner.locator('#company-title').bounding_box()['width']>180
            owner.screenshot(path=str(OUT/f'settings-{width}.png'),full_page=True); owner.screenshot(path=str(OUT/f'settings-{width}-viewport.png'))
            results.append({'page':'settings','width':width,'status':'PASS'})
        owner.goto(ORIGIN+'/workspace/members'); ready(owner)
        owner.locator(f'[data-member-id="{other_id}"]').get_by_role('button',name='Thu hồi',exact=True).click(); owner.locator('#workspace-confirm-accept').click(); ready(owner)
        assert other.request.get(ORIGIN+base+'/members').status==404
        assert other.request.get(ORIGIN+base+'/settings').status==404
        assert other.request.get(ORIGIN+'/api/customer/session').json()['workspace'] is None
        second = post(owner,'/api/customer/workspaces',{'name':'QA Workspace B','kind':'agency','website':'','country':'VN','timezone':'Asia/Ho_Chi_Minh','currency':'VND','first_client':'','request_key':secrets.token_hex(16)})
        assert second.status==200
        second_id=second.json()['workspace']['id']
        assert owner.request.get(ORIGIN+base+'/members').status==409
        assert owner.request.get(ORIGIN+base+'/settings').status==409
        assert post(owner,base+'/select',{}).status==200
        owner.goto(ORIGIN+'/workspace/settings'); ready(owner)
        owner.locator('#settings-name').fill('Unsaved scope draft')
        owner.locator('#workspace-page-select').select_option(second_id)
        owner.locator('#workspace-confirm-cancel').click()
        assert owner.locator('#workspace-page-select').input_value()==workspace_id
        assert owner.locator('#settings-name').input_value()=='Unsaved scope draft'
        owner.locator('#workspace-page-select').select_option(second_id)
        owner.locator('#workspace-confirm-accept').click()
        owner.wait_for_function('(id) => document.querySelector("#workspace-page-select").value===id && !document.querySelector("#settings-name").disabled',arg=second_id)
        assert owner.locator('#settings-name').input_value()=='QA Workspace B'
        assert owner.locator('#settings-report-name').input_value()==''
        owner.locator('#workspace-page-logout').click(); owner.wait_for_url('**/workspace/login')
        browser.close()
    assert not errors,errors
    assert not external,external
    report={'results':results,'javascript_errors':errors,'external_requests':external,'authorization_and_persistence':'PASS'}
    (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    run()
