"""
Serviço responsável pelas operações com campanhas.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Iterable
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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

        campaign.total_contacts += valid
        await self.session.commit()

        return ContactUploadResponse(
            total_processed=total,
            valid_contacts=valid,
            invalid_contacts=invalid,
            duplicated=duplicated,
            preview=preview,
        )

    async def start_campaign(self, user: User, campaign_id: UUID) -> CampaignActionResponse:
        campaign = await self._get_user_campaign(user, campaign_id)
        if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED, CampaignStatus.PAUSED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campanha não está em estado que permita iniciar.",
            )
        if campaign.total_contacts == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campanha precisa ter contatos válidos antes de iniciar.",
            )

        campaign.status = CampaignStatus.RUNNING
        campaign.started_at = campaign.started_at or campaign.scheduled_for or func.now()
        await self.session.commit()
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
        return CampaignActionResponse(status=campaign.status, message="Campanha pausada.")

    async def cancel_campaign(self, user: User, campaign_id: UUID) -> CampaignActionResponse:
        campaign = await self._get_user_campaign(user, campaign_id)
        if campaign.status not in {CampaignStatus.RUNNING, CampaignStatus.PAUSED, CampaignStatus.SCHEDULED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campanha não está em estado que permita cancelamento.",
            )

        campaign.status = CampaignStatus.CANCELLED
        campaign.completed_at = func.now()
        await self.session.commit()
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


