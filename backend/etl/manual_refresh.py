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
        normalize_club_name,
        merge_fbref_stats,
        normalize_fbref_df,
    )
    from etl.player_id_mapper import PlayerCandidate, normalize_name
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
        normalize_club_name,
        merge_fbref_stats,
        normalize_fbref_df,
    )
    from backend.etl.player_id_mapper import PlayerCandidate, normalize_name
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


def missing_local_transfermarkt_core_files() -> list[str]:
    """Return missing local mapper CSVs."""
    settings = get_cached_settings()
    required = ("players.csv", "clubs.csv")
    return [filename for filename in required if not (settings.raw_data_dir / filename).exists()]


def read_player_candidates_from_graph() -> pd.DataFrame:
    """Build a Transfermarkt-like players DataFrame from the existing Neo4j graph."""
    loader = Neo4jGraphLoader()
    try:
        rows = loader.run_read_query(
            """
            MATCH (p:Player)
            OPTIONAL MATCH (p)-[:PLAYS_POSITION]->(pos:Position)
            OPTIONAL MATCH (p)-[:HAS_VALUATION]->(v:Valuation)
            WITH p, pos, v
            ORDER BY v.valuation_date DESC
            WITH p, pos, collect(v)[0] AS latest_value
            OPTIONAL MATCH (p)-[pf:PLAYS_FOR]->(c:Club)
            WITH p, pos, latest_value, pf, c
            ORDER BY coalesce(pf.is_current, false) DESC, c.name ASC
            WITH p, pos, latest_value, collect({club_id: c.api_id, club_name: c.name})[0] AS club_ref
            OPTIONAL MATCH (club_node:Club {api_id: club_ref.club_id})-[:COMPETES_IN]->(l:League)
            WITH p, pos, latest_value, club_ref, collect(l.id)[0] AS league_id
            RETURN p.api_id AS player_id,
                   p.name AS name,
                   p.birth_date AS date_of_birth,
                   p.nationality AS country_of_citizenship,
                   club_ref.club_id AS current_club_id,
                   club_ref.club_name AS current_club_name,
                   league_id AS league_id,
                   pos.name AS position,
                   p.preferred_foot AS foot,
                   p.height_cm AS height_in_cm,
                   p.photo_url AS image_url,
                   latest_value.market_value_eur AS market_value_in_eur,
                   latest_value.market_value_eur AS highest_market_value_in_eur,
                   p.is_active AS is_active
            """,
            {},
        )
    finally:
        loader.close()

    return pd.DataFrame(rows)


def read_club_lookup_from_graph() -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    """Build club lookup structures from Neo4j when raw clubs.csv is unavailable."""
    loader = Neo4jGraphLoader()
    try:
        rows = loader.run_read_query(
            """
            MATCH (c:Club)
            OPTIONAL MATCH (c)-[:COMPETES_IN]->(l:League)
            RETURN c.api_id AS api_id,
                   c.name AS name,
                   properties(c) AS club_props,
                   collect(l.id)[0] AS league_id
            """,
            {},
        )
    finally:
        loader.close()

    lookup: dict[int, dict[str, Any]] = {}
    club_records: list[dict[str, Any]] = []
    for row in rows:
        api_id = row.get("api_id")
        if api_id is None:
            continue
        club_id = int(api_id)
        club = {
            "api_id": club_id,
            "name": row.get("name") or f"Club {club_id}",
            "founded_year": (row.get("club_props") or {}).get("founded_year"),
            "logo_url": (row.get("club_props") or {}).get("logo_url"),
            "country": (row.get("club_props") or {}).get("country"),
        }
        lookup[club_id] = club
        club_records.append(
            {
                **club,
                "league_id": row.get("league_id"),
                "normalized_name": normalize_club_name(str(club["name"])),
            }
        )
    return lookup, club_records


def build_graph_records_from_existing_graph(fbref_df: pd.DataFrame) -> tuple[list[dict[str, Any]], set[int]]:
    """Build graph records using players/clubs already present in Neo4j."""
    try:
        from etl.initial_setup import (
            SUPPORTED_LEAGUES,
            LEAGUE_NAMES,
            find_club_for_team,
            is_relevant,
            optional_int,
            optional_str,
            season_display,
            stats_properties,
            aggregate_duplicate_stats_records,
        )
        from etl.player_id_mapper import PlayerIdMapper
    except ModuleNotFoundError:
        from backend.etl.initial_setup import (
            SUPPORTED_LEAGUES,
            LEAGUE_NAMES,
            find_club_for_team,
            is_relevant,
            optional_int,
            optional_str,
            season_display,
            stats_properties,
            aggregate_duplicate_stats_records,
        )
        from backend.etl.player_id_mapper import PlayerIdMapper

    players_df = read_player_candidates_from_graph()
    if players_df.empty:
        raise RuntimeError("Mapping pemain di Neo4j kosong. Jalankan initial_setup.py terlebih dahulu.")

    def clean_optional(value: Any) -> Any:
        return None if pd.isna(value) else value

    def clean_int(value: Any) -> int | None:
        if pd.isna(value):
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    candidates: list[PlayerCandidate] = []
    for row in players_df.itertuples(index=False):
        row_data = row._asdict()
        player_id = clean_int(row_data.get("player_id"))
        name = clean_optional(row_data.get("name"))
        if player_id is None or not name:
            continue
        birth_date = clean_optional(row_data.get("date_of_birth"))
        birth_year = int(str(birth_date)[:4]) if birth_date and str(birth_date)[:4].isdigit() else None
        raw_active = clean_optional(row_data.get("is_active"))
        candidates.append(
            PlayerCandidate(
                player_id=player_id,
                name=str(name),
                normalized_name=normalize_name(str(name)),
                birth_year=birth_year,
                nationality=clean_optional(row_data.get("country_of_citizenship")),
                current_club_id=clean_int(row_data.get("current_club_id")),
                current_club_name=clean_optional(row_data.get("current_club_name")),
                league_id=clean_optional(row_data.get("league_id")),
                position=clean_optional(row_data.get("position")) or "Forward",
                sub_position=None,
                preferred_foot=clean_optional(row_data.get("foot")),
                height_cm=clean_int(row_data.get("height_in_cm")),
                birth_date=birth_date,
                photo_url=clean_optional(row_data.get("image_url")),
                market_value_eur=clean_int(row_data.get("market_value_in_eur")),
                highest_market_value_eur=clean_int(row_data.get("highest_market_value_in_eur")),
                is_active=True if raw_active is None else bool(raw_active),
            )
        )

    mapper = PlayerIdMapper(candidates)
    club_lookup, club_records = read_club_lookup_from_graph()
    records: list[dict[str, Any]] = []
    mapped_player_ids: set[int] = set()

    for _, row in fbref_df.iterrows():
        league_id = optional_str(row.get("league"))
        if league_id not in SUPPORTED_LEAGUES:
            continue
        player_name = optional_str(row.get("player"))
        if player_name is None:
            continue
        match = mapper.match(
            player_name=player_name,
            birth_year=optional_int(row.get("born")),
            league_id=league_id,
            club_name=optional_str(row.get("team")),
            nationality=optional_str(row.get("nation")),
        )
        if match is None or not is_relevant(row, match.candidate):
            continue

        candidate = match.candidate
        club = find_club_for_team(
            team_name=optional_str(row.get("team")),
            league_id=league_id,
            club_lookup=club_lookup,
            club_records=club_records,
            fallback_candidate=candidate,
        )
        club_id = int(club["api_id"])
        league_name, league_country = LEAGUE_NAMES[league_id]
        season_id = str(row["season_id"])
        nationality_id = candidate.nationality or "Unknown"
        records.append(
            {
                "player": {
                    "api_id": candidate.player_id,
                    "fbref_id": None,
                    "name": candidate.name,
                    "birth_date": candidate.birth_date,
                    "height_cm": candidate.height_cm,
                    "preferred_foot": candidate.preferred_foot,
                    "photo_url": candidate.photo_url,
                    "nationality": candidate.nationality,
                    "is_active": candidate.is_active,
                    "last_updated": datetime.now(UTC).replace(microsecond=0).isoformat(),
                },
                "club": club,
                "league": {"id": league_id, "name": league_name, "country": league_country},
                "season": {"id": season_id, "display_name": season_display(season_id)},
                "position": {"id": candidate.position, "name": candidate.position},
                "nationality": {
                    "id": nationality_id,
                    "country_name": nationality_id,
                    "country_code": optional_str(row.get("nation")),
                },
                "stats": stats_properties(row, f"{candidate.player_id}_{season_id}_{league_id}", candidate, club_id),
                "plays_for": {
                    "from_date": None,
                    "to_date": None,
                    "is_current": candidate.current_club_id == club_id,
                },
            }
        )
        mapped_player_ids.add(candidate.player_id)

    return aggregate_duplicate_stats_records(records), mapped_player_ids


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

    fbref_df = fetch_active_fbref_stats(
        season=CURRENT_SEASON,
        league=league,
        clear_internal_cache=force,
    )

    missing_core_files = missing_local_transfermarkt_core_files()
    if missing_core_files:
        LOGGER.warning(
            "File mapping Transfermarkt lokal tidak tersedia (%s); memakai mapping dari Neo4j.",
            ", ".join(missing_core_files),
        )
        graph_records, mapped_player_ids = build_graph_records_from_existing_graph(fbref_df)
    else:
        players_df = pd.read_csv(settings.raw_data_dir / "players.csv")
        clubs_df = pd.read_csv(settings.raw_data_dir / "clubs.csv")
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
