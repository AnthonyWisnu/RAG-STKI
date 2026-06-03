"""FastAPI middleware package."""

from __future__ import annotations

try:
    from api.middleware.auth import AppAuthMiddleware
except ModuleNotFoundError:
    from backend.api.middleware.auth import AppAuthMiddleware

__all__ = ["AppAuthMiddleware"]

