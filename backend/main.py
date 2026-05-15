"""Entry point FastAPI untuk backend football KG-RAG."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from api.routes import (
        chat_router,
        clubs_router,
        compare_router,
        health_router,
        players_router,
        predict_router,
        refresh_router,
        top_router,
    )
    from config.settings import get_cached_settings
except ModuleNotFoundError:
    from backend.api.routes import (
        chat_router,
        clubs_router,
        compare_router,
        health_router,
        players_router,
        predict_router,
        refresh_router,
        top_router,
    )
    from backend.config.settings import get_cached_settings


def create_app() -> FastAPI:
    """Membuat instance FastAPI dengan konfigurasi dasar."""
    app_settings = get_cached_settings()
    app = FastAPI(
        title="Football KG-RAG API",
        description=(
            "API untuk sistem tanya-jawab statistik dan valuasi pemain sepak bola."
        ),
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(players_router)
    app.include_router(compare_router)
    app.include_router(predict_router)
    app.include_router(refresh_router)
    app.include_router(top_router)
    app.include_router(clubs_router)

    return app


app = create_app()
