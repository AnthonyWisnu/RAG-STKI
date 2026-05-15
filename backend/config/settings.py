"""Konfigurasi terpusat untuk backend football KG-RAG."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv(dotenv_path: Path | None = None) -> bool:
        """Mengizinkan import settings sebelum dependency dipasang."""
        return False


PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
BACKEND_DIR: Final[Path] = PROJECT_ROOT / "backend"

load_dotenv(BACKEND_DIR / ".env")

SUPPORTED_LEAGUES: Final[dict[str, str]] = {
    "ENG-Premier League": "Premier League",
    "ESP-La Liga": "La Liga",
    "ITA-Serie A": "Serie A",
    "GER-Bundesliga": "Bundesliga",
    "FRA-Ligue 1": "Ligue 1",
}

SOCCERDATA_LEAGUE_NAME: Final[str] = "Big 5 European Leagues Combined"
SUPPORTED_SEASONS: Final[tuple[str, ...]] = (
    "2023-2024",
    "2024-2025",
    "2025-2026",
)
CURRENT_SEASON: Final[str] = "2025-2026"

PUBLIC_FBREF_STAT_TYPES: Final[tuple[str, ...]] = (
    "standard",
    "shooting",
    "misc",
    "keeper",
)
KAGGLE_TRANSFERMARKT_DATASET: Final[str] = "davidcariboo/player-scores"
REQUIRED_TRANSFERMARKT_FILES: Final[tuple[str, ...]] = (
    "players.csv",
    "clubs.csv",
    "competitions.csv",
    "player_valuations.csv",
)
TRANSFERMARKT_COMPETITION_TO_LEAGUE: Final[dict[str, str]] = {
    "GB1": "ENG-Premier League",
    "ES1": "ESP-La Liga",
    "IT1": "ITA-Serie A",
    "L1": "GER-Bundesliga",
    "FR1": "FRA-Ligue 1",
}

UNAVAILABLE_STAT_TYPES: Final[tuple[str, ...]] = (
    "passing",
    "gca",
    "defense",
    "possession",
    "keeper_adv",
)

PLAYER_RELEVANCE_MIN_MINUTES: Final[int] = 400
PLAYER_RELEVANCE_MIN_MATCHES: Final[int] = 8
PLAYER_RELEVANCE_MIN_MARKET_VALUE_EUR: Final[int] = 30_000_000
MIN_SOCCERDATA_DELAY_SECONDS: Final[int] = 6
DEFAULT_CORS_ORIGINS: Final[tuple[str, ...]] = ("http://localhost:3000",)
DEFAULT_EMBEDDING_MODEL_NAME: Final[str] = "intfloat/multilingual-e5-base"
DEFAULT_CHROMA_COLLECTION_NAME: Final[str] = "football_kg_documents"
DEFAULT_DOCUMENT_BATCH_SIZE: Final[int] = 64
DEFAULT_LLM_MODEL_NAME: Final[str] = "gpt-4o-mini"
DEFAULT_OPENAI_TIMEOUT_SECONDS: Final[int] = 45

UCL_UNAVAILABLE_MESSAGE: Final[str] = (
    "Data Champions League tidak tersedia dalam sistem ini."
)
NO_DATA_MESSAGE: Final[str] = "Data tidak tersedia dalam sistem."


def _get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _get_int_env(name: str, default: int) -> int:
    raw_value = _get_env(name, str(default))
    try:
        return int(raw_value)
    except ValueError:
        return default


def _split_csv(value: str) -> tuple[str, ...]:
    items = [item.strip() for item in value.split(",")]
    return tuple(item for item in items if item)


def _resolve_backend_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return BACKEND_DIR / path


@dataclass(frozen=True)
class Settings:
    """Nilai konfigurasi runtime yang dibaca dari environment."""

    project_root: Path
    backend_dir: Path
    raw_data_dir: Path
    processed_data_dir: Path
    refresh_state_path: Path
    fbref_cache_dir: Path
    wiki_cache_dir: Path
    chroma_persist_dir: Path
    soccerdata_dir: Path
    logs_dir: Path
    openai_api_key: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    kaggle_username: str
    kaggle_key: str
    soccerdata_delay: int
    soccerdata_no_cache: bool
    embedding_model_name: str
    chroma_collection_name: str
    document_batch_size: int
    llm_model_name: str
    openai_timeout_seconds: int
    log_level: str
    cors_origins: tuple[str, ...]


def get_settings() -> Settings:
    """Mengembalikan konfigurasi backend dengan validasi minimal."""
    soccerdata_delay = max(
        _get_int_env("SOCCERDATA_DELAY", MIN_SOCCERDATA_DELAY_SECONDS),
        MIN_SOCCERDATA_DELAY_SECONDS,
    )
    cors_origins = _split_csv(_get_env("CORS_ORIGINS", ""))
    if not cors_origins:
        cors_origins = DEFAULT_CORS_ORIGINS

    return Settings(
        project_root=PROJECT_ROOT,
        backend_dir=BACKEND_DIR,
        raw_data_dir=BACKEND_DIR / "data" / "raw",
        processed_data_dir=BACKEND_DIR / "data" / "processed",
        refresh_state_path=BACKEND_DIR / "data" / "refresh_state.json",
        fbref_cache_dir=BACKEND_DIR / "cache" / "fbref",
        wiki_cache_dir=BACKEND_DIR / "cache" / "wiki",
        chroma_persist_dir=_resolve_backend_path(
            _get_env("CHROMA_PERSIST_DIR", "data/chroma")
        ),
        soccerdata_dir=_resolve_backend_path(
            _get_env("SOCCERDATA_DIR", "cache/soccerdata")
        ),
        logs_dir=BACKEND_DIR / "logs",
        openai_api_key=_get_env("OPENAI_API_KEY"),
        neo4j_uri=_get_env("NEO4J_URI"),
        neo4j_user=_get_env("NEO4J_USER", "neo4j"),
        neo4j_password=_get_env("NEO4J_PASSWORD"),
        kaggle_username=_get_env("KAGGLE_USERNAME"),
        kaggle_key=_get_env("KAGGLE_KEY"),
        soccerdata_delay=soccerdata_delay,
        soccerdata_no_cache=_get_env("SOCCERDATA_NOCACHE", "false").lower()
        in {"1", "true", "yes"},
        embedding_model_name=_get_env(
            "EMBEDDING_MODEL_NAME",
            DEFAULT_EMBEDDING_MODEL_NAME,
        ),
        chroma_collection_name=_get_env(
            "CHROMA_COLLECTION_NAME",
            DEFAULT_CHROMA_COLLECTION_NAME,
        ),
        document_batch_size=max(
            _get_int_env("DOCUMENT_BATCH_SIZE", DEFAULT_DOCUMENT_BATCH_SIZE),
            1,
        ),
        llm_model_name=_get_env("LLM_MODEL_NAME", DEFAULT_LLM_MODEL_NAME),
        openai_timeout_seconds=max(
            _get_int_env("OPENAI_TIMEOUT_SECONDS", DEFAULT_OPENAI_TIMEOUT_SECONDS),
            1,
        ),
        log_level=_get_env("LOG_LEVEL", "INFO"),
        cors_origins=cors_origins,
    )


settings: Final[Settings] = get_settings()


@lru_cache(maxsize=1)
def get_cached_settings() -> Settings:
    """Mengembalikan konfigurasi yang dicache untuk dependency injection."""
    return settings
