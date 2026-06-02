"""Runtime cache helpers."""

from __future__ import annotations

try:
    from src.cache.chat_cache import ChatCache
except ModuleNotFoundError:
    from backend.src.cache.chat_cache import ChatCache

__all__ = ["ChatCache"]

