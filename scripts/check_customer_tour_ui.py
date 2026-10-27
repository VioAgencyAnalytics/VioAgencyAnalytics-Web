"""Live local account/workspace/tour acceptance. Creates named QA users, sends no email."""
import json
from pathlib import Path
import secrets
import time

from playwright.sync_api import sync_playwright

ORIGIN = 'http://127.0.0.1:8084'
OUT = Path(__file__).resolve().parents[1] / '.work' / 'customer-tour-qa'


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
        for width in (1440, 390):
            print(f'Checking viewport {width}', flush=True)
            context = browser.new_context(viewport={'width':width,'height':960 if width > 700 else 844})
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            email = f'tour-qa-{width}-{time.time_ns()}@example.invalid'
            password = secrets.token_urlsafe(24)
            page.goto(ORIGIN + '/workspace')
            page.wait_for_url('**/workspace/login')
            page.locator('#auth-fields:not([disabled])').wait_for()
            page.locator('[data-mode=register]').click()
            page.locator('#name-field input').fill('QA Tour')
            page.locator('#identity-auth-form [name=email]').fill(email)
            page.locator('#auth-password').fill(password)
            page.locator('#auth-submit').click()
            page.wait_for_url('**/workspace/onboarding')
            page.locator('#workspace-fields:not([disabled])').wait_for()
            page.locator('#workspace-form [name=name]').fill(f'QA Tour {width}')
            page.locator('#step-next').click()
            page.locator('#workspace-form [name=first_client]').fill('QA Brand')
            page.locator('#step-next').click()
            page.locator('#workspace-submit').click()
            page.wait_for_url('**/workspace')
            page.locator('#product-tour[open]').wait_for()
            page.wait_for_function("!document.querySelector('#tour-next').disabled")
            assert page.locator('#tour-counter').inner_text() == 'BƯỚC 1 / 8'
            assert page.evaluate('Object.keys(localStorage).length + Object.keys(sessionStorage).length') == 0
            cookie = next(c for c in context.cookies() if c['name'] == 'vio_customer_session')
            assert cookie['httpOnly']
            page.locator('#tour-highlight').click()
            page.wait_for_function("document.querySelector('#tour-counter').textContent.includes('2 / 8')")
            page.keyboard.press('Escape')
            page.locator('#product-tour:not([open])').wait_for(state='attached')
            page.reload()
            page.wait_for_function("document.querySelector('#tour-summary').textContent.includes('2/8')")
            assert not page.locator('#product-tour').is_visible()
            page.locator('.ov-heading [data-start-tour]').click()
            print(f'Resuming saved tour at {width}', flush=True)
            try:
                page.locator('#product-tour[open]').wait_for(timeout=10000)
            except Exception:
                print(json.dumps({'status':page.locator('#overview-status').text_content(),'errors':errors}), flush=True)
                page.screenshot(path=str(OUT / 'resume-error.png'), full_page=True)
                raise
            page.locator('#tour-back').click()
            page.wait_for_function("document.querySelector('#tour-counter').textContent.includes('1 / 8')")
            for step in range(8):
                print(f'Tour {width}: step {step + 1}', flush=True)
                page.wait_for_function('(step) => document.querySelector("#tour-counter").textContent === `BƯỚC ${step + 1} / 8` && !document.querySelector("#tour-next").disabled', arg=step)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'overflow {width}/{step}'
                for selector in ('#tour-tooltip', '#tour-highlight'):
                    rect = page.locator(selector).bounding_box()
                    assert rect and rect['x'] >= 0 and rect['y'] >= 0, (width, step, selector, rect)
                    assert rect['x'] + rect['width'] <= width + 1, (width, step, rect)
                page.screenshot(path=str(OUT / f'tour-{width}-{step+1}.png'))
                page.locator('#tour-next').click()
            page.locator('#product-tour:not([open])').wait_for(state='attached')
            page.reload()
            page.wait_for_function("document.querySelector('#tour-summary').textContent.includes('Đã xem xong')")
            assert not page.locator('#product-tour').is_visible()
            page.screenshot(path=str(OUT / f'overview-{width}.png'), full_page=True)
            info = page.request.get(ORIGIN + '/api/customer/session').json()
            detail = page.request.get(ORIGIN + '/api/customer/workspaces/' + info['workspace']['id']).json()
            assert detail['tour']['status'] == 'completed' and detail['tour']['step'] == 7
            assert detail['clients'][0]['name'] == 'QA Brand'
            denied = page.request.post(ORIGIN + '/api/customer/workspaces/' + info['workspace']['id'] + '/tour', data={'version':1,'step':0,'status':'active'})
            assert denied.status == 403
            page.locator('#nav-settings').click()
            page.locator('#feature-dialog[open]').wait_for()
            assert f'QA Tour {width}' in page.locator('#workspace-settings').inner_text()
            page.keyboard.press('Escape')
            page.locator('.ov-heading [data-start-tour]').click()
            page.wait_for_function("document.querySelector('#tour-counter').textContent.includes('1 / 8') && document.querySelector('#product-tour').open")
            page.locator('#tour-skip').click()
            page.locator('#product-tour:not([open])').wait_for(state='attached')
            page.locator('#overview-logout').click()
            page.wait_for_url('**/workspace/login')
            page.locator('#auth-fields:not([disabled])').wait_for()
            page.locator('#identity-auth-form [name=email]').fill(email)
            page.locator('#auth-password').fill(password)
            page.locator('#auth-submit').click()
            page.wait_for_url('**/workspace/onboarding')
            page.locator('.identity-workspace-option').click()
            page.wait_for_url('**/workspace')
            page.wait_for_function("document.querySelector('#tour-summary').textContent.includes('1/8')")
            assert not page.locator('#product-tour').is_visible()
            results.append({'width':width,'workspace_id':info['workspace']['id'],'tour':'passed'})
            context.close()
        browser.close()
    assert not errors, errors
    (OUT / 'result.json').write_text(json.dumps({'results':results,'errors':errors}), encoding='utf-8')
    print(json.dumps({'passed':len(results),'javascript_errors':errors}))


if __name__ == '__main__':
    run()
