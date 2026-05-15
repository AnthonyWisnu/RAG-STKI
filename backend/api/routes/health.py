"""Health and freshness endpoint."""

from __future__ import annotations

import json

from fastapi import APIRouter

try:
    from config.settings import get_cached_settings
except ModuleNotFoundError:
    from backend.config.settings import get_cached_settings

router = APIRouter(prefix="/api", tags=["health"])


def freshness_badge(state: dict[str, object]) -> str:
    """Build a small freshness badge for frontend display."""
    if not state.get("initial_setup_completed"):
        return "Belum ada data refresh"
    last_refresh = state.get("last_refresh") or state.get("last_initial_setup")
    return f"Data siap - refresh {last_refresh}" if last_refresh else "Data siap"


@router.get("/health")
def health_check() -> dict[str, object]:
    """Return API and data freshness status."""
    settings = get_cached_settings()
    state: dict[str, object] = {}
    if settings.refresh_state_path.exists():
        state = json.loads(settings.refresh_state_path.read_text(encoding="utf-8"))
    return {
        "status": "ok",
        "last_refresh": state.get("last_refresh"),
        "data_freshness_badge": freshness_badge(state),
        "stats_records": state.get("stats_records"),
        "valuation_records": state.get("valuation_records"),
        "mapped_players": state.get("mapped_players"),
    }
