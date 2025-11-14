"""
Dependências relacionadas à autenticação de usuários.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, WebSocket, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.user import User
from ..services.api_key_service import ApiKeyService


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> User:
    """Recupera o usuário autenticado via JWT ou API Key."""

    token = _extract_access_token(request, raise_on_missing=False)
    if token:
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

    return await _authenticate_api_key_request(request, session)


def _extract_access_token(request: Request, *, raise_on_missing: bool = True) -> str | None:
    token = request.cookies.get("whago_access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
    if not token and raise_on_missing:
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


async def authenticate_websocket(
    websocket: WebSocket,
    session: AsyncSession,
) -> User:
    token = _extract_token_from_websocket(websocket)
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


def _extract_token_from_websocket(websocket: WebSocket) -> str:
    token = websocket.cookies.get("whago_access_token")
    if not token:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso não encontrado.",
        )
    return token


async def _authenticate_api_key_request(request: Request, session: AsyncSession) -> User:
    header = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    if not header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso não encontrado.",
        )
    service = ApiKeyService(session)
    api_key = await service.authenticate(header)
    return api_key.user


__all__ = ("get_current_user", "authenticate_websocket")


