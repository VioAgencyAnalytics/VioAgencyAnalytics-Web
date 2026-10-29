"""Real local page 4 acceptance. Creates named QA records, no provider calls."""
import json
from pathlib import Path
import secrets
import time

from playwright.sync_api import sync_playwright

ORIGIN = 'http://127.0.0.1:8084'
OUT = Path(__file__).resolve().parents[1] / '.work/customer-integrations-qa'


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    results, errors, external = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
        for width in (1440, 390):
            context = browser.new_context(viewport={'width': width, 'height': 1000 if width > 700 else 844})
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: external.append(request.url) if not request.url.startswith(ORIGIN + '/') else None)
            page.goto(ORIGIN + '/workspace/integrations')
            page.wait_for_url('**/workspace/login')
            page.locator('#auth-fields:not([disabled])').wait_for()
            page.locator('[data-mode=register]').click()
            page.locator('#name-field input').fill('QA Integrations')
            page.locator('#identity-auth-form [name=email]').fill(f'integrations-qa-{width}-{time.time_ns()}@example.invalid')
            page.locator('#auth-password').fill(secrets.token_urlsafe(24))
            page.locator('#auth-submit').click()
            page.wait_for_url('**/workspace/onboarding')
            page.locator('#workspace-fields:not([disabled])').wait_for()
            page.locator('#workspace-form [name=name]').fill(f'QA Integrations {width}')
            page.locator('#step-next').click(); page.locator('#step-next').click()
            page.locator('#workspace-submit').click(); page.wait_for_url('**/workspace')
            page.locator('#product-tour[open]').wait_for()
            page.locator('#tour-skip:not([disabled])').click()
            page.locator('#product-tour:not([open])').wait_for(state='attached')
            page.locator('[data-integration-link]').click()
            page.wait_for_url('**/workspace/integrations')
            page.locator('#integrations-logout:not([disabled])').wait_for()
            assert page.locator('[data-platform]').count() == 9
            assert '0 tài khoản' in page.locator('#connected-count').inner_text()
            assert 'chưa có khách hàng' in page.locator('#integration-scope').inner_text()
            assert page.locator('#integration-client').is_disabled()
            info = page.request.get(ORIGIN + '/api/customer/session').json()
            base = f"/api/customer/workspaces/{info['workspace']['id']}"

            def post(path, data):
                csrf = page.request.get(ORIGIN + '/api/customer/session').json()['csrf']
                response = page.request.post(ORIGIN + path, data=data, headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf})
                assert response.status == 200, (path, response.status, response.text())
                return response.json()

            first = post(base + '/clients', {'name': 'QA <img src=x onerror=alert(1)>', 'website': '', 'request_key': secrets.token_hex(16)})['selected_client']
            second = post(base + '/clients', {'name': 'QA Brand B', 'website': '', 'request_key': secrets.token_hex(16)})['selected_client']
            page.locator('#integrations-refresh').click()
            page.locator('#integration-client:not([disabled])').wait_for()
            assert page.locator('#integration-client').input_value() == second['id']
            page.locator('#integration-client').select_option(first['id'])
            page.wait_for_function("document.querySelector('#integration-scope').textContent.includes('QA <img')")
            assert page.locator('#integration-scope img').count() == 0
            page.reload()
            page.locator('#integration-client:not([disabled])').wait_for()
            assert page.locator('#integration-client').input_value() == first['id']
            page.locator('[data-category=ads]').click()
            assert page.locator('[data-platform]:visible').count() == 3
            page.locator('#platform-search').fill('tiktok')
            assert page.locator('[data-platform]:visible').count() == 1
            page.locator('#platform-search').fill('no-platform-found')
            assert page.locator('#platform-no-results').is_visible()
            page.locator('#platform-reset').click()
            assert page.locator('[data-platform]:visible').count() == 9
            page.locator('[data-category=seo]').click()
            assert page.locator('[data-platform]:visible').count() == 2
            page.locator('[data-category=all]').click()
            # Filters are shareable and survive reload, including alias/multiword search.
            page.locator('#platform-search').fill('meta ads')
            assert page.locator('[data-platform]:visible').count() == 1
            page.wait_for_function("new URLSearchParams(location.search).get('q') === 'meta ads'")
            page.reload()
            page.locator('#integration-client:not([disabled])').wait_for()
            assert page.locator('#platform-search').input_value() == 'meta ads'
            assert page.locator('[data-platform]:visible').count() == 1
            page.locator('#platform-clear-filters').click()
            page.locator('#platform-status-filter').select_option('connected')
            assert page.locator('#platform-no-results').is_visible()
            page.locator('#platform-reset').click()
            assert page.locator('[data-platform]:visible').count() == 9
            page.locator('[data-platform-details=facebook_content]').click()
            assert page.locator('#integration-dialog[open]').is_visible()
            assert 'chưa được mở' in page.locator('#integration-dialog-description').inner_text()
            assert 'QA <img' in page.locator('#integration-dialog-extra').inner_text()
            assert page.locator('#integration-dialog-extra img').count() == 0
            page.keyboard.press('Escape')
            assert not page.locator('#integration-dialog').is_visible()
            assert page.evaluate("document.activeElement.dataset.platformDetails") == 'facebook_content'
            missing_csrf = page.request.post(ORIGIN + base + '/clients/' + second['id'] + '/select', data={})
            assert missing_csrf.status == 403
            # Failed refresh is recoverable without enabling a fake Connect action.
            page.route('**/api/customer/workspaces/*/integrations', lambda route: route.fulfill(status=503, json={'error': 'QA unavailable'}), times=1)
            page.locator('#integrations-refresh').click()
            page.wait_for_function("document.querySelector('#integrations-status').textContent.includes('QA unavailable')")
            assert 'Chưa tải được' in page.locator('#connected-empty-title').inner_text()
            page.locator('#connected-browse').click()
            page.wait_for_function("document.querySelector('#integrations-status').textContent.includes('Đã cập nhật trạng thái')")
            assert page.locator('[data-platform-details]').count() == 9
            assert page.locator('text=HIPAA').count() == 0
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            assert not page.evaluate('localStorage.length || sessionStorage.length')
            data = page.request.get(ORIGIN + base + '/integrations').json()
            assert data['connections'] == [] and data['summary']['connected_accounts'] == 0
            assert all(not item['can_connect'] for item in data['platforms'])
            # Browser-only records exercise the future renderer. No connection is written to DB.
            if width == 1440:
                workspace_id = info['workspace']['id']
                records = [dict(id='qa-' + source, workspace_id=workspace_id, client_id=first['id'],
                                platform_id=source, state=state, account_name='QA <img src=x>',
                                asset_name='QA asset', last_sync_at=stamp)
                           for source, state, stamp in [('ga4', 'connected', '2026-10-28T03:30:00Z'),
                                                        ('facebook_content', 'expired', None),
                                                        ('tiktok_ads', 'pending', None),
                                                        ('youtube', 'syncing', None)]]
                records += [dict(records[0], id='foreign-workspace', workspace_id='foreign'),
                            dict(records[0], id='foreign-client', client_id='foreign')]

                def synthetic_connections(route):
                    payload = route.fetch().json()
                    payload['connections'] = records
                    route.fulfill(json=payload)

                page.route('**/api/customer/workspaces/*/integrations', synthetic_connections)
                page.locator('#integrations-refresh').click()
                page.wait_for_function("document.querySelectorAll('[data-connection-id]').length === 4")
                assert page.locator('#connected-count').inner_text() == '4 tài khoản'
                assert '1 tài khoản cần kiểm tra' in page.locator('#integration-sync-note').inner_text()
                assert page.locator('#connected-list img').count() == 0
                assert 'Chưa đồng bộ' in page.locator('[data-connection-id=qa-facebook_content]').inner_text()
                assert page.locator('[data-connection-id=qa-tiktok_ads] .ig-badge').get_attribute('data-state') == 'upcoming'
                page.locator('#platform-status-filter').select_option('connected')
                assert page.locator('[data-platform]:visible').count() == 2
                page.locator('#platform-status-filter').select_option('attention')
                assert page.locator('[data-platform]:visible').count() == 1
                page.locator('#platform-clear-filters').click()
                page.locator('[data-connection-id=qa-facebook_content] button').click()
                assert 'QA <img src=x>' in page.locator('#integration-dialog-extra').inner_text()
                assert page.locator('#integration-dialog-extra img').count() == 0
                page.keyboard.press('Escape')
                page.locator('#integration-client').select_option(second['id'])
                page.wait_for_function("document.querySelector('#integration-client').disabled === false")
                assert page.locator('[data-connection-id]').count() == 0
                page.unroute('**/api/customer/workspaces/*/integrations', synthetic_connections)
                page.locator('#integration-client').select_option(first['id'])
                page.wait_for_function("document.querySelector('#integration-client').disabled === false")
                assert page.locator('[data-connection-id]').count() == 0
                for tablet_width in (1024,):
                    page.set_viewport_size({'width': tablet_width, 'height': 1000})
                    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
                    page.evaluate('document.activeElement.blur(); scrollTo(0, 0)')
                    page.screenshot(path=str(OUT / f'integrations-{tablet_width}.png'), full_page=True)
                page.set_viewport_size({'width': width, 'height': 1000})
            page.evaluate('scrollTo(0, 0)')
            if width > 700:
                page.evaluate('scrollTo(0, document.body.scrollHeight)')
                assert abs(page.locator('.ov-sidebar').bounding_box()['y']) < 2
                assert abs(page.locator('.workspace-topbar').bounding_box()['y']) < 2
                assert page.locator('.ov-sidebar').evaluate('(el) => el.scrollHeight >= el.clientHeight')
                page.evaluate('scrollTo(0, 0)')
            page.screenshot(path=str(OUT / f'integrations-{width}.png'), full_page=True)
            page.screenshot(path=str(OUT / f'integrations-{width}-viewport.png'))
            # A tab whose session changed Workspace must not display another scope.
            post('/api/customer/workspaces', {'name': 'QA scope B', 'kind': 'agency', 'website': '', 'country': 'VN',
                 'timezone': 'Asia/Ho_Chi_Minh', 'currency': 'VND', 'first_client': '', 'request_key': secrets.token_hex(16)})
            stale = page.request.get(ORIGIN + base + '/integrations')
            assert stale.status == 409
            page.locator('#integrations-refresh').click()
            page.wait_for_url('**/workspace')
            results.append({'width': width, 'status': 'PASS', 'platforms': 9})
            context.close()
        browser.close()
    assert not errors, errors
    assert not external, external
    (OUT / 'result.json').write_text(json.dumps({'results': results, 'js_errors': errors, 'external_requests': external}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'results': results, 'js_errors': errors, 'external_requests': external}))


if __name__ == '__main__':
    run()
