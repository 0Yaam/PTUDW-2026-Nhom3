import { expect, test, type Page } from "@playwright/test";

import { newUser, promoteToAdmin, registerViaApi, setLocale, type TestUser } from "./helpers";
import { resetRateLimits } from "./global-setup";

test.beforeEach(() => resetRateLimits());

async function adminSignIn(page: Page, user: TestUser, path = "/admin/categories"): Promise<void> {
  await page.goto(path);
  await page.locator('form input[name="email"]').fill(user.email);
  await page.locator('form input[name="password"]').fill(user.password);
  await page.locator('form button[type="submit"]').click();
}

test.describe("admin workspace", () => {
  const admin = newUser("admin");
  const author = newUser("plain");

  test.beforeAll(async ({ request }) => {
    resetRateLimits();
    await registerViaApi(request, admin);
    await registerViaApi(request, author);
    promoteToAdmin(admin.email);
  });

  test("admin creates a category in the Vietnamese workspace", async ({ page }) => {
    await setLocale(page, "vi");
    await adminSignIn(page, admin);
    await expect(page.locator("#category-name")).toBeVisible();

    const name = `E2E ${Date.now().toString(36)}`;
    await page.locator("#category-name").fill(name);
    const created = page.waitForResponse(
      (r) => r.url().endsWith("/api/v1/categories") && r.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Tạo danh mục" }).click();
    expect((await created).status()).toBe(201);
    await expect(page.getByText(name).first()).toBeVisible();
    // The Vietnamese workspace must not leak untranslated column labels.
    await expect(page.getByRole("columnheader", { name: /^Slug$/ })).toHaveCount(0);
  });

  test("admin finds users with Vietnamese role labels", async ({ page }) => {
    await setLocale(page, "vi");
    await adminSignIn(page, admin, `/admin/users?q=${encodeURIComponent(admin.email)}`);
    await expect(page.getByRole("cell", { name: admin.email })).toBeVisible();
    await expect(page.getByText("Quản trị viên").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Tải lại danh sách" }).first()).toBeVisible();
    await expect(page.locator("aside").getByText(/^Admin$/)).toHaveCount(0);
  });

  test("author is refused by the admin sign-in", async ({ page }) => {
    await page.goto("/admin/categories");
    await page.locator('form input[name="email"]').fill(author.email);
    await page.locator('form input[name="password"]').fill(author.password);
    await page.locator('form button[type="submit"]').click();
    await expect(page.locator('p[role="alert"]')).toHaveText("This account does not have Admin access.");
  });
});
