"""Pydantic schemas for player and related endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PlayerSearchResponse(BaseModel):
    """Search response."""

    items: list[dict[str, Any]]
    page: int
    page_size: int
    total: int
    has_next: bool


class PlayerDetailResponse(BaseModel):
    """Player detail response."""

    player: dict[str, Any]
    stats_by_season: list[dict[str, Any]]
    valuation_history: list[dict[str, Any]]


class CompareRequest(BaseModel):
    """Compare request."""

    player_ids: list[int] = Field(default_factory=list, max_length=4)
    player_names: list[str] = Field(default_factory=list, max_length=4)


class CompareResponse(BaseModel):
    """Compare response."""

    players: list[dict[str, Any]]
    radar_data: list[dict[str, Any]]
    narrative: str
    citations: list[dict[str, Any]]


class TopPerformersResponse(BaseModel):
    """Top performers response."""

    category: str
    season: str
    league: str | None
    items: list[dict[str, Any]]
    citations: list[dict[str, Any]]


class ClubResponse(BaseModel):
    """Club response."""

    club: dict[str, Any]
    squad: list[dict[str, Any]]
    top_scorers: list[dict[str, Any]]
    total_squad_value: int
