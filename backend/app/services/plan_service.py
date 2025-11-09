"""
Serviço para operações relacionadas a planos.
"""

from __future__ import annotations

from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.plan import Plan


class PlanService:
    """Encapsula regras de consulta e manutenção de planos."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_plans(self) -> Sequence[Plan]:
        result = await self.session.execute(select(Plan).order_by(Plan.id))
        return result.scalars().all()

    async def get_plan(self, slug: str) -> Plan:
        plan = await self.session.scalar(
            select(Plan).where(Plan.slug == slug.lower())
        )
        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plano não encontrado.",
            )
        return plan


__all__ = ("PlanService",)


