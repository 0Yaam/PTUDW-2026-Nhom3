import { expect, test } from "@playwright/test";

import { apiUrl, loginViaUi, newUser, registerViaApi } from "./helpers";
import { resetRateLimits } from "./global-setup";

test.beforeEach(() => resetRateLimits());

test("visitor registers, signs out and signs back in", async ({ page }) => {
  const user = newUser("reg");
  await page.goto("/#auth");
  await page.locator('.auth-card input[name="fullName"]').fill(user.fullName);
  await page.locator('.auth-card input[name="userName"]').fill(user.userName);
  await page.locator('.auth-card input[name="email"]').fill(user.email);
  await page.locator('.auth-card input[name="password"]').fill(user.password);
  await page.locator(".auth-submit").click();
  await expect(page.locator("#auth-message")).toContainText(user.fullName);
  await expect(page.locator(".auth-tabs")).toHaveCount(0);
  await expect(page.locator(".auth-card form")).toHaveCount(0);

  await page.locator(".auth-card .hero-actions button").click();
  await expect(page.locator("#auth-message")).not.toContainText(user.fullName);
  await expect(page.locator(".auth-tabs")).toBeVisible();
  await expect(page.locator(".auth-card form")).toBeVisible();

  await loginViaUi(page, user);
});

test("author creates a private draft recipe", async ({ page, request }) => {
  const user = newUser("author");
  await registerViaApi(request, user);
  await loginViaUi(page, user);

  await page.goto("/recipes/new");
  const title = `Canh chua E2E ${Date.now()}`;
  await page.locator('input[name="title"]').fill(title);
  await page.locator('textarea[name="description"]').fill("Món canh chua tạo bởi kiểm thử đầu – cuối.");
  const category = page.locator('select[name="categoryId"]');
  await expect(category.locator("option").nth(1)).toBeAttached();
  await category.selectOption({ index: 1 });
  await page.locator('input[name="prepTimeMinutes"]').fill("15");
  await page.locator('input[name="cookTimeMinutes"]').fill("20");
  await page.locator('input[name="servings"]').fill("4");
  await page.locator('textarea[name="instructions"]').fill("Nấu nước dùng, cho cá và rau vào, nêm vừa ăn.");

  const saved = page.waitForResponse((r) => r.url().endsWith("/api/v1/recipes") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Save draft" }).click();
  expect((await saved).status()).toBe(201);
  await expect(page.getByText("Draft saved")).toBeVisible();

  const recipeLink = await page.getByRole("link", { name: "Add recipe photos" }).getAttribute("href");
  expect(recipeLink).toMatch(/^\/recipes\/canh-chua-e2e-/);
  // Drafts are private: the author can open the page, a guest cannot.
  await page.goto(recipeLink!);
  await expect(page.locator("h1")).toContainText(title);
  const guest = await page.request.get(`${apiUrl}/api/v1/recipes${recipeLink!.replace("/recipes", "")}`);
  expect(guest.status()).toBe(403);
});
