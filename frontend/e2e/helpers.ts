import { execFileSync } from "node:child_process";
import path from "node:path";

import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8000";
const repoRoot = path.resolve(__dirname, "..", "..");

export type TestUser = { fullName: string; userName: string; email: string; password: string };

export function newUser(prefix: string): TestUser {
  const id = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
  return {
    fullName: `E2E ${prefix} ${id}`,
    userName: `e2e_${prefix}_${id}`.slice(0, 50),
    email: `e2e-${prefix}-${id}@example.com`,
    password: "E2e-Passw0rd!",
  };
}

export async function registerViaApi(request: APIRequestContext, user: TestUser): Promise<void> {
  const response = await request.post(`${apiUrl}/api/v1/auth/register`, { data: user });
  expect(response.status(), await response.text()).toBe(201);
}

/** Grants Admin through the local database, the same way an operator provisions Admins. */
export function promoteToAdmin(email: string): void {
  execFileSync(
    "docker",
    [
      "compose", "exec", "-T", "postgres", "psql", "-U", "culinary", "-d", "culinary_blog",
      "-v", "ON_ERROR_STOP=1", "-c", `UPDATE users SET role = 'Admin' WHERE email = '${email}'`,
    ],
    { cwd: repoRoot, stdio: "pipe" },
  );
}

export function deleteContactMessages(email: string): void {
  if (!/^e2e-[a-z0-9-]+@example\.com$/i.test(email)) {
    throw new Error("Refusing to delete contact messages for a non-E2E email.");
  }
  execFileSync(
    "docker",
    [
      "compose", "exec", "-T", "postgres", "psql", "-U", "culinary", "-d", "culinary_blog",
      "-v", "ON_ERROR_STOP=1", "-c", `DELETE FROM contact_messages WHERE email = '${email}'`,
    ],
    { cwd: repoRoot, stdio: "pipe" },
  );
}

export async function setLocale(page: Page, locale: "en" | "vi"): Promise<void> {
  const url = new URL(process.env.E2E_BASE_URL ?? "http://localhost:3000");
  await page.context().addCookies([{ name: "NEXT_LOCALE", value: locale, domain: url.hostname, path: "/" }]);
}

export async function loginViaUi(page: Page, user: TestUser): Promise<void> {
  await page.goto("/#auth");
  await page.locator(".auth-tabs button").nth(1).click();
  await page.locator('.auth-card input[name="email"]').fill(user.email);
  await page.locator('.auth-card input[name="password"]').fill(user.password);
  await page.locator(".auth-submit").click();
  await expect(page.locator("#auth-message")).toContainText(user.fullName);
  await expect(page.locator(".auth-tabs")).toHaveCount(0);
  await expect(page.locator(".auth-card form")).toHaveCount(0);
}
