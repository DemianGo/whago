"""
Rotas de campanhas.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import AsyncSessionLocal, get_db
from ..dependencies.auth import authenticate_websocket, get_current_user
from ..core.redis import get_redis_client
from ..models.campaign import Campaign
from ..models.user import User
from ..schemas.campaign import (
    CampaignActionResponse,
    CampaignCreate,
    CampaignDetail,
    CampaignMediaResponse,
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


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_campaign(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    service = CampaignService(session)
    await service.delete_campaign(current_user, campaign_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@router.post("/{campaign_id}/dispatch-sync", response_model=CampaignActionResponse)
async def dispatch_campaign_sync(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CampaignActionResponse:
    service = CampaignService(session)
    return await service.dispatch_sync(current_user, campaign_id)


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


@router.websocket("/ws/{campaign_id}")
async def campaign_updates_ws(websocket: WebSocket, campaign_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        try:
            user = await authenticate_websocket(websocket, session)
        except HTTPException as exc:
            await websocket.close(code=1008, reason=exc.detail)
            return

        campaign = await session.get(Campaign, campaign_id)
        if campaign is None or campaign.user_id != user.id:
            await websocket.close(code=1008, reason="Campanha não encontrada ou acesso negado.")
            return

        initial_payload = {
            "type": "initial_state",
            "campaign_id": str(campaign.id),
            "status": campaign.status.value,
            "total_contacts": campaign.total_contacts,
            "sent_count": campaign.sent_count,
            "delivered_count": campaign.delivered_count,
            "read_count": campaign.read_count,
            "failed_count": campaign.failed_count,
            "credits_consumed": campaign.credits_consumed,
        }

    await websocket.accept()
    await websocket.send_json(initial_payload)

    redis = get_redis_client()
    pubsub = redis.pubsub()
    channel = f"{settings.redis_campaign_updates_channel}:{campaign_id}"
    await pubsub.subscribe(channel)

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
            if message is None:
                await asyncio.sleep(0.5)
                continue
            await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await pubsub.unsubscribe(channel)
        finally:
            await pubsub.close()
            with suppress(RuntimeError):
                await websocket.close()


@router.get(
    "/{campaign_id}/media",
    response_model=list[CampaignMediaResponse],
)
async def list_campaign_media(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CampaignMediaResponse]:
    service = CampaignService(session)
    return await service.list_media(current_user, campaign_id)


@router.post(
    "/{campaign_id}/media",
    response_model=CampaignMediaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_campaign_media(
    campaign_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CampaignMediaResponse:
    service = CampaignService(session)
    return await service.upload_media(current_user, campaign_id, file)


@router.get(
    "/{campaign_id}/media/{media_id}",
    response_class=FileResponse,
)
async def download_campaign_media(
    campaign_id: UUID,
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FileResponse:
    service = CampaignService(session)
    return await service.download_media(current_user, campaign_id, media_id)


@router.delete(
    "/{campaign_id}/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_campaign_media(
    campaign_id: UUID,
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    service = CampaignService(session)
    await service.delete_media(current_user, campaign_id, media_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


