"""Stitch overview acceptance. Synthetic analytics are browser-only QA, never stored."""
import csv
import io
import json
from pathlib import Path
import secrets
import time

from playwright.sync_api import sync_playwright

ORIGIN = 'http://127.0.0.1:8084'
OUT = Path(__file__).resolve().parents[1] / '.work/customer-overview-design'


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    errors, external, results = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: external.append(request.url) if not request.url.startswith(ORIGIN + '/') and not request.url.startswith('blob:') else None)
        page.goto(ORIGIN + '/workspace/login')
        page.locator('#auth-fields:not([disabled])').wait_for()
        page.locator('[data-mode=register]').click()
        page.locator('#name-field input').fill('QA Tổng quan')
        page.locator('#identity-auth-form [name=email]').fill(f'overview-design-{time.time_ns()}@example.invalid')
        page.locator('#auth-password').fill(secrets.token_urlsafe(24)); page.locator('#auth-submit').click()
        page.wait_for_url('**/workspace/onboarding')
        page.locator('#workspace-fields:not([disabled])').wait_for()
        page.locator('#workspace-form [name=name]').fill('VIO Agency · QA Design')
        page.locator('#step-next').click()
        page.locator('#workspace-form [name=first_client]').fill('VIO Brand')
        page.locator('#step-next').click(); page.locator('#workspace-submit').click()
        page.wait_for_url('**/workspace')
        page.locator('#product-tour[open]').wait_for(); page.locator('#tour-skip:not([disabled])').click()
        page.locator('#product-tour:not([open])').wait_for(state='attached')
        page.locator('#overview-client-context:not([disabled])').wait_for()
        session = page.request.get(ORIGIN + '/api/customer/session').json()
        base = f"/api/customer/workspaces/{session['workspace']['id']}"
        detail = page.request.get(ORIGIN + base).json()
        alpha = detail['selected_client']['id']
        csrf = page.request.get(ORIGIN + '/api/customer/session').json()['csrf']
        reply = page.request.post(ORIGIN + base + '/clients', data={'name': '=SUM(1,2)', 'website': '', 'request_key': secrets.token_hex(16)}, headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf})
        assert reply.status == 200
        page.reload(); page.locator('#overview-client-context:not([disabled])').wait_for()
        assert page.locator('[data-kpi]').count() == 4
        assert page.locator('[data-source]').count() == 9
        assert all(value == '—' for value in page.locator('[data-kpi-value]').all_text_contents())
        # Validate future binding: real zero != null; gaps aren't turned into zero.
        assert page.evaluate("""() => {
          const c = VioOverview.getContext();
          const end = c.period.end;
          const d = new Date(end + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate()-1);
          const middle = d.toISOString().slice(0,10); d.setUTCDate(d.getUTCDate()-1);
          const start = d.toISOString().slice(0,10);
          return VioOverview.applySnapshot({...c, metrics: {
            spend: {status:'ready',value:0,previous:0},
            clicks: {status:'partial',value:null},
            conversions: {status:'empty',value:null}},
            trends: {spend: {status:'partial',points:[{date:start,value:0},{date:middle,value:null},{date:end,value:4}]}},
            reports:[{name:'QA <img src=x onerror=alert(1)>',status:'final',href:'javascript:alert(1)'}]});
        }""")
        assert page.locator('[data-kpi=spend] [data-kpi-value]').inner_text() != '—'
        assert page.locator('[data-kpi=clicks] [data-kpi-value]').inner_text() == '—'
        assert page.locator('#overview-trend-svg path').get_attribute('d').count('M') == 2
        assert page.locator('#overview-reports-list img').count() == 0
        assert page.locator('#overview-reports-list a').count() == 0
        assert not page.evaluate("() => VioOverview.applySnapshot({...VioOverview.getContext(), scope:{workspace_id:'foreign',client_id:'foreign'}})")
        assert not page.evaluate("() => VioOverview.applySnapshot({...VioOverview.getContext(),currency:'INVALID'})")
        assert not page.evaluate("() => VioOverview.applySnapshot({...VioOverview.getContext(),timezone:'UTC'})")
        with page.expect_download() as download:
            page.locator('#overview-export').click()
        content = Path(download.value.path()).read_text(encoding='utf-8-sig')
        rows = list(csv.reader(io.StringIO(content)))
        assert next(row for row in rows if row and row[0] == 'Khách hàng')[1].startswith("'=SUM")
        assert next(row for row in rows if row and row[0] == 'Tổng chi tiêu quảng cáo')[1] == '0'
        assert next(row for row in rows if row and row[0] == 'Lượt chuyển đổi (Conversions)')[1] == ''
        # A new period or client invalidates previous data immediately.
        old = page.evaluate('VioOverview.getContext()')
        page.locator('#overview-period').select_option('last7')
        assert '7 ngày' in page.locator('#overview-comparison').inner_text()
        assert all(value == '—' for value in page.locator('[data-kpi-value]').all_text_contents())
        assert not page.evaluate('(c) => VioOverview.applySnapshot(c)', old)
        page.locator('#overview-period').select_option('last30')
        page.evaluate("() => VioOverview.applySnapshot({...VioOverview.getContext(),metrics:{spend:{status:'ready',value:10}}})")
        # A failed selection restores the old context, clears data and rejects
        # any late response while a different client is being selected.
        def fail_selection(route):
            assert not page.evaluate("() => VioOverview.applySnapshot({...VioOverview.getContext(),metrics:{spend:{status:'ready',value:777}}})")
            route.fulfill(status=503, json={'error': 'QA selection failed'})
        page.route('**' + base + '/clients/' + alpha + '/select', fail_selection, times=1)
        page.locator('#overview-client-context').select_option(alpha)
        page.wait_for_function("document.querySelector('#overview-marketing-status').textContent.includes('QA selection failed')")
        assert page.locator('#overview-client-context').input_value() != alpha
        assert page.locator('[data-kpi=spend] [data-kpi-value]').inner_text() == '—'
        page.locator('#overview-client-context').select_option(alpha)
        page.wait_for_function('(id) => VioOverview.getContext().scope.client_id === id', arg=alpha)
        assert page.locator('[data-kpi=spend] [data-kpi-value]').inner_text() == '—'
        for width, height in ((1440, 1000), (1280, 900), (390, 844)):
            page.set_viewport_size({'width': width, 'height': height})
            page.evaluate('scrollTo(0,0)')
            page.locator('#overview-marketing-status').evaluate('(el) => el.hidden = true')
            page.screenshot(path=str(OUT / f'overview-{width}.png'), full_page=True)
            page.screenshot(path=str(OUT / f'viewport-{width}.png'))
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            page.locator('[data-trend=clicks]').click()
            assert page.locator('[data-trend=clicks]').get_attribute('aria-selected') == 'true'
            page.keyboard.press('ArrowRight')
            assert page.locator('[data-trend=conversions]').get_attribute('aria-selected') == 'true'
            page.locator('[data-trend=spend]').click()
            page.locator('.od-channel[data-overview-channel=facebook_ads]').click()
            page.locator('#feature-dialog[open]').wait_for()
            assert page.locator('#overview-feature-connect').is_visible()
            page.keyboard.press('Escape')
            page.locator('[data-feature=reports]').last.click()
            page.locator('#feature-dialog[open]').wait_for()
            assert not page.locator('#overview-feature-connect').is_visible()
            page.keyboard.press('Escape')
            page.evaluate('scrollTo(0,document.documentElement.scrollHeight)')
            page.wait_for_timeout(100)
            assert abs(page.locator('.workspace-topbar').bounding_box()['y']) < 2
            if width > 700: assert abs(page.locator('.ov-sidebar').bounding_box()['y']) < 2
            results.append({'width': width, 'status': 'PASS'})
        assert not page.evaluate('localStorage.length || sessionStorage.length')
        context.close(); browser.close()
    assert not errors, errors
    assert not external, external
    (OUT / 'result.json').write_text(json.dumps({'results': results, 'js_errors': errors, 'external_requests': external}), encoding='utf-8')
    print(json.dumps({'results': results, 'binding': 'PASS', 'export': 'PASS', 'js_errors': errors}))


if __name__ == '__main__':
    run()
