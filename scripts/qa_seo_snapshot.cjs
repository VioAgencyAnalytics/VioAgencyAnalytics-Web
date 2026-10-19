// Run against scripts/serve_seo_snapshot_qa.py only. Synthetic fixture, never production.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');

(async () => {
  const edge = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
  const browser = await chromium.launch(fs.existsSync(edge)
    ? {headless: true, executablePath: edge} : {headless: true, channel: 'msedge'});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
    const errors = [], requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    page.on('request', request => requests.push(request.url()));
    await page.goto('http://127.0.0.1:18084/reports/rpt_fixture_only?revision=2&section=seo');
    const table = page.locator('#seo-keywords [data-snapshot-table]').first();
    const rows = table.locator('tbody tr:visible');
    await table.locator('[data-page-size]').selectOption('all');
    assert.equal(await rows.count(), 15);
    for (const [rank, expected] of [[5,2], [10,4], [20,6], [30,8], [50,10], [100,12]]) {
      await table.locator('[data-snapshot-rank]').selectOption(String(rank));
      assert.equal(await rows.count(), expected);
      assert.equal(await page.locator(`[data-keyword-tier="${rank}"]`).innerText(), String((expected - 2)));
    }
    await table.locator('[data-snapshot-rank]').selectOption('10');
    await table.locator('[data-snapshot-search]').fill('keyword-0');
    assert.equal(await rows.count(), 1);
    await table.locator('[data-snapshot-search]').fill('no-match');
    assert.equal(await rows.count(), 0);
    await table.locator('[data-snapshot-search]').fill('');
    await table.locator('[data-snapshot-rank]').selectOption('all');
    await table.locator('[data-page-size]').selectOption('10');
    await table.locator('[data-page-next]').click();
    assert.equal(await rows.count(), 5);
    await table.locator('[data-snapshot-rank]').selectOption('5');
    assert.equal(await rows.count(), 2);
    assert.equal(await table.locator('[data-page-number]').innerText(), '1 / 1');
    await table.locator('[data-snapshot-sort="4"]').click();
    assert.equal(await rows.first().getAttribute('data-position'), '1');
    await table.locator('[data-snapshot-sort="4"]').click();
    assert.equal(await rows.first().getAttribute('data-position'), '5');
    await rows.first().locator('[data-snapshot-detail]').click();
    assert.match(await page.locator('#snapshot-detail').innerText(), /Revision 2/);
    await page.locator('#snapshot-detail [data-close-dialog]').click();
    const kpis = await page.locator('#seo-kpis').innerText();
    const chart = page.locator('#seo-trend [data-bundle-chart]').first();
    await chart.locator('svg [tabindex="0"]').first().focus();
    assert.equal(await chart.locator('.pb-chart-tooltip').isVisible(), true);
    await page.locator('#date-range').click();
    await page.locator('#date-start').fill('2026-09-01');
    await page.locator('#date-end').fill('2026-09-03');
    await page.locator('#date-form button.confirm-button').click();
    assert.equal(await rows.count(), 0);
    assert.equal(await page.locator('#seo-kpis').innerText(), kpis);
    assert.equal(await chart.locator('.pb-chart-tooltip').isVisible(), false);
    assert.match(await page.locator('#snapshot-filter-status').innerText(), /2026-09-03/);
    await page.locator('#date-range').click();
    await page.locator('#date-end').fill('2026-09-30');
    await page.locator('#date-form button.confirm-button').click();
    assert.equal(await rows.count(), 2);
    const series = page.locator('[data-snapshot-series]').first();
    const options = await series.locator('option').count();
    for (let i=0; i<options; i++) {
      await series.selectOption(String(i));
      assert.equal(await page.locator('#seo-trend [data-bundle-chart]:visible').count(), 1);
    }
    await page.locator('#export-report').click();
    const downloadPromise = page.waitForEvent('download');
    await page.locator('#export-csv').click();
    const download = await downloadPromise;
    assert.match(download.suggestedFilename(), /rpt_fixture_only-r2/);
    const csv = fs.readFileSync(await download.path(), 'utf8');
    assert.match(csv, /keyword-0/);
    assert.doesNotMatch(csv, /keyword-2/);
    await page.keyboard.press('Escape');
    await table.locator('[data-snapshot-rank]').selectOption('all');
    fs.mkdirSync('.work', {recursive: true});
    await page.locator('#dashboard-toast').waitFor({state: 'hidden'});
    for (const [width, height, label] of [[1440,1000,'desktop'], [1024,768,'tablet-landscape'], [768,1024,'tablet'], [390,844,'mobile'], [360,800,'mobile-small']]) {
      await page.setViewportSize({width, height});
      if (width < 1024) {
        await page.locator('#sidebar-toggle').click();
        assert.equal(await page.locator('#sidebar-toggle').getAttribute('aria-expanded'), 'true');
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('#sidebar-toggle').getAttribute('aria-expanded'), 'false');
      }
      await page.evaluate(() => scrollTo(0,0));
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `overflow at ${width}`);
      await page.screenshot({path: `.work/seo-snapshot-${label}.png`, fullPage: true});
    }
    assert.deepEqual(errors, []);
    assert.ok(requests.every(url => url.startsWith('http://127.0.0.1:18084/')));
    assert.ok(!requests.some(url => url.includes('/api/v1/reports/seo')));
    console.log('PASS: six cumulative Top K filters, search, sort, pagination, detail, date scope, unchanged KPIs, charts, CSV, 5 responsive widths, no JS/CSP errors or external requests.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
