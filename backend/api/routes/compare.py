"""Compare endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

try:
    from api.schemas.player import CompareRequest, CompareResponse
except ModuleNotFoundError:
    from backend.api.schemas.player import CompareRequest, CompareResponse

try:
    from etl.neo4j_loader import Neo4jGraphLoader
    from src.utils.citation import kg_citation_from_row
except ModuleNotFoundError:
    from backend.etl.neo4j_loader import Neo4jGraphLoader
    from backend.src.utils.citation import kg_citation_from_row

router = APIRouter(prefix="/api", tags=["compare"])


def run_query(query: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
    """Run read query."""
    loader = Neo4jGraphLoader()
    try:
        return loader.run_read_query(query, parameters)
    finally:
        loader.close()


@router.post("/compare", response_model=CompareResponse)
def compare_players(request: CompareRequest) -> CompareResponse:
    """Compare two to four players."""
    if not request.player_ids and not request.player_names:
        raise HTTPException(status_code=400, detail="Provide player_ids or player_names")
    query = """
    MATCH (p:Player)
    WHERE p.api_id IN $player_ids OR any(name IN $player_names WHERE toLower(p.name) CONTAINS toLower(name))
    MATCH (p)-[:HAS_STATS_IN]->(s:PlayerSeasonStats)
    MATCH (s)-[:DURING]->(se:Season)
    MATCH (s)-[:WITH_CLUB]->(c:Club)
    MATCH (s)-[:IN_LEAGUE]->(l:League)
    WITH p, s, se, c, l
    ORDER BY se.id DESC
    WITH p, collect({season: se.id, club: c.name, league: l.name, minutes: s.minutes,
        goals: s.goals, assists: s.assists, shots_total: s.shots_total,
        saves: s.saves, clean_sheets: s.clean_sheets})[0] AS latest
    RETURN p.api_id AS player_id, p.name AS player, latest
    LIMIT 4
    """
    rows = run_query(query, {"player_ids": request.player_ids, "player_names": request.player_names})
    radar_data = []
    for row in rows:
        latest = row["latest"] or {}
        radar_data.append(
            {
                "player_id": row["player_id"],
                "player": row["player"],
                "goals": latest.get("goals") or 0,
                "assists": latest.get("assists") or 0,
                "minutes": latest.get("minutes") or 0,
                "shots_total": latest.get("shots_total") or 0,
                "saves": latest.get("saves"),
                "clean_sheets": latest.get("clean_sheets"),
            }
        )
    citations = [kg_citation_from_row({"player": row["player"]}, index).to_dict() for index, row in enumerate(rows)]
    names = ", ".join(row["player"] for row in rows)
    return CompareResponse(
        players=rows,
        radar_data=radar_data,
        narrative=f"Comparison generated for {names} using latest available season stats.",
        citations=citations,
    )
