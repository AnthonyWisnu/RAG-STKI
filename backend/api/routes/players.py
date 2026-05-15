"""Player search, detail, valuation, and top performers routes."""

from __future__ import annotations

from typing import Any

from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, Query

try:
    from api.schemas.player import (
        PlayerDetailResponse,
        PlayerSearchResponse,
        TopPerformersResponse,
    )
except ModuleNotFoundError:
    from backend.api.schemas.player import (
        PlayerDetailResponse,
        PlayerSearchResponse,
        TopPerformersResponse,
    )

try:
    from config.settings import CURRENT_SEASON
    from etl.neo4j_loader import Neo4jGraphLoader
    from src.utils.citation import kg_citation_from_row
except ModuleNotFoundError:
    from backend.config.settings import CURRENT_SEASON
    from backend.etl.neo4j_loader import Neo4jGraphLoader
    from backend.src.utils.citation import kg_citation_from_row

router = APIRouter(prefix="/api/players", tags=["players"])
top_router = APIRouter(prefix="/api", tags=["top-performers"])

SEARCH_CACHE: TTLCache = TTLCache(maxsize=256, ttl=300)
TOP_CACHE: TTLCache = TTLCache(maxsize=128, ttl=300)


def run_query(query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Run read query and close Neo4j driver."""
    loader = Neo4jGraphLoader()
    try:
        return loader.run_read_query(query, parameters or {})
    finally:
        loader.close()


def cache_key(**kwargs: Any) -> tuple[tuple[str, Any], ...]:
    """Stable cache key from query params."""
    return tuple(sorted(kwargs.items()))


@router.get("/search", response_model=PlayerSearchResponse)
def search_players(
    q: str = Query(default="", description="Nama pemain"),
    position: str | None = None,
    league: str | None = None,
    season: str = CURRENT_SEASON,
    sort: str = Query(default="name", pattern="^(name|goals|assists|minutes|market_value)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PlayerSearchResponse:
    """Search players with filters and TTL cache."""
    key = cache_key(q=q, position=position, league=league, season=season, sort=sort, page=page, page_size=page_size)
    if key in SEARCH_CACHE:
        return PlayerSearchResponse(**SEARCH_CACHE[key])

    search_terms = [term for term in q.lower().split() if term]
    order_map = {
        "name": "player ASC",
        "goals": "goals DESC",
        "assists": "assists DESC",
        "minutes": "minutes DESC",
        "market_value": "market_value_eur DESC",
    }
    offset = (page - 1) * page_size
    query = f"""
    MATCH (p:Player)-[:HAS_STATS_IN]->(s:PlayerSeasonStats)
    MATCH (s)-[:DURING]->(se:Season {{id: $season}})
    MATCH (s)-[:WITH_CLUB]->(c:Club)
    MATCH (s)-[:IN_LEAGUE]->(l:League)
    WHERE all(term IN $search_terms WHERE toLower(p.name) CONTAINS term)
      AND ($league IS NULL OR l.name = $league)
    OPTIONAL MATCH (p)-[:PLAYS_POSITION]->(pos:Position)
    WITH p, s, c, l, pos
    WHERE $position IS NULL OR pos.name = $position
    OPTIONAL MATCH (p)-[:HAS_VALUATION]->(v:Valuation)
    WITH p, s, c, l, pos, max(v.market_value_eur) AS market_value_eur
    WITH p.name AS player, p.api_id AS player_id, pos.name AS position, c.name AS club,
         l.name AS league, s.season_id AS season, s.goals AS goals, s.assists AS assists,
         s.minutes AS minutes, market_value_eur
    ORDER BY {order_map[sort]}
    WITH collect({{
        player_id: player_id, name: player, position: position, club: club, league: league,
        season: season, goals: goals, assists: assists, minutes: minutes,
        market_value_eur: market_value_eur
    }}) AS rows
    RETURN size(rows) AS total, rows[$offset..$end] AS items
    """
    rows = run_query(
        query,
        {
            "search_terms": search_terms,
            "position": position,
            "league": league,
            "season": season,
            "offset": offset,
            "end": offset + page_size,
        },
    )
    result = rows[0] if rows else {"total": 0, "items": []}
    payload = {
        "items": result["items"],
        "page": page,
        "page_size": page_size,
        "total": result["total"],
        "has_next": offset + page_size < result["total"],
    }
    SEARCH_CACHE[key] = payload
    return PlayerSearchResponse(**payload)


@router.get("/{player_id}", response_model=PlayerDetailResponse)
def get_player(player_id: int) -> PlayerDetailResponse:
    """Get player profile, season stats, and valuation history."""
    query = """
    MATCH (p:Player {api_id: $player_id})
    OPTIONAL MATCH (p)-[:PLAYS_POSITION]->(pos:Position)
    WITH p, pos
    OPTIONAL MATCH (p)-[:HAS_STATS_IN]->(s:PlayerSeasonStats)
    OPTIONAL MATCH (s)-[:DURING]->(se:Season)
    OPTIONAL MATCH (s)-[:WITH_CLUB]->(c:Club)
    OPTIONAL MATCH (s)-[:IN_LEAGUE]->(l:League)
    WITH p, pos, s, se, c, l
    ORDER BY se.id DESC
    WITH p, pos, collect(CASE WHEN s IS NULL THEN NULL ELSE {
        id: s.id, season: se.id, club: c.name, league: l.name, position: s.position,
        matches_played: s.matches_played, starts: s.starts, minutes: s.minutes,
        goals: s.goals, assists: s.assists, shots_total: s.shots_total,
        saves: s.saves, save_pct: s.save_pct, clean_sheets: s.clean_sheets
    } END) AS raw_stats
    OPTIONAL MATCH (p)-[:HAS_VALUATION]->(v:Valuation)
    WITH p, pos, [item IN raw_stats WHERE item IS NOT NULL] AS stats, v
    ORDER BY v.valuation_date DESC
    RETURN {
        player_id: p.api_id, name: p.name, birth_date: p.birth_date, height_cm: p.height_cm,
        preferred_foot: p.preferred_foot, nationality: p.nationality, position: pos.name,
        photo_url: p.photo_url
    } AS player,
    stats AS stats_by_season,
    collect(CASE WHEN v IS NULL THEN NULL ELSE {
        id: v.id, valuation_date: v.valuation_date, market_value_eur: v.market_value_eur,
        source: v.source
    } END)[0..24] AS valuations
    """
    rows = run_query(query, {"player_id": player_id})
    if not rows:
        raise HTTPException(status_code=404, detail="Player not found")
    row = rows[0]
    valuations = [item for item in row["valuations"] if item is not None]
    return PlayerDetailResponse(
        player=row["player"],
        stats_by_season=row["stats_by_season"],
        valuation_history=valuations,
    )


@router.get("/{player_id}/valuation-history")
def get_valuation_history(player_id: int) -> dict[str, Any]:
    """Get valuation history for a player."""
    rows = run_query(
        """
        MATCH (p:Player {api_id: $player_id})-[:HAS_VALUATION]->(v:Valuation)
        RETURN p.name AS player, v.market_value_eur AS market_value_eur,
               v.valuation_date AS valuation_date, v.source AS source
        ORDER BY v.valuation_date DESC
        LIMIT 60
        """,
        {"player_id": player_id},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Valuation history not found")
    current = rows[0]["market_value_eur"]
    previous = rows[1]["market_value_eur"] if len(rows) > 1 else current
    trend = "up" if current > previous else "down" if current < previous else "stable"
    return {
        "player_id": player_id,
        "player": rows[0]["player"],
        "valuations": rows,
        "trend_narrative": f"Latest value is EUR {current:,}; short-term trend is {trend}.",
    }


@top_router.get("/top-performers", response_model=TopPerformersResponse)
def top_performers(
    category: str = Query(default="goals", pattern="^(goals|assists|saves|clean_sheets|minutes)$"),
    season: str = CURRENT_SEASON,
    league: str | None = None,
    position: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
) -> TopPerformersResponse:
    """Return top performers for available public stats."""
    key = cache_key(category=category, season=season, league=league, position=position, limit=limit)
    if key in TOP_CACHE:
        return TopPerformersResponse(**TOP_CACHE[key])
    where_league = "AND l.name = $league" if league else ""
    query = f"""
    MATCH (p:Player)-[:HAS_STATS_IN]->(s:PlayerSeasonStats)
    MATCH (s)-[:DURING]->(se:Season {{id: $season}})
    MATCH (s)-[:WITH_CLUB]->(c:Club)
    MATCH (s)-[:IN_LEAGUE]->(l:League)
    WHERE s.{category} IS NOT NULL {where_league}
      AND ($position IS NULL OR s.position = $position)
    RETURN p.name AS player, c.name AS club, l.name AS league, se.id AS season,
           s.position AS position, s.{category} AS value, s.goals AS goals,
           s.assists AS assists, s.minutes AS minutes
    ORDER BY value DESC, minutes ASC
    LIMIT $limit
    """
    rows = run_query(query, {"season": season, "league": league, "position": position, "limit": limit})
    payload = {
        "category": category,
        "season": season,
        "league": league,
        "items": rows,
        "citations": [kg_citation_from_row(row, index).to_dict() for index, row in enumerate(rows[:8])],
    }
    TOP_CACHE[key] = payload
    return TopPerformersResponse(**payload)
