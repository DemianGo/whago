"""Rotas REST para gerenciamento de API Keys."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.user import User
from ..schemas.api_key import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyResponse
from ..services.api_key_service import ApiKeyService

router = APIRouter(prefix="/api/v1/api-keys", tags=["API Keys"])


def _service(session: AsyncSession) -> ApiKeyService:
    return ApiKeyService(session)


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ApiKeyResponse]:
    await session.refresh(current_user, attribute_names=["plan"])
    if not (current_user.plan and (current_user.plan.features or {}).get("api_access")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Recurso disponível apenas no plano Enterprise.")
    service = _service(session)
    keys = await service.list_keys(current_user)
    return [ApiKeyResponse.model_validate(key, from_attributes=True) for key in keys]


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiKeyCreateResponse:
    await session.refresh(current_user, attribute_names=["plan"])
    service = _service(session)
    api_key, raw_value = await service.create_key(current_user, payload.name)
    await session.commit()
    base = ApiKeyResponse.model_validate(api_key, from_attributes=True)
    return ApiKeyCreateResponse(**base.model_dump(), key=raw_value)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await session.refresh(current_user, attribute_names=["plan"])
    service = _service(session)
    await service.revoke_key(current_user, key_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
