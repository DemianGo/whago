"""
Utilitários para acesso ao Redis.
"""

from __future__ import annotations

import logging
from typing import Optional

from redis.asyncio import Redis

from ..config import settings

logger = logging.getLogger("whago.redis")

_redis_client: Optional[Redis] = None


def get_redis_client() -> Redis:
    """
    Retorna cliente Redis singleton.

    Em caso de falha ao criar o cliente, levanta exceção para que chamadas
    subsequentes possam optar por fallback.
    """

    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Fecha o cliente Redis atual."""

    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Erro ao fechar conexão Redis: %s", exc)
        finally:
            _redis_client = None


__all__ = ("get_redis_client", "close_redis")


