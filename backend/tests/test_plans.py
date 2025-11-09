"""
Testes referentes à listagem e gerenciamento de planos.

Os cenários refletem os requisitos do PRD para garantir que planos,
recursos e permissões estejam corretos.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_list_plans_returns_all_default_plans(async_client_factory) -> None:
    """A listagem de planos deve retornar Free, Business e Enterprise."""

    async with async_client_factory() as client:
        response = await client.get("/api/v1/plans")

    assert response.status_code == 200
    data = response.json()
    slugs = {plan["slug"] for plan in data}
    assert {"free", "business", "enterprise"}.issubset(slugs)


async def test_plan_detail_includes_features(async_client_factory) -> None:
    """Detalhes do plano devem conter limites e recursos declarados no PRD."""

    async with async_client_factory() as client:
        response = await client.get("/api/v1/plans/business")

    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "business"
    assert body["features"]["contacts_per_list"] == 10000
    assert body["features"]["scheduling"] is True


async def test_plan_detail_not_found(async_client_factory) -> None:
    """Consultar plano inexistente deve retornar 404."""

    async with async_client_factory() as client:
        response = await client.get("/api/v1/plans/inexistente")

    assert response.status_code == 404


async def test_create_plan_requires_admin(async_client_factory) -> None:
    """Criação/alteração de planos deve ser restrita a administradores."""

    payload = {
        "name": "Plano Especial",
        "slug": "special",
        "price": 499.0,
        "max_chips": 15,
        "monthly_messages": 50000,
        "features": {"campaigns_active": "Ilimitadas"},
    }

    async with async_client_factory() as client:
        response = await client.post("/api/v1/plans", json=payload)

    assert response.status_code in {401, 403}


