"""Prompt loader for backend LLM modules."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

try:
    from config.settings import get_cached_settings
except ModuleNotFoundError:
    from backend.config.settings import get_cached_settings


class PromptLoader:
    """Load prompt text from `backend/config/prompts`."""

    def __init__(self, prompts_dir: Path | None = None) -> None:
        settings = get_cached_settings()
        self.prompts_dir = prompts_dir or settings.backend_dir / "config" / "prompts"

    @lru_cache(maxsize=32)
    def load(self, filename: str) -> str:
        """Load a prompt by filename."""
        path = self.prompts_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt tidak ditemukan: {path}")
        return path.read_text(encoding="utf-8")
