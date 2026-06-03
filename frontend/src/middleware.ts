import { NextRequest, NextResponse } from "next/server";

import { authCookieName, authEnabled, verifySessionToken } from "@/lib/auth";

const PUBLIC_PATHS = ["/login", "/auth/login", "/auth/logout"];

function isPublicPath(pathname: string): boolean {
  return (
    PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`)) ||
    pathname.startsWith("/_next/") ||
    pathname === "/favicon.ico" ||
    pathname === "/robots.txt" ||
    pathname === "/sitemap.xml" ||
    /\.[a-zA-Z0-9]+$/u.test(pathname)
  );
}

export async function middleware(request: NextRequest) {
  if (!authEnabled()) {
    return NextResponse.next();
  }

  const { pathname, search } = request.nextUrl;
  const token = request.cookies.get(authCookieName())?.value;
  const session = await verifySessionToken(token);

  if (pathname === "/login" && session) {
    return NextResponse.redirect(new URL("/chat", request.url));
  }

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  if (!session) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image).*)"],
};

