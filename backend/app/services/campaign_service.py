"""
Serviço responsável pelas operações com campanhas.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tasks.campaign_tasks import resume_campaign_dispatch, start_campaign_dispatch
from ..config import settings
from ..core.redis import get_redis_client
from ..models.campaign import (
    Campaign,
    CampaignContact,
    CampaignMessage,
    CampaignStatus,
    CampaignType,
    MessageStatus,
)
from ..models.chip import Chip
from ..models.plan import PlanTier
from ..models.user import User
from .notification_service import NotificationService, NotificationType
from .audit_service import AuditService
from ..schemas.campaign import (
    CampaignActionResponse,
    CampaignCreate,
    CampaignDetail,
    CampaignMessageResponse,
    CampaignSettings,
    CampaignSummary,
    CampaignUpdate,
    ContactUploadResponse,
)

logger = logging.getLogger("whago.campaigns")


class CampaignService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_campaigns(self, user: User) -> list[CampaignSummary]:
        result = await self.session.execute(
            select(Campaign)
            .where(Campaign.user_id == user.id)
            .order_by(Campaign.created_at.desc())
        )
        campaigns = result.scalars().all()
        return [CampaignSummary.model_validate(c) for c in campaigns]

    async def get_campaign(self, user: User, campaign_id: UUID) -> CampaignDetail:
        campaign = await self._get_user_campaign(user, campaign_id)
        return CampaignDetail.model_validate(campaign)

    async def create_campaign(
        self,
        user: User,
        data: CampaignCreate,
    ) -> CampaignDetail:
        db_user = await self._get_user_with_plan(user)
        self._ensure_campaign_type_allowed(db_user, data.type)
        if data.type == CampaignType.AB_TEST and not data.message_template_b:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campanhas A/B Test exigem a segunda variação de mensagem.",
            )
        if data.scheduled_for is not None:
            self._ensure_scheduling_allowed(db_user)

        settings = self._normalize_settings(db_user, data.settings, data.type)
        await self._validate_chip_limits(db_user, settings.chip_ids)

        campaign = Campaign(
            user_id=db_user.id,
            name=data.name,
            description=data.description,
            type=data.type,
            status=CampaignStatus.SCHEDULED if data.scheduled_for else CampaignStatus.DRAFT,
            message_template=data.message_template,
            message_template_b=data.message_template_b,
            settings=settings.model_dump(mode="json"),
            scheduled_for=data.scheduled_for,
        )
        self.session.add(campaign)
        await self.session.flush()
        notifier = NotificationService(self.session)
        await notifier.create(
            user_id=db_user.id,
            title="Campanha criada",
            message=f"{campaign.name} foi criada com status {campaign.status.value}.",
            type_=NotificationType.SUCCESS,
            extra_data={"campaign_id": str(campaign.id)},
            auto_commit=False,
        )
        audit = AuditService(self.session)
        await audit.record(
            user_id=db_user.id,
            action="campaign.create",
            entity_type="campaign",
            entity_id=str(campaign.id),
            description="Campanha criada pelo usuário.",
            extra_data={"status": campaign.status.value},
            auto_commit=False,
        )
        await self.session.commit()
        await self.session.refresh(campaign)
        return CampaignDetail.model_validate(campaign)

    async def update_campaign(
        self,
        user: User,
        campaign_id: UUID,
        data: CampaignUpdate,
    ) -> CampaignDetail:
        campaign = await self._get_user_campaign(user, campaign_id)
        db_user = await self._get_user_with_plan(user)
        if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Só é possível editar campanhas em rascunho ou agendadas.",
            )

        if data.name is not None:
            campaign.name = data.name
        if data.description is not None:
            campaign.description = data.description
        if data.message_template is not None:
            campaign.message_template = data.message_template
        if data.message_template_b is not None:
            campaign.message_template_b = data.message_template_b
        if data.scheduled_for is not None:
            if data.scheduled_for and data.scheduled_for < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data de agendamento não pode estar no passado.",
                )
            if data.scheduled_for is not None:
                self._ensure_scheduling_allowed(db_user)
            campaign.scheduled_for = data.scheduled_for
        if data.settings is not None:
            settings = self._normalize_settings(db_user, data.settings, campaign.type)
            await self._validate_chip_limits(db_user, settings.chip_ids)
            campaign.settings = settings.model_dump(mode="json")

        await self.session.commit()
        await self.session.refresh(campaign)
        return CampaignDetail.model_validate(campaign)

    async def delete_campaign(self, user: User, campaign_id: UUID) -> None:
        campaign = await self._get_user_campaign(user, campaign_id)
        if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.CANCELLED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Só é possível excluir campanhas em rascunho ou canceladas.",
            )
        await self.session.delete(campaign)
        await self.session.commit()

    async def upload_contacts(
        self,
        user: User,
        campaign_id: UUID,
        file: UploadFile,
    ) -> ContactUploadResponse:
        campaign = await self._get_user_campaign(user, campaign_id)
        db_user = await self._get_user_with_plan(user)
        contacts_limit = self._get_contacts_limit(db_user)
        if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível importar contatos após o início da campanha.",
            )

        content = await file.read()
        decoded = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))

        result_existing = await self.session.execute(
            select(func.count(CampaignContact.id)).where(CampaignContact.campaign_id == campaign.id)
        )
        existing_contacts = result_existing.scalar_one()

        total = 0
        valid = 0
        invalid = 0
        duplicated = 0
        preview: list[dict] = []
        seen_numbers: set[str] = set()

        for row in reader:
            total += 1
            number = (row.get("numero") or row.get("number") or "").strip()
            if not number:
                invalid += 1
                continue

            normalized = self._normalize_phone(number)
            if not normalized:
                invalid += 1
                continue

            if normalized in seen_numbers:
                duplicated += 1
                continue

            if contacts_limit is not None and existing_contacts + valid + 1 > contacts_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Limite de {contacts_limit} contatos por campanha atingido para o seu plano. "
                        "Considere remover contatos ou fazer upgrade de plano."
                    ),
                )

            seen_numbers.add(normalized)
            name = (row.get("nome") or row.get("name") or "").strip() or None
            company = (row.get("empresa") or row.get("company") or "").strip() or None
            variables = {
                key: value
                for key, value in row.items()
                if key not in {"numero", "number", "nome", "name", "empresa", "company"}
            }
            variables = {k: v for k, v in variables.items() if v}

            contact = CampaignContact(
                campaign_id=campaign.id,
                phone_number=normalized,
                name=name,
                company=company,
                variables=variables or None,
            )
            self.session.add(contact)
            valid += 1

            if len(preview) < 10:
                preview.append({"numero": normalized, "nome": name, "empresa": company})

        result_total = await self.session.execute(
            select(func.count(CampaignContact.id)).where(CampaignContact.campaign_id == campaign.id)
        )
        campaign.total_contacts = result_total.scalar_one()
        await self.session.commit()

        await self._publish_event(
            campaign.id,
            {
                "type": "contacts_updated",
                "total_contacts": campaign.total_contacts,
                "added": valid,
            },
        )

        return ContactUploadResponse(
            total_processed=total,
            valid_contacts=valid,
            invalid_contacts=invalid,
            duplicated=duplicated,
            preview=preview,
        )

    async def start_campaign(self, user: User, campaign_id: UUID) -> CampaignActionResponse:
        campaign = await self._get_user_campaign(user, campaign_id)
        db_user = await self._get_user_with_plan(user)
        self._ensure_campaign_type_allowed(db_user, campaign.type)
        if campaign.status == CampaignStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campanha já está em andamento.",
            )
        if campaign.status in {CampaignStatus.CANCELLED, CampaignStatus.COMPLETED, CampaignStatus.ERROR}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível iniciar uma campanha encerrada.",
            )

        audit = AuditService(self.session)

        result_contacts = await self.session.execute(
            select(func.count(CampaignContact.id)).where(CampaignContact.campaign_id == campaign.id)
        )
        total_contacts = result_contacts.scalar_one()
        if total_contacts == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campanha precisa ter contatos válidos antes de iniciar.",
            )

        settings_data = campaign.settings or {}
        chip_ids = settings_data.get("chip_ids") or []
        if not chip_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Configure ao menos um chip para a campanha.",
            )

        campaign.total_contacts = total_contacts

        remaining_to_send = max(total_contacts - campaign.sent_count, 0)
        if remaining_to_send == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não há mensagens pendentes para envio nesta campanha.",
            )

        await self._ensure_active_campaign_limit(db_user, campaign)
        await self._ensure_credit_balance(db_user, remaining_to_send)
        await self._ensure_monthly_limit(db_user, remaining_to_send)

        now = datetime.now(timezone.utc)

        if campaign.status == CampaignStatus.PAUSED:
            campaign.status = CampaignStatus.RUNNING
            await audit.record(
                user_id=user.id,
                action="campaign.resume",
                entity_type="campaign",
                entity_id=str(campaign.id),
                description="Campanha retomada após pausa.",
                extra_data=None,
                auto_commit=False,
            )
            await self.session.commit()
            resume_campaign_dispatch.delay(str(campaign.id))
            await self._publish_status(campaign.id, CampaignStatus.RUNNING, resumed_at=now)
            await self.session.refresh(campaign)
            return CampaignActionResponse(status=campaign.status, message="Campanha retomada.")

        if campaign.scheduled_for:
            eta = campaign.scheduled_for
            if eta.tzinfo is None:
                eta = eta.replace(tzinfo=timezone.utc)
            if eta > now:
                campaign.status = CampaignStatus.SCHEDULED
                campaign.started_at = None
                await audit.record(
                    user_id=user.id,
                    action="campaign.schedule",
                    entity_type="campaign",
                    entity_id=str(campaign.id),
                    description="Campanha agendada para execução futura.",
                    extra_data={"scheduled_for": eta.isoformat()},
                    auto_commit=False,
                )
                await self.session.commit()
                start_campaign_dispatch.apply_async((str(campaign.id),), eta=eta)
                await self._publish_status(
                    campaign.id,
                    CampaignStatus.SCHEDULED,
                    scheduled_for=eta,
                )
                await self.session.refresh(campaign)
                return CampaignActionResponse(
                    status=campaign.status,
                    message=f"Campanha agendada para {eta.isoformat()}",
                )

        campaign.status = CampaignStatus.RUNNING
        campaign.started_at = now
        await audit.record(
            user_id=user.id,
            action="campaign.start",
            entity_type="campaign",
            entity_id=str(campaign.id),
            description="Campanha iniciada para envio imediato.",
            extra_data={"remaining_contacts": remaining_to_send},
            auto_commit=False,
        )
        await self.session.commit()
        start_campaign_dispatch.delay(str(campaign.id))
        await self._publish_status(campaign.id, CampaignStatus.RUNNING, started_at=now)
        await self.session.refresh(campaign)
        return CampaignActionResponse(status=campaign.status, message="Campanha iniciada.")

    async def pause_campaign(self, user: User, campaign_id: UUID) -> CampaignActionResponse:
        campaign = await self._get_user_campaign(user, campaign_id)
        if campaign.status != CampaignStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Só é possível pausar campanhas em andamento.",
            )

        campaign.status = CampaignStatus.PAUSED
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="campaign.pause",
            entity_type="campaign",
            entity_id=str(campaign.id),
            description="Campanha pausada pelo usuário.",
            extra_data=None,
            auto_commit=False,
        )
        await self.session.commit()
        await self._publish_status(campaign.id, CampaignStatus.PAUSED, paused_at=datetime.now(timezone.utc))
        await self.session.refresh(campaign)
        return CampaignActionResponse(status=campaign.status, message="Campanha pausada.")

    async def cancel_campaign(self, user: User, campaign_id: UUID) -> CampaignActionResponse:
        campaign = await self._get_user_campaign(user, campaign_id)
        if campaign.status not in {CampaignStatus.RUNNING, CampaignStatus.PAUSED, CampaignStatus.SCHEDULED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campanha não está em estado que permita cancelamento.",
            )

        now = datetime.now(timezone.utc)
        update_result = await self.session.execute(
            update(CampaignMessage)
            .where(
                CampaignMessage.campaign_id == campaign.id,
                CampaignMessage.status.in_(
                    [MessageStatus.PENDING, MessageStatus.SENDING, MessageStatus.FAILED]
                ),
            )
            .values(
                status=MessageStatus.FAILED,
                failure_reason="Campanha cancelada pelo usuário.",
            )
        )
        affected = update_result.rowcount or 0
        campaign.failed_count += affected
        campaign.status = CampaignStatus.CANCELLED
        campaign.completed_at = now
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="campaign.cancel",
            entity_type="campaign",
            entity_id=str(campaign.id),
            description="Campanha cancelada pelo usuário.",
            extra_data={"messages_marked_failed": affected},
            auto_commit=False,
        )
        await self.session.commit()
        await self._publish_status(campaign.id, CampaignStatus.CANCELLED, cancelled_at=now)
        await self.session.refresh(campaign)
        return CampaignActionResponse(status=campaign.status, message="Campanha cancelada.")

    async def list_messages(
        self,
        user: User,
        campaign_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CampaignMessageResponse]:
        await self._get_user_campaign(user, campaign_id)
        result = await self.session.execute(
            select(CampaignMessage)
            .where(CampaignMessage.campaign_id == campaign_id)
            .order_by(CampaignMessage.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        messages = result.scalars().all()
        return [CampaignMessageResponse.model_validate(msg) for msg in messages]

    async def _get_user_campaign(self, user: User, campaign_id: UUID) -> Campaign:
        campaign = await self.session.get(Campaign, campaign_id)
        if not campaign or campaign.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campanha não encontrada.",
            )
        return campaign

    async def _get_user_with_plan(self, user: User) -> User:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.plan))
            .where(User.id == user.id)
        )
        db_user = result.scalar_one_or_none()
        if db_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado.",
            )
        return db_user

    def _ensure_campaign_type_allowed(self, user: User, campaign_type: CampaignType) -> None:
        if campaign_type == CampaignType.AB_TEST:
            if user.plan is None or user.plan.tier != PlanTier.ENTERPRISE:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Campanhas A/B Test estão disponíveis apenas no plano Enterprise.",
                )

    def _ensure_scheduling_allowed(self, user: User) -> None:
        features = self._get_plan_features(user)
        scheduling_allowed = bool(features.get("scheduling", False))
        if not scheduling_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu plano não permite agendamento de campanhas. Faça upgrade para liberar este recurso.",
            )

    def _get_plan_features(self, user: User) -> dict:
        if user.plan and user.plan.features:
            return user.plan.features
        return {}

    def _parse_limit_value(self, raw_value) -> int | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, bool):
            return 1 if raw_value else 0
        if isinstance(raw_value, (int, float)):
            return int(raw_value)
        if isinstance(raw_value, str):
            digits = "".join(ch for ch in raw_value if ch.isdigit())
            if digits:
                return int(digits)
        return None

    def _get_contacts_limit(self, user: User) -> int | None:
        features = self._get_plan_features(user)
        return self._parse_limit_value(features.get("contacts_per_list"))

    async def _ensure_active_campaign_limit(self, user: User, campaign: Campaign) -> None:
        features = self._get_plan_features(user)
        limit = self._parse_limit_value(features.get("campaigns_active"))
        if limit is None or limit <= 0:
            return

        result = await self.session.execute(
            select(func.count(Campaign.id)).where(
                Campaign.user_id == user.id,
                Campaign.id != campaign.id,
                Campaign.status.in_(
                    [CampaignStatus.RUNNING, CampaignStatus.SCHEDULED]
                ),
            )
        )
        active_count = result.scalar_one() or 0
        if active_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Você atingiu o limite de campanhas ativas para o seu plano. "
                    "Finalize uma campanha ativa ou faça upgrade para iniciar outra."
                ),
            )

    async def _ensure_credit_balance(self, user: User, messages_needed: int) -> None:
        if messages_needed <= 0:
            return
        if user.credits < messages_needed:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    f"Créditos insuficientes. São necessários {messages_needed} créditos e você possui "
                    f"{user.credits}. Compre créditos adicionais ou reduza a campanha."
                ),
            )

    async def _ensure_monthly_limit(self, user: User, messages_needed: int) -> None:
        if messages_needed <= 0:
            return
        plan = user.plan
        if plan is None or plan.monthly_messages <= 0:
            return

        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = await self.session.execute(
            select(func.count(CampaignMessage.id))
            .join(Campaign, CampaignMessage.campaign_id == Campaign.id)
            .where(
                Campaign.user_id == user.id,
                CampaignMessage.sent_at.is_not(None),
                CampaignMessage.sent_at >= month_start,
                CampaignMessage.status.in_(
                    [MessageStatus.SENT, MessageStatus.DELIVERED, MessageStatus.READ]
                ),
            )
        )
        messages_sent = result.scalar_one() or 0
        remaining = plan.monthly_messages - messages_sent
        if remaining < messages_needed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Limite mensal de mensagens do plano excedido. "
                    f"Disponível neste mês: {max(remaining, 0)} mensagem(ns). "
                    "Faça upgrade ou aguarde o próximo ciclo."
                ),
            )

    async def _publish_event(self, campaign_id: UUID, payload: dict) -> None:
        redis = get_redis_client()
        channel = f"{settings.redis_campaign_updates_channel}:{campaign_id}"
        try:
            await redis.publish(channel, json.dumps(payload, default=str))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao publicar evento da campanha %s: %s", campaign_id, exc)

    async def _publish_status(
        self,
        campaign_id: UUID,
        status: CampaignStatus,
        **metadata,
    ) -> None:
        await self._publish_event(
            campaign_id,
            {
                "type": "status",
                "status": status,
                "metadata": metadata,
            },
        )

    def _normalize_settings(
        self,
        user: User,
        settings: CampaignSettings | None,
        campaign_type: CampaignType,
    ) -> CampaignSettings:
        if settings is None:
            settings = CampaignSettings()
        if campaign_type != CampaignType.AB_TEST:
            settings.randomize_interval = bool(settings.randomize_interval)

        features = self._get_plan_features(user)
        min_interval = self._parse_limit_value(features.get("min_interval_seconds"))
        if min_interval is not None:
            settings.interval_seconds = max(settings.interval_seconds, min_interval)

        return settings

    async def _validate_chip_limits(self, user: User, chip_ids: Iterable[UUID]) -> None:
        chip_ids = list({chip_id for chip_id in chip_ids})
        if not chip_ids:
            return
        result = await self.session.execute(
            select(func.count(Chip.id)).where(
                Chip.user_id == user.id,
                Chip.id.in_(chip_ids),
            )
        )
        if result.scalar_one() != len(chip_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível validar os chips selecionados.",
            )

    def _normalize_phone(self, number: str) -> str | None:
        digits = "".join(filter(str.isdigit, number))
        if len(digits) == 13 and digits.startswith("55"):
            return digits
        if len(digits) == 11:
            return f"55{digits}"
        if len(digits) == 12 and digits.startswith("55"):
            return digits
        return None


__all__ = ("CampaignService",)


