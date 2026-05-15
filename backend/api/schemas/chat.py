"""Pydantic schemas for chat endpoint."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request payload."""

    question: str = Field(..., min_length=2)
    use_llm_planner: bool = False
    use_llm_valuation: bool = False


class ChatResponse(BaseModel):
    """Chat response payload."""

    answer: str
    strategy_used: Literal["kg_only", "vector_only", "hybrid", "valuation_reasoning"]
    language: Literal["id", "en"]
    data_available: bool
    citations: list[dict[str, Any]]
    context: dict[str, Any]
    fallback_signal: str | None = None
