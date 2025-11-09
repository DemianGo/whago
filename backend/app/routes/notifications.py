"""Rotas REST para notificações in-app."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.user import User
from ..schemas.notification import (
    NotificationCountResponse,
    NotificationMarkReadRequest,
    NotificationResponse,
)
from ..services.notification_service import NotificationService

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


def _service(session: AsyncSession) -> NotificationService:
    return NotificationService(session)


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False, alias="unread_only"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[NotificationResponse]:
    service = _service(session)
    notifications = await service.list_notifications(
        current_user,
        limit=limit,
        offset=offset,
        only_unread=unread_only,
    )
    return [NotificationResponse.model_validate(notif) for notif in notifications]


@router.get("/unread-count", response_model=NotificationCountResponse)
async def unread_count(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationCountResponse:
    service = _service(session)
    count = await service.unread_count(current_user)
    return NotificationCountResponse(unread=count)


@router.post("/mark-read", status_code=status.HTTP_200_OK)
async def mark_read(
    payload: NotificationMarkReadRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationCountResponse:
    if not payload.notification_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lista de notificações vazia.")
    service = _service(session)
    updated = await service.mark_read(current_user, payload.notification_ids)
    return NotificationCountResponse(unread=max(0, (await service.unread_count(current_user))))


@router.post("/mark-all-read", status_code=status.HTTP_200_OK)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationCountResponse:
    service = _service(session)
    await service.mark_all_read(current_user)
    return NotificationCountResponse(unread=0)
