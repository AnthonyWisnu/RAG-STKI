"""Schema API backend."""

try:
    from api.schemas.chat import ChatRequest, ChatResponse
    from api.schemas.player import (
        ClubResponse,
        CompareRequest,
        CompareResponse,
        PlayerDetailResponse,
        PlayerSearchResponse,
        TopPerformersResponse,
    )
    from api.schemas.predict import PredictRequest, PredictResponse
except ModuleNotFoundError:
    from backend.api.schemas.chat import ChatRequest, ChatResponse
    from backend.api.schemas.player import (
        ClubResponse,
        CompareRequest,
        CompareResponse,
        PlayerDetailResponse,
        PlayerSearchResponse,
        TopPerformersResponse,
    )
    from backend.api.schemas.predict import PredictRequest, PredictResponse

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "ClubResponse",
    "CompareRequest",
    "CompareResponse",
    "PlayerDetailResponse",
    "PlayerSearchResponse",
    "PredictRequest",
    "PredictResponse",
    "TopPerformersResponse",
]
