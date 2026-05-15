"""Manual refresh routes."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

try:
    from etl.manual_refresh import run_manual_refresh
    from etl.state_tracker import RefreshStateTracker
except ModuleNotFoundError:
    from backend.etl.manual_refresh import run_manual_refresh
    from backend.etl.state_tracker import RefreshStateTracker

router = APIRouter(prefix="/api/refresh", tags=["refresh"])


class RefreshRequest(BaseModel):
    """Request body for manual refresh."""

    mode: Literal["all", "valuations", "stats"] = "all"
    force: bool = False
    dry_run: bool = False


def read_status() -> dict[str, Any]:
    """Read current refresh status."""
    state = RefreshStateTracker().read()
    return {
        "status": state.get("manual_refresh_status", "idle"),
        "mode": state.get("manual_refresh_mode"),
        "started_at": state.get("manual_refresh_started_at"),
        "completed_at": state.get("manual_refresh_completed_at"),
        "failed_at": state.get("manual_refresh_failed_at"),
        "error": state.get("manual_refresh_error"),
        "skipped_reason": state.get("manual_refresh_skipped_reason"),
        "last_refresh": state.get("last_refresh"),
        "last_manual_refresh": state.get("last_manual_refresh"),
        "stats_records": state.get("stats_records"),
        "valuation_records": state.get("valuation_records"),
        "mapped_players": state.get("mapped_players"),
    }


@router.get("/status")
def refresh_status() -> dict[str, Any]:
    """Return manual refresh status."""
    return read_status()


@router.post("/start")
def start_refresh(
    request: RefreshRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Start manual refresh in background."""
    status = read_status()
    if status.get("status") == "running":
        return {"accepted": False, "message": "Refresh masih berjalan.", "status": status}
    background_tasks.add_task(
        run_manual_refresh,
        mode=request.mode,
        force=request.force,
        dry_run=request.dry_run,
    )
    return {
        "accepted": True,
        "message": "Refresh dijadwalkan. Proses berjalan di background.",
        "status": read_status(),
    }
