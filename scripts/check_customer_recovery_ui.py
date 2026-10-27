"""Browser checks of recovery UI with mocked account APIs; never sends real email."""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ORIGIN = 'http://127.0.0.1:8084'
OUT = Path(__file__).resolve().parents[1] / '.work' / 'customer-recovery-qa'


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
        for width in (1440, 390):
            context = browser.new_context(viewport={'width': width, 'height': 960})
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            calls = []
            state = {'expired': False, 'outage': False, 'limited': False}

            def api(route):
                path = route.request.url.split('/api/customer/')[1]
                body = route.request.post_data_json if route.request.method == 'POST' else None
                calls.append((path, body))
                code = 200
                if path == 'session':
                    data = {'user': None, 'csrf': 'qa-csrf', 'capabilities': {'google': True, 'email_delivery': True}}
                elif path == 'auth/email/reset':
                    code = 503 if state['outage'] else 429 if state['limited'] else 200
                    data = {'error': 'Dịch vụ email tạm thời không khả dụng.'} if state['outage'] else {'error': 'Vui lòng chờ trước khi gửi lại.'} if state['limited'] else {'message': 'Nếu tài khoản phù hợp, hướng dẫn sẽ được gửi đến email của bạn.'}
                elif path == 'auth/email/confirm':
                    code = 400 if state['expired'] else 200
                    data = {'error': 'Liên kết đã hết hạn hoặc đã được sử dụng.', 'code': 'email_token'} if state['expired'] else {'message': 'Đã đặt lại mật khẩu. Vui lòng đăng nhập lại.'}
                else:
                    raise AssertionError('Unexpected API: ' + path)
                route.fulfill(status=code, json=data)

            page.route('**/api/customer/**', api)
            page.goto(ORIGIN + '/workspace/login')
            page.locator('#auth-fields:not([disabled])').wait_for()
            page.locator('#identity-auth-form [name=email]').fill('qa@example.test')
            page.locator('#forgot-password').click()
            assert page.locator('#recovery-email-label input').input_value() == 'qa@example.test'
            state['outage'] = True
            page.locator('#email-action-submit').click()
            page.wait_for_function("document.querySelector('#identity-status').textContent.includes('tạm thời')")
            assert page.locator('#recovery-email-label input').input_value() == 'qa@example.test'
            state['outage'] = False
            page.locator('#email-action-submit').click()
            page.locator('#email-sent:visible').wait_for()
            page.screenshot(path=str(OUT / f'sent-{width}.png'), full_page=True)
            page.locator('#recovery-retry').click()
            state['limited'] = True
            page.locator('#recovery-email-label input').fill('qa@example.test')
            page.locator('#email-action-submit').click()
            page.wait_for_function("document.querySelector('#identity-status').textContent.includes('chờ')")
            state['limited'] = False
            page.goto(ORIGIN + '/workspace/login#reset=qa-token')
            page.locator('#reset-password:visible').wait_for()
            assert '#' not in page.url
            page.locator('#reset-password').fill('New-password-123!')
            page.locator('#reset-password-confirm').fill('Mismatch-password-123!')
            page.locator('#email-action-submit').click()
            assert not any(path == 'auth/email/confirm' for path, _ in calls)
            assert page.locator('#reset-password-confirm').evaluate('(e) => !e.validity.valid')
            page.locator('#reset-password-confirm').fill('New-password-123!')
            page.locator('#toggle-reset-password').click()
            assert page.locator('#reset-password').get_attribute('type') == 'text'
            page.screenshot(path=str(OUT / f'reset-{width}.png'), full_page=True)
            page.locator('#email-action-submit').click()
            page.locator('#auth-main:visible').wait_for()
            assert 'Đã đặt lại mật khẩu' in page.locator('#identity-status').inner_text()
            confirms = [body for path, body in calls if path == 'auth/email/confirm']
            assert confirms == [{'kind': 'reset', 'token': 'qa-token', 'password': 'New-password-123!'}]
            state['expired'] = True
            page.goto(ORIGIN + '/workspace/login#reset=expired-token')
            page.locator('#reset-password:visible').fill('New-password-123!')
            page.locator('#reset-password-confirm').fill('New-password-123!')
            page.locator('#email-action-submit').click()
            page.locator('#request-new-reset:visible').wait_for()
            page.locator('#request-new-reset').click()
            assert page.locator('#recovery-email-label').is_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            context.close()
        browser.close()
    assert not errors, errors
    print(json.dumps({'viewports_passed': 2, 'javascript_errors': errors, 'email_transport': 'mocked; no email sent'}))


if __name__ == '__main__':
    run()
