"""Header search and sticky navigation on live customer Docker; QA tenant only."""
import json
from pathlib import Path
import secrets
import time

from playwright.sync_api import sync_playwright

ORIGIN = 'http://127.0.0.1:8084'
OUT = Path(__file__).resolve().parents[1] / '.work/customer-shell-qa'


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    errors, results = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
        context = browser.new_context(viewport={'width': 1440, 'height': 960})
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(ORIGIN + '/workspace/login')
        page.locator('#auth-fields:not([disabled])').wait_for()
        page.locator('[data-mode=register]').click()
        page.locator('#name-field input').fill('QA Header')
        page.locator('#identity-auth-form [name=email]').fill(f'header-qa-{time.time_ns()}@example.invalid')
        page.locator('#auth-password').fill(secrets.token_urlsafe(24))
        page.locator('#auth-submit').click()
        page.wait_for_url('**/workspace/onboarding')
        page.locator('#workspace-fields:not([disabled])').wait_for()
        page.locator('#workspace-form [name=name]').fill('QA Workspace Header')
        page.locator('#step-next').click()
        page.locator('#workspace-form [name=first_client]').fill('Khách hàng Alpha')
        page.locator('#step-next').click(); page.locator('#workspace-submit').click()
        page.wait_for_url('**/workspace')
        page.locator('#product-tour[open]').wait_for()
        page.locator('#tour-skip:not([disabled])').click()
        page.locator('#product-tour:not([open])').wait_for(state='attached')
        session = page.request.get(ORIGIN + '/api/customer/session').json()
        workspace_id = session['workspace']['id']
        base = f'/api/customer/workspaces/{workspace_id}'

        def post(path, data):
            csrf = page.request.get(ORIGIN + '/api/customer/session').json()['csrf']
            response = page.request.post(ORIGIN + path, data=data, headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf})
            assert response.status == 200, (path, response.status, response.text())
            return response.json()

        post(base + '/clients', {'name': 'QA <img src=x onerror=alert(1)>', 'website': '', 'request_key': secrets.token_hex(16)})
        post('/api/customer/workspaces', {'name': 'QA Other Workspace', 'kind': 'agency', 'website': '',
             'country': 'VN', 'timezone': 'Asia/Ho_Chi_Minh', 'currency': 'VND',
             'first_client': 'Secret Other Workspace Client', 'request_key': secrets.token_hex(16)})
        post(base + '/select', {})
        for width, height in ((1440, 960), (390, 844), (1440, 600)):
            page.set_viewport_size({'width': width, 'height': height})
            page.goto(ORIGIN + '/workspace')
            page.locator('#overview-logout:not([disabled])').wait_for()
            page.evaluate('scrollTo(0, document.documentElement.scrollHeight)')
            page.wait_for_function('scrollY > 0')
            page.wait_for_timeout(150)
            assert abs(page.locator('.workspace-topbar').bounding_box()['y']) < 2
            if width > 700:
                rect = page.locator('.ov-sidebar').bounding_box()
                assert abs(rect['y']) < 2 and abs(rect['height'] - height) < 2, rect
                assert page.locator('.ov-sidebar').evaluate('(el) => getComputedStyle(el).overflowY') == 'auto'
                page.locator('#nav-settings').click()
                page.wait_for_url('**/workspace/settings')
                page.locator('#settings-name:not([disabled])').wait_for()
                page.goto(ORIGIN + '/workspace')
                page.locator('#overview-logout:not([disabled])').wait_for()
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            page.screenshot(path=str(OUT / f'overview-scrolled-{width}-{height}.png'))
            page.keyboard.press('Control+k')
            page.locator('#workspace-search-dialog[open]').wait_for()
            page.wait_for_function("!document.querySelector('#workspace-search-results').getAttribute('aria-busy').includes('true')")
            assert page.locator('#workspace-search-input').evaluate('(el) => el === document.activeElement')
            page.locator('#workspace-search-input').fill('secret other')
            assert page.locator('.wh-result').count() == 0
            page.locator('#workspace-search-input').fill('<img')
            assert page.locator('.wh-result').count() == 1
            assert page.locator('#workspace-search-results img').count() == 0
            page.locator('#workspace-search-input').fill('khach hang alpha')
            assert page.locator('.wh-result').count() == 1
            page.keyboard.press('ArrowDown'); page.keyboard.press('Enter')
            page.wait_for_url('**/workspace')
            page.wait_for_function("document.querySelector('#selected-client-summary')?.textContent.includes('Alpha')")
            page.locator('#workspace-search-open').click()
            page.wait_for_function("document.querySelector('#workspace-search-results').getAttribute('aria-busy') === 'false'")
            page.locator('#workspace-search-input').fill('ga4')
            assert page.locator('.wh-result').count() == 1
            page.screenshot(path=str(OUT / f'search-{width}-{height}.png'))
            page.keyboard.press('Enter')
            page.wait_for_url('**/workspace/integrations?platform=ga4')
            page.locator('#integrations-logout:not([disabled])').wait_for()
            assert page.locator('[data-platform]:visible').count() == 1
            assert page.locator('[data-platform=ga4]').is_visible()
            page.evaluate('scrollTo(0, document.documentElement.scrollHeight)')
            page.wait_for_timeout(150)
            assert abs(page.locator('.workspace-topbar').bounding_box()['y']) < 2
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            page.locator('#workspace-help').click()
            page.locator('#integration-dialog[open]').wait_for()
            page.keyboard.press('Escape')
            page.locator('#workspace-search-open').click()
            page.locator('#workspace-search-dialog[open]').wait_for()
            page.keyboard.press('Escape')
            assert page.locator('#workspace-search-open').evaluate('(el) => el === document.activeElement')
            assert not page.evaluate('localStorage.length || sessionStorage.length')
            results.append({'width': width, 'height': height, 'status': 'PASS'})
        context.close(); browser.close()
    assert not errors, errors
    (OUT / 'result.json').write_text(json.dumps({'results': results, 'js_errors': errors}), encoding='utf-8')
    print(json.dumps({'results': results, 'js_errors': errors}))


if __name__ == '__main__':
    run()
