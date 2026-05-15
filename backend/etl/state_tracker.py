"""State tracker untuk ETL manual dan initial setup."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from config.settings import get_cached_settings
except ModuleNotFoundError:
    from backend.config.settings import get_cached_settings


def utc_now_iso() -> str:
    """Mengembalikan timestamp UTC dalam format ISO."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class RefreshStateTracker:
    """Pembaca dan penulis `refresh_state.json`."""

    def __init__(self, state_path: Path | None = None) -> None:
        """Membuat tracker state.

        Args:
            state_path: Path file state. Default memakai settings.
        """
        settings = get_cached_settings()
        self.state_path = state_path or settings.refresh_state_path

    def read(self) -> dict[str, Any]:
        """Membaca state dari disk jika tersedia."""
        if not self.state_path.exists():
            return {}
        with self.state_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def write(self, state: dict[str, Any]) -> None:
        """Menulis state ke disk."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.state_path.open("w", encoding="utf-8") as file:
            json.dump(state, file, indent=2, sort_keys=True)

    def mark_initial_setup_complete(
        self,
        stats_records: int,
        valuation_records: int,
        mapped_players: int,
    ) -> dict[str, Any]:
        """Menandai initial setup selesai.

        Args:
            stats_records: Jumlah record PlayerSeasonStats.
            valuation_records: Jumlah record Valuation.
            mapped_players: Jumlah pemain unik yang berhasil dimapping.

        Returns:
            State terbaru.
        """
        state = self.read()
        timestamp = utc_now_iso()
        state.update(
            {
                "initial_setup_completed": True,
                "last_initial_setup": timestamp,
                "last_refresh": timestamp,
                "stats_records": stats_records,
                "valuation_records": valuation_records,
                "mapped_players": mapped_players,
            }
        )
        self.write(state)
        return state

    def mark_manual_refresh_started(
        self,
        mode: str,
        force: bool,
        dry_run: bool,
    ) -> dict[str, Any]:
        """Menandai manual refresh mulai berjalan."""
        state = self.read()
        state.update(
            {
                "manual_refresh_status": "running",
                "manual_refresh_mode": mode,
                "manual_refresh_force": force,
                "manual_refresh_dry_run": dry_run,
                "manual_refresh_started_at": utc_now_iso(),
                "manual_refresh_error": None,
            }
        )
        self.write(state)
        return state

    def mark_manual_refresh_complete(
        self,
        mode: str,
        stats_records: int | None = None,
        valuation_records: int | None = None,
        mapped_players: int | None = None,
        skipped_reason: str | None = None,
    ) -> dict[str, Any]:
        """Menandai manual refresh selesai atau diskip secara aman."""
        state = self.read()
        timestamp = utc_now_iso()
        state.update(
            {
                "manual_refresh_status": "skipped" if skipped_reason else "completed",
                "manual_refresh_completed_at": timestamp,
                "manual_refresh_mode": mode,
                "manual_refresh_error": None,
                "manual_refresh_skipped_reason": skipped_reason,
            }
        )
        if skipped_reason is None:
            state["last_refresh"] = timestamp
            state["last_manual_refresh"] = timestamp
        if stats_records is not None:
            state["stats_records"] = stats_records
        if valuation_records is not None:
            state["valuation_records"] = valuation_records
        if mapped_players is not None:
            state["mapped_players"] = mapped_players
        self.write(state)
        return state

    def mark_manual_refresh_failed(self, error: str) -> dict[str, Any]:
        """Menandai manual refresh gagal."""
        state = self.read()
        state.update(
            {
                "manual_refresh_status": "failed",
                "manual_refresh_failed_at": utc_now_iso(),
                "manual_refresh_error": error,
            }
        )
        self.write(state)
        return state
