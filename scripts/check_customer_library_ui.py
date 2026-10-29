"""Channel/report UX QA. Synthetic renderer fixtures stay in browser memory only."""
import json
from pathlib import Path
import secrets
import time

from playwright.sync_api import sync_playwright

ORIGIN = 'http://127.0.0.1:8084'
OUT = Path(__file__).resolve().parents[1] / '.work/customer-library-qa'


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    results, errors, external, forbidden = [], [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = context.new_page()
        page.set_default_timeout(15000)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda r: external.append(r.url) if not r.url.startswith(ORIGIN + '/') else None)
        page.on('request', lambda r: forbidden.append(r.url) if any(s in r.url for s in ('/report/', '/api/v1/facebook', '/auth/customer/google', '/verify-email', '/password/forgot')) else None)
        page.goto(ORIGIN + '/workspace/channels')
        page.wait_for_url('**/workspace/login')
        page.locator('#auth-fields:not([disabled])').wait_for()
        page.locator('[data-mode=register]').click()
        page.locator('#name-field input').fill('QA · Tiếng Việt')
        page.locator('#identity-auth-form [name=email]').fill(f'library-ui-{time.time_ns()}@example.invalid')
        page.locator('#auth-password').fill(secrets.token_urlsafe(24))
        page.locator('#auth-submit').click()
        page.wait_for_url('**/workspace/onboarding')
        page.locator('#workspace-fields:not([disabled])').wait_for()
        page.locator('#workspace-form [name=name]').fill('VIO · QA Phân tích & Báo cáo')
        page.locator('#step-next').click()
        page.locator('#workspace-form [name=first_client]').fill('Thương hiệu Việt')
        page.locator('#step-next').click(); page.locator('#workspace-submit').click()
        page.wait_for_url('**/workspace')
        page.locator('#product-tour[open]').wait_for(); page.locator('#tour-skip:not([disabled])').click()
        page.locator('#product-tour:not([open])').wait_for(state='attached')
        session = page.request.get(ORIGIN + '/api/customer/session').json()
        base = '/api/customer/workspaces/' + session['workspace']['id']

        def post(path, data):
            csrf = page.request.get(ORIGIN + '/api/customer/session').json()['csrf']
            reply = page.request.post(ORIGIN + path, data=data, headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf})
            assert reply.ok, (path, reply.status)
            return reply.json()

        def ready():
            page.locator('#library-workspace-select:not([disabled])').wait_for()
            page.wait_for_function('VioLibrary.ready')

        def shots(name):
            for width in (1440, 1024, 390):
                page.set_viewport_size({'width': width, 'height': 1000 if width > 700 else 844})
                page.evaluate('document.activeElement.blur(); scrollTo(0,0)')
                page.wait_for_timeout(100)
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), (name, width)
                assert page.locator('.lb-main').evaluate('(el) => !el.textContent.includes("KinderHealth")')
                page.screenshot(path=str(OUT / f'{name}-{width}.png'), full_page=True)
                page.screenshot(path=str(OUT / f'{name}-{width}-viewport.png'))
                if width > 700:
                    page.evaluate('scrollTo(0,document.body.scrollHeight)')
                    assert abs(page.locator('.workspace-topbar').bounding_box()['y']) < 2
                    assert abs(page.locator('.ov-sidebar').bounding_box()['y']) < 2
                    page.evaluate('scrollTo(0,0)')
                results.append({'page': name, 'width': width, 'status': 'PASS'})

        page.goto(ORIGIN + '/workspace/channels'); ready()
        assert page.locator('[data-channel-card]').count() == 9
        assert all(v == '—' for v in page.locator('[data-value]').all_text_contents())
        page.locator('[data-library-group=ads]').click()
        assert page.locator('[data-channel-card]:visible').count() == 3
        page.locator('#library-search').fill('khong co kenh nay')
        assert page.locator('#library-no-results').is_visible()
        page.locator('#library-reset').click()
        page.locator('#library-search').fill('tu khoa')
        assert page.locator('[data-channel-card]:visible').count() >= 1
        page.reload(); ready(); assert page.locator('#library-search').input_value() == 'tu khoa'
        page.locator('#library-search').fill('')
        page.locator('#channels-status').select_option('ready')
        assert page.locator('#library-no-results').is_visible()
        page.locator('#library-reset').click()
        shots('channels')
        for width in (1440, 390):
            page.set_viewport_size({'width': width, 'height': 1000 if width > 700 else 844})
            page.locator('[data-open-channel=seo]').click()
            assert page.locator('#library-preview[open]').is_visible()
            assert page.locator('#library-preview-title').inner_text() == 'SEO & Keywords'
            assert page.locator('#library-preview-export').is_disabled()
            assert not page.evaluate('document.querySelector("#library-preview").scrollWidth > document.querySelector("#library-preview").clientWidth')
            page.screenshot(path=str(OUT / f'channel-preview-{width}.png'))
            page.keyboard.press('Escape')
        page.goto(ORIGIN + '/workspace/channels?channel=facebook_content'); ready()
        page.locator('#library-preview[open]').wait_for()
        assert page.locator('#library-preview-title').inner_text() == 'Facebook Content'
        page.keyboard.press('Escape')
        # Zero is real data only in this browser fixture; null stays missing.
        assert page.evaluate("""() => {
            const c=VioChannels.getContext(); window.libraryQaSnapshot={...c,channels:[{...c.scope,workspace_id:c.scope.workspace_id,client_id:c.scope.client_id,id:'facebook_ads',state:'ready',metrics:{spend:0,clicks:null,roas:2}}]};
            return VioChannels.render(libraryQaSnapshot);
        }""")
        assert '0' in page.locator('[data-channel-card=facebook_ads] [data-value=spend]').inner_text()
        assert page.locator('[data-channel-card=facebook_ads] [data-value=clicks]').inner_text() == '—'
        for change in ("scope:{...libraryQaSnapshot.scope,client_id:'foreign'}", "scope:{...libraryQaSnapshot.scope,workspace_id:'foreign'}", "currency:'USD'", "request_id:'stale'"):
            assert not page.evaluate('() => VioChannels.render({...libraryQaSnapshot,' + change + '})')
        page.locator('#library-period').select_option('last7')
        assert not page.evaluate('() => VioChannels.render(libraryQaSnapshot)')
        assert all(v == '—' for v in page.locator('[data-value]').all_text_contents())
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.locator('[data-channel-link=ga4]').click()
        assert page.locator('#library-preview-title').inner_text() == 'Google Analytics 4'
        assert page.locator('#library-period').input_value() == 'last7'
        page.keyboard.press('Escape')
        first = page.locator('#library-client').input_value()
        second = post(base + '/clients', {'name': 'QA Khách hàng B', 'website': '', 'request_key': secrets.token_hex(16)})['selected_client']['id']
        page.locator('#library-refresh').click(); ready()
        assert page.locator('#library-client').input_value() == second
        page.locator('#library-client').select_option(first); ready()
        assert page.locator('#library-client').input_value() == first
        assert not page.evaluate('() => VioChannels.render(libraryQaSnapshot)')

        page.locator('#nav-reports').click(); page.wait_for_url('**/workspace/reports'); ready()
        assert page.locator('[data-template-card]').count() == 10
        assert page.locator('#reports-saved-count').inner_text() == '—'
        page.locator('[data-library-group=search]').click()
        assert page.locator('[data-template-card]:visible').count() == 3
        page.locator('[data-library-group=all]').click()
        shots('reports')
        for width in (1440, 390):
            page.set_viewport_size({'width': width, 'height': 1000 if width > 700 else 844})
            page.locator('[data-open-template=overview]').click()
            assert page.locator('#library-preview[open]').is_visible()
            page.screenshot(path=str(OUT / f'report-preview-{width}.png'))
            page.keyboard.press('Escape')
            page.locator('[data-open-builder]').first.click()
            page.locator('#report-builder-name').fill('QA <img src=x onerror=alert(1)>')
            page.locator('#report-builder-layout').select_option('paid')
            assert page.locator('#report-builder-form [name=source]:checked').count() == 3
            page.screenshot(path=str(OUT / f'report-builder-{width}.png'))
            page.locator('#report-builder-submit').click()
            assert page.locator('#library-preview-title').inner_text() == 'QA <img src=x onerror=alert(1)>'
            assert page.locator('#library-preview-title img').count() == 0
            assert page.locator('#library-preview-edit').is_visible()
            page.locator('#library-preview-edit').click()
            assert page.locator('#report-builder-name').input_value() == 'QA <img src=x onerror=alert(1)>'
            page.locator('#report-builder-layout').select_option('blank')
            page.locator('#report-builder-submit').click()
            assert page.locator('#library-preview-metrics').is_hidden()
            assert page.locator('#library-preview .lb-preview-section h3').first.inner_text() == 'Khu vực nội dung tùy chỉnh'
            page.keyboard.press('Escape')
        page.locator('#reports-history').click()
        assert page.locator('#report-history-dialog[open]').is_visible()
        page.keyboard.press('Escape')
        assert page.request.post(ORIGIN + base + '/reports', data={}).status == 403
        # A synthetic, scoped future payload exercises lists without DB writes.
        assert page.evaluate("""() => {
            const c=VioReports.getContext(); window.libraryReportsQa={...c,reports_loaded:true,exports_loaded:true,reports:Array.from({length:12},(_,i)=>({workspace_id:c.scope.workspace_id,client_id:c.scope.client_id,id:'qa_'+i,name:i===0?'QA <img src=x>':'QA Report '+i,status:i%2?'draft':'published',period:c.period,source_ids:['ga4'],updated_at:'2026-01-01T10:00:00Z'})),exports:[]};
            libraryReportsQa.reports.push({...libraryReportsQa.reports[0],id:'foreign',client_id:'foreign',name:'FOREIGN SECRET'});
            return VioReports.render(libraryReportsQa);
        }""")
        assert page.locator('#reports-saved-count').inner_text() == '12'
        assert page.locator('#reports-rows tr').count() == 10
        assert 'FOREIGN SECRET' not in page.locator('#reports-panel').inner_text()
        assert page.locator('#reports-rows img').count() == 0
        page.locator('.lb-pagination button', has_text='Trang sau').click()
        assert page.locator('#reports-rows tr').count() == 2
        page.locator('[data-report-tab=draft]').click()
        assert page.locator('#reports-rows tr').count() == 6
        page.locator('#reports-search').fill('no report here')
        assert page.locator('#reports-empty').is_visible()
        page.locator('#reports-search').fill('')
        page.locator('#library-period').select_option('last90')
        assert not page.evaluate('() => VioReports.render(libraryReportsQa)')
        assert page.locator('#reports-saved-count').inner_text() == '—'
        assert not page.evaluate('localStorage.length || sessionStorage.length')
        page.keyboard.press('Control+k')
        page.locator('#workspace-search-input').fill('Phan tich kenh')
        page.locator('#workspace-search-results a[href="/workspace/channels"]').click(); ready()
        page.locator('#library-logout').click(); page.wait_for_url('**/workspace/login')
        assert not errors, errors
        assert not external, external
        assert not forbidden, forbidden
        context.close(); browser.close()
    report = {'results': results, 'javascript_errors': errors, 'external_requests': external, 'forbidden_requests': forbidden, 'interactions': 'PASS'}
    (OUT / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    run()
