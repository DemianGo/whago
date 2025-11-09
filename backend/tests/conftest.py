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
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.user import User

BASE_URL = "http://localhost:8000"


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


@pytest_asyncio.fixture
async def register_user(
    db_session: AsyncSession,
    user_payload_factory: Callable[..., dict[str, Any]],
) -> AsyncIterator[Callable[..., Awaitable[tuple[httpx.Response, dict[str, Any]]]]]:
    """
    Registra usuários via API real e garante cleanup ao término.

    Retorna callable que aceita overrides no payload e devolve (response, payload).
    """

    created_emails: set[str] = set()

    async def _register(**overrides: Any) -> tuple[httpx.Response, dict[str, Any]]:
        payload = user_payload_factory(**overrides)
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            response = await client.post("/api/v1/auth/register", json=payload)

        if 200 <= response.status_code < 300:
            created_emails.add(payload["email"].lower())
        return response, payload

    yield _register

    if created_emails:
        await db_session.execute(
            delete(User).where(User.email.in_(list(created_emails)))
        )
        await db_session.commit()


@pytest_asyncio.fixture
async def get_user_by_email(
    db_session: AsyncSession,
) -> Callable[[str], Awaitable[User | None]]:
    """Retorna callable para buscar usuários diretamente no banco."""

    async def _get(email: str) -> User | None:
        result = await db_session.execute(
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
        return httpx.AsyncClient(base_url=base_url, headers=headers, **kwargs)

    return _factory


