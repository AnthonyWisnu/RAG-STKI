"""Application login guard for FastAPI API routes."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

try:
    from config.settings import Settings
except ModuleNotFoundError:
    from backend.config.settings import Settings


AUTH_COOKIE_NAME = "scoutrag_session"


class AppAuthMiddleware(BaseHTTPMiddleware):
    """Protect `/api/*` endpoints with the same signed cookie as Next.js."""

    def __init__(self, app: Any, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings
        if self.settings.app_auth_enabled and len(self.settings.app_auth_secret) < 32:
            raise RuntimeError(
                "APP_AUTH_SECRET must be at least 32 characters when auth is enabled."
            )

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if not self._should_check(request):
            return await call_next(request)

        token = request.cookies.get(AUTH_COOKIE_NAME)
        if not token or not self._verify_token(token):
            return JSONResponse(
                {"detail": "Authentication required."},
                status_code=401,
            )

        return await call_next(request)

    def _should_check(self, request: Request) -> bool:
        if not self.settings.app_auth_enabled:
            return False
        if request.method.upper() == "OPTIONS":
            return False
        return request.url.path.startswith("/api/")

    def _verify_token(self, token: str) -> bool:
        try:
            payload_part, signature_part = token.split(".", 1)
        except ValueError:
            return False

        expected_signature = _sign(payload_part, self.settings.app_auth_secret)
        if not hmac.compare_digest(signature_part, expected_signature):
            return False

        payload = _decode_payload(payload_part)
        if payload is None:
            return False

        return (
            payload.get("sub") == self.settings.app_auth_username
            and isinstance(payload.get("exp"), (int, float))
            and float(payload["exp"]) > time.time()
        )


def _sign(value: str, secret: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _base64url_encode(digest)


def _decode_payload(value: str) -> dict[str, Any] | None:
    try:
        decoded = _base64url_decode(value).decode("utf-8")
        payload = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")
