"""
Rotas referentes ao usuário autenticado.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.user import User
from ..schemas.user import UserPublic, UserUpdate
from ..services.user_service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["Usuários"])


@router.get("/me", response_model=UserPublic)
async def get_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserPublic:
    service = UserService(session)
    return await service.get_profile(current_user)


@router.put("/me", response_model=UserPublic)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserPublic:
    service = UserService(session)
    return await service.update_profile(current_user, payload)


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserPublic:
    service = UserService(session)
    return await service.get_user_by_id(current_user, user_id)


@router.post("/me/suspend", status_code=204, response_class=Response, response_model=None)
async def suspend_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    service = UserService(session)
    await service.suspend_user(current_user.id)


__all__ = ("router",)


