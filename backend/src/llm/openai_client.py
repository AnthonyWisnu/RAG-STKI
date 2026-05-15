"""Small OpenAI client wrapper with timeout and JSON helpers."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

try:
    from config.settings import get_cached_settings
except ModuleNotFoundError:
    from backend.config.settings import get_cached_settings

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    """LLM response envelope."""

    content: str
    model: str
    parsed_json: dict[str, Any] | None = None


class OpenAIClient:
    """OpenAI wrapper that never hardcodes secrets."""

    def __init__(self, model: str | None = None, timeout_seconds: int | None = None) -> None:
        self.settings = get_cached_settings()
        self.model = model or self.settings.llm_model_name
        self.timeout_seconds = timeout_seconds or self.settings.openai_timeout_seconds
        self._client: Any | None = None

    @property
    def available(self) -> bool:
        """Return True if OpenAI can be called."""
        return bool(self.settings.openai_api_key)

    def client(self) -> Any:
        """Create OpenAI client lazily."""
        if not self.available:
            raise RuntimeError("OPENAI_API_KEY belum tersedia")
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("Package openai belum terpasang") from exc
            self._client = OpenAI(
                api_key=self.settings.openai_api_key,
                timeout=self.timeout_seconds,
            )
        return self._client

    def chat_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Call chat completion and return text."""
        LOGGER.info("OpenAI chat request model=%s", self.model)
        response = self.client().chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        return LLMResponse(content=content, model=self.model)

    def chat_json(
        self,
        system_prompt: str,
        payload: dict[str, Any],
        temperature: float = 0.1,
    ) -> LLMResponse:
        """Call chat completion and parse JSON object output."""
        LOGGER.info("OpenAI JSON request model=%s", self.model)
        response = self.client().chat.completions.create(
            model=self.model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return LLMResponse(
            content=content,
            model=self.model,
            parsed_json=json.loads(content),
        )
