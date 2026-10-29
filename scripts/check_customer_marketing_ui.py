"""Live page 05 UX acceptance; analytics fixtures exist only inside the browser."""
import csv
import io
import json
from pathlib import Path
import secrets
import time

from playwright.sync_api import sync_playwright

ORIGIN = 'http://127.0.0.1:8084'
OUT = Path(__file__).resolve().parents[1] / '.work/customer-marketing-qa'


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    errors, external, results = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: external.append(request.url) if not request.url.startswith(ORIGIN + '/') and not request.url.startswith('blob:') else None)
        page.goto(ORIGIN + '/workspace/dashboard'); page.wait_for_url('**/workspace/login')
        page.locator('#auth-fields:not([disabled])').wait_for()
        page.locator('[data-mode=register]').click()
        page.locator('#name-field input').fill('QA Marketing')
        page.locator('#identity-auth-form [name=email]').fill(f'marketing-qa-{time.time_ns()}@example.invalid')
        page.locator('#auth-password').fill(secrets.token_urlsafe(24)); page.locator('#auth-submit').click()
        page.wait_for_url('**/workspace/onboarding'); page.locator('#workspace-fields:not([disabled])').wait_for()
        page.locator('#workspace-form [name=name]').fill('VIO Agency · QA Dashboard')
        page.locator('#step-next').click()
        page.locator('#workspace-form [name=first_client]').fill('VIO Brand')
        page.locator('#step-next').click(); page.locator('#workspace-submit').click()
        page.wait_for_url('**/workspace'); page.locator('#product-tour[open]').wait_for()
        page.locator('#tour-skip:not([disabled])').click(); page.locator('#product-tour:not([open])').wait_for(state='attached')
        page.locator('#nav-dashboard').click(); page.wait_for_url('**/workspace/dashboard')
        page.locator('#marketing-client:not([disabled])').wait_for()
        assert page.locator('#nav-dashboard').get_attribute('aria-current') == 'page'
        assert page.locator('[data-metric]').count() == 4
        assert page.locator('#marketing-platform-rows tr').count() == 9
        assert all(value == '—' for value in page.locator('[data-metric-value]').all_text_contents())
        assert page.locator('#marketing-sources li').count() == 9
        # Shared navigation/search work across the three authenticated pages.
        for route in ('/workspace', '/workspace/integrations'):
            page.goto(ORIGIN + route)
            page.locator('.wh-logout:not([disabled])').wait_for()
            page.keyboard.press('Control+k')
            page.locator('#workspace-search-dialog[open]').wait_for()
            page.locator('#workspace-search-input').fill('Dashboard Marketing')
            page.locator('#workspace-search-results a[href="/workspace/dashboard"]').click()
            page.wait_for_url('**/workspace/dashboard')
            page.locator('#marketing-client:not([disabled])').wait_for()
        page.locator('[data-platform-group=paid]').click()
        assert page.locator('#marketing-platform-rows tr').count() == 3
        page.locator('[data-platform-group=all]').click()
        page.locator('#marketing-source').select_option('ga4')
        assert page.locator('#marketing-platform-rows tr').count() == 1
        assert page.locator('#marketing-sources li').count() == 1
        page.reload(); page.locator('#marketing-client:not([disabled])').wait_for()
        assert page.locator('#marketing-source').input_value() == 'ga4'
        page.locator('#marketing-source').select_option('all')
        page.locator('[data-metric-info=conversions]').click()
        assert 'trùng lặp' in page.locator('#marketing-dialog-description').inner_text()
        page.keyboard.press('Escape')
        page.locator('[data-chart-metric=spend]').click(); page.keyboard.press('ArrowRight')
        assert page.locator('[data-chart-metric=impressions]').get_attribute('aria-selected') == 'true'
        page.locator('[data-chart-metric=spend]').click()

        # Bind one scoped snapshot. No synthetic provider value is sent to any API/DB.
        assert page.evaluate("""() => {
          const c = VioMarketing.getContext(), end = c.period.end;
          const d = new Date(end + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate()-1);
          const middle = d.toISOString().slice(0,10); d.setUTCDate(d.getUTCDate()-1);
          const start = d.toISOString().slice(0,10);
          const scoped = (p) => ({workspace_id:c.scope.workspace_id, client_id:c.scope.client_id, platform_id:p});
          window.qaMarketingSnapshot = {...c, metrics:{spend:{status:'ready',value:0,previous:0},impressions:{status:'partial',value:1234,previous:1000},clicks:{status:'partial',value:null}},
            trends:{spend:{status:'partial',points:[{date:start,value:0},{date:middle,value:null},{date:end,value:5}]}},
            platform_metrics:[{...scoped('facebook_ads'),status:'partial',values:{spend:0,clicks:null,ctr:null}},
              {...scoped('ga4'),workspace_id:'foreign',status:'ready',values:{clicks:123456789}}],
            connections:[{...scoped('facebook_ads'),id:'qa-connection',state:'connected'}],
            campaigns:Array.from({length:12},(_,i)=>({...scoped('facebook_ads'),id:'qa-'+i,name:i===0?'=SUM(1,2)':'QA <img src=x> '+i,state:i%2?'paused':'active',data_status:'partial',values:{spend:i===0?0:null,ctr:null,clicks:i}})),
            last_updated_at:new Date().toISOString()};
          qaMarketingSnapshot.campaigns.push({...scoped('google_ads'),id:'foreign',client_id:'foreign',name:'FOREIGN RECORD',data_status:'ready',values:{spend:999999999}});
          return VioMarketing.applySnapshot(qaMarketingSnapshot);
        }""")
        assert page.locator('[data-metric=spend] [data-metric-value]').inner_text() != '—'
        assert page.locator('[data-metric=clicks] [data-metric-value]').inner_text() == '—'
        assert page.locator('#marketing-chart-svg path').get_attribute('d').count('M') == 2
        page.locator('#marketing-trend-table summary').click()
        assert '0' in page.locator('#marketing-trend-table tbody').inner_text()
        assert '—' in page.locator('#marketing-trend-table tbody').inner_text()
        assert page.locator('#marketing-campaign-count').inner_text() == '12 chiến dịch'
        assert page.locator('#marketing-campaign-rows tr').count() == 10
        assert page.locator('#marketing-campaign-rows img').count() == 0
        assert 'FOREIGN RECORD' not in page.locator('body').inner_text()
        page.locator('#marketing-page-next').click()
        assert page.locator('#marketing-campaign-rows tr').count() == 2
        page.locator('#marketing-campaign-search').fill('khong ton tai')
        assert page.locator('#marketing-campaign-reset').is_visible()
        page.locator('#marketing-campaign-reset').click()
        page.locator('#marketing-campaign-state').select_option('active')
        assert page.locator('#marketing-campaign-count').inner_text() == '6 chiến dịch'
        page.locator('#marketing-campaign-state').select_option('all')
        for invalid in ["scope:{workspace_id:'foreign',client_id:'foreign'}", "currency:'USD'", "timezone:'UTC'", "source:'ga4'", "granularity:'week'", "comparison:'none'", "request_id:'old'"]:
            assert not page.evaluate('() => VioMarketing.applySnapshot({...qaMarketingSnapshot,' + invalid + '})')
        with page.expect_download() as download:
            page.locator('#marketing-export').click()
        content = Path(download.value.path()).read_text(encoding='utf-8-sig')
        parsed = list(csv.reader(io.StringIO(content)))
        assert any(row and row[0] == "'=SUM(1,2)" for row in parsed)
        assert any(row and row[0].startswith('Lượt nhấp') and row[1] == '' for row in parsed)
        assert 'FOREIGN RECORD' not in content
        # A changed period clears the snapshot and rejects a delayed response.
        page.locator('#marketing-period').select_option('last7')
        assert all(value == '—' for value in page.locator('[data-metric-value]').all_text_contents())
        assert not page.evaluate('() => VioMarketing.applySnapshot(qaMarketingSnapshot)')
        page.locator('#marketing-period').select_option('custom')
        page.locator('#marketing-start').fill('2020-01-01'); page.locator('#marketing-end').fill('2026-01-01')
        page.locator('#marketing-custom-period button').click()
        assert '366' in page.locator('#marketing-status').inner_text()
        page.locator('#marketing-period').select_option('last30')
        # A metadata failure never masquerades as a successful empty data refresh.
        page.route('**/api/customer/workspaces/*/integrations', lambda route: route.fulfill(status=503, json={'error':'QA unavailable'}), times=1)
        page.locator('#marketing-refresh').click()
        page.wait_for_function("document.querySelector('#marketing-status').textContent.includes('QA unavailable')")
        assert page.locator('#marketing-client').is_disabled()
        page.locator('#marketing-refresh').click(); page.locator('#marketing-client:not([disabled])').wait_for()
        assert not page.evaluate('localStorage.length || sessionStorage.length')
        for width in (1440, 1024, 390):
            page.set_viewport_size({'width':width,'height':1000 if width > 700 else 844})
            page.evaluate('document.activeElement.blur(); scrollTo(0,0)')
            page.wait_for_timeout(100)
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), width
            if width <= 700:
                assert page.locator('#nav-dashboard').evaluate('(el) => {const item=el.getBoundingClientRect(), nav=el.closest("nav").getBoundingClientRect(); return item.left >= nav.left-1 && item.right <= nav.right+1;}')
            page.screenshot(path=str(OUT / f'marketing-{width}.png'), full_page=True)
            page.screenshot(path=str(OUT / f'marketing-{width}-viewport.png'))
            if width > 700:
                page.evaluate('scrollTo(0,document.body.scrollHeight)')
                assert abs(page.locator('.workspace-topbar').bounding_box()['y']) < 2
                assert abs(page.locator('.ov-sidebar').bounding_box()['y']) < 2
            results.append({'width':width,'status':'PASS'})
        # Real existing client selection API and stale Workspace guard are preserved.
        session = page.request.get(ORIGIN + '/api/customer/session').json()
        base = '/api/customer/workspaces/' + session['workspace']['id']

        def post(path, data):
            csrf = page.request.get(ORIGIN + '/api/customer/session').json()['csrf']
            reply = page.request.post(ORIGIN + path, data=data, headers={'Origin':ORIGIN,'X-CSRF-Token':csrf})
            assert reply.status == 200, (path, reply.status)
            return reply.json()

        original_client = page.locator('#marketing-client').input_value()
        next_client = post(base + '/clients', {'name':'=SUM(1,2)','website':'','request_key':secrets.token_hex(16)})['selected_client']
        page.locator('#marketing-refresh').click(); page.locator('#marketing-client:not([disabled])').wait_for()
        assert page.locator('#marketing-client').input_value() == next_client['id']
        page.locator('#marketing-client').select_option(original_client)
        page.locator('#marketing-client:not([disabled])').wait_for()
        assert page.request.get(ORIGIN + base).json()['selected_client']['id'] == original_client
        assert page.request.post(ORIGIN + base + '/clients/' + next_client['id'] + '/select', data={}).status == 403
        post('/api/customer/workspaces', {'name':'QA Marketing B','kind':'agency','website':'','country':'VN','timezone':'Asia/Ho_Chi_Minh','currency':'VND','first_client':'','request_key':secrets.token_hex(16)})
        page.locator('#marketing-refresh').click(); page.wait_for_url('**/workspace')
        page.locator('#product-tour[open]').wait_for(); page.locator('#tour-skip:not([disabled])').click()
        page.goto(ORIGIN + '/workspace/dashboard'); page.locator('#marketing-logout:not([disabled])').wait_for()
        assert page.locator('#marketing-client').is_disabled()
        page.locator('#marketing-workspace-select').select_option(session['workspace']['id'])
        page.wait_for_function('(id) => document.querySelector("#marketing-workspace-select").value === id && !document.querySelector("#marketing-client").disabled', arg=session['workspace']['id'])
        assert page.request.get(ORIGIN + '/api/customer/session').json()['workspace']['id'] == session['workspace']['id']
        page.locator('#marketing-logout').click(); page.wait_for_url('**/workspace/login')
        browser.close()
    assert not errors, errors
    assert not external, external
    report = {'results':results,'javascript_errors':errors,'external_requests':external,'binding_and_scope':'PASS'}
    (OUT / 'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    run()
