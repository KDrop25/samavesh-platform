import { cookies } from "next/headers";
import { API_URL } from "@/lib/config";
import { SESSION_COOKIE } from "@/lib/cookie-options";

export type ValidationIssue = {
  loc: (string | number)[];
  type: string;
  msg: string;
  ctx?: Record<string, unknown>;
};
export type ApiFailure = { ok: false; status: number; code: string; detail?: ValidationIssue[] };
export type ApiResult<T> = { ok: true; data: T } | ApiFailure;

/**
 * Server-side call to the FastAPI backend. The browser never talks to the API directly:
 * the session JWT lives in an httpOnly cookie on this origin and is forwarded as a bearer token.
 * Pass `token: null` for public endpoints.
 */
export async function api<T = unknown>(
  path: string,
  init: { method?: string; body?: unknown; token?: string | null } = {},
): Promise<ApiResult<T>> {
  const token = init.token === undefined ? (await cookies()).get(SESSION_COOKIE)?.value : init.token;
  let res: Response;
  try {
    res = await fetch(API_URL + path, {
      method: init.method ?? "GET",
      headers: {
        ...(init.body !== undefined && { "Content-Type": "application/json" }),
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      cache: "no-store",
    });
  } catch {
    return { ok: false, status: 503, code: "api_unreachable" };
  }
  if (res.status === 204) return { ok: true, data: undefined as T };
  const json = await res.json().catch(() => null);
  if (res.ok) return { ok: true, data: json as T };
  return {
    ok: false,
    status: res.status,
    code: json?.code ?? (res.status === 422 ? "validation" : "unexpected"),
    detail: Array.isArray(json?.detail) ? json.detail : undefined,
  };
}
