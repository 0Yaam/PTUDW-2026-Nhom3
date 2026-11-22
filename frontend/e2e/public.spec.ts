import { expect, test } from "@playwright/test";

import { deleteContactMessages, setLocale } from "./helpers";

test("guest opens the home page and a published recipe", async ({ page }) => {
  await page.goto("/");
  const firstRecipe = page.locator('a[href^="/recipes/"]:not([href="/recipes/new"])').first();
  await expect(firstRecipe).toBeVisible();
  const href = await firstRecipe.getAttribute("href");
  await page.goto(href!);
  await expect(page).toHaveURL(new RegExp(`${href}$`));
  await expect(page.locator("h1")).toBeVisible();
});

test("guest searches recipes without Vietnamese accents", async ({ page }) => {
  await page.goto("/recipes");
  const search = page.locator('input[type="search"]');
  await search.fill("pho");
  const response = page.waitForResponse((r) => r.url().includes("/api/v1/recipes") && r.url().includes("q=pho"));
  await search.press("Enter");
  expect((await response).status()).toBe(200);
  await expect(page.locator('main a[href^="/recipes/"]:not([href="/recipes/new"])').first()).toBeVisible();
});

test("guest switches the interface to Vietnamese", async ({ page }) => {
  await setLocale(page, "vi");
  await page.goto("/#auth");
  await expect(page.locator(".auth-tabs button").nth(1)).toHaveText("Đăng nhập");
  await expect(page.locator("html")).toHaveAttribute("lang", "vi");
});

test("guest sends a contact message", async ({ page }) => {
  const email = `e2e-contact-${Date.now()}@example.com`;
  try {
    await page.goto("/contact");
    await page.locator('input[name="fullName"]').fill("E2E Contact");
    await page.locator('input[name="email"]').fill(email);
    await page.locator('textarea[name="message"]').fill(
      "This message verifies the public contact form.",
    );
    const response = page.waitForResponse(
      (item) => item.url().endsWith("/api/v1/contact") && item.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Send message" }).click();
    expect((await response).status()).toBe(202);
    await expect(page.getByRole("heading", { name: "Message received." })).toBeVisible();
  } finally {
    deleteContactMessages(email);
  }
});

test("tablet header switches to the overflow-safe menu", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 800 });
  await page.goto("/");
  await expect(page.locator(".desktop-nav")).toBeHidden();
  await expect(page.locator(".mobile-nav")).toBeVisible();
  const overflow = await page.locator(".site-header-inner").evaluate(
    (header) => header.scrollWidth > header.clientWidth,
  );
  expect(overflow).toBe(false);
});

test("unknown pages show the not-found screen", async ({ page }) => {
  const response = await page.goto("/khong-ton-tai-e2e");
  expect(response?.status()).toBe(404);
});
