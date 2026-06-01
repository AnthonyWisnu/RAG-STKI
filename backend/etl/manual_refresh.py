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
    from etl.kaggle_loader import download_transfermarkt_dataset, inspect_dataset_files
    from etl.fbref_scraper import FBrefFetchRequest, FBrefScraper
    from etl.initial_setup import (
        build_graph_records,
        build_valuation_records,
        merge_fbref_stats,
        normalize_fbref_df,
    )
    from config.settings import (
        CURRENT_SEASON,
        PUBLIC_FBREF_STAT_TYPES,
        SOCCERDATA_LEAGUE_NAME,
        get_cached_settings,
    )
except ModuleNotFoundError:
    from backend.etl.neo4j_loader import Neo4jGraphLoader
    from backend.etl.state_tracker import RefreshStateTracker
    from backend.etl.kaggle_loader import download_transfermarkt_dataset, inspect_dataset_files
    from backend.etl.fbref_scraper import FBrefFetchRequest, FBrefScraper
    from backend.etl.initial_setup import (
        build_graph_records,
        build_valuation_records,
        merge_fbref_stats,
        normalize_fbref_df,
    )
    from backend.config.settings import (
        CURRENT_SEASON,
        PUBLIC_FBREF_STAT_TYPES,
        SOCCERDATA_LEAGUE_NAME,
        get_cached_settings,
    )

import pandas as pd

LOGGER = logging.getLogger(__name__)
THROTTLE_HOURS = 24
SOCCERDATA_SEASON_IDS = {
    "2023-2024": "2324",
    "2024-2025": "2425",
    "2025-2026": "2526",
}


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
    last_refresh = parse_timestamp(str(state.get("last_stats_refresh") or state.get("last_refresh") or ""))
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


def read_mapped_player_ids() -> set[int]:
    """Read player ids already available in the graph."""
    loader = Neo4jGraphLoader()
    try:
        rows = loader.run_read_query(
            "MATCH (p:Player) RETURN p.api_id AS player_id",
            {},
        )
    finally:
        loader.close()
    return {int(row["player_id"]) for row in rows if row.get("player_id") is not None}


def ensure_local_transfermarkt_core_files() -> None:
    """Ensure local mapper CSVs exist without downloading Kaggle during stats refresh."""
    settings = get_cached_settings()
    required = ("players.csv", "clubs.csv")
    missing = [filename for filename in required if not (settings.raw_data_dir / filename).exists()]
    if missing:
        raise FileNotFoundError(
            "File mapping Transfermarkt lokal belum lengkap: "
            f"{', '.join(missing)}. Jalankan initial_setup.py dulu."
        )


def clear_soccerdata_fbref_cache(season: str = CURRENT_SEASON) -> list[Path]:
    """Remove soccerdata FBref HTML cache so forced refresh fetches fresh pages."""
    settings = get_cached_settings()
    season_id = SOCCERDATA_SEASON_IDS.get(season)
    if season_id is None:
        raise ValueError(f"Season tidak dikenal untuk cache soccerdata: {season}")

    fbref_cache_dir = settings.soccerdata_dir / "data" / "FBref"
    if not fbref_cache_dir.exists():
        return []

    removed: list[Path] = []
    for stat_type in PUBLIC_FBREF_STAT_TYPES:
        for path in fbref_cache_dir.glob(f"players_*_{season_id}_{stat_type}.html"):
            path.unlink()
            removed.append(path)
            LOGGER.info("Cache internal soccerdata dihapus: %s", path)
    return removed


def fetch_active_fbref_stats(
    season: str = CURRENT_SEASON,
    league: str = SOCCERDATA_LEAGUE_NAME,
    clear_internal_cache: bool = False,
) -> pd.DataFrame:
    """Fetch only the active season from FBref/soccerdata and refresh project cache."""
    if clear_internal_cache:
        removed = clear_soccerdata_fbref_cache(season=season)
        LOGGER.info("Cache internal soccerdata yang dihapus: %s file", len(removed))

    scraper = FBrefScraper()
    stats_by_type: dict[str, pd.DataFrame] = {}
    for stat_type in PUBLIC_FBREF_STAT_TYPES:
        request = FBrefFetchRequest(
            league=league,
            season=season,
            stat_type=stat_type,
        )
        dataframe, result = scraper.fetch_player_stats(request, force_refresh=True)
        LOGGER.info(
            "FBref refresh selesai: league=%s season=%s stat_type=%s rows=%s cache=%s",
            league,
            season,
            stat_type,
            result.row_count,
            result.cache_path,
        )
        stats_by_type[stat_type] = normalize_fbref_df(dataframe, stat_type, season)
    return merge_fbref_stats(stats_by_type)


def refresh_valuations(force_download: bool) -> int:
    """Download latest Transfermarkt CSV and upsert valuations for mapped players."""
    settings = get_cached_settings()
    status = inspect_dataset_files(settings.raw_data_dir)
    if force_download or not status.is_complete:
        download_transfermarkt_dataset(settings.raw_data_dir, force=force_download)

    valuations_df = pd.read_csv(settings.raw_data_dir / "player_valuations.csv")
    mapped_player_ids = read_mapped_player_ids()
    valuation_records = build_valuation_records(valuations_df, mapped_player_ids)

    loader = Neo4jGraphLoader()
    try:
        loader.verify_connectivity()
        loader.setup_constraints()
        return loader.load_valuations(valuation_records)
    finally:
        loader.close()


def parse_refresh_mode(mode: str) -> tuple[str, str]:
    """Split mode into base mode and optional league filter."""
    if ":" not in mode:
        return mode, SOCCERDATA_LEAGUE_NAME
    base_mode, league = mode.split(":", 1)
    return base_mode, league.strip() or SOCCERDATA_LEAGUE_NAME


def refresh_stats(mode: str, force: bool = False) -> dict[str, int]:
    """Refresh active-season FBref stats without resetting graph or downloading Kaggle."""
    settings = get_cached_settings()
    base_mode, league = parse_refresh_mode(mode)
    if base_mode not in {"all", "stats"}:
        raise ValueError(f"Mode refresh statistik tidak dikenal: {mode}")

    ensure_local_transfermarkt_core_files()
    players_df = pd.read_csv(settings.raw_data_dir / "players.csv")
    clubs_df = pd.read_csv(settings.raw_data_dir / "clubs.csv")

    fbref_df = fetch_active_fbref_stats(
        season=CURRENT_SEASON,
        league=league,
        clear_internal_cache=force,
    )
    graph_records, mapped_player_ids = build_graph_records(fbref_df, players_df, clubs_df)

    loader = Neo4jGraphLoader()
    try:
        loader.verify_connectivity()
        loader.setup_constraints()
        loader.load_player_stats(graph_records)
    finally:
        loader.close()

    counts = read_graph_counts()
    counts["refreshed_stats_records"] = len(graph_records)
    counts["refreshed_mapped_players"] = len(mapped_player_ids)
    return counts


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
        if mode == "valuations":
            if not dry_run:
                refresh_valuations(force_download=True)
            counts = read_graph_counts()
        else:
            base_mode, _ = parse_refresh_mode(mode)
            if base_mode not in {"all", "stats"}:
                raise ValueError(f"Mode refresh tidak dikenal: {mode}")
            if dry_run:
                counts = read_graph_counts()
            else:
                counts = refresh_stats(mode=mode, force=force)

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
