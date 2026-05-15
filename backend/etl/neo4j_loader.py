"""Loader Neo4j untuk Knowledge Graph sepak bola."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

try:
    from config.settings import get_cached_settings
except ModuleNotFoundError:
    from backend.config.settings import get_cached_settings

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Neo4jLoadSummary:
    """Ringkasan hasil load data ke Neo4j."""

    player_stats_records: int
    valuation_records: int


class Neo4jLoaderError(RuntimeError):
    """Error saat operasi Neo4j gagal."""


def chunked(items: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    """Membagi list dictionary menjadi batch kecil."""
    for index in range(0, len(items), size):
        yield items[index : index + size]


class Neo4jGraphLoader:
    """Loader Knowledge Graph berbasis Neo4j."""

    def __init__(self) -> None:
        """Membuat koneksi Neo4j dari environment."""
        settings = get_cached_settings()
        if not settings.neo4j_uri or not settings.neo4j_user or not settings.neo4j_password:
            raise Neo4jLoaderError("Konfigurasi Neo4j belum lengkap di .env")

        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise Neo4jLoaderError("Package neo4j belum terpasang") from exc

        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def close(self) -> None:
        """Menutup koneksi driver Neo4j."""
        self.driver.close()

    def verify_connectivity(self) -> None:
        """Memastikan koneksi Neo4j bisa digunakan."""
        self.driver.verify_connectivity()
        LOGGER.info("Koneksi Neo4j berhasil")

    def setup_constraints(self) -> None:
        """Membuat constraint unik yang dibutuhkan graph."""
        statements = [
            "CREATE CONSTRAINT player_api_id IF NOT EXISTS FOR (n:Player) REQUIRE n.api_id IS UNIQUE",
            "CREATE CONSTRAINT club_api_id IF NOT EXISTS FOR (n:Club) REQUIRE n.api_id IS UNIQUE",
            "CREATE CONSTRAINT league_id IF NOT EXISTS FOR (n:League) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT season_id IF NOT EXISTS FOR (n:Season) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT position_id IF NOT EXISTS FOR (n:Position) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT nationality_id IF NOT EXISTS FOR (n:Nationality) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT player_stats_id IF NOT EXISTS FOR (n:PlayerSeasonStats) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT valuation_id IF NOT EXISTS FOR (n:Valuation) REQUIRE n.id IS UNIQUE",
        ]
        with self.driver.session() as session:
            for statement in statements:
                session.run(statement)
        LOGGER.info("Constraint Neo4j siap")

    def reset_graph(self) -> None:
        """Menghapus graph hasil setup agar initial setup bisa diulang bersih."""
        query = """
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN $labels)
        DETACH DELETE n
        """
        labels = [
            "Player",
            "Club",
            "League",
            "Season",
            "Position",
            "Nationality",
            "PlayerSeasonStats",
            "Valuation",
        ]
        with self.driver.session() as session:
            session.run(query, labels=labels)
        LOGGER.info("Graph Neo4j hasil setup dibersihkan")

    def load_player_stats(self, records: list[dict[str, Any]], batch_size: int = 250) -> int:
        """Load node pemain, klub, liga, musim, posisi, nasionalitas, dan stats.

        Args:
            records: Records hasil transform ETL.
            batch_size: Ukuran batch UNWIND.

        Returns:
            Jumlah record stats yang diproses.
        """
        query = """
        UNWIND $records AS row
        MERGE (p:Player {api_id: row.player.api_id})
        SET p += row.player
        MERGE (c:Club {api_id: row.club.api_id})
        SET c += row.club
        MERGE (l:League {id: row.league.id})
        SET l += row.league
        MERGE (se:Season {id: row.season.id})
        SET se += row.season
        MERGE (pos:Position {id: row.position.id})
        SET pos += row.position
        MERGE (nat:Nationality {id: row.nationality.id})
        SET nat += row.nationality
        MERGE (s:PlayerSeasonStats {id: row.stats.id})
        SET s += row.stats
        MERGE (p)-[plays:PLAYS_FOR]->(c)
        SET plays += row.plays_for
        MERGE (c)-[competes:COMPETES_IN {season: row.season.id}]->(l)
        MERGE (p)-[:HAS_STATS_IN]->(s)
        MERGE (s)-[:DURING]->(se)
        MERGE (s)-[:WITH_CLUB]->(c)
        MERGE (s)-[:IN_LEAGUE]->(l)
        MERGE (p)-[:PLAYS_POSITION]->(pos)
        MERGE (p)-[:NATIONALITY_OF]->(nat)
        MERGE (l)-[:HAS_SEASON]->(se)
        """
        total = 0
        with self.driver.session() as session:
            for batch in chunked(records, batch_size):
                session.run(query, records=batch)
                total += len(batch)
                LOGGER.info("Loaded PlayerSeasonStats batch: %s total=%s", len(batch), total)
        return total

    def load_valuations(self, records: list[dict[str, Any]], batch_size: int = 500) -> int:
        """Load node Valuation dan relationship ke Player.

        Args:
            records: Records valuation.
            batch_size: Ukuran batch UNWIND.

        Returns:
            Jumlah record valuation yang diproses.
        """
        query = """
        UNWIND $records AS row
        MATCH (p:Player {api_id: row.player_id})
        MERGE (v:Valuation {id: row.valuation.id})
        SET v += row.valuation
        MERGE (p)-[:HAS_VALUATION]->(v)
        """
        total = 0
        with self.driver.session() as session:
            for batch in chunked(records, batch_size):
                session.run(query, records=batch)
                total += len(batch)
                LOGGER.info("Loaded Valuation batch: %s total=%s", len(batch), total)
        return total

    def run_read_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Menjalankan query baca dan mengembalikan list dictionary."""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def load_all(
        self,
        player_stats_records: list[dict[str, Any]],
        valuation_records: list[dict[str, Any]],
    ) -> Neo4jLoadSummary:
        """Menjalankan semua tahap load Neo4j.

        Args:
            player_stats_records: Records stats pemain.
            valuation_records: Records valuation.

        Returns:
            Ringkasan jumlah record yang dimuat.
        """
        self.verify_connectivity()
        self.setup_constraints()
        stats_count = self.load_player_stats(player_stats_records)
        valuation_count = self.load_valuations(valuation_records)
        return Neo4jLoadSummary(
            player_stats_records=stats_count,
            valuation_records=valuation_count,
        )
