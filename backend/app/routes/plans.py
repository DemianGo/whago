"""
Rotas públicas para consulta de planos.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.user import User
from ..schemas.plan import PlanResponse
from ..services.plan_service import PlanService

router = APIRouter(prefix="/api/v1/plans", tags=["Planos"])


@router.get("", response_model=list[PlanResponse])
async def list_plans(session: AsyncSession = Depends(get_db)) -> list[PlanResponse]:
    """Lista todos os planos disponíveis."""

    service = PlanService(session)
    plans = await service.list_plans()
    return [PlanResponse.model_validate(plan) for plan in plans]


@router.get("/{slug}", response_model=PlanResponse)
async def get_plan(slug: str, session: AsyncSession = Depends(get_db)) -> PlanResponse:
    """Retorna os detalhes de um plano específico."""

    service = PlanService(session)
    plan = await service.get_plan(slug)
    return PlanResponse.model_validate(plan)


@router.post("", status_code=status.HTTP_403_FORBIDDEN)
async def create_plan(
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Placeholder para criação de planos.

    Apenas administradores poderão criar planos no futuro.
    """

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Somente administradores podem criar ou alterar planos.",
    )


__all__ = ("router",)


