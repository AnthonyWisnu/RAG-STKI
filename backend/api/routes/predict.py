"""Valuation reasoning route."""

from __future__ import annotations

from fastapi import APIRouter

try:
    from api.schemas.predict import PredictRequest, PredictResponse
except ModuleNotFoundError:
    from backend.api.schemas.predict import PredictRequest, PredictResponse

try:
    from src.valuation.valuation_reasoner import ValuationReasoner
except ModuleNotFoundError:
    from backend.src.valuation.valuation_reasoner import ValuationReasoner

router = APIRouter(prefix="/api", tags=["predict"])


@router.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    """Return LLM valuation reasoning result."""
    result = ValuationReasoner().reason(
        request.player_name,
        language=request.language,
        use_llm=request.use_llm,
    )
    return PredictResponse(
        player=result.get("player", {}),
        current_value=result.get("current_value"),
        estimated_range=result.get("estimated_range"),
        trend_direction=str(result.get("trend_direction") or "unknown"),
        supporting_factors=result.get("supporting_factors", []),
        explanation=str(result.get("explanation") or ""),
        citations=result.get("citations", []),
        raw=result,
    )
