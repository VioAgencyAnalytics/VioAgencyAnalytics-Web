// Run only with serve_executive_qa.py. No provider or production requests.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.KDH_UI_QA_BASE_URL || 'http://127.0.0.1:18085';
assert.ok(['http://127.0.0.1:18085','http://127.0.0.1:8081'].includes(base), 'Use only an isolated local fixture server');
const edge = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
(async () => {
  const browser = await chromium.launch(fs.existsSync(edge) ? {headless:true, executablePath:edge} : {headless:true, channel:'msedge'});
  try {
    const page = await browser.newPage();
    const errors = [], external = [], checks = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => {if(m.type() === 'error') errors.push(m.text());});
    await page.route('**/*', route => {
      if(route.request().url().startsWith(base + '/')) return route.continue();
      external.push(route.request().url());
      return route.abort();
    });
    fs.mkdirSync('.work/executive-ui', {recursive:true});
    for(const width of [1440,1024,768,390,360]) {
      await page.setViewportSize({width,height:900});
      for(const channel of ['overview','seo','facebook_ads','facebook_content','tiktok','youtube','gmb']) {
        const response = await page.goto(base + '/qa/' + channel);
        assert.equal(response.status(),200);
        await page.evaluate(() => document.fonts.ready);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),true,channel + ' overflow ' + width);
        const readability = await page.evaluate(() => {
          const failures = [];
          const visible = el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
          const requireSize = (selector, minimum) => document.querySelectorAll(selector).forEach(el => {
            if(visible(el) && parseFloat(getComputedStyle(el).fontSize) < minimum)
              failures.push(`${selector}: ${el.textContent.trim().slice(0,45)} below ${minimum}px`);
          });
          requireSize('.dashboard-main h1',28);
          requireSize('.dashboard-main h2,.dashboard-main h3.font-headline-md,.snapshot-table-heading h3',18);
          requireSize('.executive-kpi .uppercase,.fb-kpi-label,.fc-kpi-label,.vd-kpi-label',14);
          requireSize('.snapshot-table th,.snapshot-table td,.report-nav-link,.report-submenu a',14);
          requireSize('.snapshot-missing,.snapshot-kpi-note,.table-source,.header-comparison',13);
          const rgb = value => (value.match(/[\d.]+/g) || []).map(Number);
          const blend = (front, back) => front.slice(0,3).map((c,i) => c*(front[3] ?? 1)+back[i]*(1-(front[3] ?? 1)));
          const background = el => {
            const chain = []; for(let node=el;node;node=node.parentElement) chain.unshift(node);
            return chain.reduce((color,node) => blend(rgb(getComputedStyle(node).backgroundColor),color),[255,255,255]);
          };
          const luminance = color => color.map(c => c/255).map(c => c<=.04045 ? c/12.92 : ((c+.055)/1.055)**2.4)
            .reduce((sum,c,i) => sum+c*[.2126,.7152,.0722][i],0);
          document.querySelectorAll('.snapshot-missing,.snapshot-kpi-note,.table-source,.snapshot-table th,.header-comparison,.briefing-meta').forEach(el => {
            if(!visible(el)) return;
            const bg = background(el), fg = blend(rgb(getComputedStyle(el).color),bg);
            const a=luminance(fg), b=luminance(bg), ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
            if(ratio < 4.5) failures.push(`Contrast ${ratio.toFixed(2)}: ${el.textContent.trim().slice(0,45)}`);
          });
          document.querySelectorAll('.executive-kpi,#date-range-label,.header-comparison').forEach(el => {
            if(el.scrollWidth > el.clientWidth+1) failures.push(`Clipped text: ${el.textContent.trim().slice(0,45)}`);
          });
          document.querySelectorAll('.pb-chart-surface>svg').forEach(svg => {
            if(!visible(svg)) return;
            const texts = [...svg.querySelectorAll('text')];
            for(const text of texts) {
              const box=text.getBBox(), view=svg.viewBox.baseVal;
              if(box.x < 0 || box.x+box.width > view.width+1) failures.push('Clipped chart axis label');
              if(parseFloat(getComputedStyle(text).fontSize)*svg.getScreenCTM().a < 13.9) failures.push('Chart axis below 14px rendered');
            }
            const ticks = texts.filter(text => text.getAttribute('y') === '250').map(text => text.getBBox());
            for(let i=1;i<ticks.length;i++) if(ticks[i-1].x+ticks[i-1].width+4 > ticks[i].x) failures.push('Overlapping chart axis labels');
          });
          return failures;
        });
        assert.deepEqual(readability,[],channel + ' readability ' + width);
        const header = await page.locator('.dashboard-header').boundingBox();
        const comparison = await page.locator('.header-comparison').boundingBox();
        assert.ok(comparison.y >= header.y && comparison.y + comparison.height <= header.y + header.height + 1, 'Comparison outside header ' + width);
        const status = await page.locator('.snapshot-status').boundingBox();
        assert.ok(status.y >= header.y+header.height, 'Report status obscured by header ' + width);
        for(const name of ['Nguồn dữ liệu','Xuất báo cáo']) {
          const button = page.getByRole('button',{name,exact:true});
          assert.equal(await button.isVisible(),true);
          const box = await button.boundingBox();
          assert.ok(box.x >= 0 && box.x + box.width <= width, name + ' outside viewport');
          assert.ok(box.y >= header.y && box.y + box.height <= header.y + header.height + 1, name + ' outside header');
        }
        assert.equal(await page.locator('#period-switcher').count(),0);
        if(channel === 'overview') {
          const disclosure = page.locator('.channel-trend').first();
          const chart = disclosure.locator('[data-bundle-chart]').first();
          const savedChart = await chart.locator('script').textContent();
          await disclosure.locator('summary').click();
          assert.equal(await chart.locator('svg[role="img"]').isVisible(),true);
          await disclosure.locator('summary').click();
          await page.evaluate(() => dispatchEvent(new Event('beforeprint')));
          assert.equal(await disclosure.getAttribute('open'),'');
          await page.evaluate(() => dispatchEvent(new Event('afterprint')));
          assert.equal(await disclosure.getAttribute('open'),null);
          assert.equal(await chart.locator('script').textContent(),savedChart);
          const overviewLink = page.locator('.overview-nav-link');
          assert.equal(await overviewLink.getAttribute('aria-current'),'page');
          assert.match(await overviewLink.getAttribute('href'),/revision=2/);
        }
        await page.getByRole('button',{name:'Nguồn dữ liệu',exact:true}).click();
        assert.equal(await page.locator('#source-dialog').isVisible(),true);
        assert.match(await page.locator('#source-dialog').innerText(),/Revision 2/);
        await page.keyboard.press('Escape');
        if(width < 1024) {
          await page.locator('#sidebar-toggle').click();
          assert.equal(await page.locator('#sidebar-toggle').getAttribute('aria-expanded'),'true');
          await page.keyboard.press('Escape');
          assert.equal(await page.locator('#sidebar-toggle').getAttribute('aria-expanded'),'false');
        }
        await page.screenshot({path:'.work/executive-ui/' + channel + '-' + width + '.png',fullPage:true});
        checks.push(channel + ':' + width);
      }
    }
    assert.deepEqual(errors,[]);
    assert.deepEqual(external,[]);
    fs.writeFileSync('.work/executive-ui/results.json',JSON.stringify({checks,errors,external},null,2));
    console.log('PASS: ' + checks.length + ' page/viewport combinations; readable type and sampled text contrast >=4.5:1; chart labels readable and unclipped; no page overflow; source/export accessible; source dialog and mobile navigation; no JS/CSP errors or external requests.');
  } finally { await browser.close(); }
})().catch(error => {console.error(error);process.exitCode=1;});
