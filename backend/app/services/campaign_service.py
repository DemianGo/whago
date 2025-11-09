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

from ...tasks.campaign_tasks import resume_campaign_dispatch, start_campaign_dispatch
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
from ..models.user import User
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
        settings = self._normalize_settings(data.settings, data.type)
        await self._validate_chip_limits(user, settings.chip_ids)

        campaign = Campaign(
            user_id=user.id,
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
            campaign.scheduled_for = data.scheduled_for
        if data.settings is not None:
            settings = self._normalize_settings(data.settings, campaign.type)
            await self._validate_chip_limits(user, settings.chip_ids)
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
        if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível importar contatos após o início da campanha.",
            )

        content = await file.read()
        decoded = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))

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

        now = datetime.now(timezone.utc)

        if campaign.status == CampaignStatus.PAUSED:
            campaign.status = CampaignStatus.RUNNING
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
        settings: CampaignSettings | None,
        campaign_type: CampaignType,
    ) -> CampaignSettings:
        if settings is None:
            settings = CampaignSettings()
        if campaign_type != CampaignType.AB_TEST:
            settings.randomize_interval = bool(settings.randomize_interval)
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


