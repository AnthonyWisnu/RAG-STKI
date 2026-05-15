"""Pydantic schemas for valuation reasoning endpoint."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    """LLM valuation reasoning request."""

    player_name: str = Field(..., min_length=2)
    language: str = Field(default="id", pattern="^(id|en)$")
    use_llm: bool = False


class PredictResponse(BaseModel):
    """LLM valuation reasoning response."""

    player: dict[str, Any]
    current_value: dict[str, Any] | None
    estimated_range: dict[str, Any] | None
    trend_direction: str
    supporting_factors: list[dict[str, Any]]
    explanation: str
    citations: list[dict[str, Any]]
    raw: dict[str, Any]
