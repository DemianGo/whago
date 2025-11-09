"""
Dependências relacionadas à autenticação de usuários.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.user import User


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Recupera o usuário autenticado a partir do cookie de access token.

    Raises:
        HTTPException: quando token ausente ou inválido.
    """

    token = _extract_access_token(request)
    payload = _decode_token(token)

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem identificador de usuário.",
        )

    user = await session.get(User, UUID(user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inválido ou inativo.",
        )

    return user


def _extract_access_token(request: Request) -> str:
    token = request.cookies.get("whago_access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso não encontrado.",
        )
    return token


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        ) from exc


__all__ = ("get_current_user",)


