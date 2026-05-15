"""Route API backend."""

try:
    from api.routes.chat import router as chat_router
    from api.routes.clubs import router as clubs_router
    from api.routes.compare import router as compare_router
    from api.routes.health import router as health_router
    from api.routes.players import router as players_router
    from api.routes.players import top_router
    from api.routes.predict import router as predict_router
    from api.routes.refresh import router as refresh_router
except ModuleNotFoundError:
    from backend.api.routes.chat import router as chat_router
    from backend.api.routes.clubs import router as clubs_router
    from backend.api.routes.compare import router as compare_router
    from backend.api.routes.health import router as health_router
    from backend.api.routes.players import router as players_router
    from backend.api.routes.players import top_router
    from backend.api.routes.predict import router as predict_router
    from backend.api.routes.refresh import router as refresh_router

__all__ = [
    "chat_router",
    "clubs_router",
    "compare_router",
    "health_router",
    "players_router",
    "predict_router",
    "top_router",
]
