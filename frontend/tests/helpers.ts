import AxeBuilder from "@axe-core/playwright";
import { expect, type Locator, type Page } from "@playwright/test";

export const DEMO_PASSWORD = "Samavesh-Demo-2026";
export const THEMES = ["light", "dark", "contrast"] as const;

/** Seeded demo accounts (backend/app/seed.py). */
export const ACCOUNTS = {
  administrator: "admin@samavesh.example.com",
  nodal_officer: "nodal@samavesh.example.com",
  grievance_officer: "grievance@samavesh.example.com",
  support_staff: "staff@samavesh.example.com",
  student: "student@samavesh.example.com",
  guardian: "guardian@samavesh.example.com",
} as const;
export type RoleName = keyof typeof ACCOUNTS;

export async function signIn(page: Page, role: RoleName) {
  await page.goto("/login");
  await page.getByLabel("Email address").fill(ACCOUNTS[role]);
  await page.getByLabel("Password").fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/dashboard");
}

export async function setPreference(page: Page, name: "theme" | "locale" | "text_size", value: string) {
  await page.context().addCookies([{ name, value, url: "http://localhost:3210" }]);
}

/** Run axe against the current page for WCAG 2.1 A + AA. Any violation fails the test. */
export async function expectNoViolations(page: Page, label: string) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const summary = results.violations.map(
    (v) => `${v.id}: ${v.help} [${v.nodes.map((n) => n.target.join(" ")).join(" | ")}]`,
  );
  expect.soft(summary, `axe violations on ${label}`).toEqual([]);
}

/** Visit a page in every theme, plus once in Hindi, and scan each. */
export async function scanInAllThemes(page: Page, path: string) {
  for (const theme of THEMES) {
    await setPreference(page, "theme", theme);
    await page.goto(path);
    await expectNoViolations(page, `${path} (${theme})`);
  }
  await setPreference(page, "locale", "hi");
  await page.goto(path);
  await expect(page.locator("html")).toHaveAttribute("lang", "hi");
  await expectNoViolations(page, `${path} (hindi)`);
  await setPreference(page, "locale", "en");
}

/** Press Tab until `target` has focus. Fails if it is not reachable by keyboard. */
export async function tabTo(page: Page, target: Locator, maxTabs = 40) {
  for (let i = 0; i < maxTabs; i++) {
    await page.keyboard.press("Tab");
    if (await target.evaluate((el) => el === document.activeElement)) {
      // Every focused control must show a visible focus indicator (WCAG 2.4.7).
      const outline = await target.evaluate((el) => getComputedStyle(el).outlineStyle);
      expect(outline, "focused element has a visible outline").not.toBe("none");
      return;
    }
  }
  throw new Error(`Could not reach ${target} with the Tab key in ${maxTabs} presses`);
}
