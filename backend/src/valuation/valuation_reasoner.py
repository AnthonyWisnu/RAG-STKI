"""LLM-based market valuation reasoning from KG/RAG context."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
for path in (PROJECT_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from config.settings import NO_DATA_MESSAGE, get_cached_settings
    from etl.neo4j_loader import Neo4jGraphLoader
    from src.utils.logging import configure_logging
except ModuleNotFoundError:
    from backend.config.settings import NO_DATA_MESSAGE, get_cached_settings
    from backend.etl.neo4j_loader import Neo4jGraphLoader
    from backend.src.utils.logging import configure_logging

LOGGER = logging.getLogger(__name__)

PLAYER_CONTEXT_QUERY = """
MATCH (p:Player)
WHERE toLower(p.name) = toLower($player_name)
   OR toLower(p.name) CONTAINS toLower($player_name)
WITH p
ORDER BY CASE WHEN toLower(p.name) = toLower($player_name) THEN 0 ELSE 1 END, p.name
LIMIT 1
OPTIONAL MATCH (p)-[:PLAYS_POSITION]->(pos:Position)
WITH p, pos
OPTIONAL MATCH (p)-[:HAS_STATS_IN]->(s:PlayerSeasonStats)
OPTIONAL MATCH (s)-[:WITH_CLUB]->(c:Club)
OPTIONAL MATCH (s)-[:IN_LEAGUE]->(l:League)
OPTIONAL MATCH (s)-[:DURING]->(se:Season)
WITH p, pos, s, c, l, se
ORDER BY se.id DESC
WITH p, pos, collect(
    CASE WHEN s IS NULL THEN NULL ELSE s {
        .*,
        citation_id: "stats:" + toString(p.api_id) + ":" + se.id + ":" + l.id,
        club: c.name,
        league: l.name,
        season: se.id
    } END
) AS raw_stats
OPTIONAL MATCH (p)-[:HAS_VALUATION]->(v:Valuation)
WITH p, pos, [item IN raw_stats WHERE item IS NOT NULL] AS stats, v
ORDER BY v.valuation_date DESC
WITH p, pos, stats, collect(
    CASE WHEN v IS NULL THEN NULL ELSE {
        citation_id: "valuation:" + toString(p.api_id) + ":" + v.valuation_date,
        id: v.id,
        valuation_date: v.valuation_date,
        market_value_eur: v.market_value_eur,
        source: v.source
    } END
) AS raw_valuations
RETURN p.api_id AS player_id,
       p.name AS name,
       p.birth_date AS birth_date,
       p.height_cm AS height_cm,
       p.preferred_foot AS preferred_foot,
       p.nationality AS nationality,
       pos.name AS position,
       stats,
       [item IN raw_valuations WHERE item IS NOT NULL] AS valuations
"""

POSITION_SAMPLE_QUERY = """
MATCH (p:Player)-[:PLAYS_POSITION]->(pos:Position {name: $position})
MATCH (p)-[:HAS_VALUATION]->(:Valuation)
MATCH (p)-[:HAS_STATS_IN]->(s:PlayerSeasonStats)
WITH p, max(s.minutes) AS max_minutes
WHERE max_minutes >= 400
RETURN p.name AS name
ORDER BY name
LIMIT 1
"""


@dataclass(frozen=True)
class Citation:
    """Citation yang bisa dipakai UI dan answer synthesis."""

    id: str
    label: str
    source: str


@dataclass(frozen=True)
class ValuationContext:
    """Konteks valuasi dari Knowledge Graph."""

    player: dict[str, Any]
    latest_stats: list[dict[str, Any]]
    valuation_history: list[dict[str, Any]]
    summary: dict[str, Any]
    citations: list[Citation]
    generated_at: str


def euro_label(value: int | float | None, language: str = "id") -> str:
    """Format nilai EUR untuk UI dan prompt."""
    if value is None:
        return "data tidak tersedia" if language == "id" else "unavailable"
    amount = float(value)
    if amount >= 1_000_000:
        unit = "juta" if language == "id" else "million"
        return f"EUR {amount / 1_000_000:.1f} {unit}"
    if amount >= 1_000:
        unit = "ribu" if language == "id" else "thousand"
        return f"EUR {amount / 1_000:.0f} {unit}"
    return f"EUR {amount:.0f}"


def numeric(value: Any) -> float | None:
    """Convert to float without inventing zero for missing values."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def value_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep valuation rows with valid numeric value."""
    return [
        row
        for row in rows
        if row.get("valuation_date") is not None and numeric(row.get("market_value_eur")) is not None
    ]


def non_null_stats(stats: dict[str, Any]) -> dict[str, Any]:
    """Remove null fields so unavailable public stats never appear as zero."""
    blocked = {"id", "player_id", "club_id", "league_id", "last_updated"}
    return {key: value for key, value in stats.items() if key not in blocked and value is not None}


def per_90(value: Any, nineties: Any) -> float | None:
    """Calculate per-90 if both values are available."""
    stat_value = numeric(value)
    nineties_value = numeric(nineties)
    if stat_value is None or not nineties_value:
        return None
    return round(stat_value / nineties_value, 2)


def trend_direction(current_value: float, comparison_value: float) -> str:
    """Classify valuation trend using a small deadband."""
    if comparison_value <= 0:
        return "unknown"
    delta_pct = (current_value - comparison_value) / comparison_value
    if delta_pct > 0.05:
        return "up"
    if delta_pct < -0.05:
        return "down"
    return "stable"


def trend_label(trend: str, language: str) -> str:
    """Translate trend labels for user-facing text."""
    if language != "id":
        return trend
    return {
        "up": "naik",
        "down": "turun",
        "stable": "stabil",
        "unknown": "tidak diketahui",
    }.get(trend, trend)


def estimate_range(current_value: float, trend: str) -> tuple[int, int]:
    """Build conservative valuation range around current market value."""
    if trend == "up":
        low_multiplier, high_multiplier = 0.95, 1.22
    elif trend == "down":
        low_multiplier, high_multiplier = 0.72, 1.05
    elif trend == "stable":
        low_multiplier, high_multiplier = 0.88, 1.12
    else:
        low_multiplier, high_multiplier = 0.80, 1.20
    low = int(round(current_value * low_multiplier / 100_000) * 100_000)
    high = int(round(current_value * high_multiplier / 100_000) * 100_000)
    return max(low, 0), max(high, 0)


def build_citations(stats: list[dict[str, Any]], valuations: list[dict[str, Any]]) -> list[Citation]:
    """Create citations from stats rows and valuation rows."""
    citations: list[Citation] = []
    for row in valuations[:6]:
        citations.append(
            Citation(
                id=str(row["citation_id"]),
                label=f"Transfermarkt valuation {row['valuation_date']}",
                source=str(row.get("source") or "Transfermarkt Kaggle"),
            )
        )
    for row in stats[:3]:
        citations.append(
            Citation(
                id=str(row["citation_id"]),
                label=f"{row.get('season')} {row.get('league')} stats",
                source="FBref via soccerdata",
            )
        )
    return citations


def summarize_context(
    player: dict[str, Any],
    stats: list[dict[str, Any]],
    valuations: list[dict[str, Any]],
    language: str,
) -> dict[str, Any]:
    """Calculate current value, high/low, deltas, trend, and public stats summaries."""
    if not valuations:
        return {
            "has_enough_data": False,
            "reason": "valuation_history_empty",
            "message": NO_DATA_MESSAGE,
        }

    values = [numeric(row.get("market_value_eur")) for row in valuations]
    valid_values = [value for value in values if value is not None]
    if not valid_values:
        return {
            "has_enough_data": False,
            "reason": "valuation_values_invalid",
            "message": NO_DATA_MESSAGE,
        }

    current = float(valid_values[0])
    oldest = float(valid_values[-1])
    highest = max(valid_values)
    lowest = min(valid_values)
    delta = current - oldest
    trend = trend_direction(current, oldest)
    low, high = estimate_range(current, trend)
    latest_stats = stats[0] if stats else {}
    goals_per_90 = per_90(latest_stats.get("goals"), latest_stats.get("nineties"))
    assists_per_90 = per_90(latest_stats.get("assists"), latest_stats.get("nineties"))
    saves_per_90 = per_90(latest_stats.get("saves"), latest_stats.get("nineties"))

    public_stats = {
        "season": latest_stats.get("season"),
        "club": latest_stats.get("club"),
        "league": latest_stats.get("league"),
        "matches_played": latest_stats.get("matches_played"),
        "minutes": latest_stats.get("minutes"),
        "goals": latest_stats.get("goals"),
        "assists": latest_stats.get("assists"),
    }
    optional_stats = {
        "goals_per_90": goals_per_90,
        "assists_per_90": assists_per_90,
        "shots_total": latest_stats.get("shots_total"),
        "saves": latest_stats.get("saves"),
        "saves_per_90": saves_per_90,
        "save_pct": latest_stats.get("save_pct"),
        "clean_sheets": latest_stats.get("clean_sheets"),
        "goals_against": latest_stats.get("goals_against"),
    }
    public_stats.update({key: value for key, value in optional_stats.items() if value is not None})

    return {
        "has_enough_data": True,
        "player_name": player.get("name"),
        "position": player.get("position"),
        "current_value": {
            "eur": int(current),
            "label": euro_label(current, language),
            "date": valuations[0].get("valuation_date"),
        },
        "highest_value": {"eur": int(highest), "label": euro_label(highest, language)},
        "lowest_value": {"eur": int(lowest), "label": euro_label(lowest, language)},
        "value_delta": {
            "eur": int(delta),
            "label": euro_label(abs(delta), language),
            "direction": "positive" if delta > 0 else "negative" if delta < 0 else "neutral",
        },
        "trend_direction": trend,
        "estimated_range": {
            "low_eur": low,
            "high_eur": high,
            "label": f"{euro_label(low, language)} - {euro_label(high, language)}",
        },
        "public_stats": public_stats,
        "valuation_sample_size": len(valuations),
        "stats_sample_size": len(stats),
    }


def build_supporting_factors(summary: dict[str, Any], citations: list[Citation], language: str) -> list[dict[str, Any]]:
    """Build deterministic supporting factors grounded by citations."""
    if not summary.get("has_enough_data"):
        return []
    valuation_citations = [citation.id for citation in citations if citation.id.startswith("valuation:")]
    stats_citations = [citation.id for citation in citations if citation.id.startswith("stats:")]
    current = summary["current_value"]
    delta = summary["value_delta"]
    stats = summary.get("public_stats", {})
    if language == "id":
        factors = [
            {
                "factor": f"Nilai pasar terbaru {current['label']} pada {current['date']}.",
                "impact": "neutral",
                "citation_ids": valuation_citations[:1],
            },
            {
                "factor": f"Tren valuasi {trend_label(summary['trend_direction'], language)} dengan perubahan {delta['label']} dari sampel historis terbaru.",
                "impact": "positive" if delta["direction"] == "positive" else "negative" if delta["direction"] == "negative" else "neutral",
                "citation_ids": valuation_citations[:2],
            },
        ]
        if stats:
            factors.append(
                {
                    "factor": f"Statistik publik terbaru: {stats.get('minutes', 0)} menit, {stats.get('matches_played', 0)} laga, {stats.get('goals', 0)} gol, {stats.get('assists', 0)} assist.",
                    "impact": "neutral",
                    "citation_ids": stats_citations[:1],
                }
            )
    else:
        factors = [
            {
                "factor": f"Latest market value is {current['label']} on {current['date']}.",
                "impact": "neutral",
                "citation_ids": valuation_citations[:1],
            },
            {
                "factor": f"Valuation trend is {summary['trend_direction']} with a historical delta of {delta['label']}.",
                "impact": "positive" if delta["direction"] == "positive" else "negative" if delta["direction"] == "negative" else "neutral",
                "citation_ids": valuation_citations[:2],
            },
        ]
        if stats:
            factors.append(
                {
                    "factor": f"Latest public stats: {stats.get('minutes', 0)} minutes, {stats.get('matches_played', 0)} matches, {stats.get('goals', 0)} goals, {stats.get('assists', 0)} assists.",
                    "impact": "neutral",
                    "citation_ids": stats_citations[:1],
                }
            )
    return factors


class ValuationReasoner:
    """Build KG context and generate LLM-based valuation reasoning."""

    def __init__(self) -> None:
        self.settings = get_cached_settings()

    def get_player_context(self, player_name: str, language: str = "id") -> ValuationContext:
        """Fetch player profile, stats, and valuation history from Neo4j."""
        loader = Neo4jGraphLoader()
        try:
            rows = loader.run_read_query(PLAYER_CONTEXT_QUERY, {"player_name": player_name})
        finally:
            loader.close()
        if not rows:
            raise ValueError(f"Pemain tidak ditemukan di Knowledge Graph: {player_name}")

        row = rows[0]
        raw_stats = row.get("stats") or []
        stats = [non_null_stats(stat) for stat in raw_stats]
        valuations = value_rows(row.get("valuations") or [])
        player = {
            "player_id": row.get("player_id"),
            "name": row.get("name"),
            "birth_date": row.get("birth_date"),
            "height_cm": row.get("height_cm"),
            "preferred_foot": row.get("preferred_foot"),
            "nationality": row.get("nationality"),
            "position": row.get("position"),
        }
        sampled_valuations = valuations[:12]
        citations = build_citations(stats, sampled_valuations)
        summary = summarize_context(player, stats, sampled_valuations, language)
        return ValuationContext(
            player=player,
            latest_stats=stats[:3],
            valuation_history=sampled_valuations,
            summary=summary,
            citations=citations,
            generated_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        )

    def fallback_answer(self, context: ValuationContext, language: str) -> dict[str, Any]:
        """Return grounded deterministic answer when LLM is unavailable."""
        summary = context.summary
        citations = [asdict(citation) for citation in context.citations]
        if not summary.get("has_enough_data"):
            return {
                "player": context.player,
                "current_value": None,
                "estimated_range": None,
                "trend_direction": "unknown",
                "supporting_factors": [],
                "explanation": summary.get("message") or NO_DATA_MESSAGE,
                "citations": citations,
                "llm_used": False,
                "fallback_reason": summary.get("reason"),
            }

        factors = build_supporting_factors(summary, context.citations, language)
        if language == "id":
            explanation = (
                f"{context.player['name']} memiliki nilai pasar terbaru {summary['current_value']['label']} "
                f"dengan tren {trend_label(summary['trend_direction'], language)}. Range estimasi konservatif adalah "
                f"{summary['estimated_range']['label']}. Estimasi ini memakai riwayat valuasi dan statistik publik "
                "yang tersedia dari KG, bukan angka pasti."
            )
        else:
            explanation = (
                f"{context.player['name']} has a latest market value of {summary['current_value']['label']} "
                f"with a {summary['trend_direction']} trend. The conservative estimated range is "
                f"{summary['estimated_range']['label']}. This estimate uses available KG valuation history and "
                "public stats, not a fixed-price prediction."
            )
        return {
            "player": context.player,
            "current_value": summary["current_value"],
            "highest_value": summary["highest_value"],
            "lowest_value": summary["lowest_value"],
            "value_delta": summary["value_delta"],
            "estimated_range": summary["estimated_range"],
            "trend_direction": summary["trend_direction"],
            "supporting_factors": factors,
            "explanation": explanation,
            "citations": citations,
            "llm_used": False,
        }

    def build_prompt_payload(self, context: ValuationContext, language: str) -> dict[str, Any]:
        """Build compact JSON payload for LLM."""
        return {
            "language": language,
            "player": context.player,
            "summary": context.summary,
            "latest_stats": context.latest_stats,
            "valuation_history": context.valuation_history,
            "citations": [asdict(citation) for citation in context.citations],
        }

    def call_llm(self, context: ValuationContext, language: str) -> dict[str, Any]:
        """Call OpenAI for answer synthesis and return parsed JSON."""
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY belum tersedia")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Package openai belum terpasang") from exc

        prompt_path = self.settings.backend_dir / "config" / "prompts" / "valuation_reasoning_prompt.txt"
        system_prompt = prompt_path.read_text(encoding="utf-8")
        client = OpenAI(
            api_key=self.settings.openai_api_key,
            timeout=self.settings.openai_timeout_seconds,
        )
        response = client.chat.completions.create(
            model=self.settings.llm_model_name,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        self.build_prompt_payload(context, language),
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        fallback = self.fallback_answer(context, language)
        parsed["player"] = context.player
        parsed["llm_used"] = True
        parsed.setdefault("current_value", fallback.get("current_value"))
        parsed.setdefault("highest_value", fallback.get("highest_value"))
        parsed.setdefault("lowest_value", fallback.get("lowest_value"))
        parsed.setdefault("value_delta", fallback.get("value_delta"))
        parsed.setdefault("estimated_range", fallback.get("estimated_range"))
        parsed.setdefault("trend_direction", fallback.get("trend_direction"))

        factors = parsed.get("supporting_factors") or []
        generic_factor = any(
            "berbasis data" in str(factor.get("factor", "")).lower()
            or "data-based" in str(factor.get("factor", "")).lower()
            for factor in factors
            if isinstance(factor, dict)
        )
        if len(factors) < 2 or generic_factor:
            parsed["supporting_factors"] = fallback.get("supporting_factors", [])

        citations = parsed.get("citations") or []
        if len(citations) < len(context.citations):
            parsed["citations"] = [asdict(citation) for citation in context.citations]
        return parsed

    def reason(
        self,
        player_name: str,
        language: str = "id",
        use_llm: bool = True,
    ) -> dict[str, Any]:
        """Build valuation answer for a player."""
        context = self.get_player_context(player_name, language)
        if not context.summary.get("has_enough_data"):
            return self.fallback_answer(context, language)
        if use_llm:
            try:
                return self.call_llm(context, language)
            except Exception as exc:  # pragma: no cover - network/API fallback
                LOGGER.warning("LLM valuation call gagal, fallback deterministik dipakai: %s", exc)
                answer = self.fallback_answer(context, language)
                answer["fallback_reason"] = f"llm_error: {exc}"
                return answer
        return self.fallback_answer(context, language)


def find_sample_players_by_position() -> dict[str, str]:
    """Find one smoke-test player per main position."""
    positions = ("Goalkeeper", "Defender", "Midfielder", "Forward")
    loader = Neo4jGraphLoader()
    try:
        samples = {}
        for position in positions:
            rows = loader.run_read_query(POSITION_SAMPLE_QUERY, {"position": position})
            if rows:
                samples[position] = rows[0]["name"]
        return samples
    finally:
        loader.close()


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI parser."""
    parser = argparse.ArgumentParser(description="Run LLM valuation reasoning")
    parser.add_argument("--player", default="Aaron Ramsdale", help="Nama pemain")
    parser.add_argument("--language", default="id", choices=("id", "en"), help="Bahasa output")
    parser.add_argument("--use-llm", action="store_true", help="Panggil OpenAI LLM")
    parser.add_argument("--smoke-test", action="store_true", help="Tes sample GK, DEF, MID, FWD")
    return parser


def main() -> None:
    """CLI entry point."""
    settings = get_cached_settings()
    configure_logging(settings.log_level, settings.logs_dir / "valuation_reasoner.log")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    args = build_arg_parser().parse_args()
    reasoner = ValuationReasoner()
    if args.smoke_test:
        samples = find_sample_players_by_position()
        for position, player_name in samples.items():
            result = reasoner.reason(player_name, language=args.language, use_llm=args.use_llm)
            print(
                json.dumps(
                    {
                        "position": position,
                        "player": result["player"]["name"],
                        "current_value": result.get("current_value"),
                        "estimated_range": result.get("estimated_range"),
                        "trend_direction": result.get("trend_direction"),
                        "citations_count": len(result.get("citations", [])),
                        "llm_used": result.get("llm_used", False),
                    },
                    ensure_ascii=False,
                )
            )
        return

    result = reasoner.reason(args.player, language=args.language, use_llm=args.use_llm)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
