// Captures the report screenshots (Vietnamese UI) from the running Docker stack.
// Usage: node scripts/report-screenshots.mjs <output-dir>
// Requires E2E_ADMIN_EMAIL / E2E_ADMIN_PASSWORD for an existing Admin account.
import { chromium } from "@playwright/test";
import path from "node:path";

const base = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const out = process.argv[2] ?? "screenshots";
const admin = { email: process.env.E2E_ADMIN_EMAIL, password: process.env.E2E_ADMIN_PASSWORD };

const browser = await chromium.launch({ channel: process.env.E2E_BROWSER_CHANNEL ?? "chrome" });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
await context.addCookies([{ name: "NEXT_LOCALE", value: "vi", domain: new URL(base).hostname, path: "/" }]);
const page = await context.newPage();

async function shot(name, height = 1000) {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(out, `${name}.png`), clip: { x: 0, y: 0, width: 1440, height } });
  console.log("saved", name);
}

await page.goto(`${base}/`);
await shot("home", 1150);

await page.goto(`${base}/recipes`);
await page.locator('input[type="search"]').fill("bánh");
await page.locator('input[type="search"]').press("Enter");
await page.waitForResponse((r) => r.url().includes("/api/v1/recipes") && r.url().includes("q="));
await shot("search", 1050);

await page.goto(`${base}/recipes/pho-bo-ha-noi`);
await shot("detail", 1100);

if (admin.email && admin.password) {
  // Main-site session for the recipe editor.
  await page.goto(`${base}/#auth`);
  await page.locator(".auth-tabs button").nth(1).click();
  await page.locator('.auth-card input[name="email"]').fill(admin.email);
  await page.locator('.auth-card input[name="password"]').fill(admin.password);
  await page.locator(".auth-submit").click();
  await page.locator("#auth-message").filter({ hasText: "Admin" }).waitFor();
  await page.goto(`${base}/recipes/pho-bo-ha-noi/edit`);
  await page.locator('input[name="title"]').waitFor();
  await shot("edit", 1050);

  // Admin workspace has its own sign-in form.
  await page.goto(`${base}/admin/categories`);
  await page.locator('form input[name="email"]').fill(admin.email);
  await page.locator('form input[name="password"]').fill(admin.password);
  await page.locator('form button[type="submit"]').click();
  await page.locator("#category-name").waitFor();
  await page.goto(`${base}/admin/categories#overview`);
  await shot("admin", 980);

  await page.goto(`${base}/admin/users`);
  const form = page.locator('form input[name="email"]');
  if (await form.count()) {
    await form.fill(admin.email);
    await page.locator('form input[name="password"]').fill(admin.password);
    await page.locator('form button[type="submit"]').click();
  }
  await page.getByRole("table").waitFor();
  await shot("users", 1000);
}

await browser.close();
