"""
Testes de autenticação do backend WHAGO.

Todos os testes executam requisições HTTP reais contra o serviço ativo,
validando cenários de sucesso, falha e isolamento multi-tenant.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select

from app.models.user import User

pytestmark = pytest.mark.asyncio


async def _login(
    base_url: str,
    email: str,
    password: str,
) -> httpx.Response:
    """Executa login real e retorna a resposta."""

    async with httpx.AsyncClient(base_url=base_url) as client:
        return await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )


async def _get_with_token(
    base_url: str,
    path: str,
    token: str,
) -> httpx.Response:
    """Executa requisições GET autenticadas via header Bearer."""

    async with httpx.AsyncClient(
        base_url=base_url,
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        return await client.get(path)


async def test_register_success_returns_tokens_and_default_plan(
    register_user,
    get_user_by_email,
) -> None:
    """Cadastro válido deve retornar tokens, plano Free e 100 créditos."""

    response, payload = await register_user()
    assert response.status_code == 201

    data = response.json()
    assert "tokens" in data and "user" in data
    assert data["tokens"]["access_token"]
    assert data["tokens"]["refresh_token"]
    assert data["user"]["plan"] == "Plano Free"
    assert data["user"]["credits"] == 100
    assert "password" not in data["user"]

    user = await get_user_by_email(payload["email"])
    assert user is not None
    assert user.plan is not None and user.plan.slug == "free"


async def test_register_duplicate_email_returns_error(register_user) -> None:
    """Tentativa de reutilizar email existente deve falhar com 400."""

    response, payload = await register_user()
    assert response.status_code == 201

    second_response, _ = await register_user(email=payload["email"])
    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "Este email já está cadastrado."


async def test_register_rejects_invalid_email(register_user) -> None:
    """Email fora do padrão deve gerar erro de validação (422)."""

    response, _ = await register_user(email="invalid-email")
    assert response.status_code == 422
    body = response.json()
    assert body["detail"][0]["loc"][-1] == "email"


@pytest.mark.parametrize(
    "password,expected_message",
    [
        ("curta!", "Senha deve possuir ao menos 8 caracteres"),
        ("semnumero!", "Senha deve possuir ao menos 8 caracteres"),
        ("SemNumero!", "Senha deve possuir ao menos 8 caracteres"),
        ("SemEspecial1", "Senha deve possuir ao menos 8 caracteres"),
    ],
)
async def test_register_enforces_password_strength(
    register_user,
    password: str,
    expected_message: str,
) -> None:
    """Senha precisa seguir as regras de complexidade definidas no PRD."""

    response, _ = await register_user(password=password)
    assert response.status_code == 422
    assert expected_message in response.json()["detail"][0]["msg"]


async def test_register_rejects_invalid_phone(register_user) -> None:
    """Telefone fora do formato E.164 deve resultar em erro de validação."""

    response, _ = await register_user(phone="+33123456789")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "phone"


async def test_register_requires_company_and_document_for_business_plan(
    register_user,
) -> None:
    """Planos Business/Enterprise exigem empresa e documento válidos."""

    # Falta documento
    response_missing_document, _ = await register_user(
        plan_slug="business",
        company_name="Empresa Teste",
    )
    assert response_missing_document.status_code == 422

    # Documento inválido
    response_invalid_document, _ = await register_user(
        plan_slug="business",
        company_name="Empresa Valida",
        document="123456",
    )
    assert response_invalid_document.status_code == 422


async def test_login_success_with_valid_credentials(
    register_user,
    base_url: str,
) -> None:
    """Login com credenciais corretas deve retornar tokens atualizados."""

    register_response, payload = await register_user()
    assert register_response.status_code == 201

    login_response = await _login(
        base_url,
        email=payload["email"],
        password=payload["password"],
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["tokens"]["access_token"]
    assert login_data["tokens"]["refresh_token"]
    assert login_data["user"]["email"] == payload["email"].lower()


async def test_login_invalid_credentials_fails(base_url: str) -> None:
    """Sistema deve responder 401 para credenciais incorretas."""

    response = await _login(
        base_url,
        email="naoexisto@example.com",
        password="SenhaIncorreta!1",
    )
    assert response.status_code == 401


async def test_login_inactive_user_is_forbidden(
    register_user,
    base_url: str,
    async_client_factory,
) -> None:
    """Usuários suspensos não podem autenticar (403)."""

    register_response, payload = await register_user()
    assert register_response.status_code == 201

    login_response = await _login(
        base_url,
        email=payload["email"],
        password=payload["password"],
    )
    assert login_response.status_code == 200
    tokens = login_response.json()["tokens"]

    async with async_client_factory(
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    ) as client:
        suspend_response = await client.post("/api/v1/users/me/suspend")
    assert suspend_response.status_code == 204

    login_response = await _login(
        base_url,
        email=payload["email"],
        password=payload["password"],
    )
    assert login_response.status_code == 403
    assert "suspensa" in login_response.json()["detail"]


async def test_refresh_token_success(register_user, async_client_factory) -> None:
    """Refresh token válido deve gerar novo par de tokens."""

    register_response, _ = await register_user()
    assert register_response.status_code == 201
    tokens = register_response.json()["tokens"]
    refresh_token = tokens["refresh_token"]

    async with async_client_factory() as client:
        client.cookies.set("whago_refresh_token", refresh_token, domain="localhost")
        refresh_response = await client.post("/api/v1/auth/refresh")

    assert refresh_response.status_code == 200
    new_tokens = refresh_response.json()["tokens"]
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


async def test_refresh_invalid_token_returns_unauthorized(async_client_factory) -> None:
    """Refresh token inválido deve retornar 401."""

    async with async_client_factory() as client:
        client.cookies.set("whago_refresh_token", "token-invalido", domain="localhost")
        response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


async def test_logout_revokes_refresh_token(register_user, async_client_factory) -> None:
    """Logout deve invalidar o refresh token previamente emitido."""

    register_response, _ = await register_user()
    tokens = register_response.json()["tokens"]
    refresh_token = tokens["refresh_token"]

    async with async_client_factory() as client:
        client.cookies.set("whago_refresh_token", refresh_token, domain="localhost")
        logout_response = await client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200

        # Mesmo token não deve mais funcionar
        client.cookies.set("whago_refresh_token", refresh_token, domain="localhost")
        refresh_response = await client.post("/api/v1/auth/refresh")
        assert refresh_response.status_code == 401


async def test_forgot_and_reset_password_flow(register_user, base_url: str) -> None:
    """Fluxo completo de recuperação de senha deve permitir novo login."""

    register_response, payload = await register_user()
    email = payload["email"]
    assert register_response.status_code == 201

    async with httpx.AsyncClient(base_url=base_url) as client:
        forgot_response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": email},
        )
        assert forgot_response.status_code == 200
        body = forgot_response.json()
        assert "debug_reset_token" in body
        reset_token = body["debug_reset_token"]

        new_password = "NovaSenhaForte!2"
        reset_response = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": reset_token, "new_password": new_password},
        )
        assert reset_response.status_code == 200

    login_response = await _login(base_url, email=email, password="NovaSenhaForte!2")
    assert login_response.status_code == 200


async def test_reset_password_invalid_token(register_user, base_url: str) -> None:
    """Tokens inválidos devem impedir o reset de senha."""

    register_response, payload = await register_user()
    assert register_response.status_code == 201

    async with httpx.AsyncClient(base_url=base_url) as client:
        reset_response = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "token-invalido", "new_password": "SenhaForte!3"},
        )
    assert reset_response.status_code == 400


async def test_multi_tenant_isolation_on_chips_endpoint(
    register_user,
    base_url: str,
) -> None:
    """Cada usuário deve enxergar apenas seus próprios chips."""

    response_a, payload_a = await register_user()
    response_b, payload_b = await register_user()
    assert response_a.status_code == response_b.status_code == 201

    alias = f"chip-{uuid4().hex[:8]}"
    access_token_a = response_a.json()["tokens"]["access_token"]
    access_token_b = response_b.json()["tokens"]["access_token"]

    async with httpx.AsyncClient(
        base_url=base_url,
        headers={"Authorization": f"Bearer {access_token_a}"},
    ) as client:
        chip_response = await client.post("/api/v1/chips", json={"alias": alias})
    assert chip_response.status_code == 201

    response_user_a = await _get_with_token(base_url, "/api/v1/chips", access_token_a)
    response_user_b = await _get_with_token(base_url, "/api/v1/chips", access_token_b)

    assert response_user_a.status_code == 200
    assert any(ch["alias"] == alias for ch in response_user_a.json())

    assert response_user_b.status_code == 200
    assert all(ch["alias"] != alias for ch in response_user_b.json())


