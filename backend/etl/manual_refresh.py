"""Manual incremental refresh runner.

Modul ini tidak menjalankan initial setup ulang. Refresh membaca
`refresh_state.json`, memakai throttle 24 jam secara default, dan memperbarui
state berdasarkan data terakhir yang sudah ada di Neo4j.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
for path in (PROJECT_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from etl.neo4j_loader import Neo4jGraphLoader
    from etl.state_tracker import RefreshStateTracker
except ModuleNotFoundError:
    from backend.etl.neo4j_loader import Neo4jGraphLoader
    from backend.etl.state_tracker import RefreshStateTracker

LOGGER = logging.getLogger(__name__)
THROTTLE_HOURS = 24


def parse_timestamp(value: str | None) -> datetime | None:
    """Parse ISO timestamp from refresh state."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def should_throttle(state: dict[str, Any], force: bool) -> str | None:
    """Return throttle reason when refresh should be skipped."""
    if force:
        return None
    last_refresh = parse_timestamp(str(state.get("last_refresh") or ""))
    if last_refresh is None:
        return None
    if datetime.now(UTC) - last_refresh < timedelta(hours=THROTTLE_HOURS):
        return f"Refresh terakhir kurang dari {THROTTLE_HOURS} jam. Gunakan force untuk bypass."
    return None


def read_graph_counts() -> dict[str, int]:
    """Read current graph counts without rewriting data."""
    loader = Neo4jGraphLoader()
    try:
        rows = loader.run_read_query(
            """
            MATCH (s:PlayerSeasonStats)
            WITH count(s) AS stats_records
            MATCH (v:Valuation)
            WITH stats_records, count(v) AS valuation_records
            MATCH (p:Player)
            RETURN stats_records, valuation_records, count(p) AS mapped_players
            """,
            {},
        )
    finally:
        loader.close()
    if not rows:
        return {"stats_records": 0, "valuation_records": 0, "mapped_players": 0}
    return {
        "stats_records": int(rows[0].get("stats_records") or 0),
        "valuation_records": int(rows[0].get("valuation_records") or 0),
        "mapped_players": int(rows[0].get("mapped_players") or 0),
    }


def run_manual_refresh(
    mode: str = "all",
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run state-aware manual refresh.

    Args:
        mode: `all`, `valuations`, or `stats`.
        force: Bypass 24-hour throttle.
        dry_run: Preview without updating `last_refresh`.

    Returns:
        Updated refresh state.
    """
    tracker = RefreshStateTracker()
    state = tracker.read()
    if state.get("manual_refresh_status") == "running":
        return state

    skipped_reason = should_throttle(state, force)
    if skipped_reason:
        return tracker.mark_manual_refresh_complete(mode=mode, skipped_reason=skipped_reason)

    tracker.mark_manual_refresh_started(mode=mode, force=force, dry_run=dry_run)
    try:
        counts = read_graph_counts()
        if dry_run:
            return tracker.mark_manual_refresh_complete(
                mode=mode,
                stats_records=counts["stats_records"],
                valuation_records=counts["valuation_records"],
                mapped_players=counts["mapped_players"],
                skipped_reason="Dry run selesai. Tidak ada write refresh.",
            )
        return tracker.mark_manual_refresh_complete(
            mode=mode,
            stats_records=counts["stats_records"],
            valuation_records=counts["valuation_records"],
            mapped_players=counts["mapped_players"],
        )
    except Exception as exc:
        LOGGER.exception("Manual refresh gagal")
        return tracker.mark_manual_refresh_failed(str(exc))


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="Run manual incremental refresh")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", choices=["valuations", "stats"], default=None)
    parser.add_argument("--league", default=None)
    return parser


def main() -> None:
    """CLI entry point."""
    args = build_arg_parser().parse_args()
    mode = args.only or "all"
    if args.league:
        mode = f"{mode}:{args.league}"
    state = run_manual_refresh(mode=mode, force=args.force, dry_run=args.dry_run)
    print(state)


if __name__ == "__main__":
    main()
