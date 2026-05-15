"""Mapping pemain FBref ke ID pemain Transfermarkt."""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

try:
    from config.settings import TRANSFERMARKT_COMPETITION_TO_LEAGUE
except ModuleNotFoundError:
    from backend.config.settings import TRANSFERMARKT_COMPETITION_TO_LEAGUE

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlayerCandidate:
    """Kandidat pemain dari dataset Transfermarkt."""

    player_id: int
    name: str
    normalized_name: str
    birth_year: int | None
    nationality: str | None
    current_club_id: int | None
    current_club_name: str | None
    league_id: str | None
    position: str
    sub_position: str | None
    preferred_foot: str | None
    height_cm: int | None
    birth_date: str | None
    photo_url: str | None
    market_value_eur: int | None
    highest_market_value_eur: int | None
    is_active: bool


@dataclass(frozen=True)
class PlayerMatch:
    """Hasil mapping satu pemain FBref ke Transfermarkt."""

    candidate: PlayerCandidate
    confidence: float
    reason: str


def normalize_name(value: str | None) -> str:
    """Menormalisasi nama untuk pencocokan lintas sumber.

    Args:
        value: Nama pemain atau klub.

    Returns:
        Nama lowercase tanpa aksen dan tanda baca.
    """
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.lower()
    ascii_value = re.sub(r"[^a-z0-9]+", " ", ascii_value)
    return re.sub(r"\s+", " ", ascii_value).strip()


def map_position(position: str | None, sub_position: str | None = None) -> str:
    """Mengubah posisi Transfermarkt menjadi empat posisi utama."""
    raw_value = f"{position or ''} {sub_position or ''}".lower()
    if "goalkeeper" in raw_value:
        return "Goalkeeper"
    if "defender" in raw_value or "back" in raw_value:
        return "Defender"
    if "midfield" in raw_value:
        return "Midfielder"
    return "Forward"


def parse_int(value: Any) -> int | None:
    """Mengubah nilai menjadi int atau None."""
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def parse_birth_year(value: Any) -> int | None:
    """Mengambil tahun lahir dari tanggal atau angka tahun."""
    if pd.isna(value):
        return None
    text = str(value)
    match = re.search(r"(19|20)\d{2}", text)
    if match is None:
        return None
    return int(match.group(0))


def clean_date(value: Any) -> str | None:
    """Mengubah tanggal pandas menjadi string YYYY-MM-DD jika tersedia."""
    if pd.isna(value):
        return None
    text = str(value)
    if len(text) >= 10 and re.match(r"\d{4}-\d{2}-\d{2}", text[:10]):
        return text[:10]
    return text


def build_player_candidates(players_df: pd.DataFrame) -> list[PlayerCandidate]:
    """Membangun daftar kandidat dari CSV `players.csv`.

    Args:
        players_df: DataFrame Transfermarkt players.

    Returns:
        Daftar kandidat pemain yang siap dipakai mapper.
    """
    candidates: list[PlayerCandidate] = []
    for row in players_df.itertuples(index=False):
        row_data = row._asdict()
        player_id = parse_int(row_data.get("player_id"))
        name = row_data.get("name")
        if player_id is None or pd.isna(name):
            continue

        competition_id = row_data.get("current_club_domestic_competition_id")
        league_id = TRANSFERMARKT_COMPETITION_TO_LEAGUE.get(str(competition_id))
        last_season = parse_int(row_data.get("last_season"))
        candidates.append(
            PlayerCandidate(
                player_id=player_id,
                name=str(name),
                normalized_name=normalize_name(str(name)),
                birth_year=parse_birth_year(row_data.get("date_of_birth")),
                nationality=(
                    None
                    if pd.isna(row_data.get("country_of_citizenship"))
                    else str(row_data.get("country_of_citizenship"))
                ),
                current_club_id=parse_int(row_data.get("current_club_id")),
                current_club_name=(
                    None
                    if pd.isna(row_data.get("current_club_name"))
                    else str(row_data.get("current_club_name"))
                ),
                league_id=league_id,
                position=map_position(
                    row_data.get("position"),
                    row_data.get("sub_position"),
                ),
                sub_position=(
                    None
                    if pd.isna(row_data.get("sub_position"))
                    else str(row_data.get("sub_position"))
                ),
                preferred_foot=(
                    None if pd.isna(row_data.get("foot")) else str(row_data.get("foot"))
                ),
                height_cm=parse_int(row_data.get("height_in_cm")),
                birth_date=clean_date(row_data.get("date_of_birth")),
                photo_url=(
                    None
                    if pd.isna(row_data.get("image_url"))
                    else str(row_data.get("image_url"))
                ),
                market_value_eur=parse_int(row_data.get("market_value_in_eur")),
                highest_market_value_eur=parse_int(
                    row_data.get("highest_market_value_in_eur")
                ),
                is_active=bool(last_season is not None and last_season >= 2023),
            )
        )
    LOGGER.info("Kandidat Transfermarkt dibuat: %s pemain", len(candidates))
    return candidates


class PlayerIdMapper:
    """Mapper pemain FBref ke pemain Transfermarkt."""

    def __init__(self, candidates: list[PlayerCandidate]) -> None:
        """Membuat mapper dengan index nama.

        Args:
            candidates: Daftar kandidat Transfermarkt.
        """
        self.candidates = candidates
        self.by_name: dict[str, list[PlayerCandidate]] = {}
        self.by_birth_year: dict[int, list[PlayerCandidate]] = {}
        self.by_first_token: dict[str, list[PlayerCandidate]] = {}
        for candidate in candidates:
            self.by_name.setdefault(candidate.normalized_name, []).append(candidate)
            if candidate.birth_year is not None:
                self.by_birth_year.setdefault(candidate.birth_year, []).append(candidate)
            first_token = candidate.normalized_name.split(" ", 1)[0]
            if first_token:
                self.by_first_token.setdefault(first_token, []).append(candidate)

    def match(
        self,
        player_name: str,
        birth_year: int | None = None,
        league_id: str | None = None,
        club_name: str | None = None,
        nationality: str | None = None,
    ) -> PlayerMatch | None:
        """Mencari kandidat terbaik untuk satu baris FBref.

        Args:
            player_name: Nama pemain dari FBref.
            birth_year: Tahun lahir dari FBref jika tersedia.
            league_id: ID liga internal.
            club_name: Nama klub dari FBref.
            nationality: Kode atau nama negara dari FBref.

        Returns:
            Hasil match terbaik atau None jika tidak ada kandidat cukup kuat.
        """
        normalized = normalize_name(player_name)
        candidates = self.by_name.get(normalized, [])
        reason_parts: list[str] = []

        if not candidates:
            candidates = self._fuzzy_candidates(normalized, birth_year)
            reason_parts.append("fuzzy_name")
        else:
            reason_parts.append("exact_name")

        best_candidate: PlayerCandidate | None = None
        best_score = 0.0
        for candidate in candidates:
            score = self._score_candidate(
                candidate=candidate,
                normalized_player_name=normalized,
                birth_year=birth_year,
                league_id=league_id,
                club_name=club_name,
                nationality=nationality,
            )
            if score > best_score:
                best_candidate = candidate
                best_score = score

        if best_candidate is None or best_score < 75:
            return None

        return PlayerMatch(
            candidate=best_candidate,
            confidence=round(best_score, 2),
            reason=",".join(reason_parts),
        )

    def _fuzzy_candidates(
        self,
        normalized_name_value: str,
        birth_year: int | None,
    ) -> list[PlayerCandidate]:
        candidates: list[tuple[float, PlayerCandidate]] = []
        if birth_year is not None and birth_year in self.by_birth_year:
            candidate_pool = self.by_birth_year[birth_year]
        else:
            first_token = normalized_name_value.split(" ", 1)[0]
            candidate_pool = self.by_first_token.get(first_token, self.candidates)

        for candidate in candidate_pool:
            ratio = SequenceMatcher(
                None,
                normalized_name_value,
                candidate.normalized_name,
            ).ratio()
            if ratio >= 0.92:
                candidates.append((ratio, candidate))
        candidates.sort(key=lambda item: item[0], reverse=True)
        return [candidate for _, candidate in candidates[:10]]

    def _score_candidate(
        self,
        candidate: PlayerCandidate,
        normalized_player_name: str,
        birth_year: int | None,
        league_id: str | None,
        club_name: str | None,
        nationality: str | None,
    ) -> float:
        score = 0.0
        name_ratio = SequenceMatcher(
            None,
            normalized_player_name,
            candidate.normalized_name,
        ).ratio()
        score += name_ratio * 70

        if birth_year is not None and candidate.birth_year == birth_year:
            score += 18
        if league_id is not None and candidate.league_id == league_id:
            score += 10
        if club_name and candidate.current_club_name:
            club_ratio = SequenceMatcher(
                None,
                normalize_name(club_name),
                normalize_name(candidate.current_club_name),
            ).ratio()
            score += club_ratio * 8
        if nationality and candidate.nationality:
            if normalize_name(nationality) in normalize_name(candidate.nationality):
                score += 4
        if candidate.is_active:
            score += 3
        return score
