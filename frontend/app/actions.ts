"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { api } from "@/lib/api";
import { ACCOMMODATION_TYPES } from "@/lib/constants";
import { preferenceCookie } from "@/lib/cookie-options";
import { failure, formValues, pick, type FormState } from "@/lib/form";
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

// ---- Accommodation plans, provision log, terms ----

export async function savePlan(
  studentId: number,
  planId: number | null,
  _: FormState,
  form: FormData,
): Promise<FormState> {
  const t = await getT();
  const errors: Record<string, string> = {};
  const items = [];
  for (const type of ACCOMMODATION_TYPES) {
    if (!form.get(`include_${type}`)) continue;
    const raw = String(form.get(`interval_${type}`) ?? "").trim();
    const interval = raw === "" ? null : Number(raw);
    if (interval !== null && !(Number.isInteger(interval) && interval >= 1 && interval <= 365)) {
      errors[`interval_${type}`] = `${t(`type.${type}`)}: ${t("error.interval")}`;
    }
    items.push({ type, details: String(form.get(`details_${type}`) ?? "").trim() || null, interval_days: interval });
  }
  if (Object.keys(errors).length) return { errors, values: formValues(form) };
  if (items.length === 0) return { message: t("error.rule.items"), values: formValues(form) };

  const body = { ...pick(form, ["start_date", "review_date", "notes"]), items };
  const result = planId
    ? await api(`/plans/${planId}`, { method: "PUT", body })
    : await api(`/students/${studentId}/plans`, { method: "POST", body });
  if (!result.ok) return failure(t, result, form);
  redirect(`/students/${studentId}/plans?saved=1`);
}

export async function submitPlan(studentId: number, planId: number): Promise<FormState> {
  const t = await getT();
  const result = await api(`/plans/${planId}/submit`, { method: "POST" });
  if (!result.ok) return failure(t, result);
  revalidatePath(`/students/${studentId}/plans`);
  return { ok: true, message: t("plans.submitted") };
}

export async function logProvision(studentId: number, itemId: number, _: FormState, form: FormData): Promise<FormState> {
  const t = await getT();
  const body = pick(form, ["provided_on", "notes"]);
  const result = await api(`/plan-items/${itemId}/provisions`, { method: "POST", body });
  if (!result.ok) return failure(t, result, form);
  revalidatePath(`/students/${studentId}/plans`);
  return { ok: true, message: t("provision.logged") };
}

export async function addTerm(_: FormState, form: FormData): Promise<FormState> {
  const t = await getT();
  const result = await api("/terms", { method: "POST", body: pick(form, ["name", "start_date", "end_date"]) });
  if (!result.ok) return failure(t, result, form);
  revalidatePath("/terms");
  return { ok: true, message: t("terms.added") };
}
