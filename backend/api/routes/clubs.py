"""Club routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

try:
    from api.schemas.player import ClubResponse
except ModuleNotFoundError:
    from backend.api.schemas.player import ClubResponse

try:
    from config.settings import CURRENT_SEASON, SUPPORTED_LEAGUES
    from etl.neo4j_loader import Neo4jGraphLoader
except ModuleNotFoundError:
    from backend.config.settings import CURRENT_SEASON, SUPPORTED_LEAGUES
    from backend.etl.neo4j_loader import Neo4jGraphLoader

router = APIRouter(prefix="/api/clubs", tags=["clubs"])
MIN_VALID_SQUAD_COUNT = 8
POPULAR_CLUBS = [
    {"display_name": "Real Madrid", "official_name": "Real Madrid Club de Fútbol"},
    {"display_name": "FC Barcelona", "official_name": "Futbol Club Barcelona"},
    {"display_name": "PSG", "official_name": "Paris Saint-Germain Football Club"},
    {"display_name": "Manchester United", "official_name": "Manchester United Football Club"},
    {"display_name": "Manchester City", "official_name": "Manchester City Football Club"},
    {"display_name": "Arsenal", "official_name": "Arsenal Football Club"},
    {"display_name": "Liverpool", "official_name": "Liverpool Football Club"},
    {"display_name": "Chelsea", "official_name": "Chelsea Football Club"},
    {"display_name": "AC Milan", "official_name": "Associazione Calcio Milan"},
    {"display_name": "Juventus", "official_name": "Juventus Football Club"},
    {"display_name": "Inter Milan", "official_name": "Football Club Internazionale Milano S.p.A."},
    {"display_name": "Bayern München", "official_name": "FC Bayern München"},
]


def run_query(query: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
    """Run a Neo4j read query."""
    loader = Neo4jGraphLoader()
    try:
        return loader.run_read_query(query, parameters)
    finally:
        loader.close()


@router.get("/search")
def search_clubs(q: str = "", season: str = CURRENT_SEASON, limit: int = 12) -> dict[str, Any]:
    """Search clubs with player count for selector UI."""
    if not q.strip():
        query = """
        UNWIND $popular_clubs AS preferred
        MATCH (c:Club {name: preferred.official_name})
        MATCH (s:PlayerSeasonStats)-[:WITH_CLUB]->(c)
        MATCH (s)-[:DURING]->(:Season {id: $season})
        MATCH (s)-[:IN_LEAGUE]->(l:League)
        WHERE l.id IN $league_ids
        WITH preferred, c, l, count(DISTINCT s) AS squad_count
        WHERE squad_count >= $min_squad_count
        RETURN c.api_id AS club_id,
               preferred.display_name AS name,
               c.country AS country,
               l.name AS league,
               squad_count,
               preferred.order AS sort_order
        ORDER BY sort_order ASC
        LIMIT $limit
        """
        popular_clubs = [
            {**club, "order": index}
            for index, club in enumerate(POPULAR_CLUBS)
        ]
        rows = run_query(
            query,
            {
                "popular_clubs": popular_clubs,
                "season": season,
                "limit": limit,
                "league_ids": list(SUPPORTED_LEAGUES.keys()),
                "min_squad_count": MIN_VALID_SQUAD_COUNT,
            },
        )
        for row in rows:
            row.pop("sort_order", None)
        return {"items": rows, "total": len(rows)}

    query = """
    MATCH (c:Club)
    WHERE $q = "" OR toLower(c.name) CONTAINS toLower($q)
    MATCH (s:PlayerSeasonStats)-[:WITH_CLUB]->(c)
    MATCH (s)-[:DURING]->(:Season {id: $season})
    MATCH (s)-[:IN_LEAGUE]->(l:League)
    WHERE l.id IN $league_ids
    WITH c, l, count(DISTINCT s) AS squad_count
    WHERE squad_count >= $min_squad_count
    RETURN c.api_id AS club_id, c.name AS name, c.country AS country,
           l.name AS league, squad_count
    ORDER BY name ASC
    LIMIT $limit
    """
    rows = run_query(
        query,
        {
            "q": q,
            "season": season,
            "limit": limit,
            "league_ids": list(SUPPORTED_LEAGUES.keys()),
            "min_squad_count": MIN_VALID_SQUAD_COUNT,
        },
    )
    return {"items": rows, "total": len(rows)}


@router.get("/{club_id}", response_model=ClubResponse)
def get_club(club_id: int, season: str = CURRENT_SEASON) -> ClubResponse:
    """Return club detail, squad, top scorers, and total squad value."""
    query = """
    MATCH (c:Club {api_id: $club_id})
    MATCH (s:PlayerSeasonStats)-[:WITH_CLUB]->(c)
    MATCH (s)-[:DURING]->(:Season {id: $season})
    MATCH (s)-[:IN_LEAGUE]->(l:League)
    WHERE l.id IN $league_ids
    MATCH (p:Player)-[:HAS_STATS_IN]->(s)
    OPTIONAL MATCH (p)-[:HAS_VALUATION]->(v:Valuation)
    WITH c, l, p, s, v
    ORDER BY v.valuation_date DESC
    WITH c, l, p, s, collect(v)[0] AS latest_value
    WITH c, l, collect({
        player_id: p.api_id, name: p.name, position: s.position, minutes: s.minutes,
        goals: s.goals, assists: s.assists, market_value_eur: latest_value.market_value_eur
    }) AS squad
    WHERE size(squad) >= $min_squad_count
    RETURN {club_id: c.api_id, name: c.name, country: c.country, league: l.name, founded_year: null} AS club,
           squad
    """
    rows = run_query(
        query,
        {
            "club_id": club_id,
            "season": season,
            "league_ids": list(SUPPORTED_LEAGUES.keys()),
            "min_squad_count": MIN_VALID_SQUAD_COUNT,
        },
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Club not found")
    squad = rows[0]["squad"]
    top_scorers = sorted(squad, key=lambda row: row.get("goals") or 0, reverse=True)[:5]
    total_squad_value = sum(int(row.get("market_value_eur") or 0) for row in squad)
    return ClubResponse(
        club=rows[0]["club"],
        squad=squad,
        top_scorers=top_scorers,
        total_squad_value=total_squad_value,
    )
