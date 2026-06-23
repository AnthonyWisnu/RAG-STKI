"""Chat route powered by agentic router."""

from __future__ import annotations

import logging

from fastapi import APIRouter

try:
    from api.schemas.chat import ChatRequest, ChatResponse
except ModuleNotFoundError:
    from backend.api.schemas.chat import ChatRequest, ChatResponse

try:
    from src.retrieval.agentic_router import AgenticRouter, is_low_information_question
    from src.cache.chat_cache import ChatCache
except ModuleNotFoundError:
    from backend.src.retrieval.agentic_router import AgenticRouter, is_low_information_question
    from backend.src.cache.chat_cache import ChatCache

router = APIRouter(prefix="/api", tags=["chat"])
LOGGER = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Answer a user question through the agentic retrieval router."""
    cache = ChatCache()
    should_use_cache = not is_low_information_question(request.question)
    if should_use_cache:
        cached_response = cache.get(
            request.question,
            use_llm_planner=request.use_llm_planner,
            use_llm_valuation=request.use_llm_valuation,
        )
        if cached_response is not None:
            return ChatResponse(**cached_response)

    try:
        result = AgenticRouter().answer(
            request.question,
            use_llm_planner=request.use_llm_planner,
            use_llm_valuation=request.use_llm_valuation,
        )
    except Exception as exc:
        LOGGER.exception("Chat retrieval gagal")
        message = (
            "Layanan retrieval sedang tidak terhubung dengan benar. "
            "Coba lagi setelah koneksi data/Neo4j pulih."
        )
        return ChatResponse(
            answer=message,
            strategy_used="kg_only",
            language="id",
            data_available=False,
            citations=[],
            context={"kg_rows": [], "vector_documents": [], "valuation": None, "debug": {"error": str(exc)}},
            fallback_signal=message,
        )
    response = ChatResponse(
        answer=result.answer,
        strategy_used=result.strategy_used,
        language=result.language,
        data_available=result.data_available,
        citations=result.citations,
        context={
            "kg_rows": result.kg_rows,
            "vector_documents": result.vector_documents,
            "valuation": result.valuation,
            "debug": result.debug,
        },
        fallback_signal=result.fallback_signal,
    )
    if should_use_cache and response.data_available:
        cache.set(
            request.question,
            response.model_dump(mode="json"),
            use_llm_planner=request.use_llm_planner,
            use_llm_valuation=request.use_llm_valuation,
        )
    return response
