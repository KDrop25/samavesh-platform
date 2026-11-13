import { NextResponse, type NextRequest } from "next/server";
import { api } from "@/lib/api";
import { API_PUBLIC_URL } from "@/lib/config";

/**
 * Stable download link. Checks the signed-in user's access with the API, gets a one-minute
 * single-use-purpose token, and redirects the browser to the API to stream the file.
 */
export async function GET(request: NextRequest, ctx: RouteContext<"/files/[id]">) {
  const { id } = await ctx.params;
  if (!/^\d+$/.test(id)) return new NextResponse(null, { status: 404 });
  const result = await api<{ token: string }>(`/files/${id}/token`, { method: "POST" });
  if (!result.ok) {
    return result.status === 401
      ? NextResponse.redirect(new URL("/login", request.url))
      : new NextResponse(null, { status: 404 });
  }
  return NextResponse.redirect(`${API_PUBLIC_URL}/files/${id}?token=${result.data.token}`);
}
