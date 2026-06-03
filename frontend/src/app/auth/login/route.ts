import { NextResponse } from "next/server";

import {
  authCookieName,
  authCookieSecure,
  createSessionToken,
  sessionCookieMaxAge,
  validateLogin,
} from "@/lib/auth";

type LoginPayload = {
  username?: string;
  password?: string;
};

export async function POST(request: Request) {
  let payload: LoginPayload;
  try {
    payload = (await request.json()) as LoginPayload;
  } catch {
    return NextResponse.json({ error: "Payload login tidak valid." }, { status: 400 });
  }

  const username = String(payload.username ?? "").trim();
  const password = String(payload.password ?? "");
  if (!username || !password) {
    return NextResponse.json(
      { error: "Username dan password wajib diisi." },
      { status: 400 },
    );
  }

  if (!validateLogin(username, password)) {
    return NextResponse.json(
      { error: "Username atau password salah." },
      { status: 401 },
    );
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(authCookieName(), await createSessionToken(username), {
    httpOnly: true,
    secure: authCookieSecure(),
    sameSite: "lax",
    path: "/",
    maxAge: sessionCookieMaxAge(),
  });
  return response;
}

