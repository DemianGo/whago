"""
Testes relacionados ao gerenciamento de usuários.

Asserções seguem os requisitos do PRD e ajudam a evidenciar gaps
quando funcionalidades ainda não estiverem implementadas.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_get_profile_success(register_user, async_client_factory) -> None:
    """Usuário autenticado deve conseguir consultar o próprio perfil."""

    response, _ = await register_user()
    access_token = response.json()["tokens"]["access_token"]

    async with async_client_factory(
        headers={"Authorization": f"Bearer {access_token}"}
    ) as client:
        profile_response = await client.get("/api/v1/users/me")

    assert profile_response.status_code == 200
    data = profile_response.json()
    assert data["email"]
    assert "password" not in data


async def test_get_profile_requires_auth(async_client_factory) -> None:
    """Consultar perfil sem token deve retornar 401 Unauthorized."""

    async with async_client_factory() as client:
        response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_update_profile_success(register_user, async_client_factory) -> None:
    """Usuário deve conseguir atualizar nome e telefone com dados válidos."""

    response, payload = await register_user()
    access_token = response.json()["tokens"]["access_token"]

    async with async_client_factory(
        headers={"Authorization": f"Bearer {access_token}"}
    ) as client:
        update_response = await client.put(
            "/api/v1/users/me",
            json={
                "name": f"{payload['name']} Atualizado",
                "phone": "+5511987654321",
            },
        )

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["name"].endswith("Atualizado")
    assert body["phone"] == "+5511987654321"


async def test_update_profile_invalid_phone(register_user, async_client_factory) -> None:
    """Telefone inválido deve ser rejeitado durante atualização do perfil."""

    response, _ = await register_user()
    access_token = response.json()["tokens"]["access_token"]

    async with async_client_factory(
        headers={"Authorization": f"Bearer {access_token}"}
    ) as client:
        update_response = await client.put(
            "/api/v1/users/me",
            json={"phone": "+4412345678"},
        )

    assert update_response.status_code == 422


async def test_multi_tenant_access_isolated(register_user, async_client_factory) -> None:
    """Usuário B não deve acessar dados diretos de usuário A."""

    response_a, _ = await register_user()
    response_b, _ = await register_user()
    user_a_id = response_a.json()["user"]["id"]
    access_token_b = response_b.json()["tokens"]["access_token"]

    async with async_client_factory(
        headers={"Authorization": f"Bearer {access_token_b}"}
    ) as client:
        forbidden_response = await client.get(f"/api/v1/users/{user_a_id}")

    assert forbidden_response.status_code == 403


async def test_update_plan_requires_document_for_business(
    register_user,
    async_client_factory,
) -> None:
    """Upgrade de plano para Business deve exigir empresa e documento válidos."""

    response, _ = await register_user()
    access_token = response.json()["tokens"]["access_token"]

    async with async_client_factory(
        headers={"Authorization": f"Bearer {access_token}"}
    ) as client:
        upgrade_response = await client.put(
            "/api/v1/users/me",
            json={"plan_slug": "business"},
        )

    assert upgrade_response.status_code == 422
    assert "Documento (CNPJ/CPF) é obrigatório" in upgrade_response.text


