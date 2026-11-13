import { expect, test, type Page } from "@playwright/test";
import { signIn } from "./helpers";

/** End-to-end flows through the real UI and API. Each run uses fresh email addresses. */

const unique = (prefix: string) => `${prefix}.${Date.now()}@example.com`;

/** Read the newest 6-digit code for an address from the dev outbox page. */
async function codeFromOutbox(page: Page, email: string): Promise<string> {
  await page.goto("/dev/outbox");
  const row = page.getByRole("row").filter({ hasText: email }).first();
  const text = await row.innerText();
  return /\b\d{6}\b/.exec(text)![0];
}

test("a student registers, verifies their email with the code and reaches the dashboard", async ({ page }) => {
  const email = unique("student");
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Test Student");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password").fill("a long test passphrase");
  await page.getByLabel("Date of birth").fill("2004-01-15");
  await page.getByRole("button", { name: "Create account" }).click();

  await page.waitForURL("**/verify?**");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Check your email");

  // A wrong code is rejected with a clear message and the form stays usable.
  await page.getByLabel("6-digit code").fill("000000");
  await page.getByRole("button", { name: "Verify email" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("That code is not correct");

  const code = await codeFromOutbox(page, email);
  await page.goto(`/verify?email=${encodeURIComponent(email)}`);
  await page.getByLabel("6-digit code").fill(code);
  await page.getByRole("button", { name: "Verify email" }).click();

  await page.waitForURL("**/dashboard");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Welcome, Test Student");
  await expect(page.getByText("Your role: Student")).toBeVisible();
});

test("an administrator invites staff, who set a password and sign in", async ({ page }) => {
  const email = unique("staff");
  await signIn(page, "administrator");
  await page.goto("/admin/users");
  await page.getByLabel("Full name").fill("Invited Staff");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Role").selectOption("support_staff");
  await page.getByRole("button", { name: "Send invitation" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Invitation sent" })).toBeFocused();
  await expect(page.getByRole("row").filter({ hasText: email })).toContainText("Invited, not yet signed in");
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.waitForURL("**/login");

  await page.goto("/reset-password");
  await page.getByLabel("Email address").fill(email);
  await page.getByRole("button", { name: "Send code" }).click();
  await page.waitForURL("**/reset-password?email=**");
  const code = await codeFromOutbox(page, email);
  await page.goto(`/reset-password?email=${encodeURIComponent(email)}`);
  await page.getByLabel("6-digit code").fill(code);
  await page.getByLabel("New password").fill("staff test passphrase");
  await page.getByRole("button", { name: "Set password" }).click();

  await page.waitForURL("**/login?password=set");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password").fill("staff test passphrase");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/dashboard");
  await expect(page.getByText("Your role: Support staff")).toBeVisible();
});

test("role-restricted pages are not reachable by other roles", async ({ page }) => {
  await page.goto("/admin/users");
  await page.waitForURL("**/login"); // signed out
  await signIn(page, "student");
  await page.goto("/admin/users");
  await page.waitForURL("**/dashboard"); // wrong role
  await expect(page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Users" })).toHaveCount(0);
});

test("the language switch changes the interface and the page language", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "हिन्दी" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "hi");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("साइन इन करें");
  await page.getByRole("button", { name: "English" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
});
