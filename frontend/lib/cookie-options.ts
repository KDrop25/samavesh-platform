/** Shared by server actions and proxy.ts, so it must not import next/headers. */

export const SESSION_COOKIE = "session";
/** Expiry timestamp (ms). Readable by script so the timeout warning can be shown; holds no secret. */
export const SESSION_EXP_COOKIE = "session_exp";

const secure = process.env.NODE_ENV === "production";

export function sessionCookies(token: string, expiresIn: number) {
  const base = { secure, sameSite: "lax" as const, path: "/", maxAge: expiresIn };
  return [
    { name: SESSION_COOKIE, value: token, ...base, httpOnly: true },
    { name: SESSION_EXP_COOKIE, value: String(Date.now() + expiresIn * 1000), ...base },
  ];
}

export const preferenceCookie = { secure, sameSite: "lax" as const, path: "/", maxAge: 60 * 60 * 24 * 365 };
