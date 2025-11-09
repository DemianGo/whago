"""
Rotas de campanhas.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.user import User
from ..schemas.campaign import (
    CampaignActionResponse,
    CampaignCreate,
    CampaignDetail,
    CampaignMessageResponse,
    CampaignSummary,
    CampaignUpdate,
    ContactUploadResponse,
)
from ..services.campaign_service import CampaignService

router = APIRouter(prefix="/api/v1/campaigns", tags=["Campanhas"])


@router.get("/", response_model=list[CampaignSummary])
async def list_campaigns(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CampaignSummary]:
    service = CampaignService(session)
    return await service.list_campaigns(current_user)


@router.post(
    "/",
    response_model=CampaignDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    payload: CampaignCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CampaignDetail:
    service = CampaignService(session)
    return await service.create_campaign(current_user, payload)


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CampaignDetail:
    service = CampaignService(session)
    return await service.get_campaign(current_user, campaign_id)


@router.put("/{campaign_id}", response_model=CampaignDetail)
async def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CampaignDetail:
    service = CampaignService(session)
    return await service.update_campaign(current_user, campaign_id, payload)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    service = CampaignService(session)
    await service.delete_campaign(current_user, campaign_id)


@router.post(
    "/{campaign_id}/contacts/upload",
    response_model=ContactUploadResponse,
)
async def upload_contacts(
    campaign_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ContactUploadResponse:
    service = CampaignService(session)
    return await service.upload_contacts(current_user, campaign_id, file)


@router.post(
    "/{campaign_id}/start",
    response_model=CampaignActionResponse,
)
async def start_campaign(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CampaignActionResponse:
    service = CampaignService(session)
    return await service.start_campaign(current_user, campaign_id)


@router.post(
    "/{campaign_id}/pause",
    response_model=CampaignActionResponse,
)
async def pause_campaign(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CampaignActionResponse:
    service = CampaignService(session)
    return await service.pause_campaign(current_user, campaign_id)


@router.post(
    "/{campaign_id}/cancel",
    response_model=CampaignActionResponse,
)
async def cancel_campaign(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CampaignActionResponse:
    service = CampaignService(session)
    return await service.cancel_campaign(current_user, campaign_id)


@router.get(
    "/{campaign_id}/messages",
    response_model=list[CampaignMessageResponse],
)
async def list_messages(
    campaign_id: UUID,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CampaignMessageResponse]:
    service = CampaignService(session)
    return await service.list_messages(current_user, campaign_id, limit=limit, offset=offset)


