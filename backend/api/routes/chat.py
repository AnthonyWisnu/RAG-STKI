"""Chat route powered by agentic router."""

from __future__ import annotations

from fastapi import APIRouter

try:
    from api.schemas.chat import ChatRequest, ChatResponse
except ModuleNotFoundError:
    from backend.api.schemas.chat import ChatRequest, ChatResponse

try:
    from src.retrieval.agentic_router import AgenticRouter
except ModuleNotFoundError:
    from backend.src.retrieval.agentic_router import AgenticRouter

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Answer a user question through the agentic retrieval router."""
    result = AgenticRouter().answer(
        request.question,
        use_llm_planner=request.use_llm_planner,
        use_llm_valuation=request.use_llm_valuation,
    )
    return ChatResponse(
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
