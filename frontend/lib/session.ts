import { cache } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { api } from "@/lib/api";
import { SESSION_COOKIE, SESSION_EXP_COOKIE, sessionCookies } from "@/lib/cookie-options";

export type Role =
  | "student"
  | "guardian"
  | "support_staff"
  | "nodal_officer"
  | "grievance_officer"
  | "administrator";

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  locale: string;
  date_of_birth: string | null;
};

export type SessionPayload = { token: string; expires_in: number; user: User };

/** The signed-in user, verified by the API. Cached for the duration of one request. */
export const getUser = cache(async (): Promise<User | null> => {
  if (!(await cookies()).has(SESSION_COOKIE)) return null;
  const result = await api<User>("/auth/me");
  return result.ok ? result.data : null;
});

/**
 * Page guard. This only decides what to render - the API enforces access on every call,
 * so hiding a page is never the security boundary.
 */
export async function requireUser(...roles: Role[]): Promise<User> {
  const user = await getUser();
  if (!user) redirect("/login");
  if (roles.length && !roles.includes(user.role)) redirect("/dashboard");
  return user;
}

export async function setSession(token: string, expiresIn: number) {
  const store = await cookies();
  for (const cookie of sessionCookies(token, expiresIn)) store.set(cookie);
}

export async function clearSession() {
  const store = await cookies();
  store.delete(SESSION_COOKIE);
  store.delete(SESSION_EXP_COOKIE);
}
