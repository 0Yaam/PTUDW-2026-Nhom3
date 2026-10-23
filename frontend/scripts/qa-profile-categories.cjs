/* eslint-disable @typescript-eslint/no-require-imports -- standalone CommonJS QA runner */
/* Run after npm run build. Requires Playwright + Chromium on NODE_PATH. */
const assert = require('node:assert/strict');
const http = require('node:http');
const { spawn } = require('node:child_process');
const path = require('node:path');
const { chromium } = require('playwright');

const port = Number(process.env.LAB7_QA_PORT || 3187);
const apiPort = port + 1;
let mode = 'many';
const categories = Array.from({ length: 9 }, (_, i) => ({
  id: `category-${i}`, name: `Category ${i}`, slug: `stable-slug-${i}`,
  description: 'Recipes from our kitchen', image_url: null, recipe_count: i,
}));
const server = http.createServer((req, res) => {
  res.setHeader('Content-Type', 'application/json');
  if (mode === 'error') { res.writeHead(503); res.end('{}'); }
  else res.end(JSON.stringify(mode === 'empty' ? [] : categories));
});
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

(async () => {
  await new Promise(resolve => server.listen(apiPort, '127.0.0.1', resolve));
  const app = spawn(process.execPath, [path.resolve(__dirname, '../node_modules/next/dist/bin/next'), 'start', '-p', String(port)], {
    cwd: path.resolve(__dirname, '..'),
    env: { ...process.env, API_INTERNAL_URL: `http://127.0.0.1:${apiPort}` },
    stdio: 'ignore',
  });
  let browser;
  try {
    const base = `http://localhost:${port}`;
    let ready = false;
    for (let i = 0; i < 80; i++) {
      try { await fetch(`${base}/profile`); ready = true; break; } catch { await pause(250); }
    }
    assert(ready, 'QA app did not start');
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    await context.addCookies([{ name: 'NEXT_LOCALE', value: 'en', url: base }]);
    const page = await context.newPage();
    await page.goto(`${base}/categories`);
    await page.getByRole('heading', { name: 'All recipe categories', exact: true }).waitFor();
    assert.equal(await page.locator('.category-card').count(), 9);
    assert.equal(await page.locator('.category-card a').first().getAttribute('href'), '/categories/stable-slug-0');
    assert.equal(await page.locator('main button').count(), 0);
    assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href').then(v => new URL(v).pathname), '/categories');
    await page.locator('.category-card a').first().focus();
    assert(await page.locator('.category-card a').first().evaluate(el => el === document.activeElement));
    await page.setViewportSize({ width: 390, height: 844 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.equal(await page.locator('header a[href="/categories"]').count() > 0, true);
    console.log('PASS categories: all items, slug links, metadata, keyboard, mobile, no write controls');
    mode = 'empty';
    await page.reload();
    await page.getByRole('heading', { name: 'Our kitchen is getting ready.' }).waitFor();
    mode = 'error';
    await page.reload();
    await page.getByRole('heading', { name: 'Categories could not be loaded' }).waitFor();
    mode = 'many';
    await page.getByRole('button', { name: 'Try again' }).click();
    await page.locator('.category-card').first().waitFor();
    console.log('PASS categories: empty, API failure, retry recovery');

    await page.goto(`${base}/profile`);
    await page.getByRole('link', { name: 'Go to sign in', exact: true }).waitFor();
    let profile = { id: 'one', fullName: 'Han Tester', userName: 'han_tester', avatarUrl: null, email: 'han@example.com', roles: ['Author'] };
    let profileMode = 'success';
    let lastUpdate;
    await page.route('**/api/v1/auth/profile', async route => {
      if (profileMode === 'failure') return route.fulfill({ status: 503, json: { detail: 'Unavailable' } });
      if (route.request().method() === 'PUT') {
        lastUpdate = route.request().postDataJSON();
        if (profileMode === 'duplicate') return route.fulfill({ status: 409, json: { type: 'USER_NAME_TAKEN', detail: 'User name is already taken.' } });
        profile = { ...profile, ...lastUpdate };
      }
      await route.fulfill({ json: profile });
    });
    async function setSession(token) {
      await page.evaluate(token => {
        sessionStorage.setItem('culinary-blog.auth-session', JSON.stringify({ accessToken: token, refreshToken: 'fixture', expiresAt: new Date(Date.now() + 3600000).toISOString(), user: { fullName: 'Han Tester', roles: ['Author'] } }));
        window.dispatchEvent(new Event('culinary-blog:auth-session-changed'));
      }, token);
    }
    await setSession('first');
    await page.locator('input[name="fullName"]').waitFor();
    assert(await page.locator('input[name="email"]').getAttribute('readonly') !== null);
    const save = page.locator('button[type="submit"]');
    assert(await save.isDisabled());
    await page.locator('input[name="fullName"]').fill('Han Updated');
    await save.click();
    await page.waitForFunction(() => document.querySelector('button[type="submit"]')?.disabled);
    assert.equal(lastUpdate.fullName, 'Han Updated');
    assert.deepEqual(Object.keys(lastUpdate).sort(), ['avatarUrl', 'fullName', 'userName']);
    profileMode = 'duplicate';
    await page.locator('input[name="userName"]').fill('someone_else');
    await save.click();
    await page.locator('#user-name-error').waitFor();
    assert.equal(await page.locator('input[name="userName"]').getAttribute('aria-invalid'), 'true');
    profileMode = 'failure';
    await setSession('second');
    await page.getByRole('button', { name: 'Try again' }).waitFor();
    assert.equal(await page.locator('input[name="fullName"]').count(), 0);
    profileMode = 'success';
    profile = { ...profile, id: 'two', fullName: 'Second User' };
    await page.getByRole('button', { name: 'Try again' }).click();
    await page.waitForFunction(() => document.querySelector('input[name="fullName"]')?.value === 'Second User');
    console.log('PASS profile: signed out, unchanged/save, readonly identity, duplicate name, account isolation, retry');
  } finally {
    if (browser) await browser.close();
    app.kill();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
