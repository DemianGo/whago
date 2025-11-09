from __future__ import annotations

import asyncio
from pathlib import Path
import logging
from decimal import Decimal
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.engine import URL
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

logger = logging.getLogger("whago.database")

RAW_DATABASE_URL = settings.database_url


def _adjust_database_host(raw_url: str) -> str:
    try:
        parsed_url: URL = make_url(raw_url)
    except Exception:  # noqa: BLE001
        return raw_url

    is_docker = Path("/.dockerenv").exists()
    if is_docker and parsed_url.host in {"localhost", "127.0.0.1"}:
        logger.warning(
            "Detectado host '%s' dentro de container Docker. "
            "Substituindo por 'postgres' para comunicação interna.",
            parsed_url.host,
        )
        parsed_url = parsed_url.set(host="postgres")
    return parsed_url.render_as_string(hide_password=False)


DATABASE_URL_RAW_ADJUSTED = _adjust_database_host(RAW_DATABASE_URL)

if DATABASE_URL_RAW_ADJUSTED.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL_RAW_ADJUSTED.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )
else:
    DATABASE_URL = DATABASE_URL_RAW_ADJUSTED

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,
    future=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

MAX_CONNECTION_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db(max_attempts: int = MAX_CONNECTION_ATTEMPTS) -> bool:
    """Inicializa a conexão com o banco e garante planos padrão.

    Args:
        max_attempts: Número máximo de tentativas antes de desistir.

    Returns:
        bool: True se a conexão for estabelecida; False caso contrário.
    """

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(
                "Tentando conectar ao banco de dados (tentativa %s/%s) - URL efetiva: %s",
                attempt,
                max_attempts,
                DATABASE_URL_RAW_ADJUSTED,
            )
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Conexão estabelecida com sucesso.")
            await _ensure_default_plans()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Falha ao conectar ao banco de dados na tentativa %s: %s",
                attempt,
                exc,
                exc_info=settings.debug,
            )
            if attempt == max_attempts:
                logger.critical("Não foi possível conectar ao banco após múltiplas tentativas.")
                return False
            logger.info(
                "Aguardando %s segundos antes da próxima tentativa.",
                RETRY_DELAY_SECONDS,
            )
            await asyncio.sleep(RETRY_DELAY_SECONDS)
    return False


async def wait_for_db_readiness() -> None:
    """Executa tentativas indiscriminadas até que o banco esteja acessível."""

    while True:
        connected = await init_db(max_attempts=1)
        if connected:
            logger.info("Banco de dados disponível após tentativas em background.")
            break
        logger.warning(
            "Banco de dados ainda indisponível. Nova tentativa em %s segundos.",
            RETRY_DELAY_SECONDS,
        )
        await asyncio.sleep(RETRY_DELAY_SECONDS)


async def _ensure_default_plans() -> None:
    """Garante que os planos padrões existam na base."""

    from .models.plan import Plan  # Import local para evitar ciclo

    default_plans = [
        {
            "name": "Plano Free",
            "slug": "free",
            "tier": "FREE",
            "price": Decimal("0"),
            "max_chips": 1,
            "monthly_messages": 500,
            "features": {
                "campaigns_active": 1,
                "contacts_per_list": 100,
                "support": "Sem suporte prioritário",
                "data_retention_days": 30,
                "min_interval_seconds": 10,
                "scheduling": False,
                "api_access": False,
                "chip_maturation": False,
                "chip_rotation": False,
            },
        },
        {
            "name": "Plano Business",
            "slug": "business",
            "tier": "BUSINESS",
            "price": Decimal("97"),
            "max_chips": 3,
            "monthly_messages": 5000,
            "features": {
                "campaigns_active": "Ilimitadas",
                "contacts_per_list": 10000,
                "support": "Email prioritário (24h)",
                "data_retention_days": 90,
                "min_interval_seconds": 5,
                "scheduling": True,
                "advanced_stats": True,
                "report_export": True,
                "api_access": False,
                "chip_maturation": True,
                "chip_rotation": True,
            },
        },
        {
            "name": "Plano Enterprise",
            "slug": "enterprise",
            "tier": "ENTERPRISE",
            "price": Decimal("297"),
            "max_chips": 10,
            "monthly_messages": 20000,
            "features": {
                "campaigns_active": "Ilimitadas",
                "contacts_per_list": "Ilimitados",
                "support": "Prioritário (2h)",
                "data_retention_days": -1,
                "min_interval_seconds": 3,
                "scheduling": True,
                "advanced_stats": True,
                "report_export": "Personalizados",
                "api_access": True,
                "chip_maturation": "Com IA",
                "chip_rotation": "Inteligente",
                "multi_user": 5,
                "webhooks": True,
            },
        },
    ]

    async with AsyncSessionLocal() as session:
        has_changes = False
        for plan_data in default_plans:
            existing = await session.scalar(
                select(Plan).where(Plan.slug == plan_data["slug"])
            )
            if existing:
                continue
            logger.info("Inserindo plano padrão: %s", plan_data["name"])
            session.add(Plan(**plan_data))
            has_changes = True
        if has_changes:
            await session.commit()
            logger.info("Planos padrão inseridos com sucesso.")
        else:
            logger.info("Planos padrão já estavam cadastrados.")
