"""Page 3 acceptance on the dedicated local stack; creates named QA records only."""
import json
from pathlib import Path
import secrets
import time

from playwright.sync_api import sync_playwright

ORIGIN = 'http://127.0.0.1:8084'
OUT = Path(__file__).resolve().parents[1] / '.work/customer-overview-qa'


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    errors, results = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
        for width in (1440,390):
            context = browser.new_context(viewport={'width':width,'height':1000 if width>700 else 844})
            page = context.new_page()
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(ORIGIN+'/workspace/login')
            page.locator('#auth-fields:not([disabled])').wait_for()
            page.locator('[data-mode=register]').click()
            page.locator('#name-field input').fill('QA Overview')
            page.locator('#identity-auth-form [name=email]').fill(f'overview-qa-{width}-{time.time_ns()}@example.invalid')
            page.locator('#auth-password').fill(secrets.token_urlsafe(24))
            page.locator('#auth-submit').click()
            page.wait_for_url('**/workspace/onboarding')
            page.locator('#workspace-fields:not([disabled])').wait_for()
            page.locator('#workspace-form [name=name]').fill(f'QA Overview {width}')
            page.locator('#step-next').click(); page.locator('#step-next').click()
            page.locator('#workspace-submit').click(); page.wait_for_url('**/workspace')
            page.locator('#product-tour[open]').wait_for()
            page.locator('#tour-skip:not([disabled])').click()
            page.locator('#product-tour:not([open])').wait_for(state='attached')
            page.locator('#add-client:not([disabled])').wait_for()
            assert page.locator('#active-client-count').inner_text()=='0'
            assert '1/4' in page.locator('#setup-summary').inner_text()
            info = page.request.get(ORIGIN+'/api/customer/session').json()
            workspace_id = info['workspace']['id']
            base = f'/api/customer/workspaces/{workspace_id}'

            def post(path, data):
                csrf = page.request.get(ORIGIN+'/api/customer/session').json()['csrf']
                response = page.request.post(ORIGIN+path,data=data,headers={'Origin':ORIGIN,'X-CSRF-Token':csrf})
                assert response.status==200,(path,response.status,response.text())
                return response.json()

            # Server commits creation, then the response is lost. Retrying the
            # same form must reuse its request key rather than duplicate a client.
            intercepted = []
            def lost_response(route):
                reply = route.fetch()
                assert reply.status==200
                intercepted.append(reply.json()['selected_client']['id'])
                route.abort()
            page.route('**'+base+'/clients',lost_response,times=1)
            page.locator('#add-client').click()
            malicious_name = 'QA <img src=x onerror=alert(1)>'
            page.locator('#client-name').fill(malicious_name)
            page.locator('#client-website').fill('https://example.test/brand')
            page.locator('#client-save').click()
            page.locator('#client-error:not([hidden])').wait_for()
            assert page.locator('#client-name').input_value()==malicious_name
            page.locator('#client-save:not([disabled])').click()
            page.locator('#client-editor:not([open])').wait_for(state='attached')
            assert len(intercepted)==1
            first_id=intercepted[0]
            assert page.locator('#active-client-count').inner_text()=='1'
            assert page.locator('#client-list img, #client-list script').count()==0
            assert '3/4' in page.locator('#setup-summary').inner_text()
            page.reload(); page.locator('#add-client:not([disabled])').wait_for()
            assert malicious_name in page.locator('#selected-client-summary').inner_text()

            page.locator('#add-client').click(); page.locator('#client-name').fill('QA Brand Two')
            page.locator('#client-save').click(); page.locator('#client-editor:not([open])').wait_for(state='attached')
            detail=page.request.get(ORIGIN+base).json()
            second_id=detail['selected_client']['id']
            page.locator('#client-search').fill('no matching name')
            assert 'Không có khách hàng phù hợp' in page.locator('#client-list').inner_text()
            page.locator('#client-search').fill('')
            row=page.locator(f'[data-client-id="{first_id}"]')
            row.get_by_role('button',name='Chỉnh sửa',exact=True).click()
            # Concurrent edit after the form opened: the stale version is denied
            # and the reader explicitly reloads the newer values.
            post(base+f'/clients/{first_id}/update',{'name':'Concurrent edit','website':'https://example.test/new','version':1})
            page.locator('#client-name').fill('Stale overwrite')
            page.locator('#client-save').click(); page.locator('#client-reload-latest:not([hidden])').wait_for()
            assert page.locator('#client-name').input_value()=='Stale overwrite'
            page.locator('#client-reload-latest').click()
            page.wait_for_function("document.querySelector('#client-name').value === 'Concurrent edit'")
            page.locator('#client-name').fill('QA Updated Brand')
            page.locator('#client-save').click(); page.locator('#client-editor:not([open])').wait_for(state='attached')
            page.locator(f'[data-client-id="{second_id}"]').get_by_role('button',name='Lưu trữ',exact=True).click()
            page.locator('#client-confirm-submit').click(); page.locator('#client-confirm:not([open])').wait_for(state='attached')
            assert 'Chưa chọn' in page.locator('#selected-client-summary').inner_text()
            assert '2/4' in page.locator('#setup-summary').inner_text()
            page.locator('#client-filter').select_option('archived')
            page.locator(f'[data-client-id="{second_id}"]').get_by_role('button',name='Khôi phục',exact=True).click()
            page.locator('#client-confirm-submit').click(); page.locator('#client-confirm:not([open])').wait_for(state='attached')
            assert 'Chưa chọn' in page.locator('#selected-client-summary').inner_text()
            page.locator('#client-filter').select_option('active')
            page.locator(f'[data-client-id="{first_id}"]').get_by_role('button',name='Chọn làm việc',exact=True).click()
            page.wait_for_function("document.querySelector('#selected-client-summary').textContent.includes('QA Updated Brand')")
            assert '3/4' in page.locator('#setup-summary').inner_text()
            assert page.locator('[data-setup-step=integrations]').get_attribute('data-state')=='planned'
            assert page.request.post(ORIGIN+base+f'/clients/{first_id}/archive',data={'version':3}).status==403

            other=post('/api/customer/workspaces',{'name':'QA Other Workspace','kind':'agency','website':'','country':'VN','timezone':'Asia/Ho_Chi_Minh','currency':'VND','first_client':'','request_key':secrets.token_hex(16)})
            assert other['workspace']['id']!=workspace_id
            page.reload(); page.locator('#add-client:not([disabled])').wait_for()
            assert page.locator('#active-client-count').inner_text()=='0'
            page.locator('#product-tour[open]').wait_for()
            page.locator('#tour-skip:not([disabled])').click()
            page.locator('#product-tour:not([open])').wait_for(state='attached')
            page.locator('#overview-workspace-select').select_option(workspace_id)
            page.wait_for_function("document.querySelector('#selected-client-summary')?.textContent.includes('QA Updated Brand')")
            page.locator('#add-client:not([disabled])').wait_for()
            assert page.locator('#active-client-count').inner_text()=='2'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'), f'Overflow at {width}'
            assert page.evaluate('localStorage.length + sessionStorage.length')==0
            page.screenshot(path=str(OUT/f'overview-{width}.png'),full_page=True)
            results.append({'width':width,'crud':'PASS','response_loss_retry':'PASS','conflict':'PASS','workspace_isolation':'PASS'})
            context.close()
        browser.close()
    assert not errors,errors
    (OUT/'result.json').write_text(json.dumps({'results':results,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':len(results),'javascript_errors':errors}))


if __name__=='__main__':
    run()
