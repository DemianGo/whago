"""
Serviço para operações com usuários autenticados.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.plan import Plan, PlanTier
from ..models.user import User
from ..schemas.user import UserPublic, UserUpdate


class UserService:
    """Regras de negócio relacionadas ao perfil do usuário."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_profile(self, user: User) -> UserPublic:
        return await self._build_user_public(user.id)

    async def update_profile(self, user: User, data: UserUpdate) -> UserPublic:
        db_user = await self.session.get(User, user.id)
        if db_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado.",
            )

        if data.name is not None:
            db_user.name = data.name.strip()
        if data.phone is not None:
            db_user.phone = data.phone
        if data.company_name is not None:
            db_user.company_name = data.company_name
        if data.document is not None:
            db_user.document = data.document

        if data.plan_slug is not None:
            plan = await self._get_plan_by_slug(data.plan_slug)
            self._enforce_plan_requirements(plan, db_user, data)
            db_user.plan = plan

        await self.session.commit()
        return await self._build_user_public(user.id)

    async def get_user_by_id(self, current_user: User, user_id: UUID) -> UserPublic:
        if current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar este usuário.",
            )

        return await self._build_user_public(user_id)

    async def suspend_user(self, user_id: UUID) -> None:
        user = await self.session.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado.",
            )
        user.is_active = False
        user.is_suspended = True
        await self.session.commit()

    async def _get_plan_by_slug(self, slug: str) -> Plan:
        plan = await self.session.scalar(
            select(Plan).where(Plan.slug == slug.lower())
        )
        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plano selecionado é inválido.",
            )
        return plan

    def _enforce_plan_requirements(
        self,
        plan: Plan,
        user: User,
        data: UserUpdate,
    ) -> None:
        if plan.tier in {PlanTier.BUSINESS, PlanTier.ENTERPRISE}:
            company_name = (
                data.company_name if data.company_name is not None else user.company_name
            )
            document = data.document if data.document is not None else user.document
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Documento (CNPJ/CPF) é obrigatório para este plano.",
                )
            if not company_name:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Nome da empresa é obrigatório para este plano.",
                )

    async def _build_user_public(self, user_id: UUID) -> UserPublic:
        result = await self.session.execute(
            select(
                User.id,
                User.email,
                User.name,
                User.phone,
                User.company_name,
                User.document,
                User.credits,
                User.is_active,
                User.is_verified,
                User.created_at,
                User.updated_at,
                Plan.name.label("plan_name"),
            )
            .join(Plan, Plan.id == User.plan_id, isouter=True)
            .where(User.id == user_id)
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado.",
            )
        return UserPublic.model_validate(
            {
                "id": row["id"],
                "email": row["email"],
                "name": row["name"],
                "phone": row["phone"],
                "company_name": row["company_name"],
                "document": row["document"],
                "credits": row["credits"],
                "plan": row["plan_name"],
                "is_active": row["is_active"],
                "is_verified": row["is_verified"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )


__all__ = ("UserService",)


