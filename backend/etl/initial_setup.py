"""Initial setup ETL untuk Knowledge Graph dan cache data awal."""

from __future__ import annotations

import argparse
import ast
import logging
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
for path in (PROJECT_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from config.settings import (
        PUBLIC_FBREF_STAT_TYPES,
        SOCCERDATA_LEAGUE_NAME,
        SUPPORTED_LEAGUES,
        SUPPORTED_SEASONS,
        TRANSFERMARKT_COMPETITION_TO_LEAGUE,
        get_cached_settings,
    )
    from etl.fbref_scraper import FBrefFetchRequest, FBrefScraper
    from etl.kaggle_loader import download_transfermarkt_dataset, inspect_dataset_files
    from etl.neo4j_loader import Neo4jGraphLoader
    from etl.player_id_mapper import (
        PlayerCandidate,
        PlayerIdMapper,
        build_player_candidates,
        normalize_name,
    )
    from etl.state_tracker import RefreshStateTracker
    from src.utils.logging import configure_logging
except ModuleNotFoundError:
    from backend.config.settings import (
        PUBLIC_FBREF_STAT_TYPES,
        SOCCERDATA_LEAGUE_NAME,
        SUPPORTED_LEAGUES,
        SUPPORTED_SEASONS,
        TRANSFERMARKT_COMPETITION_TO_LEAGUE,
        get_cached_settings,
    )
    from backend.etl.fbref_scraper import FBrefFetchRequest, FBrefScraper
    from backend.etl.kaggle_loader import download_transfermarkt_dataset, inspect_dataset_files
    from backend.etl.neo4j_loader import Neo4jGraphLoader
    from backend.etl.player_id_mapper import (
        PlayerCandidate,
        PlayerIdMapper,
        build_player_candidates,
        normalize_name,
    )
    from backend.etl.state_tracker import RefreshStateTracker
    from backend.src.utils.logging import configure_logging

LOGGER = logging.getLogger(__name__)

LEAGUE_NAMES = {
    "ENG-Premier League": ("Premier League", "England"),
    "ESP-La Liga": ("La Liga", "Spain"),
    "ITA-Serie A": ("Serie A", "Italy"),
    "GER-Bundesliga": ("Bundesliga", "Germany"),
    "FRA-Ligue 1": ("Ligue 1", "France"),
}

FBREF_SEASON_TO_ID = {
    "2324": "2023-2024",
    "2425": "2024-2025",
    "2526": "2025-2026",
}

STANDARD_COLUMNS = {
    "Playing Time|MP": "matches_played",
    "Playing Time|Starts": "starts",
    "Playing Time|Min": "minutes",
    "Playing Time|90s": "nineties",
    "Performance|Gls": "goals",
    "Performance|Ast": "assists",
    "Performance|G-PK": "non_penalty_goals",
    "Performance|PK": "penalty_kicks",
    "Performance|PKatt": "penalty_attempted",
    "Performance|CrdY": "yellow_cards",
    "Performance|CrdR": "red_cards",
}

SHOOTING_COLUMNS = {
    "Standard|Sh": "shots_total",
    "Standard|SoT": "shots_on_target",
    "Standard|SoT%": "shots_on_target_pct",
    "Expected|xG": "xg",
    "Expected|npxG": "non_penalty_xg",
    "Expected|npxG/Sh": "xg_per_shot",
    "Expected|G-xG": "goals_minus_xg",
}

MISC_COLUMNS = {
    "Performance|Fls": "fouls_committed",
    "Performance|Fld": "fouls_drawn",
    "Performance|Off": "offsides",
    "Aerial Duels|Won": "aerial_won",
    "Aerial Duels|Lost": "aerial_lost",
    "Aerial Duels|Won%": "aerial_won_pct",
    "Performance|Recov": "ball_recoveries",
}

KEEPER_COLUMNS = {
    "Performance|GA": "goals_against",
    "Performance|GA90": "goals_against_per_90",
    "Performance|Saves": "saves",
    "Performance|Save%": "save_pct",
    "Performance|CS": "clean_sheets",
    "Performance|CS%": "clean_sheet_pct",
    "Penalty Kicks|PKatt": "penalty_kicks_attempted_gk",
    "Penalty Kicks|PKA": "penalty_kicks_allowed",
    "Penalty Kicks|PKsv": "penalty_kicks_saved",
}

KEY_COLUMNS = ["league", "season_id", "team", "player", "nation", "pos", "age", "born"]
TEAM_NAME_ALIASES = {
    "manchester utd": "manchester united",
    "man utd": "manchester united",
    "wolves": "wolverhampton wanderers",
    "brighton": "brighton hove albion",
    "nott ham forest": "nottingham forest",
    "nottingham forest": "nottingham forest",
    "paris saint germain": "paris saint germain",
    "psg": "paris saint germain",
    "inter": "internazionale",
    "milan": "milan",
    "monchengladbach": "borussia monchengladbach",
    "gladbach": "borussia monchengladbach",
}
CLUB_NOISE_TOKENS = {
    "football",
    "club",
    "fc",
    "cf",
    "afc",
    "ac",
    "ss",
    "sc",
    "s",
    "p",
    "a",
    "sad",
    "spa",
    "gmbh",
    "co",
    "kg",
}
ADDITIVE_STATS_FIELDS = {
    "matches_played",
    "starts",
    "minutes",
    "nineties",
    "yellow_cards",
    "red_cards",
    "goals",
    "assists",
    "non_penalty_goals",
    "penalty_kicks",
    "penalty_attempted",
    "shots_total",
    "shots_on_target",
    "xg",
    "non_penalty_xg",
    "goals_minus_xg",
    "fouls_committed",
    "fouls_drawn",
    "offsides",
    "aerial_won",
    "aerial_lost",
    "ball_recoveries",
    "goals_against",
    "saves",
    "clean_sheets",
    "penalty_kicks_attempted_gk",
    "penalty_kicks_allowed",
    "penalty_kicks_saved",
}


def flatten_column(column: Any) -> str:
    """Mengubah kolom MultiIndex atau string tuple FBref menjadi string stabil."""
    if isinstance(column, tuple):
        left, right = column
        return str(right) if str(left) in {"", "nan"} else f"{left}|{right}".strip("|")
    text = str(column)
    if text.startswith("(") and text.endswith(")"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, tuple) and len(parsed) == 2:
                left, right = parsed
                return str(right) if str(left) == "" else f"{left}|{right}".strip("|")
        except (SyntaxError, ValueError):
            return text
    return text


def normalize_fbref_df(dataframe: pd.DataFrame, stat_type: str, season_id: str) -> pd.DataFrame:
    """Menormalisasi DataFrame FBref menjadi kolom canonical."""
    flattened = dataframe.copy()
    flattened.columns = [flatten_column(column) for column in flattened.columns]
    rename_base = {
        "league": "league",
        "season": "season_raw",
        "team": "team",
        "player": "player",
        "nation": "nation",
        "pos": "pos",
        "age": "age",
        "born": "born",
    }
    if stat_type == "standard":
        rename_map = {**rename_base, **STANDARD_COLUMNS}
    elif stat_type == "shooting":
        rename_map = {**rename_base, **SHOOTING_COLUMNS}
    elif stat_type == "misc":
        rename_map = {**rename_base, **MISC_COLUMNS}
    elif stat_type == "keeper":
        rename_map = {**rename_base, **KEEPER_COLUMNS}
    else:
        raise ValueError(f"stat_type tidak didukung: {stat_type}")

    selected_columns = [column for column in rename_map if column in flattened.columns]
    normalized = flattened[selected_columns].rename(columns=rename_map)
    normalized["season_id"] = season_id
    if "season_raw" in normalized.columns:
        normalized = normalized.drop(columns=["season_raw"])
    if "league" in normalized.columns:
        normalized["league"] = normalized["league"].fillna("GER-Bundesliga")
    for column in KEY_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None
    return normalized


def merge_fbref_stats(stats_by_type: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Menggabungkan standard, shooting, misc, dan keeper stats."""
    base = stats_by_type["standard"].copy()
    for stat_type in ("shooting", "misc", "keeper"):
        dataframe = stats_by_type.get(stat_type)
        if dataframe is None or dataframe.empty:
            continue
        value_columns = [column for column in dataframe.columns if column not in KEY_COLUMNS]
        base = base.merge(
            dataframe[KEY_COLUMNS + value_columns],
            on=KEY_COLUMNS,
            how="left",
        )
    return base


def fetch_all_fbref_stats() -> pd.DataFrame:
    """Fetch semua stat_type publik untuk semua musim scope."""
    scraper = FBrefScraper()
    merged_frames: list[pd.DataFrame] = []
    for season in SUPPORTED_SEASONS:
        stats_by_type: dict[str, pd.DataFrame] = {}
        for stat_type in PUBLIC_FBREF_STAT_TYPES:
            request = FBrefFetchRequest(
                league=SOCCERDATA_LEAGUE_NAME,
                season=season,
                stat_type=stat_type,
            )
            dataframe, result = scraper.fetch_player_stats(request)
            LOGGER.info(
                "FBref ready: season=%s stat_type=%s rows=%s columns=%s cache=%s",
                season,
                stat_type,
                result.row_count,
                result.column_count,
                result.cache_path,
            )
            stats_by_type[stat_type] = normalize_fbref_df(dataframe, stat_type, season)
        merged = merge_fbref_stats(stats_by_type)
        LOGGER.info("Merged FBref season=%s rows=%s columns=%s", season, len(merged), len(merged.columns))
        merged_frames.append(merged)
    return pd.concat(merged_frames, ignore_index=True)


def to_number_or_none(value: Any) -> float | None:
    """Mengubah nilai menjadi float atau None jika data tidak tersedia."""
    if value is None or pd.isna(value):
        return None
    text = str(value).replace(",", "")
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def to_number_or_zero(value: Any) -> float:
    """Mengubah nilai menjadi float; hanya dipakai untuk statistik dasar yang valid bernilai 0."""
    number = to_number_or_none(value)
    return 0.0 if number is None else number


def to_int_or_none(value: Any) -> int | None:
    """Mengubah nilai menjadi int atau None jika data tidak tersedia."""
    number = to_number_or_none(value)
    return None if number is None else int(number)


def to_int_or_zero(value: Any) -> int:
    """Mengubah nilai menjadi int; hanya dipakai untuk statistik dasar yang valid bernilai 0."""
    return int(to_number_or_zero(value))


def optional_int(value: Any) -> int | None:
    """Mengubah nilai menjadi int atau None."""
    if pd.isna(value):
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def optional_str(value: Any) -> str | None:
    """Mengubah nilai menjadi string atau None."""
    if pd.isna(value) or value is None:
        return None
    text = str(value).strip()
    return text or None


def season_display(season_id: str) -> str:
    """Mengubah `2024-2025` menjadi `2024/25`."""
    start, end = season_id.split("-")
    return f"{start}/{end[-2:]}"


def get_candidate_dict(candidates: list[PlayerCandidate]) -> dict[int, PlayerCandidate]:
    """Membuat index kandidat berdasarkan player_id."""
    return {candidate.player_id: candidate for candidate in candidates}


def is_relevant(row: pd.Series, candidate: PlayerCandidate) -> bool:
    """Menerapkan filter relevansi pemain sesuai AGENT.md."""
    minutes = to_int_or_zero(row.get("minutes"))
    matches = to_int_or_zero(row.get("matches_played"))
    market_value = candidate.market_value_eur or 0
    return minutes >= 400 or matches >= 8 or market_value >= 30_000_000


def load_club_lookup(clubs_df: pd.DataFrame) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    """Membuat lookup klub Transfermarkt dari `clubs.csv`."""
    lookup: dict[int, dict[str, Any]] = {}
    club_records: list[dict[str, Any]] = []
    for row in clubs_df.itertuples(index=False):
        row_data = row._asdict()
        club_id = optional_int(row_data.get("club_id"))
        if club_id is None:
            continue
        competition_id = optional_str(row_data.get("domestic_competition_id"))
        league_id = TRANSFERMARKT_COMPETITION_TO_LEAGUE.get(competition_id or "")
        club = {
            "api_id": club_id,
            "name": optional_str(row_data.get("name")) or f"Club {club_id}",
            "founded_year": None,
            "logo_url": None,
            "country": None,
        }
        lookup[club_id] = club
        club_records.append(
            {
                **club,
                "league_id": league_id,
                "normalized_name": normalize_club_name(club["name"]),
            }
        )
    return lookup, club_records


def normalize_club_name(value: str | None) -> str:
    """Menormalisasi nama klub dan alias umum FBref."""
    normalized = normalize_name(value)
    normalized = TEAM_NAME_ALIASES.get(normalized, normalized)
    tokens = [token for token in normalized.split() if token not in CLUB_NOISE_TOKENS]
    cleaned = " ".join(tokens)
    return TEAM_NAME_ALIASES.get(cleaned, cleaned)


def find_club_for_team(
    team_name: str | None,
    league_id: str,
    club_lookup: dict[int, dict[str, Any]],
    club_records: list[dict[str, Any]],
    fallback_candidate: PlayerCandidate,
) -> dict[str, Any]:
    """Mencari klub Transfermarkt paling cocok untuk nama tim FBref."""
    normalized_team = normalize_club_name(team_name)
    exact_league_clubs = [club for club in club_records if club.get("league_id") == league_id]
    scoped_clubs = exact_league_clubs or club_records
    best_club: dict[str, Any] | None = None
    best_score = 0.0
    for club in scoped_clubs:
        normalized_club = str(club["normalized_name"])
        if not normalized_team or not normalized_club:
            continue
        if normalized_team == normalized_club:
            score = 1.0
        elif normalized_team in normalized_club or normalized_club in normalized_team:
            score = 0.94
        else:
            from difflib import SequenceMatcher

            score = SequenceMatcher(None, normalized_team, normalized_club).ratio()
        if club.get("league_id") == league_id:
            score += 0.05
        if score > best_score:
            best_score = score
            best_club = club

    if best_club is not None and best_score >= 0.72:
        return {
            "api_id": best_club["api_id"],
            "name": best_club["name"],
            "founded_year": best_club["founded_year"],
            "logo_url": best_club["logo_url"],
            "country": best_club["country"],
        }

    if fallback_candidate.current_club_id in club_lookup:
        return club_lookup[fallback_candidate.current_club_id]

    fallback_name = team_name or fallback_candidate.current_club_name or "Unknown"
    return {
        "api_id": abs(hash(f"{league_id}:{fallback_name}")) % 1_000_000_000,
        "name": fallback_name,
        "founded_year": None,
        "logo_url": None,
        "country": None,
    }


def stats_properties(row: pd.Series, stats_id: str, candidate: PlayerCandidate, club_id: int) -> dict[str, Any]:
    """Membangun properti node PlayerSeasonStats."""
    props = {
        "id": stats_id,
        "player_id": candidate.player_id,
        "season_id": row["season_id"],
        "league_id": row["league"],
        "club_id": club_id,
        "position": candidate.position,
        "matches_played": to_int_or_zero(row.get("matches_played")),
        "starts": to_int_or_zero(row.get("starts")),
        "minutes": to_int_or_zero(row.get("minutes")),
        "nineties": to_number_or_zero(row.get("nineties")),
        "yellow_cards": to_int_or_zero(row.get("yellow_cards")),
        "red_cards": to_int_or_zero(row.get("red_cards")),
        "goals": to_int_or_zero(row.get("goals")),
        "assists": to_int_or_zero(row.get("assists")),
        "non_penalty_goals": to_int_or_zero(row.get("non_penalty_goals")),
        "penalty_kicks": to_int_or_zero(row.get("penalty_kicks")),
        "penalty_attempted": to_int_or_zero(row.get("penalty_attempted")),
        "shots_total": to_number_or_zero(row.get("shots_total")),
        "shots_on_target": to_number_or_zero(row.get("shots_on_target")),
        "shots_on_target_pct": to_number_or_none(row.get("shots_on_target_pct")),
        "xg": to_number_or_none(row.get("xg")),
        "non_penalty_xg": to_number_or_none(row.get("non_penalty_xg")),
        "xg_per_shot": to_number_or_none(row.get("xg_per_shot")),
        "goals_minus_xg": to_number_or_none(row.get("goals_minus_xg")),
        "fouls_committed": to_number_or_zero(row.get("fouls_committed")),
        "fouls_drawn": to_number_or_zero(row.get("fouls_drawn")),
        "offsides": to_number_or_zero(row.get("offsides")),
        "aerial_won": to_number_or_none(row.get("aerial_won")),
        "aerial_lost": to_number_or_none(row.get("aerial_lost")),
        "aerial_won_pct": to_number_or_none(row.get("aerial_won_pct")),
        "ball_recoveries": to_number_or_none(row.get("ball_recoveries")),
        "goals_against": to_number_or_none(row.get("goals_against")),
        "goals_against_per_90": to_number_or_none(row.get("goals_against_per_90")),
        "saves": to_number_or_none(row.get("saves")),
        "save_pct": to_number_or_none(row.get("save_pct")),
        "clean_sheets": to_number_or_none(row.get("clean_sheets")),
        "clean_sheet_pct": to_number_or_none(row.get("clean_sheet_pct")),
        "penalty_kicks_attempted_gk": to_number_or_none(row.get("penalty_kicks_attempted_gk")),
        "penalty_kicks_allowed": to_number_or_none(row.get("penalty_kicks_allowed")),
        "penalty_kicks_saved": to_number_or_none(row.get("penalty_kicks_saved")),
        "sofascore_rating": None,
        "last_updated": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    return props


def recompute_derived_stats(stats: dict[str, Any]) -> None:
    """Menghitung ulang statistik turunan setelah agregasi multi-klub."""
    shots_total = to_number_or_zero(stats.get("shots_total"))
    shots_on_target = to_number_or_zero(stats.get("shots_on_target"))
    if shots_total > 0:
        stats["shots_on_target_pct"] = round(shots_on_target / shots_total * 100, 2)
        xg = to_number_or_none(stats.get("xg"))
        if xg is not None:
            stats["xg_per_shot"] = round(xg / shots_total, 3)

    aerial_won = to_number_or_none(stats.get("aerial_won"))
    aerial_lost = to_number_or_none(stats.get("aerial_lost"))
    if aerial_won is not None and aerial_lost is not None and aerial_won + aerial_lost > 0:
        stats["aerial_won_pct"] = round(aerial_won / (aerial_won + aerial_lost) * 100, 2)

    matches_played = to_number_or_zero(stats.get("matches_played"))
    clean_sheets = to_number_or_none(stats.get("clean_sheets"))
    if clean_sheets is not None and matches_played > 0:
        stats["clean_sheet_pct"] = round(clean_sheets / matches_played * 100, 2)

    nineties = to_number_or_zero(stats.get("nineties"))
    goals_against = to_number_or_none(stats.get("goals_against"))
    if goals_against is not None and nineties > 0:
        stats["goals_against_per_90"] = round(goals_against / nineties, 2)

    saves = to_number_or_none(stats.get("saves"))
    if saves is not None and goals_against is not None and saves + goals_against > 0:
        stats["save_pct"] = round(saves / (saves + goals_against) * 100, 2)


def add_optional_stat_value(target_value: Any, source_value: Any) -> float | None:
    """Menjumlahkan statistik tanpa mengubah dua nilai kosong menjadi 0 palsu."""
    target_number = to_number_or_none(target_value)
    source_number = to_number_or_none(source_value)
    if target_number is None and source_number is None:
        return None
    return (target_number or 0.0) + (source_number or 0.0)


def aggregate_duplicate_stats_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mengagregasi duplikasi player-season-league sesuai ID stats di spec."""
    grouped: dict[str, dict[str, Any]] = {}
    duplicate_rows = 0
    for record in records:
        stats_id = str(record["stats"]["id"])
        if stats_id not in grouped:
            grouped[stats_id] = record
            continue

        duplicate_rows += 1
        target = grouped[stats_id]
        source_stats = record["stats"]
        target_stats = target["stats"]
        target_minutes = to_number_or_zero(target_stats.get("minutes"))
        source_minutes = to_number_or_zero(source_stats.get("minutes"))

        for field in ADDITIVE_STATS_FIELDS:
            target_stats[field] = add_optional_stat_value(
                target_stats.get(field),
                source_stats.get(field),
            )

        if source_minutes > target_minutes:
            target["club"] = record["club"]
            target["stats"]["club_id"] = record["stats"]["club_id"]
            target["plays_for"] = record["plays_for"]

        recompute_derived_stats(target_stats)

    if duplicate_rows:
        LOGGER.info(
            "Agregasi duplicate PlayerSeasonStats: duplicate_rows=%s final_records=%s",
            duplicate_rows,
            len(grouped),
        )
    return list(grouped.values())


def build_graph_records(
    fbref_df: pd.DataFrame,
    players_df: pd.DataFrame,
    clubs_df: pd.DataFrame,
) -> tuple[list[dict[str, Any]], set[int]]:
    """Membangun record graph dari FBref dan Transfermarkt."""
    candidates = build_player_candidates(players_df)
    mapper = PlayerIdMapper(candidates)
    club_lookup, club_records = load_club_lookup(clubs_df)
    records: list[dict[str, Any]] = []
    mapped_player_ids: set[int] = set()
    unmatched = 0
    filtered = 0

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
        if match is None:
            unmatched += 1
            continue
        candidate = match.candidate
        if not is_relevant(row, candidate):
            filtered += 1
            continue

        club = find_club_for_team(
            team_name=optional_str(row.get("team")),
            league_id=league_id,
            club_lookup=club_lookup,
            club_records=club_records,
            fallback_candidate=candidate,
        )
        club_id = int(club["api_id"])
        league_name, league_country = LEAGUE_NAMES[league_id]
        nationality_id = candidate.nationality or "Unknown"
        season_id = str(row["season_id"])
        stats_id = f"{candidate.player_id}_{season_id}_{league_id}"
        record = {
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
            "stats": stats_properties(row, stats_id, candidate, club_id),
            "plays_for": {
                "from_date": None,
                "to_date": None,
                "is_current": candidate.current_club_id == club_id,
            },
        }
        records.append(record)
        mapped_player_ids.add(candidate.player_id)

    records = aggregate_duplicate_stats_records(records)
    LOGGER.info("Graph records siap: %s", len(records))
    LOGGER.info("Unmatched FBref rows: %s", unmatched)
    LOGGER.info("Filtered rows: %s", filtered)
    LOGGER.info("Mapped unique players: %s", len(mapped_player_ids))
    return records, mapped_player_ids


def build_valuation_records(
    valuations_df: pd.DataFrame,
    mapped_player_ids: set[int],
) -> list[dict[str, Any]]:
    """Membangun records Valuation untuk pemain yang masuk KG."""
    scoped = valuations_df[valuations_df["player_id"].isin(mapped_player_ids)].copy()
    records: list[dict[str, Any]] = []
    for row in scoped.itertuples(index=False):
        row_data = row._asdict()
        player_id = optional_int(row_data.get("player_id"))
        valuation_date = optional_str(row_data.get("date"))
        market_value = optional_int(row_data.get("market_value_in_eur"))
        if player_id is None or valuation_date is None or market_value is None:
            continue
        valuation_id = f"{player_id}_{valuation_date}"
        records.append(
            {
                "player_id": player_id,
                "valuation": {
                    "id": valuation_id,
                    "market_value_eur": market_value,
                    "valuation_date": valuation_date,
                    "source": "Transfermarkt Kaggle",
                },
            }
        )
    LOGGER.info("Valuation records siap: %s", len(records))
    return records


def backup_fbref_cache(cache_dir: Path) -> Path:
    """Membuat backup snapshot folder cache FBref."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_dir = cache_dir.parent / f"fbref_backup_{timestamp}"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    shutil.copytree(cache_dir, backup_dir)
    LOGGER.info("Backup cache FBref dibuat: %s", backup_dir)
    return backup_dir


def build_arg_parser() -> argparse.ArgumentParser:
    """Membuat parser CLI initial setup."""
    parser = argparse.ArgumentParser(description="Initial setup football KG-RAG")
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Gunakan cache parquet yang sudah ada, tanpa fetch FBref baru.",
    )
    parser.add_argument(
        "--season",
        default=None,
        help="Batasi satu musim untuk debugging.",
    )
    parser.add_argument(
        "--reset-graph",
        action="store_true",
        help="Bersihkan graph hasil setup sebelum load ulang.",
    )
    return parser


def main() -> None:
    """Menjalankan initial setup ETL."""
    settings = get_cached_settings()
    configure_logging(settings.log_level, settings.logs_dir / "initial_setup.log")
    args = build_arg_parser().parse_args()

    LOGGER.info("Initial setup dimulai")
    dataset_status = inspect_dataset_files(settings.raw_data_dir)
    if not dataset_status.is_complete:
        download_transfermarkt_dataset(settings.raw_data_dir)
    else:
        LOGGER.info("Dataset Kaggle lokal sudah lengkap")

    players_df = pd.read_csv(settings.raw_data_dir / "players.csv")
    clubs_df = pd.read_csv(settings.raw_data_dir / "clubs.csv")
    valuations_df = pd.read_csv(settings.raw_data_dir / "player_valuations.csv")
    LOGGER.info("CSV loaded: players=%s clubs=%s valuations=%s", len(players_df), len(clubs_df), len(valuations_df))

    if args.season:
        seasons = (args.season,)
    else:
        seasons = SUPPORTED_SEASONS

    if args.skip_fetch:
        frames = []
        for season in seasons:
            stats_by_type = {}
            for stat_type in PUBLIC_FBREF_STAT_TYPES:
                path = settings.fbref_cache_dir / f"{stat_type}_{season}.parquet"
                dataframe = pd.read_parquet(path)
                stats_by_type[stat_type] = normalize_fbref_df(dataframe, stat_type, season)
            frames.append(merge_fbref_stats(stats_by_type))
        fbref_df = pd.concat(frames, ignore_index=True)
    else:
        original_seasons = tuple(SUPPORTED_SEASONS)
        if args.season:
            supported_seasons = (args.season,)
            globals()["SUPPORTED_SEASONS"] = supported_seasons
        fbref_df = fetch_all_fbref_stats()
        globals()["SUPPORTED_SEASONS"] = original_seasons

    graph_records, mapped_player_ids = build_graph_records(fbref_df, players_df, clubs_df)
    valuation_records = build_valuation_records(valuations_df, mapped_player_ids)

    loader = Neo4jGraphLoader()
    try:
        if args.reset_graph:
            loader.reset_graph()
        summary = loader.load_all(graph_records, valuation_records)
    finally:
        loader.close()

    backup_fbref_cache(settings.fbref_cache_dir)
    state = RefreshStateTracker().mark_initial_setup_complete(
        stats_records=summary.player_stats_records,
        valuation_records=summary.valuation_records,
        mapped_players=len(mapped_player_ids),
    )
    LOGGER.info("refresh_state.json updated: %s", state)
    LOGGER.info("Initial setup selesai")


if __name__ == "__main__":
    main()
