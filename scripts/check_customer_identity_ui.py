"""Browser acceptance against the isolated customer development stack (8084).

Creates distinctly named QA accounts/workspaces in that local database.
Screenshots and results are private under .work/customer-identity-qa.
"""
import json
from pathlib import Path
import secrets
import time

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.work' / 'customer-identity-qa'
ORIGIN = 'http://127.0.0.1:8084'


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    errors, results, accounts = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
        for label, width, height in [('desktop',1440,1000),('mobile',390,844)]:
            context = browser.new_context(viewport={'width':width,'height':height})
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            def capture(name):
                page.evaluate('document.fonts.ready')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), name + ' horizontal overflow'
                page.screenshot(path=str(OUT / f'{label}-{name}.png'), full_page=True)
            page.goto(ORIGIN + '/workspace/onboarding')
            page.wait_for_url('**/workspace/login')
            page.locator('#auth-fields:not([disabled])').wait_for()
            capture('login')
            capabilities = page.request.get(ORIGIN + '/api/customer/session').json()['capabilities']
            assert page.locator('#google-login').is_enabled() == capabilities['google']
            page.locator('#forgot-password').click()
            if capabilities['email_delivery']:
                assert page.locator('#email-action-form').is_visible()
                page.locator('#back-to-login').click()
                page.locator('#auth-fields:not([disabled])').wait_for()
            else:
                assert 'chưa khả dụng' in page.locator('#identity-status').inner_text()
            page.locator('[data-mode=register]').click()
            email = f'customer-qa-{label}-{int(time.time())}@example.invalid'
            password = secrets.token_urlsafe(22)
            page.locator('#name-field input').fill('Kiểm thử ' + label)
            page.locator('#identity-auth-form [name=email]').fill(email)
            page.locator('#auth-password').fill(password)
            capture('register')
            page.locator('#auth-submit').click()
            page.wait_for_url('**/workspace/onboarding')
            page.locator('#workspace-fields:not([disabled])').wait_for()
            capture('onboarding')
            assert page.evaluate('Object.keys(localStorage).length + Object.keys(sessionStorage).length') == 0
            info = page.request.get(ORIGIN + '/api/customer/session').json()
            accounts.append(info['user']['id'])
            cookies = context.cookies()
            session_cookie = next(cookie for cookie in cookies if cookie['name'] == 'vio_customer_session')
            assert session_cookie['httpOnly'] and session_cookie['sameSite'] == 'Lax'
            assert 'vio_customer_session' not in page.evaluate('document.cookie')
            page.locator('#workspace-form [name=name]').fill('QA Workspace ' + label)
            page.locator('#workspace-form [name=website]').fill('https://example.invalid')
            page.locator('#workspace-form [name=kind][value=business]').check()
            page.locator('#step-next').click()
            page.locator('#workspace-form [name=first_client]').fill('QA Thương hiệu ' + label)
            page.locator('#step-next').click()
            assert 'QA Workspace ' + label in page.locator('#workspace-review').inner_text()
            capture('review')
            page.locator('#workspace-submit').click()
            page.wait_for_url('**/workspace')
            page.locator('#product-tour[open]').wait_for()
            page.locator('#tour-skip').click()
            page.locator('#product-tour:not([open])').wait_for(state='attached')
            info = page.request.get(ORIGIN + '/api/customer/session').json()
            assert len(info['workspaces']) == 1
            workspace_id = info['workspace']['id']
            assert info['workspace']['role'] == 'owner'
            page.reload()
            page.locator('.ov-heading').wait_for()
            assert 'QA Workspace ' + label in page.locator('.ov-heading h1').inner_text()
            assert 'QA Thương hiệu ' + label in page.locator('#client-card').inner_text()
            capture('saved')
            page.locator('#overview-logout').click()
            page.wait_for_url('**/workspace/login')
            page.locator('#auth-fields:not([disabled])').wait_for()
            assert page.request.get(ORIGIN + '/api/customer/session').json()['user'] is None
            page.locator('#identity-auth-form [name=email]').fill(email)
            page.locator('#auth-password').fill('wrong-password')
            page.locator('#auth-submit').click()
            page.wait_for_function("document.querySelector('#identity-status').textContent.length > 0")
            assert 'không đúng' in page.locator('#identity-status').inner_text(), page.locator('#identity-status').inner_text()
            capture('login-error')
            page.locator('#auth-password').fill(password)
            page.locator('#auth-submit').click()
            page.wait_for_url('**/workspace/onboarding')
            page.locator('#workspace-fields:not([disabled])').wait_for()
            page.locator('.identity-workspace-option').click()
            page.wait_for_url('**/workspace')
            page.locator('.ov-heading').wait_for()
            current = page.request.get(ORIGIN + '/api/customer/session').json()
            assert current['workspace']['id'] == workspace_id
            assert len(current['workspaces']) == 1
            denied = page.request.post(ORIGIN + '/api/customer/workspaces', data={'name':'attack'})
            assert denied.status == 403
            results.append({'viewport':label,'account_id':info['user']['id'],'workspace_id':workspace_id,'checks':'signup, logout, login, create, reload, select, cookie, CSRF, layout'})
            context.close()
        browser.close()
    assert not errors, errors
    (OUT / 'result.json').write_text(json.dumps({'results':results,'errors':errors,'qa_account_ids':accounts}, indent=2), encoding='utf-8')
    print(json.dumps({'passed':len(results),'screenshots':len(list(OUT.glob('*.png'))),'javascript_errors':errors}))


if __name__ == '__main__':
    run()
