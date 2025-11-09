"""
Fixtures compartilhadas para a suíte de testes do backend WHAGO.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, Awaitable
from uuid import uuid4

import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete, select, create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, Session
from sqlalchemy.engine import make_url

from app.database import AsyncSessionLocal
from app.config import settings
from app.models.user import User

BASE_URL = "http://localhost:8000"

SYNC_ENGINE = create_engine(make_url(settings.database_url).set(drivername="postgresql+psycopg2", host="postgres"))


@pytest.fixture(scope="session")
def base_url() -> str:
    """URL base para chamadas HTTP reais contra o backend."""

    return BASE_URL


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Fornece uma sessão assíncrona do SQLAlchemy para setup/teardown."""

    async with AsyncSessionLocal() as session:
        yield session
        await session.close()


@pytest.fixture
def user_payload_factory() -> Callable[..., dict[str, Any]]:
    """Gera payloads de usuário válidos com dados únicos."""

    def _factory(**overrides: Any) -> dict[str, Any]:
        unique = uuid4().hex[:8]
        number_suffix = str(uuid4().int)[-8:]
        payload: dict[str, Any] = {
            "email": f"test-user-{unique}@example.com",
            "name": f"Usuário Teste {unique}",
            "password": "SenhaForte!1",
            "phone": f"+55119{number_suffix}",
            "company_name": overrides.get("company_name"),
            "document": overrides.get("document"),
            "plan_slug": overrides.get("plan_slug", "free"),
        }

        for key, value in overrides.items():
            if value is not None or key not in payload:
                payload[key] = value
        return payload

    return _factory


@pytest.fixture
def register_user(
    user_payload_factory: Callable[..., dict[str, Any]],
) -> Callable[..., Awaitable[tuple[httpx.Response, dict[str, Any]]]]:
    """Registra usuário via API e retorna resposta + payload utilizado."""

    async def _register(**overrides: Any) -> tuple[httpx.Response, dict[str, Any]]:
        payload = user_payload_factory(**overrides)
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            response = await client.post("/api/v1/auth/register", json=payload)
        return response, payload
    return _register


@pytest_asyncio.fixture
async def get_user_by_email() -> Callable[[str], Awaitable[User | None]]:
    """Retorna callable para buscar usuários diretamente no banco."""

    async def _get(email: str) -> User | None:
        with Session(SYNC_ENGINE) as session:
            result = session.execute(
                select(User)
                .options(selectinload(User.plan))
                .where(User.email == email.lower())
            )
            return result.scalar_one_or_none()

    return _get


@pytest.fixture
def async_client_factory(base_url: str) -> Callable[..., httpx.AsyncClient]:
    """
    Fornece fábrica de clientes HTTP assíncronos.

    Útil para criar clientes com cabeçalhos/cookies específicos por teste.
    """

    def _factory(**kwargs: Any) -> httpx.AsyncClient:
        headers = kwargs.pop("headers", {})
        client = httpx.AsyncClient(base_url=base_url, headers=headers, **kwargs)

        original_set = client.cookies.set

        def patched_set(name: str, value: str, *args: Any, **set_kwargs: Any):
            domain = set_kwargs.get("domain")
            if domain == "localhost":
                set_kwargs.pop("domain")
            return original_set(name, value, *args, **set_kwargs)

        client.cookies.set = patched_set  # type: ignore[assignment]
        return client

    return _factory





