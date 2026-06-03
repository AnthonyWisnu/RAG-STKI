import { NextResponse } from "next/server";

import { authCookieName } from "@/lib/auth";

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
  const response = NextResponse.redirect(new URL("/login", request.url));
  return clearCookie(response);
}

export async function GET(request: Request) {
  return logoutRedirect(request);
}

export async function POST() {
  const response = NextResponse.json({ ok: true });
  return clearCookie(response);
}
