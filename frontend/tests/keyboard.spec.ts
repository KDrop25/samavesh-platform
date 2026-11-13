import { expect, test } from "@playwright/test";
import { ACCOUNTS, DEMO_PASSWORD, tabTo } from "./helpers";

/** Keyboard-only walkthroughs: no mouse, no programmatic focus. */

test("skip link is the first stop and moves focus to the main content", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Skip to main content" });
  await expect(skip).toBeFocused();
  await expect(skip).toBeInViewport();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
});

test("sign in, reach the users page and sign out using only the keyboard", async ({ page }) => {
  await page.goto("/login");
  await tabTo(page, page.getByLabel("Email address"));
  await page.keyboard.type(ACCOUNTS.administrator);
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Password")).toBeFocused();
  await page.keyboard.type(DEMO_PASSWORD);
  await page.keyboard.press("Enter");
  await page.waitForURL("**/dashboard");

  await tabTo(page, page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Users" }));
  await page.keyboard.press("Enter");
  await page.waitForURL("**/admin/users");
  await expect(page.getByRole("link", { name: "Users" }).first()).toHaveAttribute("aria-current", "page");

  await tabTo(page, page.getByRole("button", { name: "Sign out" }));
  await page.keyboard.press("Enter");
  await page.waitForURL("**/login");
});

test("a failed form moves focus to an error summary that links to the field", async ({ page }) => {
  await page.goto("/register");
  await tabTo(page, page.getByRole("button", { name: "Create account" }));
  await page.keyboard.press("Enter");

  const summary = page.locator("main").getByRole("alert"); // not Next's own route announcer
  await expect(summary).toBeFocused();
  await expect(summary).toContainText("There is a problem");

  // The first link in the summary takes the user straight to the field it describes.
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  const field = page.getByLabel("Full name");
  await expect(field).toBeFocused();
  await expect(field).toHaveAttribute("aria-invalid", "true");
  await expect(field).toHaveAccessibleDescription(/Enter a value/);
});

test("display settings can be changed by keyboard and announce the result", async ({ page }) => {
  await page.goto("/settings");
  await tabTo(page, page.getByRole("radio", { name: "Match my device" }));
  await page.keyboard.press("ArrowDown"); // Light
  await page.keyboard.press("ArrowDown"); // Dark
  await tabTo(page, page.getByRole("button", { name: "Save settings" }));
  await page.keyboard.press("Enter");

  const status = page.getByRole("status");
  await expect(status).toBeFocused();
  await expect(status).toHaveText("Display settings saved.");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});
