import { test } from "@playwright/test";
import {
  ADULT_STUDENT,
  MINOR_STUDENT,
  expectNoViolations,
  scanInAllThemes,
  signIn,
  type RoleName,
} from "./helpers";

/**
 * Every page, in every theme and in Hindi, must pass axe (WCAG 2.1 A + AA).
 * When you add a page, add it here - an unlisted page is an untested page.
 */
const PUBLIC_PAGES = [
  "/",
  "/login",
  "/login?timeout=1",
  "/register",
  "/verify?email=someone@example.com",
  "/reset-password",
  "/reset-password?email=someone@example.com",
  "/settings",
  "/dev/outbox",
];

const PAGES_BY_ROLE: Record<RoleName, string[]> = {
  administrator: ["/dashboard", "/admin/users", "/students", MINOR_STUDENT],
  nodal_officer: ["/dashboard", "/students", ADULT_STUDENT, MINOR_STUDENT],
  grievance_officer: ["/dashboard"],
  support_staff: ["/dashboard", "/students", ADULT_STUDENT, MINOR_STUDENT],
  student: ["/dashboard", ADULT_STUDENT],
  guardian: ["/dashboard", "/students", MINOR_STUDENT],
};

test.describe("axe: public pages", () => {
  for (const path of PUBLIC_PAGES) {
    test(path, async ({ page }) => {
      await scanInAllThemes(page, path);
    });
  }
});

for (const [role, paths] of Object.entries(PAGES_BY_ROLE) as [RoleName, string[]][]) {
  test.describe(`axe: ${role}`, () => {
    for (const path of paths) {
      test(path, async ({ page }) => {
        await signIn(page, role);
        await scanInAllThemes(page, path);
      });
    }
  });
}

test.describe("axe: error states", () => {
  test("sign-in with wrong password", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email address").fill("nobody@example.com");
    await page.getByLabel("Password").fill("definitely wrong");
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.locator("main").getByRole("alert").waitFor();
    await expectNoViolations(page, "/login (error)");
  });

  test("registration with nothing filled in", async ({ page }) => {
    await page.goto("/register");
    await page.getByRole("button", { name: "Create account" }).click();
    await page.locator("main").getByRole("alert").waitFor();
    await expectNoViolations(page, "/register (field errors)");
  });
});
