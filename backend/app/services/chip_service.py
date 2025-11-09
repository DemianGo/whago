"""
Serviço para operações relacionadas a chips.
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Iterable
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.chip import Chip, ChipEvent, ChipEventType, ChipStatus
from ..models.plan import Plan
from ..models.user import User
from .notification_service import NotificationService, NotificationType
from .audit_service import AuditService
from ..schemas.chip import (
    ChipCreate,
    ChipResponse,
    ChipEventResponse,
    ChipQrResponse,
)
from .baileys_client import BaileysClient, get_baileys_client


logger = logging.getLogger("whago.chips")


class ChipService:
    def __init__(
        self,
        session: AsyncSession,
        baileys_client: BaileysClient | None = None,
    ):
        self.session = session
        self.baileys = baileys_client or get_baileys_client()

    async def list_chips(self, user: User) -> list[ChipResponse]:
        result = await self.session.execute(
            select(Chip).where(Chip.user_id == user.id).order_by(Chip.created_at.asc())
        )
        chips = result.scalars().all()
        return [ChipResponse.model_validate(chip) for chip in chips]

    async def get_chip(self, user: User, chip_id: UUID) -> ChipResponse:
        chip = await self._get_user_chip(user, chip_id)
        return ChipResponse.model_validate(chip)

    async def get_chip_events(self, user: User, chip_id: UUID) -> list[ChipEventResponse]:
        chip = await self._get_user_chip(user, chip_id)
        await self.session.refresh(chip, attribute_names=["events"])
        events = sorted(chip.events, key=lambda ev: ev.created_at, reverse=True)
        return [ChipEventResponse.model_validate(event) for event in events]

    async def create_chip(
        self,
        user: User,
        payload: ChipCreate,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> ChipResponse:
        await self._ensure_alias_unique(user, payload.alias)
        await self._enforce_plan_limits(user)

        fallback = False
        session_id: str | None = None

        try:
            baileys_response = await self.baileys.create_session(payload.alias)
            session_id = baileys_response.get("session_id") or baileys_response.get("sessionId")
            if not session_id:
                raise ValueError("Resposta do Baileys sem session_id.")
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Falha ao criar sessão no Baileys para alias %s: %s. Aplicando fallback local.",
                payload.alias,
                exc,
            )
            fallback = True
            session_id = f"fallback-{uuid4()}"

        chip = Chip(
            user_id=user.id,
            alias=payload.alias,
            session_id=session_id,
            status=ChipStatus.WAITING_QR,
            extra_data={
                "created_via": "api",
                "user_agent": user_agent,
                "ip": ip_address,
                "baileys_fallback": fallback,
            },
        )
        self.session.add(chip)
        await self.session.flush()

        await self._add_event(
            chip,
            ChipEventType.SYSTEM,
            f"Chip criado e aguardando QR (sessão {session_id}).",
        )

        notifier = NotificationService(self.session)
        await notifier.create(
            user_id=user.id,
            title="Novo chip aguardando QR",
            message=f"O chip {payload.alias} foi criado e precisa ser conectado.",
            type_=NotificationType.INFO,
            extra_data={"chip_id": str(chip.id), "session_id": session_id},
            auto_commit=False,
        )
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="chip.create",
            entity_type="chip",
            entity_id=str(chip.id),
            description=f"Chip {payload.alias} criado.",
            extra_data={"session_id": session_id},
            ip_address=ip_address,
            user_agent=user_agent,
            auto_commit=False,
        )

        await self.session.commit()
        await self.session.refresh(chip)
        return ChipResponse.model_validate(chip)

    async def get_qr_code(self, user: User, chip_id: UUID) -> ChipQrResponse:
        chip = await self._get_user_chip(user, chip_id)
        data = await self.baileys.get_qr_code(chip.session_id)
        expires_raw = data.get("expires_at") or data.get("expiresAt")
        expires_at = None
        if isinstance(expires_raw, str):
            try:
                expires_at = datetime.fromisoformat(expires_raw)
            except ValueError:
                expires_at = None
        return ChipQrResponse(qr=data.get("qr"), expires_at=expires_at)

    async def delete_chip(self, user: User, chip_id: UUID) -> None:
        chip = await self._get_user_chip(user, chip_id)
        await self.baileys.delete_session(chip.session_id)
        await self.session.delete(chip)
        await self.session.commit()

    async def disconnect_chip(self, user: User, chip_id: UUID) -> ChipResponse:
        chip = await self._get_user_chip(user, chip_id)
        await self.baileys.disconnect_session(chip.session_id)
        chip.status = ChipStatus.DISCONNECTED
        await self._add_event(
            chip,
            ChipEventType.STATUS_CHANGE,
            "Chip desconectado manualmente pelo usuário.",
        )
        notifier = NotificationService(self.session)
        await notifier.create(
            user_id=user.id,
            title="Chip desconectado",
            message=f"O chip {chip.alias} foi desconectado.",
            type_=NotificationType.WARNING,
            extra_data={"chip_id": str(chip.id)},
            auto_commit=False,
        )
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="chip.disconnect",
            entity_type="chip",
            entity_id=str(chip.id),
            description=f"Chip {chip.alias} desconectado pelo usuário.",
            extra_data=None,
            ip_address=None,
            user_agent=None,
            auto_commit=False,
        )
        await self.session.commit()
        await self.session.refresh(chip)
        return ChipResponse.model_validate(chip)

    async def _get_user_chip(self, user: User, chip_id: UUID) -> Chip:
        chip = await self.session.get(Chip, chip_id)
        if not chip or chip.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chip não encontrado.",
            )
        return chip

    async def _ensure_alias_unique(self, user: User, alias: str) -> None:
        result = await self.session.execute(
            select(func.count(Chip.id)).where(
                Chip.user_id == user.id,
                func.lower(Chip.alias) == alias.lower(),
            )
        )
        if result.scalar_one() > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um chip com esse apelido.",
            )

    async def _enforce_plan_limits(self, user: User) -> None:
        await self.session.refresh(user, attribute_names=["plan"])
        max_chips = self._get_plan_max_chips(user.plan)
        result = await self.session.execute(
            select(func.count(Chip.id)).where(Chip.user_id == user.id)
        )
        current = result.scalar_one()
        if current >= max_chips:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Limite de chips do plano atingido.",
            )

    @staticmethod
    def _get_plan_max_chips(plan: Plan | None) -> int:
        if not plan:
            return 1
        return plan.max_chips or 1

    async def _add_event(
        self,
        chip: Chip,
        event_type: ChipEventType,
        description: str,
        extra: dict | None = None,
    ) -> None:
        event = ChipEvent(
            chip_id=chip.id,
            type=event_type,
            description=description,
            extra_data=extra or {},
        )
        self.session.add(event)
        await self.session.flush()


__all__ = ("ChipService",)


