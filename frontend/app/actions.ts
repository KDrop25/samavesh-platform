"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { api } from "@/lib/api";
import { preferenceCookie } from "@/lib/cookie-options";
import { failure, pick, type FormState } from "@/lib/form";
import { getLocale, getT, type Locale } from "@/lib/i18n";
import { clearSession, setSession, type SessionPayload } from "@/lib/session";

const emailParam = (email: unknown) => encodeURIComponent(String(email ?? ""));

// ---- Accounts ----

export async function login(_: FormState, form: FormData): Promise<FormState> {
  const t = await getT();
  const body = pick(form, ["email", "password"]);
  const result = await api<SessionPayload>("/auth/login", { method: "POST", body, token: null });
  if (!result.ok) {
    if (result.code === "email_not_verified") redirect(`/verify?email=${emailParam(body.email)}`);
    return failure(t, result, form);
  }
  await setSession(result.data.token, result.data.expires_in);
  redirect("/dashboard");
}

export async function register(_: FormState, form: FormData): Promise<FormState> {
  const t = await getT();
  const fields = pick(form, ["email", "password", "full_name", "role", "date_of_birth"]);
  const body = { ...fields, locale: await getLocale() }; // emails are sent in the language being used
  const result = await api("/auth/register", { method: "POST", body, token: null });
  if (!result.ok) return failure(t, result, form);
  redirect(`/verify?email=${emailParam(fields.email)}`);
}

export async function verifyEmail(_: FormState, form: FormData): Promise<FormState> {
  const t = await getT();
  const body = pick(form, ["email", "code"]);
  const result = await api<SessionPayload>("/auth/verify", { method: "POST", body, token: null });
  if (!result.ok) return failure(t, result, form);
  await setSession(result.data.token, result.data.expires_in);
  redirect("/dashboard");
}

export async function resendCode(_: FormState, form: FormData): Promise<FormState> {
  const t = await getT();
  const result = await api("/auth/resend", { method: "POST", body: pick(form, ["email"]), token: null });
  return result.ok ? { ok: true, message: t("verify.resent") } : failure(t, result);
}

export async function forgotPassword(_: FormState, form: FormData): Promise<FormState> {
  const t = await getT();
  const body = pick(form, ["email"]);
  const result = await api("/auth/password/forgot", { method: "POST", body, token: null });
  if (!result.ok) return failure(t, result, form);
  redirect(`/reset-password?email=${emailParam(body.email)}`);
}

export async function resetPassword(_: FormState, form: FormData): Promise<FormState> {
  const t = await getT();
  const body = pick(form, ["email", "code", "new_password"]);
  const result = await api("/auth/password/reset", { method: "POST", body, token: null });
  if (!result.ok) return failure(t, result, form);
  redirect("/login?password=set");
}

export async function logout() {
  await api("/auth/logout", { method: "POST" });
  await clearSession();
  redirect("/login");
}

/** "Stay signed in" from the timeout warning. */
export async function extendSession(): Promise<boolean> {
  const result = await api<SessionPayload>("/auth/refresh", { method: "POST" });
  if (result.ok) await setSession(result.data.token, result.data.expires_in);
  return result.ok;
}

// ---- Display preferences (stored in cookies on this device) ----

export async function setLanguage(locale: Locale) {
  (await cookies()).set("locale", locale, preferenceCookie);
  revalidatePath("/", "layout");
}

export async function savePreferences(_: FormState, form: FormData): Promise<FormState> {
  const store = await cookies();
  const { theme, text_size, locale } = pick(form, ["theme", "text_size", "locale"]);
  if (theme && ["light", "dark", "contrast"].includes(theme)) store.set("theme", theme, preferenceCookie);
  else store.delete("theme"); // "auto": follow the device
  if (text_size && ["large", "larger"].includes(text_size)) store.set("text_size", text_size, preferenceCookie);
  else store.delete("text_size");
  store.set("locale", locale === "hi" ? "hi" : "en", preferenceCookie);
  revalidatePath("/", "layout");
  const t = await getT();
  return { ok: true, message: t("settings.saved") };
}

// ---- Administration ----

export async function inviteUser(_: FormState, form: FormData): Promise<FormState> {
  const t = await getT();
  const body = pick(form, ["email", "full_name", "role"]);
  const result = await api("/admin/users", { method: "POST", body });
  if (!result.ok) return failure(t, result, form);
  revalidatePath("/admin/users");
  return { ok: true, message: t("users.invited", { email: String(body.email) }) };
}

export async function setUserActive(id: number, name: string, active: boolean): Promise<FormState> {
  const t = await getT();
  const result = await api(`/admin/users/${id}`, { method: "PATCH", body: { is_active: active } });
  if (!result.ok) return failure(t, result);
  revalidatePath("/admin/users");
  return { ok: true, message: t(active ? "users.activated" : "users.deactivated", { name }) };
}

// ---- Students: guardians, consent, staff assignment, support profile ----

/** Run an API call for a student page and turn the outcome into a form result. */
async function studentAction(
  studentId: number,
  path: string,
  init: { method: string; body?: unknown },
  success: string,
  form?: FormData,
): Promise<FormState> {
  const t = await getT();
  const result = await api(`/students/${studentId}${path}`, init);
  if (!result.ok) return failure(t, result, form);
  revalidatePath(`/students/${studentId}`);
  return { ok: true, message: success };
}

export async function inviteGuardian(studentId: number, _: FormState, form: FormData): Promise<FormState> {
  const t = await getT();
  const body = pick(form, ["guardian_email", "relationship"]);
  const message = t("guardians.invited", { email: String(body.guardian_email ?? "") });
  return studentAction(studentId, "/guardians", { method: "POST", body }, message, form);
}

export async function removeGuardian(studentId: number, linkId: number, email: string): Promise<FormState> {
  const t = await getT();
  return studentAction(studentId, `/guardians/${linkId}`, { method: "DELETE" }, t("guardians.removed", { email }));
}

/** Guardian consenting in the app (no fields) or staff recording a paper consent (three fields). */
export async function recordConsent(studentId: number, _: FormState, form: FormData): Promise<FormState> {
  const t = await getT();
  const body = pick(form, ["consenting_person_name", "relationship", "consent_date"]);
  return studentAction(studentId, "/consent", { method: "POST", body }, t("consent.saved"), form);
}

export async function assignStaff(studentId: number, _: FormState, form: FormData): Promise<FormState> {
  const t = await getT();
  const body = { staff_id: Number(form.get("staff_id")) };
  return studentAction(studentId, "/assignments", { method: "POST", body }, t("staff.assigned"), form);
}

export async function endAssignment(studentId: number, assignmentId: number, name: string): Promise<FormState> {
  const t = await getT();
  return studentAction(studentId, `/assignments/${assignmentId}`, { method: "DELETE" }, t("staff.ended", { name }));
}

export async function saveProfile(studentId: number, _: FormState, form: FormData): Promise<FormState> {
  const t = await getT();
  const text = pick(form, [
    "enrollment_no",
    "programme",
    "department",
    "year_of_study",
    "udid_number",
    "benchmark_percentage",
    "support_needs",
    "communication_preference",
  ]);
  const body = { ...text, disability_categories: form.getAll("disability_categories") };
  return studentAction(studentId, "/profile", { method: "PUT", body }, t("profile.saved"), form);
}
