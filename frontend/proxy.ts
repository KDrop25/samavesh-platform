import { NextResponse, type NextRequest } from "next/server";
import { API_URL } from "@/lib/config";
import { SESSION_COOKIE, SESSION_EXP_COOKIE, sessionCookies } from "@/lib/cookie-options";

const REFRESH_AFTER_SECONDS = 60;

/**
 * Sliding 30-minute idle timeout. Any request (navigation or form submit) counts as activity:
 * if the session token is more than a minute old it is swapped for a fresh one. A token that
 * has already expired cannot be refreshed, so 30 minutes without a request ends the session.
 * Access control is NOT done here - every API call enforces it.
 */
export async function proxy(request: NextRequest) {
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.next();

  let issuedAt = 0;
  try {
    issuedAt = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).iat;
  } catch {
    // unreadable token: fall through and let the API reject it
  }
  if (Date.now() / 1000 - issuedAt < REFRESH_AFTER_SECONDS) return NextResponse.next();

  let refreshed: Response;
  try {
    refreshed = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
  } catch {
    return NextResponse.next(); // API unreachable: keep the current token, pages will report it
  }

  if (!refreshed.ok) {
    const response = NextResponse.next();
    if (refreshed.status === 401) {
      response.cookies.delete(SESSION_COOKIE);
      response.cookies.delete(SESSION_EXP_COOKIE);
    }
    return response;
  }

  const { token: fresh, expires_in } = await refreshed.json();
  request.cookies.set(SESSION_COOKIE, fresh); // so this same request already uses the new token
  const response = NextResponse.next({ request: { headers: request.headers } });
  for (const cookie of sessionCookies(fresh, expires_in)) response.cookies.set(cookie);
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
