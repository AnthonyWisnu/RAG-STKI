"""Generate retrieval documents from Neo4j, Wikipedia cache, and valuations."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
for path in (PROJECT_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from config.settings import get_cached_settings
    from etl.neo4j_loader import Neo4jGraphLoader
    from src.utils.logging import configure_logging
except ModuleNotFoundError:
    from backend.config.settings import get_cached_settings
    from backend.etl.neo4j_loader import Neo4jGraphLoader
    from backend.src.utils.logging import configure_logging

LOGGER = logging.getLogger(__name__)

PLAYER_CONTEXT_QUERY = """
MATCH (p:Player)-[:HAS_STATS_IN]->(s:PlayerSeasonStats)
MATCH (s)-[:DURING]->(se:Season)
MATCH (s)-[:WITH_CLUB]->(c:Club)
MATCH (s)-[:IN_LEAGUE]->(l:League)
OPTIONAL MATCH (p)-[:PLAYS_POSITION]->(pos:Position)
WITH p, pos, s, se, c, l
ORDER BY se.id DESC
WITH p, pos, collect({
    season: se.id,
    club: c.name,
    league: l.name,
    league_id: l.id,
    matches_played: s.matches_played,
    starts: s.starts,
    minutes: s.minutes,
    goals: s.goals,
    assists: s.assists,
    shots_total: s.shots_total,
    shots_on_target: s.shots_on_target,
    fouls_committed: s.fouls_committed,
    fouls_drawn: s.fouls_drawn,
    offsides: s.offsides,
    saves: s.saves,
    save_pct: s.save_pct,
    clean_sheets: s.clean_sheets,
    goals_against: s.goals_against
}) AS season_stats
OPTIONAL MATCH (p)-[:HAS_VALUATION]->(v:Valuation)
WITH p, pos, season_stats, v
ORDER BY v.valuation_date DESC
WITH p, pos, season_stats, collect({
    date: v.valuation_date,
    value: v.market_value_eur,
    source: v.source
})[0..12] AS valuations
RETURN p.api_id AS player_id,
       p.name AS name,
       p.birth_date AS birth_date,
       p.height_cm AS height_cm,
       p.preferred_foot AS preferred_foot,
       p.nationality AS nationality,
       pos.name AS position,
       season_stats,
       valuations
ORDER BY name
LIMIT $limit
"""


@dataclass(frozen=True)
class RetrievalDocument:
    """Dokumen yang siap di-upsert ke vector database."""

    doc_id: str
    text: str
    metadata: dict[str, Any]


def clean_text(value: str) -> str:
    """Normalize whitespace agar dokumen embedding stabil."""
    return re.sub(r"\s+", " ", value).strip()


def format_value_eur(value: Any, language: str = "id") -> str:
    """Format nilai EUR untuk narasi manusia."""
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


def value_number(value: Any) -> float | None:
    """Convert numeric value without turning missing values into zero."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def latest_stat(stats: list[dict[str, Any]]) -> dict[str, Any]:
    """Ambil statistik musim terbaru dari hasil query yang sudah diurutkan desc."""
    return stats[0] if stats else {}


def non_empty_valuations(valuations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Buang valuation kosong dari OPTIONAL MATCH."""
    return [
        valuation
        for valuation in valuations
        if valuation.get("date") is not None and valuation.get("value") is not None
    ]


def stat_line_id(stat: dict[str, Any]) -> str:
    """Render satu baris statistik Bahasa Indonesia tanpa field null."""
    parts = [
        f"{stat.get('season')} bersama {stat.get('club')} di {stat.get('league')}",
        f"{stat.get('matches_played', 0)} laga",
        f"{stat.get('minutes', 0)} menit",
        f"{stat.get('goals', 0)} gol",
        f"{stat.get('assists', 0)} assist",
    ]
    if stat.get("shots_total") is not None:
        parts.append(f"{stat['shots_total']:.0f} tembakan")
    if stat.get("saves") is not None:
        parts.append(f"{stat['saves']:.0f} saves")
    if stat.get("save_pct") is not None:
        parts.append(f"save percentage {stat['save_pct']:.1f}%")
    if stat.get("clean_sheets") is not None:
        parts.append(f"{stat['clean_sheets']:.0f} clean sheets")
    return "- " + ", ".join(parts) + "."


def stat_line_en(stat: dict[str, Any]) -> str:
    """Render one English stats line without null fields."""
    parts = [
        f"{stat.get('season')} with {stat.get('club')} in {stat.get('league')}",
        f"{stat.get('matches_played', 0)} matches",
        f"{stat.get('minutes', 0)} minutes",
        f"{stat.get('goals', 0)} goals",
        f"{stat.get('assists', 0)} assists",
    ]
    if stat.get("shots_total") is not None:
        parts.append(f"{stat['shots_total']:.0f} shots")
    if stat.get("saves") is not None:
        parts.append(f"{stat['saves']:.0f} saves")
    if stat.get("save_pct") is not None:
        parts.append(f"{stat['save_pct']:.1f}% save percentage")
    if stat.get("clean_sheets") is not None:
        parts.append(f"{stat['clean_sheets']:.0f} clean sheets")
    return "- " + ", ".join(parts) + "."


def build_stats_summary(stats: list[dict[str, Any]], language: str) -> str:
    """Buat ringkasan statistik publik beberapa musim terakhir."""
    if not stats:
        return "Data statistik publik tidak tersedia." if language == "id" else "Public statistics are unavailable."
    renderer = stat_line_id if language == "id" else stat_line_en
    return "\n".join(renderer(stat) for stat in stats[:3])


def build_valuation_summary(valuations: list[dict[str, Any]], language: str) -> str:
    """Buat narasi tren valuasi dari node Valuation."""
    valuations = non_empty_valuations(valuations)
    if not valuations:
        return "Data valuasi tidak tersedia." if language == "id" else "Valuation data is unavailable."

    current = valuations[0]
    oldest = valuations[-1]
    current_value = value_number(current.get("value"))
    oldest_value = value_number(oldest.get("value"))
    if current_value is None or oldest_value is None:
        return "Data valuasi tidak lengkap." if language == "id" else "Valuation data is incomplete."

    delta = current_value - oldest_value
    direction = "naik" if delta > 0 else "turun" if delta < 0 else "stabil"
    if language == "id":
        return (
            f"Nilai terbaru {format_value_eur(current_value, language)} pada {current['date']}. "
            f"Dibanding titik awal sampel {oldest['date']} sebesar {format_value_eur(oldest_value, language)}, "
            f"tren valuasi {direction} dengan perubahan {format_value_eur(abs(delta), language)}."
        )
    direction_en = "up" if delta > 0 else "down" if delta < 0 else "stable"
    return (
        f"Latest market value is {format_value_eur(current_value, language)} on {current['date']}. "
        f"Compared with the earliest sampled value on {oldest['date']} at {format_value_eur(oldest_value, language)}, "
        f"the valuation trend is {direction_en} by {format_value_eur(abs(delta), language)}."
    )


def load_template(language: str) -> str:
    """Load template profil dari config prompts."""
    settings = get_cached_settings()
    filename = "profile_template_id.txt" if language == "id" else "profile_template_en.txt"
    return (settings.backend_dir / "config" / "prompts" / filename).read_text(encoding="utf-8")


def cache_filename(player_id: int, language: str) -> str:
    """Nama file cache Wikipedia deterministik."""
    return f"wiki_{language}_{player_id}.json"


def fetch_wikipedia_summary(
    player_id: int,
    player_name: str,
    language: str,
    cache_dir: Path,
) -> dict[str, Any]:
    """Fetch Wikipedia summary dengan cache JSON dan fallback kosong."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / cache_filename(player_id, language)
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    result: dict[str, Any] = {
        "status": "missing",
        "language": language,
        "page_title": None,
        "url": None,
        "summary": None,
        "fetched_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    try:
        import wikipediaapi

        wiki = wikipediaapi.Wikipedia(
            language=language,
            user_agent="RAG-STKI football knowledge graph project",
        )
        titles = [f"{player_name} (footballer)", player_name]
        if language == "id":
            titles = [player_name, f"{player_name} (pemain sepak bola)"]
        for title in titles:
            page = wiki.page(title)
            if page.exists() and page.summary:
                result.update(
                    {
                        "status": "ok",
                        "page_title": page.title,
                        "url": page.fullurl,
                        "summary": clean_text(page.summary[:1600]),
                    }
                )
                break
    except Exception as exc:  # pragma: no cover - network/cache fallback
        LOGGER.warning("Wikipedia fetch gagal player_id=%s lang=%s: %s", player_id, language, exc)
        result["status"] = "error"

    cache_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def document_id(kind: str, language: str, player_id: int) -> str:
    """Doc ID stabil untuk upsert idempotent."""
    return f"{kind}:{language}:{player_id}"


def clean_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """Chroma hanya menerima metadata scalar non-null."""
    cleaned: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


def build_profile_document(row: dict[str, Any], language: str) -> RetrievalDocument:
    """Build profile document dari KG context."""
    player_id = int(row["player_id"])
    stats = row.get("season_stats") or []
    valuations = row.get("valuations") or []
    current_stat = latest_stat(stats)
    current_value = non_empty_valuations(valuations)[0]["value"] if non_empty_valuations(valuations) else None
    template = load_template(language)
    text = template.format(
        name=row.get("name") or "Unknown",
        position=row.get("position") or "Unknown",
        nationality=row.get("nationality") or "Unknown",
        current_club=current_stat.get("club") or "Unknown",
        current_league=current_stat.get("league") or "Unknown",
        current_season=current_stat.get("season") or "Unknown",
        current_value=format_value_eur(current_value, language),
        stats_summary=build_stats_summary(stats, language),
        valuation_summary=build_valuation_summary(valuations, language),
    )
    return RetrievalDocument(
        doc_id=document_id("profile", language, player_id),
        text=text,
        metadata=clean_metadata(
            {
                "player_id": player_id,
                "player_name": row.get("name"),
                "doc_type": "profile",
                "language": language,
                "position": row.get("position"),
                "club": current_stat.get("club"),
                "league": current_stat.get("league"),
                "league_id": current_stat.get("league_id"),
                "season": current_stat.get("season"),
                "source": "neo4j_kg",
            }
        ),
    )


def build_valuation_document(row: dict[str, Any], language: str) -> RetrievalDocument:
    """Build valuation trend document."""
    player_id = int(row["player_id"])
    valuations = non_empty_valuations(row.get("valuations") or [])
    current_stat = latest_stat(row.get("season_stats") or [])
    if language == "id":
        header = f"Dokumen valuasi untuk {row.get('name')}."
        detail = "Riwayat valuasi terbaru: "
    else:
        header = f"Valuation document for {row.get('name')}."
        detail = "Recent valuation history: "
    history = "; ".join(
        f"{valuation['date']} {format_value_eur(valuation['value'], language)}" for valuation in valuations[:8]
    )
    fallback = "data tidak tersedia" if language == "id" else "unavailable"
    text = f"{header}\n{build_valuation_summary(valuations, language)}\n{detail}{history or fallback}."
    return RetrievalDocument(
        doc_id=document_id("valuation", language, player_id),
        text=text,
        metadata=clean_metadata(
            {
                "player_id": player_id,
                "player_name": row.get("name"),
                "doc_type": "valuation",
                "language": language,
                "position": row.get("position"),
                "club": current_stat.get("club"),
                "league": current_stat.get("league"),
                "league_id": current_stat.get("league_id"),
                "season": current_stat.get("season"),
                "source": "neo4j_kg",
            }
        ),
    )


def build_wiki_document(
    row: dict[str, Any],
    language: str,
    wiki_summary: dict[str, Any],
) -> RetrievalDocument:
    """Build Wikipedia document, falling back to KG profile if summary is missing."""
    player_id = int(row["player_id"])
    current_stat = latest_stat(row.get("season_stats") or [])
    summary = wiki_summary.get("summary")
    if summary:
        text = f"Wikipedia summary for {row.get('name')}: {summary}"
        doc_type = "wiki"
        source = wiki_summary.get("url") or "wikipedia"
    else:
        text = (
            f"Wikipedia summary unavailable for {row.get('name')}. "
            f"KG fallback: {row.get('name')} is listed as {row.get('position') or 'Unknown'} "
            f"with latest club {current_stat.get('club') or 'Unknown'} in {current_stat.get('league') or 'Unknown'}."
        )
        doc_type = "wiki_fallback"
        source = "neo4j_kg_fallback"
    return RetrievalDocument(
        doc_id=document_id(doc_type, language, player_id),
        text=text,
        metadata=clean_metadata(
            {
                "player_id": player_id,
                "player_name": row.get("name"),
                "doc_type": doc_type,
                "language": language,
                "position": row.get("position"),
                "club": current_stat.get("club"),
                "league": current_stat.get("league"),
                "league_id": current_stat.get("league_id"),
                "season": current_stat.get("season"),
                "source": source,
                "wiki_status": wiki_summary.get("status"),
                "wiki_title": wiki_summary.get("page_title"),
            }
        ),
    )


def generate_documents(
    limit: int,
    languages: tuple[str, ...] = ("id", "en"),
    include_wiki: bool = True,
) -> list[RetrievalDocument]:
    """Generate retrieval documents from current Neo4j graph."""
    settings = get_cached_settings()
    loader = Neo4jGraphLoader()
    try:
        rows = loader.run_read_query(PLAYER_CONTEXT_QUERY, {"limit": limit})
    finally:
        loader.close()

    documents: list[RetrievalDocument] = []
    for row in rows:
        player_id = int(row["player_id"])
        for language in languages:
            documents.append(build_profile_document(row, language))
            documents.append(build_valuation_document(row, language))
            if include_wiki:
                wiki_summary = fetch_wikipedia_summary(
                    player_id=player_id,
                    player_name=str(row.get("name") or ""),
                    language=language,
                    cache_dir=settings.wiki_cache_dir,
                )
                documents.append(build_wiki_document(row, language, wiki_summary))

    LOGGER.info("Generated retrieval documents: players=%s docs=%s", len(rows), len(documents))
    return documents


def write_jsonl(documents: list[RetrievalDocument], output_path: Path) -> None:
    """Write generated documents to JSONL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for document in documents:
            handle.write(json.dumps(asdict(document), ensure_ascii=False) + "\n")
    LOGGER.info("Documents written: %s rows=%s", output_path, len(documents))


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI parser."""
    settings = get_cached_settings()
    parser = argparse.ArgumentParser(description="Generate KG/RAG retrieval documents")
    parser.add_argument("--limit", type=int, default=100, help="Jumlah pemain yang diambil dari KG")
    parser.add_argument(
        "--output",
        type=Path,
        default=settings.processed_data_dir / "documents.jsonl",
        help="Path output JSONL",
    )
    parser.add_argument(
        "--languages",
        default="id,en",
        help="Comma-separated language list: id,en",
    )
    parser.add_argument("--skip-wiki", action="store_true", help="Jangan fetch Wikipedia")
    return parser


def main() -> None:
    """Generate documents from CLI."""
    settings = get_cached_settings()
    configure_logging(settings.log_level, settings.logs_dir / "document_generator.log")
    for logger_name in ("httpx", "httpcore", "wikipediaapi"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    args = build_arg_parser().parse_args()
    languages = tuple(language.strip() for language in args.languages.split(",") if language.strip())
    documents = generate_documents(
        limit=args.limit,
        languages=languages,
        include_wiki=not args.skip_wiki,
    )
    write_jsonl(documents, args.output)
    for document in documents[:3]:
        print(json.dumps(asdict(document), ensure_ascii=False))


if __name__ == "__main__":
    main()
