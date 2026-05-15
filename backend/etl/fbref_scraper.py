"""Scraper FBref via soccerdata dengan cache parquet project-level."""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
for path in (PROJECT_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from config.settings import (
        MIN_SOCCERDATA_DELAY_SECONDS,
        PUBLIC_FBREF_STAT_TYPES,
        SOCCERDATA_LEAGUE_NAME,
        SUPPORTED_LEAGUES,
        SUPPORTED_SEASONS,
        get_cached_settings,
    )
    from src.utils.logging import configure_logging
except ModuleNotFoundError:
    from backend.config.settings import (
        MIN_SOCCERDATA_DELAY_SECONDS,
        PUBLIC_FBREF_STAT_TYPES,
        SOCCERDATA_LEAGUE_NAME,
        SUPPORTED_LEAGUES,
        SUPPORTED_SEASONS,
        get_cached_settings,
    )
    from backend.src.utils.logging import configure_logging

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FBrefFetchRequest:
    """Parameter fetch stats pemain FBref."""

    league: str
    season: str
    stat_type: str


@dataclass(frozen=True)
class FBrefCacheResult:
    """Hasil fetch atau load cache FBref."""

    request: FBrefFetchRequest
    cache_path: Path
    row_count: int
    column_count: int
    from_cache: bool


class FBrefScraperError(RuntimeError):
    """Error saat validasi, scraping, atau caching FBref gagal."""


def normalize_league(value: str) -> str:
    """Mengubah nama liga input menjadi nama yang diterima soccerdata.

    Args:
        value: Nama liga, ID liga, atau `big5`.

    Returns:
        Nama liga untuk parameter `soccerdata.FBref`.

    Raises:
        FBrefScraperError: Jika liga tidak masuk scope.
    """
    cleaned_value = value.strip()
    if cleaned_value.lower() in {"big5", "big 5", "big five"}:
        return SOCCERDATA_LEAGUE_NAME
    if cleaned_value == SOCCERDATA_LEAGUE_NAME:
        return cleaned_value
    if cleaned_value in SUPPORTED_LEAGUES:
        return cleaned_value

    display_to_id = {
        display.lower(): league_id
        for league_id, display in SUPPORTED_LEAGUES.items()
    }
    league_id = display_to_id.get(cleaned_value.lower())
    if league_id is not None:
        return league_id

    allowed = ", ".join(SUPPORTED_LEAGUES.values())
    raise FBrefScraperError(f"Liga di luar scope: {value}. Scope tersedia: {allowed}")


def validate_request(request: FBrefFetchRequest) -> None:
    """Memvalidasi request scraping FBref.

    Args:
        request: Parameter fetch FBref.

    Raises:
        FBrefScraperError: Jika musim atau stat_type tidak tersedia.
    """
    if request.season not in SUPPORTED_SEASONS:
        seasons = ", ".join(SUPPORTED_SEASONS)
        raise FBrefScraperError(
            f"Musim di luar scope: {request.season}. Scope: {seasons}"
        )
    if request.stat_type not in PUBLIC_FBREF_STAT_TYPES:
        stat_types = ", ".join(PUBLIC_FBREF_STAT_TYPES)
        raise FBrefScraperError(
            f"stat_type tidak tersedia secara publik: {request.stat_type}. "
            f"Gunakan salah satu dari: {stat_types}"
        )
    if (
        request.league != SOCCERDATA_LEAGUE_NAME
        and request.league not in SUPPORTED_LEAGUES
    ):
        raise FBrefScraperError(f"Liga di luar scope: {request.league}")


def safe_cache_component(value: str) -> str:
    """Mengubah string menjadi komponen filename cache yang aman."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


class FBrefScraper:
    """Scraper FBref yang memakai soccerdata dan cache parquet lokal."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Membuat scraper FBref.

        Args:
            cache_dir: Folder cache parquet. Default memakai setting backend.
        """
        self.settings = get_cached_settings()
        self.cache_dir = cache_dir or self.settings.fbref_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, request: FBrefFetchRequest) -> Path:
        """Mengembalikan path parquet untuk request tertentu."""
        if request.league == SOCCERDATA_LEAGUE_NAME:
            filename = f"{request.stat_type}_{request.season}.parquet"
        else:
            league_part = safe_cache_component(request.league)
            filename = f"{league_part}_{request.stat_type}_{request.season}.parquet"
        return self.cache_dir / filename

    def fetch_player_stats(
        self,
        request: FBrefFetchRequest,
        force_refresh: bool = False,
    ) -> tuple[pd.DataFrame, FBrefCacheResult]:
        """Mengambil stats pemain FBref dan menyimpan cache parquet.

        Args:
            request: Parameter fetch FBref.
            force_refresh: Jika True, abaikan cache lokal.

        Returns:
            Tuple DataFrame dan metadata cache.

        Raises:
            FBrefScraperError: Jika soccerdata gagal fetch atau cache gagal ditulis.
        """
        validate_request(request)
        cache_path = self.get_cache_path(request)

        if cache_path.exists() and not force_refresh:
            LOGGER.info("Membaca cache FBref: %s", cache_path)
            dataframe = pd.read_parquet(cache_path)
            return dataframe, FBrefCacheResult(
                request=request,
                cache_path=cache_path,
                row_count=len(dataframe),
                column_count=len(dataframe.columns),
                from_cache=True,
            )

        self._configure_soccerdata_environment()
        dataframe = self._read_from_soccerdata(request)
        self._write_cache(dataframe, cache_path)
        return dataframe, FBrefCacheResult(
            request=request,
            cache_path=cache_path,
            row_count=len(dataframe),
            column_count=len(dataframe.columns),
            from_cache=False,
        )

    def fetch_many(
        self,
        leagues: Iterable[str],
        seasons: Iterable[str],
        stat_types: Iterable[str],
        force_refresh: bool = False,
    ) -> list[FBrefCacheResult]:
        """Mengambil banyak kombinasi liga, musim, dan stat_type.

        Args:
            leagues: Daftar liga.
            seasons: Daftar musim.
            stat_types: Daftar stat_type publik FBref.
            force_refresh: Jika True, abaikan cache lokal.

        Returns:
            Daftar metadata hasil cache.
        """
        results: list[FBrefCacheResult] = []
        for league in leagues:
            normalized_league = normalize_league(league)
            for season in seasons:
                for stat_type in stat_types:
                    request = FBrefFetchRequest(
                        league=normalized_league,
                        season=season,
                        stat_type=stat_type,
                    )
                    _, result = self.fetch_player_stats(
                        request=request,
                        force_refresh=force_refresh,
                    )
                    results.append(result)
        return results

    def _configure_soccerdata_environment(self) -> None:
        delay = max(self.settings.soccerdata_delay, MIN_SOCCERDATA_DELAY_SECONDS)
        os.environ["SOCCERDATA_DELAY"] = str(delay)
        os.environ["SOCCERDATA_DIR"] = str(self.settings.soccerdata_dir)
        os.environ["SOCCERDATA_NOCACHE"] = (
            "true" if self.settings.soccerdata_no_cache else "false"
        )
        LOGGER.info("SOCCERDATA_DELAY=%s", delay)
        LOGGER.info("SOCCERDATA_DIR=%s", self.settings.soccerdata_dir)

    def _read_from_soccerdata(self, request: FBrefFetchRequest) -> pd.DataFrame:
        LOGGER.info(
            "Fetch FBref dimulai: league=%s season=%s stat_type=%s",
            request.league,
            request.season,
            request.stat_type,
        )
        try:
            import soccerdata as sd
        except ImportError as exc:
            raise FBrefScraperError("Package soccerdata belum terpasang") from exc

        try:
            fbref = sd.FBref(leagues=request.league, seasons=[request.season])
            dataframe = fbref.read_player_season_stats(stat_type=request.stat_type)
        except Exception as exc:
            raise FBrefScraperError(f"Gagal fetch FBref: {exc}") from exc

        dataframe = dataframe.reset_index()
        LOGGER.info(
            "Fetch FBref selesai: rows=%s columns=%s",
            len(dataframe),
            len(dataframe.columns),
        )
        return dataframe

    def _write_cache(self, dataframe: pd.DataFrame, cache_path: Path) -> None:
        try:
            dataframe.to_parquet(cache_path, index=False)
        except Exception as exc:
            raise FBrefScraperError(f"Gagal menulis cache parquet: {exc}") from exc
        LOGGER.info("Cache parquet tersimpan: %s", cache_path)


def build_arg_parser() -> argparse.ArgumentParser:
    """Membuat parser CLI untuk scraper FBref."""
    parser = argparse.ArgumentParser(description="Scrape FBref player season stats")
    parser.add_argument(
        "--league",
        default=SOCCERDATA_LEAGUE_NAME,
        help="Liga scope. Gunakan Big 5, nama liga, atau ID seperti ENG-Premier League.",
    )
    parser.add_argument(
        "--season",
        default=None,
        help="Musim seperti 2024-2025. Default semua musim scope.",
    )
    parser.add_argument(
        "--stat-type",
        default=None,
        help="standard, shooting, misc, atau keeper. Default semua stat_type publik.",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Abaikan cache lokal dan fetch ulang.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validasi scope dan tampilkan rencana tanpa fetch network.",
    )
    return parser


def main() -> None:
    """Menjalankan scraper FBref dari command line."""
    settings = get_cached_settings()
    configure_logging(settings.log_level)
    parser = build_arg_parser()
    args = parser.parse_args()

    scraper = FBrefScraper()
    leagues = (normalize_league(args.league),)
    seasons = (args.season,) if args.season else SUPPORTED_SEASONS
    stat_types = (args.stat_type,) if args.stat_type else PUBLIC_FBREF_STAT_TYPES

    if args.dry_run:
        for league in leagues:
            for season in seasons:
                for stat_type in stat_types:
                    request = FBrefFetchRequest(
                        league=league,
                        season=season,
                        stat_type=stat_type,
                    )
                    validate_request(request)
                    LOGGER.info(
                        "Dry-run FBref: league=%s season=%s stat_type=%s cache_path=%s",
                        request.league,
                        request.season,
                        request.stat_type,
                        scraper.get_cache_path(request),
                    )
        return

    results = scraper.fetch_many(
        leagues=leagues,
        seasons=seasons,
        stat_types=stat_types,
        force_refresh=args.force_refresh,
    )
    for result in results:
        LOGGER.info(
            "Selesai: cache=%s rows=%s columns=%s from_cache=%s",
            result.cache_path,
            result.row_count,
            result.column_count,
            result.from_cache,
        )


if __name__ == "__main__":
    main()
