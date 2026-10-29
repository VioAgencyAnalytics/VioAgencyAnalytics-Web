"""Typography QA: one isolated account, no mail or provider requests."""
import json
from pathlib import Path
import secrets
import sys
import time

from playwright.sync_api import sync_playwright

ORIGIN = 'http://127.0.0.1:8084'
OUT = Path(__file__).resolve().parents[1] / '.work/customer-typography-qa'
NAME = 'Tài khoản dùng thử VIO'


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    results, errors, external, failures = [], [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        )
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        if '--local-styles' in sys.argv:
            def local_css(route):
                path = Path(__file__).resolve().parents[1] / 'static/css/customer' / route.request.url.rsplit('/', 1)[-1]
                if path.is_file():
                    route.fulfill(path=str(path), content_type='text/css; charset=utf-8')
                else:
                    route.continue_()
            context.route(ORIGIN + '/static/css/customer/*.css', local_css)
            context.route(ORIGIN + '/static/js/customer/shell.js', lambda r: r.fulfill(
                path=str(Path(__file__).resolve().parents[1] / 'static/js/customer/shell.js'),
                content_type='application/javascript; charset=utf-8'))
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda r: external.append(r.url) if not r.url.startswith(ORIGIN + '/') else None)
        page.goto(ORIGIN + '/workspace/login')
        page.locator('#auth-fields:not([disabled])').wait_for()
        for width in (1440, 390):
            page.set_viewport_size({'width': width, 'height': 1000 if width > 700 else 844})
            assert page.locator('#auth-password').evaluate('(el) => getComputedStyle(el).fontSize') == '16px'
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            page.screenshot(path=str(OUT / f'login-{width}.png'), full_page=True)
            results.append({'page': 'login', 'width': width, 'status': 'PASS'})
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.locator('[data-mode=register]').click()
        page.locator('#name-field input').fill(NAME)
        page.locator('#identity-auth-form [name=email]').fill(f'typography-ui-{time.time_ns()}@example.invalid')
        page.locator('#auth-password').fill(secrets.token_urlsafe(24))
        page.locator('#auth-submit').click()
        page.wait_for_url('**/workspace/onboarding')
        page.locator('#workspace-fields:not([disabled])').wait_for()
        for width in (1440, 390):
            page.set_viewport_size({'width': width, 'height': 1000 if width > 700 else 844})
            assert page.locator('#workspace-form [name=name]').evaluate('(el) => getComputedStyle(el).fontSize') == '16px'
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            page.screenshot(path=str(OUT / f'onboarding-{width}.png'), full_page=True)
            results.append({'page': 'onboarding', 'width': width, 'status': 'PASS'})
        page.set_viewport_size({'width': 1440, 'height': 1000})
        assert page.request.get(ORIGIN + '/api/customer/session').json()['user']['name'] == NAME
        page.locator('#workspace-form [name=name]').fill('VIO · Kiểm tra tiếng Việt')
        page.locator('#step-next').click()
        page.locator('#workspace-form [name=first_client]').fill('Thương hiệu Việt')
        page.locator('#step-next').click()
        page.locator('#workspace-submit').click()
        page.wait_for_url('**/workspace')
        page.locator('#product-tour[open]').wait_for()
        page.locator('#tour-skip:not([disabled])').click()
        page.locator('#product-tour:not([open])').wait_for(state='attached')

        routes = (
            ('overview', '/workspace', '#overview-workspace-select'),
            ('integrations', '/workspace/integrations', '#integration-workspace-select'),
            ('dashboard', '/workspace/dashboard', '#marketing-client'),
            ('members', '/workspace/members', '#workspace-page-select'),
            ('settings', '/workspace/settings', '#workspace-page-select'),
        )
        for name, route, ready in routes:
            page.goto(ORIGIN + route)
            page.locator(ready + ':not([disabled])').wait_for()
            page.evaluate('document.fonts.ready')
            assert page.locator('.od-side-account strong').inner_text() == NAME
            for width in (1440, 1024, 390):
                page.set_viewport_size({'width': width, 'height': 1000 if width > 700 else 844})
                page.evaluate('document.activeElement.blur(); scrollTo(0, 0)')
                page.wait_for_timeout(120)
                metrics = page.evaluate("""() => {
                    const small = [];
                    for (const el of document.querySelectorAll('body *')) {
                        if (el.matches('script,style,.material-symbols-outlined') || el.closest('[aria-hidden=true]')) continue;
                        if (!Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim())) continue;
                        const cs = getComputedStyle(el), r = el.getBoundingClientRect();
                        if (!r.width || !r.height || cs.visibility === 'hidden' || r.width <= 1) continue;
                        if (parseFloat(cs.fontSize) < 12) small.push({tag: el.tagName, cls: el.className, size: cs.fontSize});
                    }
                    const side = document.querySelector('.od-side-account strong');
                    return {width: innerWidth, scroll: document.documentElement.scrollWidth, small,
                        nameSize: getComputedStyle(side).fontSize,
                        nameVisible: side.scrollWidth <= side.clientWidth + 1,
                        inputSizes: Array.from(document.querySelectorAll('main input:not([type=checkbox]):not([type=radio]):not([type=color]),main select'))
                            .filter(e => e.getBoundingClientRect().width > 1)
                            .map(e => getComputedStyle(e).fontSize)};
                }""")
                problems = []
                if metrics['scroll'] > width:
                    problems.append({'overflow': metrics['scroll']})
                if metrics['small']:
                    problems.append({'undersized': metrics['small']})
                if not all(float(size[:-2]) >= 16 for size in metrics['inputSizes']):
                    problems.append({'form_text': metrics['inputSizes']})
                if width > 700:
                    if metrics['nameSize'] != '14px' or not metrics['nameVisible']:
                        problems.append({'account': metrics})
                    footer = page.locator('.od-side-account').bounding_box()
                    if footer['y'] + footer['height'] > 1001:
                        problems.append({'account_offscreen': footer})
                    nav = page.locator('.ov-nav').bounding_box()
                    active = page.locator('.ov-nav [aria-current=page]').bounding_box()
                    assert active['y'] >= nav['y'] - 1 and active['y'] + active['height'] <= nav['y'] + nav['height'] + 1
                    page.evaluate('scrollTo(0, document.body.scrollHeight)')
                    assert abs(page.locator('.workspace-topbar').bounding_box()['y']) < 2
                    assert abs(page.locator('.ov-sidebar').bounding_box()['y']) < 2
                    page.evaluate('scrollTo(0,0)')
                page.screenshot(path=str(OUT / f'{name}-{width}.png'), full_page=True)
                page.screenshot(path=str(OUT / f'{name}-{width}-viewport.png'))
                result = {'page': name, 'width': width, 'status': 'FAIL' if problems else 'PASS'}
                if problems:
                    result['problems'] = problems
                    failures.append(result)
                results.append(result)

        # Search and dialogs use the same scale; no invitation/email is sent.
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.keyboard.press('Control+k')
        page.locator('#workspace-search-input').fill('Thành viên')
        page.locator('#workspace-search-results a[href="/workspace/members"]').click()
        page.locator('#workspace-page-select:not([disabled])').wait_for()
        assert not errors, errors
        assert not external, external
        context.close()
        browser.close()
    report = {'results': results, 'javascript_errors': errors, 'external_requests': external}
    (OUT / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))
    assert not failures, f'{len(failures)} typography/layout checks failed; see result.json'


if __name__ == '__main__':
    run()
