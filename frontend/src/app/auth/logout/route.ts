import { NextResponse } from "next/server";

import { authCookieName } from "@/lib/auth";

function publicUrl(request: Request, pathname: string): URL {
  const headers = request.headers;
  const proto =
    headers.get("x-forwarded-proto") ??
    new URL(request.url).protocol.replace(":", "");
  const host = headers.get("x-forwarded-host") ?? headers.get("host") ?? new URL(request.url).host;
  return new URL(pathname, `${proto}://${host}`);
}

function clearCookie(response: NextResponse) {
  response.cookies.set(authCookieName(), "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  return response;
}

function logoutRedirect(request: Request) {
  const response = NextResponse.redirect(publicUrl(request, "/login"));
  return clearCookie(response);
}

export async function GET(request: Request) {
  return logoutRedirect(request);
}

export async function POST() {
  const response = NextResponse.json({ ok: true });
  return clearCookie(response);
}
