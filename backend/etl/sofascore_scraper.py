"""Stub scraper Sofascore karena soccerdata 1.9 tidak mendukung stats pemain."""

from __future__ import annotations

import logging

import pandas as pd

LOGGER = logging.getLogger(__name__)


def read_player_season_stats() -> pd.DataFrame:
    """Mengembalikan DataFrame kosong tanpa error sesuai keputusan scope.

    Returns:
        DataFrame kosong. Kolom Sofascore downstream akan bernilai null.
    """
    LOGGER.info("Sofascore scraper nonaktif, mengembalikan DataFrame kosong")
    return pd.DataFrame()

