import { expect, test, type Page } from "@playwright/test";
import { ADULT_STUDENT, signIn } from "./helpers";

/** End-to-end flows through the real UI and API. Each run uses fresh email addresses. */

const unique = (prefix: string) => `${prefix}.${Date.now()}@example.com`;

/** Read the newest 6-digit code for an address from the dev outbox page. */
async function codeFromOutbox(page: Page, email: string): Promise<string> {
  await page.goto("/dev/outbox");
  const row = page.getByRole("row").filter({ hasText: email }).first();
  const text = await row.innerText();
  return /\b\d{6}\b/.exec(text)![0];
}

test("support staff draft and submit a plan, log a provision, and see planned versus delivered", async ({ page }) => {
  await signIn(page, "support_staff");
  await page.goto(`${ADULT_STUDENT}/plans`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Accommodation plans for Asha Verma");

  // Draft: an invalid interval is caught and explained, then the corrected plan is saved.
  await page.getByRole("link", { name: "Draft a new plan" }).click();
  await page.getByLabel("Start date").fill("2027-01-10");
  await page.getByLabel("Review date").fill("2027-06-30");
  const scribe = page.getByRole("group", { name: "Scribe" });
  await scribe.getByLabel("Include in this plan").check();
  await scribe.getByLabel("Scribe: Details").fill("Scribe for end-semester papers");
  await scribe.getByLabel("Scribe: Expected every (number of days)").fill("900");
  await page.getByRole("button", { name: "Save draft" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("Enter a whole number of days from 1 to 365");
  await expect(scribe.getByLabel("Include in this plan")).toBeChecked(); // the form was not wiped
  await scribe.getByLabel("Scribe: Expected every (number of days)").fill("45");
  await page.getByRole("button", { name: "Save draft" }).click();
  await page.waitForURL("**/plans?notice=plan_saved**");
  await expect(page.locator("main").getByRole("status").first()).toHaveText("The plan has been saved as a draft.");
  await expect(page.locator("main").getByRole("status").first()).toBeFocused();

  // Submit the newest draft: it is waiting for the nodal officer and is not active.
  const draft = page.getByRole("region", { name: /^Plan \d+, version 1$/ }).filter({ hasText: "Draft – Not active" }).first();
  await draft.getByRole("button", { name: /^Submit plan \d+ for approval$/ }).click();
  await expect(page.locator("main").getByRole("status").filter({ hasText: "submitted to the nodal officer" })).toBeFocused();

  // Log a provision against the approved, active plan.
  const active = page.getByRole("region").filter({ hasText: "Approved – Active" }).first();
  await active.getByText("Log a provision: Extra time").click();
  await active.getByLabel("Notes").first().fill("Quiz 3");
  await active.getByRole("button", { name: "Log provision" }).first().click();
  await expect(page.locator("main").getByRole("status").filter({ hasText: "Provision logged." })).toBeFocused();

  // Planned versus delivered for the current term.
  const summary = page.getByRole("region", { name: "Planned versus delivered" });
  await expect(summary.getByRole("table")).toContainText("Monsoon semester 2026");
  await expect(summary.getByRole("row", { name: /Physical access/ })).toContainText("Not counted");
});

test("students and guardians can read plans but cannot draft or log anything", async ({ page }) => {
  await signIn(page, "student");
  await page.goto(`${ADULT_STUDENT}/plans`);
  await expect(page.getByText("Approved – Active").first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Draft a new plan" })).toHaveCount(0);
  await expect(page.getByText(/^Log a provision/)).toHaveCount(0);
  await page.goto(`${ADULT_STUDENT}/plans/edit`);
  await page.waitForURL("**/dashboard");
});

test("an under-18 student's profile is blocked until consent is recorded, then created with a certificate", async ({ page }) => {
  const email = unique("minor");
  const name = `Minor ${Date.now()}`;

  // 1. A student under 18 registers. They cannot create their own profile.
  await page.goto("/register");
  await page.getByLabel("Full name").fill(name);
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password").fill("a long test passphrase");
  await page.getByLabel("Date of birth").fill("2012-06-01");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL("**/verify?**");
  const code = await codeFromOutbox(page, email);
  await page.goto(`/verify?email=${encodeURIComponent(email)}`);
  await page.getByLabel("6-digit code").fill(code);
  await page.getByRole("button", { name: "Verify email" }).click();
  await page.waitForURL("**/dashboard");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "My support profile" }).click();
  await expect(page.getByText("A support profile cannot be created until consent has been recorded.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save profile" })).toHaveCount(0);
  const studentUrl = page.url();
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.waitForURL("**/login");

  // 2. The nodal officer records a paper consent - person and date - which unlocks the profile.
  await signIn(page, "nodal_officer");
  await page.goto("/students");
  await page.getByRole("link", { name }).click();
  await expect(page.getByRole("button", { name: "Save profile" })).toHaveCount(0);
  await page.getByLabel("Name of the person who consented").fill("Parent Example");
  // Two forms on this page have a "Relationship" field; pick the one in the Consent section.
  await page.getByRole("region", { name: "Consent" }).getByLabel("Relationship to the student").fill("Father");
  await page.getByLabel("Date consent was given").fill("2026-11-01");
  await page.getByRole("button", { name: "Record consent" }).click();
  await expect(page.locator("main").getByRole("status").filter({ hasText: "Consent has been recorded." })).toBeFocused();
  await expect(page.getByText("Parent Example (Father) gave consent on 1 November 2026.")).toBeVisible();

  // 3. Create the profile: every disability field is optional.
  await page.getByLabel("Support needs, in your own words").fill("Needs a scribe for written exams.");
  await page.getByLabel("Low vision").check();
  await page.getByRole("button", { name: "Save profile" }).click();
  await expect(page.locator("main").getByRole("status").filter({ hasText: "Support profile saved." })).toBeFocused();

  // 4. Upload a certificate; the result is announced and the file can be downloaded again.
  const pdf = Buffer.from("%PDF-1.4 test disability certificate");
  await page.getByLabel("Choose a file to upload").setInputFiles({ name: "certificate.pdf", mimeType: "application/pdf", buffer: pdf });
  await page.getByRole("button", { name: "Upload certificate" }).click();
  await expect(page.locator("main").getByRole("status").filter({ hasText: "The certificate has been uploaded." })).toBeFocused();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Download certificate.pdf" }).click(),
  ]);
  expect(download.suggestedFilename()).toBe("certificate.pdf");

  // A file that is not a PDF/JPEG/PNG is refused with a clear message.
  await page.getByLabel("Choose a file to upload").setInputFiles({ name: "notes.pdf", mimeType: "application/pdf", buffer: Buffer.from("plain text") });
  await page.getByRole("button", { name: "Upload certificate" }).click();
  await expect(page.locator("main").getByRole("alert")).toHaveText("The file must be a PDF, JPEG or PNG.");
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.waitForURL("**/login");

  // 5. The student can read the profile but, being under 18, cannot edit it.
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password").fill("a long test passphrase");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/dashboard");
  await page.goto(studentUrl);
  await expect(page.getByText("Needs a scribe for written exams.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save profile" })).toHaveCount(0);
});

test("profiles are hidden from other students and from the grievance officer", async ({ page }) => {
  await signIn(page, "student"); // Asha
  await page.goto("/students/7"); // Imran's profile
  await expect(page.getByRole("heading", { level: 1 })).not.toHaveText("Imran Sheikh");
  await expect(page.getByText("Step-free access")).toHaveCount(0);
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.waitForURL("**/login");

  await signIn(page, "grievance_officer");
  await page.goto("/students");
  await page.waitForURL("**/dashboard");
  await page.goto("/students/6");
  await page.waitForURL("**/dashboard");
});

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
