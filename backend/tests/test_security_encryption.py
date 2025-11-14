"""Testes relacionados à segurança e criptografia em repouso."""

from __future__ import annotations

import pytest

from app.models.user import User


@pytest.mark.asyncio
async def test_user_password_is_hashed_at_rest(register_user, get_user_by_email) -> None:
    response, payload = await register_user(plan_slug="business", company_name="Empresa QA", document="11144477735")
    assert response.status_code == 201, response.text

    user: User | None = await get_user_by_email(payload["email"])
    assert user is not None
    assert user.password_hash != payload["password"]
    assert user.password_hash.startswith("$2b$") or user.password_hash.startswith("$2a$")
    assert len(user.password_hash) >= 60
