"""Serviço para consulta de logs de mensagens."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.campaign import Campaign, CampaignMessage, CampaignContact, MessageStatus
from ..models.chip import Chip
from ..models.user import User
from ..schemas.message import MessageLogResponse


class MessageService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_messages(
        self,
        user: User,
        *,
        status: Optional[MessageStatus] = None,
        campaign_id: Optional[UUID] = None,
        recipient_search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MessageLogResponse]:
        stmt = (
            select(CampaignMessage, Campaign, CampaignContact, Chip)
            .join(Campaign, CampaignMessage.campaign_id == Campaign.id)
            .join(CampaignContact, CampaignMessage.contact_id == CampaignContact.id)
            .outerjoin(Chip, CampaignMessage.chip_id == Chip.id)
            .where(Campaign.user_id == user.id)
            .order_by(CampaignMessage.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status:
            stmt = stmt.where(CampaignMessage.status == status)
        if campaign_id:
            stmt = stmt.where(CampaignMessage.campaign_id == campaign_id)
        if recipient_search:
            pattern = f"%{recipient_search.lower()}%"
            stmt = stmt.where(CampaignContact.phone_number.ilike(pattern))

        result = await self.session.execute(stmt)
        rows = result.all()
        logs: list[MessageLogResponse] = []
        for message, campaign, contact, chip in rows:
            logs.append(
                MessageLogResponse(
                    id=message.id,
                    campaign_id=campaign.id,
                    campaign_name=campaign.name,
                    status=message.status.value,
                    recipient=contact.phone_number,
                    chip_alias=chip.alias if chip else None,
                    variant=message.variant,
                    failure_reason=message.failure_reason,
                    created_at=message.created_at,
                    sent_at=message.sent_at,
                    delivered_at=message.delivered_at,
                    read_at=message.read_at,
                )
            )
        return logs


__all__ = ("MessageService",)
