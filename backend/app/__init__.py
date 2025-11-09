"""
Inicialização da aplicação WHAGO Backend.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .core.redis import close_redis
from .database import init_db, wait_for_db_readiness
from .routes import auth

logger = logging.getLogger("whago.app")


def configure_logging() -> None:
    """Configura o sistema de logging."""

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def create_application() -> FastAPI:
    """Factory para criar a aplicação FastAPI."""

    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        description="API para gerenciamento de mensagens WhatsApp em massa",
        version="1.0.0",
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "WHAGO Backend",
            "environment": settings.environment,
        }

    app.state.db_retry_task = None

    @app.on_event("startup")
    async def on_startup() -> None:
        connected = await init_db()
        if connected:
            logger.info("Banco de dados inicializado com sucesso.")
            return

        logger.error(
            "Falha ao inicializar o banco de dados durante o startup. "
            "Tentativas adicionais serão realizadas em background.",
            exc_info=settings.debug,
        )
        logger.warning("Aplicação iniciada sem conexão ativa com o banco de dados.")
        app.state.db_retry_task = asyncio.create_task(wait_for_db_readiness())

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        db_retry_task = getattr(app.state, "db_retry_task", None)
        if db_retry_task:
            db_retry_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await db_retry_task
        await close_redis()
        logger.info("Aplicação WHAGO finalizada.")

    return app
