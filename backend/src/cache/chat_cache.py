"""SQLite-backed exact cache for chat responses."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from config.settings import get_cached_settings
except ModuleNotFoundError:
    from backend.config.settings import get_cached_settings


class ChatCache:
    """Cache exact repeated chat questions to reduce repeated LLM calls."""

    def __init__(
        self,
        db_path: Path | None = None,
        ttl_seconds: int | None = None,
        enabled: bool | None = None,
    ) -> None:
        settings = get_cached_settings()
        self.db_path = db_path or settings.chat_cache_path
        self.ttl_seconds = ttl_seconds or settings.chat_cache_ttl_seconds
        self.enabled = settings.chat_cache_enabled if enabled is None else enabled

    @staticmethod
    def normalize_question(question: str) -> str:
        """Normalize text for exact cache matching without changing intent."""
        normalized = unicodedata.normalize("NFKC", question).casefold()
        normalized = re.sub(r"\s+", " ", normalized).strip()
        normalized = normalized.strip(" ?!.,;:")
        return normalized

    @staticmethod
    def current_data_version() -> str:
        """Use latest refresh timestamp as cache namespace."""
        settings = get_cached_settings()
        if not settings.refresh_state_path.exists():
            return "no-refresh-state"
        try:
            state = json.loads(
                settings.refresh_state_path.read_text(encoding="utf-8-sig")
            )
        except (OSError, json.JSONDecodeError):
            return "unreadable-refresh-state"
        version = (
            state.get("last_stats_refresh")
            or state.get("last_refresh")
            or state.get("last_initial_setup")
            or "unknown-refresh"
        )
        return str(version)

    def build_key(
        self,
        question: str,
        *,
        use_llm_planner: bool,
        use_llm_valuation: bool,
    ) -> str:
        """Build a stable cache key scoped by model, data version, and flags."""
        settings = get_cached_settings()
        payload = {
            "question": self.normalize_question(question),
            "data_version": self.current_data_version(),
            "model": settings.llm_model_name,
            "use_llm_planner": bool(use_llm_planner),
            "use_llm_valuation": bool(use_llm_valuation),
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(
        self,
        question: str,
        *,
        use_llm_planner: bool,
        use_llm_valuation: bool,
    ) -> dict[str, Any] | None:
        """Return cached response payload if present and still valid."""
        if not self.enabled:
            return None
        cache_key = self.build_key(
            question,
            use_llm_planner=use_llm_planner,
            use_llm_valuation=use_llm_valuation,
        )
        self._ensure_schema()
        now = datetime.now(UTC).isoformat()
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT response_json
                FROM chat_cache
                WHERE cache_key = ? AND expires_at > ?
                """,
                (cache_key, now),
            ).fetchone()
        if row is None:
            return None
        try:
            response = json.loads(str(row[0]))
        except json.JSONDecodeError:
            return None
        response["cached"] = True
        return response

    def set(
        self,
        question: str,
        response: dict[str, Any],
        *,
        use_llm_planner: bool,
        use_llm_valuation: bool,
    ) -> None:
        """Persist a response payload for repeated exact questions."""
        if not self.enabled:
            return
        cache_key = self.build_key(
            question,
            use_llm_planner=use_llm_planner,
            use_llm_valuation=use_llm_valuation,
        )
        now_dt = datetime.now(UTC)
        expires_at = now_dt + timedelta(seconds=self.ttl_seconds)
        payload = dict(response)
        payload["cached"] = False
        self._ensure_schema()
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO chat_cache (
                    cache_key,
                    question_normalized,
                    data_version,
                    response_json,
                    created_at,
                    expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    response_json = excluded.response_json,
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at
                """,
                (
                    cache_key,
                    self.normalize_question(question),
                    self.current_data_version(),
                    json.dumps(payload, ensure_ascii=False, default=str),
                    now_dt.isoformat(),
                    expires_at.isoformat(),
                ),
            )
            conn.commit()

    def prune_expired(self) -> int:
        """Remove expired rows and return count."""
        if not self.enabled:
            return 0
        self._ensure_schema()
        now = datetime.now(UTC).isoformat()
        with closing(self._connect()) as conn:
            cursor = conn.execute("DELETE FROM chat_cache WHERE expires_at <= ?", (now,))
            conn.commit()
            return int(cursor.rowcount)

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _ensure_schema(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_cache (
                    cache_key TEXT PRIMARY KEY,
                    question_normalized TEXT NOT NULL,
                    data_version TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_cache_expires_at
                ON chat_cache(expires_at)
                """
            )
            conn.commit()
