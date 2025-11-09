"""Rotas para visualização de mensagens enviadas."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.campaign import MessageStatus
from ..models.user import User
from ..schemas.message import MessageLogResponse
from ..services.message_service import MessageService

router = APIRouter(prefix="/api/v1/messages", tags=["Messages"])


def _service(session: AsyncSession) -> MessageService:
    return MessageService(session)


@router.get("", response_model=list[MessageLogResponse])
async def list_messages(
    status_filter: Optional[str] = Query(None, alias="status"),
    campaign_id: Optional[UUID] = Query(None, alias="campaign_id"),
    recipient: Optional[str] = Query(None, alias="recipient"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[MessageLogResponse]:
    status_enum: Optional[MessageStatus] = None
    if status_filter:
        try:
            status_enum = MessageStatus(status_filter)
        except ValueError as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status de mensagem inválido.",
            ) from exc

    service = _service(session)
    return await service.list_messages(
        current_user,
        status=status_enum,
        campaign_id=campaign_id,
        recipient_search=recipient,
        limit=limit,
        offset=offset,
    )
