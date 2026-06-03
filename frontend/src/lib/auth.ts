const AUTH_COOKIE_NAME = "scoutrag_session";
const DEFAULT_SESSION_TTL_SECONDS = 60 * 60 * 24 * 7;

type AuthSessionPayload = {
  sub: string;
  iat: number;
  exp: number;
};

type AuthCookieOptions = {
  secure?: boolean;
  now?: number;
};

function isAuthEnabled(): boolean {
  return (process.env.APP_AUTH_ENABLED ?? "false").toLowerCase() === "true";
}

function getAuthUsername(): string {
  return process.env.APP_AUTH_USERNAME ?? "admin";
}

function getAuthPassword(): string {
  return process.env.APP_AUTH_PASSWORD ?? "";
}

function getAuthSecret(): string {
  const secret = process.env.APP_AUTH_SECRET ?? "";
  if (isAuthEnabled() && secret.length < 32) {
    throw new Error("APP_AUTH_SECRET must be at least 32 characters when auth is enabled.");
  }
  return secret;
}

function getSessionTtlSeconds(): number {
  const raw = Number(process.env.APP_AUTH_SESSION_TTL_SECONDS ?? DEFAULT_SESSION_TTL_SECONDS);
  return Number.isFinite(raw) && raw >= 300 ? Math.floor(raw) : DEFAULT_SESSION_TTL_SECONDS;
}

function bytesToBase64Url(bytes: Uint8Array): string {
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/u, "");
}

function base64UrlToBytes(value: string): Uint8Array {
  const normalized = value.replaceAll("-", "+").replaceAll("_", "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  const binary = atob(padded);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

function encodeJson(payload: AuthSessionPayload): string {
  const json = JSON.stringify(payload);
  return bytesToBase64Url(new TextEncoder().encode(json));
}

function decodeJson(value: string): AuthSessionPayload | null {
  try {
    const decoded = new TextDecoder().decode(base64UrlToBytes(value));
    const payload = JSON.parse(decoded) as Partial<AuthSessionPayload>;
    if (
      typeof payload.sub !== "string" ||
      typeof payload.iat !== "number" ||
      typeof payload.exp !== "number"
    ) {
      return null;
    }
    return { sub: payload.sub, iat: payload.iat, exp: payload.exp };
  } catch {
    return null;
  }
}

async function hmacSha256(value: string, secret: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value));
  return bytesToBase64Url(new Uint8Array(signature));
}

function constantTimeEqual(left: string, right: string): boolean {
  const leftBytes = new TextEncoder().encode(left);
  const rightBytes = new TextEncoder().encode(right);
  const length = Math.max(leftBytes.length, rightBytes.length);
  let diff = leftBytes.length ^ rightBytes.length;

  for (let index = 0; index < length; index += 1) {
    diff |= (leftBytes[index] ?? 0) ^ (rightBytes[index] ?? 0);
  }

  return diff === 0;
}

export function authEnabled(): boolean {
  return isAuthEnabled();
}

export function authCookieName(): string {
  return AUTH_COOKIE_NAME;
}

export function validateLogin(username: string, password: string): boolean {
  if (!isAuthEnabled()) {
    return true;
  }
  return (
    constantTimeEqual(username, getAuthUsername()) &&
    constantTimeEqual(password, getAuthPassword())
  );
}

export async function createSessionToken(username: string, options: AuthCookieOptions = {}): Promise<string> {
  const now = options.now ?? Math.floor(Date.now() / 1000);
  const payload = encodeJson({
    sub: username,
    iat: now,
    exp: now + getSessionTtlSeconds(),
  });
  const signature = await hmacSha256(payload, getAuthSecret());
  return `${payload}.${signature}`;
}

export async function verifySessionToken(token: string | undefined, now = Math.floor(Date.now() / 1000)): Promise<AuthSessionPayload | null> {
  if (!isAuthEnabled()) {
    return { sub: getAuthUsername(), iat: now, exp: now + getSessionTtlSeconds() };
  }
  if (!token) {
    return null;
  }

  const [payloadPart, signaturePart] = token.split(".");
  if (!payloadPart || !signaturePart) {
    return null;
  }

  const expectedSignature = await hmacSha256(payloadPart, getAuthSecret());
  if (!constantTimeEqual(signaturePart, expectedSignature)) {
    return null;
  }

  const payload = decodeJson(payloadPart);
  if (!payload || payload.exp <= now || payload.sub !== getAuthUsername()) {
    return null;
  }

  return payload;
}

export function sessionCookieMaxAge(): number {
  return getSessionTtlSeconds();
}

export function authCookieSecure(): boolean {
  return process.env.NODE_ENV === "production";
}

