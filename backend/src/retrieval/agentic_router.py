"""Agentic retrieval router for KG, vector, hybrid, and valuation reasoning."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
for path in (PROJECT_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from config.settings import NO_DATA_MESSAGE, UCL_UNAVAILABLE_MESSAGE
    from src.llm.openai_client import OpenAIClient
    from src.llm.prompt_loader import PromptLoader
    from src.retrieval.kg_retriever import KGRetriever
    from src.retrieval.vector_retriever import VectorRetriever
    from src.utils.language_detect import detect_language
    from src.valuation.valuation_reasoner import ValuationReasoner
except ModuleNotFoundError:
    from backend.config.settings import NO_DATA_MESSAGE, UCL_UNAVAILABLE_MESSAGE
    from backend.src.llm.openai_client import OpenAIClient
    from backend.src.llm.prompt_loader import PromptLoader
    from backend.src.retrieval.kg_retriever import KGRetriever
    from backend.src.retrieval.vector_retriever import VectorRetriever
    from backend.src.utils.language_detect import detect_language
    from backend.src.valuation.valuation_reasoner import ValuationReasoner

LOGGER = logging.getLogger(__name__)

Strategy = Literal["kg_only", "vector_only", "hybrid", "valuation_reasoning"]


@dataclass(frozen=True)
class QueryPlan:
    """Query planner output."""

    strategy: Strategy
    language: str
    reason: str
    needs_citations: bool = True


@dataclass(frozen=True)
class AgenticResponse:
    """End-to-end retrieval response."""

    question: str
    answer: str
    strategy_used: Strategy
    language: str
    data_available: bool
    citations: list[dict[str, Any]]
    kg_rows: list[dict[str, Any]]
    vector_documents: list[dict[str, Any]]
    valuation: dict[str, Any] | None
    fallback_signal: str | None
    debug: dict[str, Any]


def is_ucl_question(question: str) -> bool:
    """Detect unsupported Champions League questions."""
    lowered = question.lower()
    return "champions league" in lowered or "liga champions" in lowered or "ucl" in lowered


def normalize_space(text: str) -> str:
    """Collapse whitespace."""
    return re.sub(r"\s+", " ", text).strip()


def extract_player_name_for_valuation(question: str) -> str:
    """Extract player candidate name from a valuation query."""
    cleaned = question
    removable = [
        "estimasi",
        "prediksi",
        "range",
        "nilai pasar",
        "valuasi",
        "valuation",
        "market value",
        "berapa",
        "estimate",
        "predict",
        "please",
        "tolong",
        "untuk",
        "for",
        "?",
    ]
    for token in removable:
        cleaned = re.sub(re.escape(token), " ", cleaned, flags=re.IGNORECASE)
    return normalize_space(cleaned)


def preview_text(text: str, max_chars: int = 360) -> str:
    """Short preview for synthesis."""
    cleaned = normalize_space(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def choose_strategy(question: str) -> QueryPlan:
    """Deterministic query planner for stable routing."""
    language = detect_language(question)
    lowered = question.lower()
    if is_ucl_question(question):
        return QueryPlan("kg_only", language, "unsupported Champions League scope")
    if any(token in lowered for token in ("estimasi", "prediksi", "estimate", "predict", "range")) and any(
        token in lowered for token in ("nilai", "valuasi", "value", "valuation", "market")
    ):
        return QueryPlan("valuation_reasoning", language, "valuation estimate requested")
    if any(token in lowered for token in ("bandingkan", "compare", "analisis", "analysis")):
        return QueryPlan("hybrid", language, "structured and narrative comparison requested")
    if any(token in lowered for token in ("mirip", "serupa", "similar")) and any(
        token in lowered for token in ("lebih murah", "lebih rendah", "lower", "cheaper", "market value", "nilai pasar")
    ):
        return QueryPlan("kg_only", language, "similar cheaper player search requested")
    if any(token in lowered for token in ("top", "ranking", "rank", "skor", "scorer", "pencetak")):
        return QueryPlan("kg_only", language, "structured data requested")
    if any(token in lowered for token in ("profil", "profile", "siapa", "who is", "ringkasan", "summary", "jelaskan", "describe")):
        if any(token in lowered for token in ("gol", "goals", "assist", "nilai", "valuasi", "valuation", "value", "stat", "stats")):
            return QueryPlan("hybrid", language, "profile plus structured data requested")
        return QueryPlan("vector_only", language, "descriptive profile requested")
    if any(
        token in lowered
        for token in (
            "gol",
            "goals",
            "assist",
            "saves",
            "clean sheet",
            "nilai pasar",
            "market value",
            "valuation",
            "valuasi",
        )
    ):
        return QueryPlan("kg_only", language, "structured data requested")
    return QueryPlan("vector_only", language, "default narrative retrieval")


class AgenticRouter:
    """Orchestrate retrieval and answer synthesis."""

    def __init__(self) -> None:
        self.kg_retriever = KGRetriever()
        self.vector_retriever: VectorRetriever | None = None
        self.valuation_reasoner = ValuationReasoner()
        self.llm = OpenAIClient()
        self.prompts = PromptLoader()

    def get_vector_retriever(self) -> VectorRetriever:
        """Load vector retriever lazily because embedding model is heavy."""
        if self.vector_retriever is None:
            self.vector_retriever = VectorRetriever()
        return self.vector_retriever

    def plan_query(self, question: str, use_llm_planner: bool = False) -> QueryPlan:
        """Plan query strategy, with optional LLM planner fallback."""
        if not use_llm_planner or not self.llm.available:
            return choose_strategy(question)
        try:
            prompt = self.prompts.load("router_prompt.txt")
            parsed = self.llm.chat_json(
                prompt,
                {"question": question, "language_hint": detect_language(question)},
            ).parsed_json or {}
            strategy = parsed.get("strategy")
            if strategy in {"kg_only", "vector_only", "hybrid", "valuation_reasoning"}:
                return QueryPlan(
                    strategy=strategy,
                    language=parsed.get("language") if parsed.get("language") in {"id", "en"} else detect_language(question),
                    reason=str(parsed.get("reason") or "llm planner"),
                    needs_citations=bool(parsed.get("needs_citations", True)),
                )
        except Exception as exc:
            LOGGER.warning("LLM planner gagal, heuristic planner dipakai: %s", exc)
        return choose_strategy(question)

    def synthesize_kg_answer(self, question: str, rows: list[dict[str, Any]], language: str) -> str:
        """Synthesize answer from KG rows."""
        if not rows:
            return NO_DATA_MESSAGE
        first = rows[0]
        if "similarity_score" in first:
            reference = first.get("reference_player")
            reference_value = first.get("reference_market_value_eur")
            lines = []
            for index, row in enumerate(rows[:5], start=1):
                value = row.get("market_value_eur")
                value_label = f"EUR {float(value) / 1_000_000:.1f} juta" if value is not None else "nilai tidak tersedia"
                if language == "id":
                    lines.append(
                        f"{index}. {row.get('player')} ({row.get('club')}, {row.get('league')}) - "
                        f"{int(row.get('minutes') or 0)} menit, {row.get('goals') or 0} gol, "
                        f"{row.get('assists') or 0} assist, nilai {value_label}, "
                        f"skor kemiripan {row.get('similarity_score')}."
                    )
                else:
                    lines.append(
                        f"{index}. {row.get('player')} ({row.get('club')}, {row.get('league')}) - "
                        f"{int(row.get('minutes') or 0)} minutes, {row.get('goals') or 0} goals, "
                        f"{row.get('assists') or 0} assists, value {value_label}, "
                        f"similarity score {row.get('similarity_score')}."
                    )
            if language == "id":
                reference_label = f"EUR {float(reference_value) / 1_000_000:.1f} juta" if reference_value is not None else "tidak tersedia"
                return (
                    f"Pemain dengan statistik paling mirip {reference} tetapi market value lebih rendah "
                    f"dari {reference_label}:\n" + "\n".join(lines)
                )
            reference_label = f"EUR {float(reference_value) / 1_000_000:.1f} million" if reference_value is not None else "unavailable"
            return (
                f"Players statistically similar to {reference} with lower market value than {reference_label}:\n"
                + "\n".join(lines)
            )
        if "goals" in first:
            lines = []
            for index, row in enumerate(rows[:5], start=1):
                if language == "id":
                    lines.append(
                        f"{index}. {row.get('player')} ({row.get('club')}) - {row.get('goals')} gol, {row.get('assists')} assist, {row.get('minutes')} menit"
                    )
                else:
                    lines.append(
                        f"{index}. {row.get('player')} ({row.get('club')}) - {row.get('goals')} goals, {row.get('assists')} assists, {row.get('minutes')} minutes"
                    )
            prefix = "Top hasil dari Knowledge Graph:" if language == "id" else "Top Knowledge Graph results:"
            return prefix + "\n" + "\n".join(lines)
        if "market_value_eur" in first:
            if language == "id":
                return (
                    f"Nilai pasar terbaru {first.get('player')} adalah EUR {int(first.get('market_value_eur', 0)):,} "
                    f"pada {first.get('valuation_date')}."
                )
            return (
                f"{first.get('player')}'s latest market value is EUR {int(first.get('market_value_eur', 0)):,} "
                f"on {first.get('valuation_date')}."
            )
        return json.dumps(rows[:5], ensure_ascii=False)

    def synthesize_vector_answer(self, documents: list[dict[str, Any]], language: str) -> str:
        """Synthesize answer from vector documents."""
        if not documents:
            return NO_DATA_MESSAGE
        top = documents[0]
        if language == "id":
            return f"Ringkasan dokumen paling relevan: {preview_text(top.get('text', ''))}"
        return f"Most relevant document summary: {preview_text(top.get('text', ''))}"

    def synthesize_hybrid_answer(
        self,
        question: str,
        kg_rows: list[dict[str, Any]],
        vector_documents: list[dict[str, Any]],
        language: str,
    ) -> str:
        """Synthesize hybrid answer from KG and vector context."""
        kg_part = self.synthesize_kg_answer(question, kg_rows, language) if kg_rows else ""
        vector_part = self.synthesize_vector_answer(vector_documents, language) if vector_documents else ""
        if not kg_part and not vector_part:
            return NO_DATA_MESSAGE
        if language == "id":
            return "\n\n".join(part for part in (kg_part, vector_part) if part)
        return "\n\n".join(part for part in (kg_part, vector_part) if part)

    def answer(
        self,
        question: str,
        use_llm_planner: bool = False,
        use_llm_valuation: bool = False,
    ) -> AgenticResponse:
        """Run end-to-end routing, retrieval, and synthesis."""
        plan = self.plan_query(question, use_llm_planner=use_llm_planner)
        if is_ucl_question(question):
            return AgenticResponse(
                question=question,
                answer=UCL_UNAVAILABLE_MESSAGE,
                strategy_used=plan.strategy,
                language=plan.language,
                data_available=False,
                citations=[],
                kg_rows=[],
                vector_documents=[],
                valuation=None,
                fallback_signal=UCL_UNAVAILABLE_MESSAGE,
                debug={"plan": asdict(plan)},
            )

        kg_rows: list[dict[str, Any]] = []
        kg_citations: list[dict[str, Any]] = []
        vector_documents: list[dict[str, Any]] = []
        vector_citations: list[dict[str, Any]] = []
        valuation: dict[str, Any] | None = None
        fallback_signal: str | None = None
        answer_text = NO_DATA_MESSAGE

        if plan.strategy == "kg_only":
            kg_result = self.kg_retriever.retrieve(question)
            kg_rows = kg_result.rows
            kg_citations = kg_result.citations
            fallback_signal = kg_result.fallback_signal
            answer_text = self.synthesize_kg_answer(question, kg_rows, plan.language)

        elif plan.strategy == "vector_only":
            vector_result = self.get_vector_retriever().retrieve(question, top_k=5)
            vector_documents = vector_result.documents
            vector_citations = vector_result.citations
            fallback_signal = vector_result.fallback_signal
            answer_text = self.synthesize_vector_answer(vector_documents, plan.language)

        elif plan.strategy == "hybrid":
            kg_result = self.kg_retriever.retrieve(question)
            vector_result = self.get_vector_retriever().retrieve(question, top_k=4)
            kg_rows = kg_result.rows
            kg_citations = kg_result.citations
            vector_documents = vector_result.documents
            vector_citations = vector_result.citations
            fallback_signal = kg_result.fallback_signal if not kg_rows and not vector_documents else None
            answer_text = self.synthesize_hybrid_answer(question, kg_rows, vector_documents, plan.language)

        elif plan.strategy == "valuation_reasoning":
            player_name = extract_player_name_for_valuation(question)
            try:
                valuation = self.valuation_reasoner.reason(
                    player_name,
                    language=plan.language,
                    use_llm=use_llm_valuation,
                )
                answer_text = valuation.get("explanation") or NO_DATA_MESSAGE
                fallback_signal = valuation.get("fallback_reason")
            except Exception as exc:
                LOGGER.warning("Valuation reasoning gagal: %s", exc)
                fallback_signal = NO_DATA_MESSAGE
                answer_text = NO_DATA_MESSAGE

        citations = kg_citations + vector_citations
        if valuation:
            citations += valuation.get("citations", [])
        data_available = bool(kg_rows or vector_documents or valuation) and fallback_signal != NO_DATA_MESSAGE
        if not data_available and fallback_signal is None:
            fallback_signal = NO_DATA_MESSAGE
            answer_text = NO_DATA_MESSAGE

        return AgenticResponse(
            question=question,
            answer=answer_text,
            strategy_used=plan.strategy,
            language=plan.language,
            data_available=data_available,
            citations=citations,
            kg_rows=kg_rows,
            vector_documents=vector_documents,
            valuation=valuation,
            fallback_signal=fallback_signal,
            debug={"plan": asdict(plan)},
        )


def smoke_queries() -> list[str]:
    """Manual integration queries across strategies and languages."""
    return [
        "top skor Premier League 2025-2026",
        "top scorer Premier League 2025-2026",
        "berapa nilai pasar Aaron Ramsdale",
        "what is Aaron Ramsdale market value",
        "Profil Aaron Ramsdale",
        "Profile Aaron Ramsdale",
        "Jelaskan profil dan nilai pasar Aaron Ramsdale",
        "Describe Aaron Ramsdale profile and value",
        "estimasi nilai pasar Aaron Ramsdale",
        "estimate market value range for Aaron Ramsdale",
        "top scorer Champions League 2025-2026",
        "siapa pemain terbaik di Liga Champions",
    ]


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI parser."""
    parser = argparse.ArgumentParser(description="Run agentic retrieval router")
    parser.add_argument("--question", default="top skor Premier League 2025-2026")
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--use-llm-planner", action="store_true")
    parser.add_argument("--use-llm-valuation", action="store_true")
    return parser


def main() -> None:
    """CLI entry point."""
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
    args = build_arg_parser().parse_args()
    router = AgenticRouter()
    if args.smoke_test:
        for query in smoke_queries():
            result = router.answer(
                query,
                use_llm_planner=args.use_llm_planner,
                use_llm_valuation=args.use_llm_valuation,
            )
            print(
                json.dumps(
                    {
                        "question": query,
                        "strategy": result.strategy_used,
                        "language": result.language,
                        "data_available": result.data_available,
                        "citations": len(result.citations),
                        "kg_rows": len(result.kg_rows),
                        "vector_docs": len(result.vector_documents),
                        "fallback": result.fallback_signal,
                        "answer_preview": preview_text(result.answer, 180),
                    },
                    ensure_ascii=False,
                )
            )
        return
    result = router.answer(
        args.question,
        use_llm_planner=args.use_llm_planner,
        use_llm_valuation=args.use_llm_valuation,
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
