"""Knowledge Graph retriever with text-to-Cypher and safe fallbacks."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
for path in (PROJECT_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from config.settings import NO_DATA_MESSAGE, UCL_UNAVAILABLE_MESSAGE
    from etl.neo4j_loader import Neo4jGraphLoader
    from src.llm.openai_client import OpenAIClient
    from src.llm.prompt_loader import PromptLoader
    from src.utils.citation import kg_citation_from_row
    from src.utils.language_detect import detect_language
except ModuleNotFoundError:
    from backend.config.settings import NO_DATA_MESSAGE, UCL_UNAVAILABLE_MESSAGE
    from backend.etl.neo4j_loader import Neo4jGraphLoader
    from backend.src.llm.openai_client import OpenAIClient
    from backend.src.llm.prompt_loader import PromptLoader
    from backend.src.utils.citation import kg_citation_from_row
    from backend.src.utils.language_detect import detect_language

LOGGER = logging.getLogger(__name__)

WRITE_CLAUSE_PATTERN = re.compile(
    r"\b(CREATE|MERGE|SET|DELETE|DETACH|DROP|REMOVE|LOAD\s+CSV|CALL\s+DBMS|CALL\s+APOC)\b",
    re.IGNORECASE,
)

LEAGUE_ALIASES = {
    "premier league": "Premier League",
    "epl": "Premier League",
    "la liga": "La Liga",
    "serie a": "Serie A",
    "bundesliga": "Bundesliga",
    "ligue 1": "Ligue 1",
}


@dataclass(frozen=True)
class CypherPlan:
    """Generated or template Cypher plan."""

    query: str
    parameters: dict[str, Any]
    intent: str
    fallback_reason: str | None = None


@dataclass(frozen=True)
class KGRetrievalResult:
    """KG retrieval result."""

    strategy: str
    language: str
    query: str | None
    parameters: dict[str, Any]
    rows: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    fallback_signal: str | None
    error: str | None = None


def infer_season(question: str) -> str:
    """Extract season from query or default to current season."""
    match = re.search(r"20\d{2}[-/ ]?20\d{2}", question)
    if match:
        return match.group(0).replace("/", "-").replace(" ", "-")
    return "2025-2026"


def infer_limit(question: str, default: int = 10) -> int:
    """Extract top-N limit."""
    match = re.search(r"\btop\s*(\d+)|\b(\d+)\s*(pemain|players)", question, re.IGNORECASE)
    if not match:
        return default
    value = next(item for item in match.groups() if item and item.isdigit())
    return max(1, min(int(value), 50))


def infer_league(question: str) -> str | None:
    """Extract league name from query."""
    lowered = question.lower()
    for alias, league in LEAGUE_ALIASES.items():
        if alias in lowered:
            return league
    return None


def infer_similarity_player(question: str) -> str:
    """Extract reference player name for similarity queries."""
    patterns = [
        r"(?:mirip|serupa|similar to|like)\s+([a-zA-ZÀ-ÿ' .-]+?)(?:\s+(?:akan|tetapi|tapi|namun|dengan|yang|lebih|but|with|market|nilai)|\?|$)",
        r"(?:statistik|stats)\s+([a-zA-ZÀ-ÿ' .-]+?)(?:\s+(?:akan|tetapi|tapi|namun|dengan|yang|lebih|but|with|market|nilai)|\?|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)
        if match:
            name = re.sub(r"\s+", " ", match.group(1)).strip(" ?.,")
            if name:
                return name
    return question.strip(" ?")


def validate_readonly_cypher(query: str) -> None:
    """Block write clauses and suspicious multi-statements."""
    stripped = query.strip()
    if ";" in stripped:
        raise ValueError("Cypher multi-statement tidak diizinkan")
    if WRITE_CLAUSE_PATTERN.search(stripped):
        raise ValueError("Cypher write clause tidak diizinkan")
    if not stripped.upper().startswith(("MATCH", "WITH")):
        raise ValueError("Cypher harus dimulai dengan MATCH atau WITH")


def build_template_plan(question: str) -> CypherPlan | None:
    """Deterministic templates for common KG-only questions."""
    lowered = question.lower()
    season = infer_season(question)
    league = infer_league(question)
    limit = infer_limit(question)

    if "champions league" in lowered or "liga champions" in lowered or "ucl" in lowered:
        return CypherPlan(
            query="",
            parameters={},
            intent="unsupported Champions League",
            fallback_reason=UCL_UNAVAILABLE_MESSAGE,
        )

    if any(token in lowered for token in ("mirip", "serupa", "similar")) and any(
        token in lowered for token in ("lebih murah", "lebih rendah", "lower", "cheaper", "market value", "nilai pasar")
    ):
        player_name = infer_similarity_player(question)
        return CypherPlan(
            query="""
            MATCH (target:Player)
            WHERE toLower(target.name) CONTAINS toLower($player_name)
            MATCH (target)-[:HAS_STATS_IN]->(target_stats:PlayerSeasonStats)-[:DURING]->(season:Season {id: $season})
            MATCH (target_stats)-[:IN_LEAGUE]->(target_league:League)
            OPTIONAL MATCH (target)-[:PLAYS_POSITION]->(target_pos:Position)
            MATCH (target)-[:HAS_VALUATION]->(target_value:Valuation)
            WITH target, target_stats, season, target_league, target_pos, target_value
            ORDER BY target_value.valuation_date DESC
            WITH target, target_stats, season, target_league, target_pos, collect(target_value)[0] AS target_value
            MATCH (candidate:Player)-[:HAS_STATS_IN]->(candidate_stats:PlayerSeasonStats)-[:DURING]->(season)
            WHERE candidate.api_id <> target.api_id
              AND coalesce(candidate_stats.minutes, 0) >= 400
            OPTIONAL MATCH (candidate)-[:PLAYS_POSITION]->(candidate_pos:Position)
            WITH target, target_stats, season, target_league, target_pos, target_value,
                 candidate, candidate_stats, candidate_pos
            WHERE candidate_pos.name = target_pos.name
            MATCH (candidate_stats)-[:WITH_CLUB]->(candidate_club:Club)
            MATCH (candidate_stats)-[:IN_LEAGUE]->(candidate_league:League)
            MATCH (candidate)-[:HAS_VALUATION]->(candidate_value:Valuation)
            WITH target, target_stats, season, target_league, target_pos, target_value,
                 candidate, candidate_stats, candidate_pos, candidate_club, candidate_league, candidate_value
            ORDER BY candidate_value.valuation_date DESC
            WITH target, target_stats, season, target_league, target_pos, target_value,
                 candidate, candidate_stats, candidate_pos, candidate_club, candidate_league,
                 collect(candidate_value)[0] AS candidate_value
            WHERE candidate_value.market_value_eur < target_value.market_value_eur
            WITH target, target_stats, season, target_league, target_pos, target_value,
                 candidate, candidate_stats, candidate_pos, candidate_club, candidate_league, candidate_value,
                 (
                   abs(coalesce(candidate_stats.minutes, 0) - coalesce(target_stats.minutes, 0)) / 3000.0 +
                   abs(coalesce(candidate_stats.goals, 0) - coalesce(target_stats.goals, 0)) / 20.0 +
                   abs(coalesce(candidate_stats.assists, 0) - coalesce(target_stats.assists, 0)) / 20.0 +
                   abs(coalesce(candidate_stats.shots_total, 0) - coalesce(target_stats.shots_total, 0)) / 80.0
                 ) AS similarity_score
            RETURN target.name AS reference_player,
                   target_value.market_value_eur AS reference_market_value_eur,
                   target_stats.minutes AS reference_minutes,
                   target_stats.goals AS reference_goals,
                   target_stats.assists AS reference_assists,
                   candidate.name AS player,
                   candidate_club.name AS club,
                   candidate_league.name AS league,
                   season.id AS season,
                   candidate_pos.name AS position,
                   candidate_value.market_value_eur AS market_value_eur,
                   candidate_stats.minutes AS minutes,
                   candidate_stats.goals AS goals,
                   candidate_stats.assists AS assists,
                   candidate_stats.shots_total AS shots_total,
                   round(similarity_score * 1000) / 1000.0 AS similarity_score
            ORDER BY similarity_score ASC, market_value_eur DESC
            LIMIT $limit
            """,
            parameters={"player_name": player_name, "season": season, "limit": limit},
            intent="similar cheaper players",
            fallback_reason="template_similar_cheaper_players",
        )

    if any(token in lowered for token in ("top skor", "top scorer", "pencetak gol", "goals")):
        where_league = (
            "MATCH (s)-[:IN_LEAGUE]->(l:League {name: $league_name})"
            if league
            else "MATCH (s)-[:IN_LEAGUE]->(l:League)"
        )
        params: dict[str, Any] = {"season": season, "limit": limit}
        if league:
            params["league_name"] = league
        return CypherPlan(
            query=f"""
            MATCH (p:Player)-[:HAS_STATS_IN]->(s:PlayerSeasonStats)
            MATCH (s)-[:DURING]->(se:Season {{id: $season}})
            {where_league}
            MATCH (s)-[:WITH_CLUB]->(c:Club)
            RETURN p.name AS player, c.name AS club, l.name AS league, se.id AS season,
                   s.goals AS goals, s.assists AS assists, s.minutes AS minutes
            ORDER BY goals DESC, minutes ASC
            LIMIT $limit
            """,
            parameters=params,
            intent="top scorers",
            fallback_reason="template_top_scorers",
        )

    if any(token in lowered for token in ("valuation", "valuasi", "nilai pasar", "market value", "value")):
        name = question
        for token in (
            "valuation",
            "valuasi",
            "nilai pasar",
            "market value",
            "value",
            "berapa",
            "what is",
            "jelaskan",
            "describe",
            "profil",
            "profile",
            "dan",
            "and",
        ):
            pattern = r"\b" + re.escape(token) + r"\b"
            name = re.sub(pattern, " ", name, flags=re.IGNORECASE)
        name = re.sub(r"\b[A-Za-z]\b", " ", name)
        name = re.sub(r"\s+", " ", name).strip(" ?")
        return CypherPlan(
            query="""
            MATCH (p:Player)
            WHERE toLower(p.name) CONTAINS toLower($player_name)
            MATCH (p)-[:HAS_VALUATION]->(v:Valuation)
            RETURN p.name AS player, v.market_value_eur AS market_value_eur,
                   v.valuation_date AS valuation_date, v.source AS source
            ORDER BY v.valuation_date DESC
            LIMIT $limit
            """,
            parameters={"player_name": name or question, "limit": limit},
            intent="valuation history",
            fallback_reason="template_valuation",
        )

    return None


class KGRetriever:
    """Retrieve structured answers from Neo4j."""

    def __init__(self) -> None:
        self.llm = OpenAIClient()
        self.prompts = PromptLoader()

    def generate_plan(self, question: str, previous_error: str | None = None) -> CypherPlan:
        """Generate Cypher plan via LLM or deterministic fallback."""
        template = build_template_plan(question)
        if template is not None:
            return template

        if self.llm.available:
            prompt = self.prompts.load("cypher_generator_prompt.txt")
            payload = {
                "question": question,
                "previous_error": previous_error,
                "instruction": "Return read-only parameterized Cypher JSON.",
            }
            parsed = self.llm.chat_json(prompt, payload).parsed_json or {}
            plan = CypherPlan(
                query=str(parsed.get("query") or ""),
                parameters=dict(parsed.get("parameters") or {}),
                intent=str(parsed.get("intent") or "llm_generated"),
                fallback_reason=parsed.get("fallback_reason"),
            )
            validate_readonly_cypher(plan.query)
            return plan

        if template is not None:
            return template
        raise RuntimeError("LLM tidak tersedia dan tidak ada template KG untuk pertanyaan ini")

    def retrieve(self, question: str, max_retries: int = 2) -> KGRetrievalResult:
        """Run text-to-Cypher and execute the query with retry."""
        language = detect_language(question)
        lowered_question = question.lower()
        if "champions league" in lowered_question or "liga champions" in lowered_question or "ucl" in lowered_question:
            return KGRetrievalResult(
                strategy="kg_only",
                language=language,
                query=None,
                parameters={},
                rows=[],
                citations=[],
                fallback_signal=UCL_UNAVAILABLE_MESSAGE,
            )

        error: str | None = None
        fallback_plan = build_template_plan(question)
        for attempt in range(max_retries + 1):
            try:
                plan = self.generate_plan(question, previous_error=error)
                if not plan.query:
                    return KGRetrievalResult(
                        strategy="kg_only",
                        language=language,
                        query=None,
                        parameters=plan.parameters,
                        rows=[],
                        citations=[],
                        fallback_signal=plan.fallback_reason or NO_DATA_MESSAGE,
                    )
                validate_readonly_cypher(plan.query)
                loader = Neo4jGraphLoader()
                try:
                    rows = loader.run_read_query(plan.query, plan.parameters)
                finally:
                    loader.close()
                citations = [kg_citation_from_row(row, index).to_dict() for index, row in enumerate(rows[:8])]
                return KGRetrievalResult(
                    strategy="kg_only",
                    language=language,
                    query=plan.query,
                    parameters=plan.parameters,
                    rows=rows,
                    citations=citations,
                    fallback_signal=None if rows else NO_DATA_MESSAGE,
                )
            except Exception as exc:
                error = str(exc)
                LOGGER.warning("KG retrieval attempt=%s failed: %s", attempt + 1, error)
                if attempt == max_retries and fallback_plan is not None and fallback_plan.query:
                    loader = Neo4jGraphLoader()
                    try:
                        rows = loader.run_read_query(fallback_plan.query, fallback_plan.parameters)
                    finally:
                        loader.close()
                    citations = [kg_citation_from_row(row, index).to_dict() for index, row in enumerate(rows[:8])]
                    return KGRetrievalResult(
                        strategy="kg_only",
                        language=language,
                        query=fallback_plan.query,
                        parameters=fallback_plan.parameters,
                        rows=rows,
                        citations=citations,
                        fallback_signal=fallback_plan.fallback_reason,
                        error=error,
                    )

        return KGRetrievalResult(
            strategy="kg_only",
            language=language,
            query=None,
            parameters={},
            rows=[],
            citations=[],
            fallback_signal=NO_DATA_MESSAGE,
            error=error,
        )


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI parser."""
    parser = argparse.ArgumentParser(description="Smoke test KG retriever")
    parser.add_argument("--question", default="top skor Premier League 2025-2026")
    return parser


def main() -> None:
    """CLI entry point."""
    args = build_arg_parser().parse_args()
    result = KGRetriever().retrieve(args.question)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
