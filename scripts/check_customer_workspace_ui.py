import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description='Verify the nine-page customer workspace UI.')
parser.add_argument('--base-url', default='http://127.0.0.1:8083')
parser.add_argument('--browser-path', default=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
args = parser.parse_args()
base_url = args.base_url.rstrip('/')
out = Path(__file__).resolve().parents[1] / '.work/customer-qa'
out.mkdir(exist_ok=True)
paths = ['login','onboarding','','integrations','dashboard','channels','reports','members','settings']
errors, failed, report = [], [], []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.browser_path, headless=True)
    context = browser.new_context(viewport={'width':1440,'height':1000}, device_scale_factor=1)
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('response', lambda response: failed.append([response.status,response.url]) if response.status >= 400 else None)
    for width in (1440,390):
        page.set_viewport_size({'width':width,'height':1000 if width==1440 else 844})
        for slug in paths:
            page.goto(base_url + '/workspace'+('/'+slug if slug else ''),wait_until='networkidle')
            page.screenshot(path=str(out/f'{slug or "overview"}-{width}.png'),full_page=True)
            overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
            offenders=page.evaluate('''() => [...document.querySelectorAll('body *')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.right>innerWidth+2&&getComputedStyle(e).position!=='fixed'}).slice(0,8).map(e=>({tag:e.tagName,cl:e.className,w:e.getBoundingClientRect().width}))''') if overflow else []
            report.append({'page':slug or 'overview','width':width,'overflow':overflow,'offenders':offenders})
    (out/'screens.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(base_url + '/workspace/channels')
    page.locator('#channelSearch').fill('facebook')
    assert page.locator('.channel-card:visible').count()==2
    page.locator('#statusFilter').select_option(index=2)
    assert page.locator('.channel-card:visible').count()==0
    page.locator('#statusFilter').select_option(index=0)
    page.locator('#channelSearch').fill('')
    page.locator('.category-btn[data-category=video]').click()
    assert page.locator('.channel-card:visible').count()==1
    page.locator('.channel-card:visible a').click()
    page.wait_for_url('**/workspace/channels/youtube')
    page.frame_locator('#customer-report-frame').locator('#main-content').wait_for()
    page.screenshot(path=str(out/'legacy-youtube-1440.png'),full_page=True)
    page.goto(base_url + '/workspace/reports?create=1')
    page.locator('#reportNameInput').fill('Báo cáo kiểm tra giao diện')
    page.locator('#createReportForm button[type=submit]').click()
    assert page.locator('.customer-local-draft').count()==1
    page.reload()
    assert page.locator('.customer-local-draft').count()==1
    page.goto(base_url + '/workspace/members')
    page.locator('[data-action=invite-open]').first.click()
    page.locator('#inviteEmail').fill('qa@example.invalid')
    page.locator('[data-action=invite-send]').click()
    assert page.locator('#customer-dialog').is_visible()
    assert 'Chưa gửi lời mời' in page.locator('#customer-dialog').inner_text()
    page.locator('#customer-dialog button').last.click()
    page.keyboard.press('Escape')
    page.goto(base_url + '/workspace/settings')
    field=page.locator('input[data-setting]:not([readonly])').first
    field.fill('Doanh nghiệp xem thử')
    page.locator('[data-action=save-settings]').click()
    page.reload()
    assert page.locator('input[data-setting]:not([readonly])').first.input_value()=='Doanh nghiệp xem thử'
    page.goto(base_url + '/workspace/onboarding')
    page.locator('#agency-name').fill('VIO Demo Workspace')
    page.locator('[data-action=create-workspace]').click()
    page.wait_for_url('**/workspace')
    assert page.locator('[data-workspace-name]').first.inner_text()=='VIO Demo Workspace'
    page.set_viewport_size({'width':390,'height':844})
    page.locator('#customer-menu').click()
    assert page.locator('#customer-menu').get_attribute('aria-expanded')=='true'
    page.locator('#customer-sidebar a[href="/workspace/settings"]').click()
    page.wait_for_url('**/workspace/settings')
    browser.close()
result={'screens':report,'js_errors':errors,'failed_requests':failed,'interactions':'passed'}
(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))

assert not errors, errors
assert not failed, failed
assert not any(screen['overflow'] for screen in report), 'Horizontal page overflow detected'
