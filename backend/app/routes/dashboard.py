"""
Endpoints para apoiar o dashboard do usuário.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.user import User
from ..schemas.dashboard import (
    ActivityFeedResponse,
    DashboardSummary,
    MessagesTrendResponse,
)
from ..services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


def _service(session: AsyncSession) -> DashboardService:
    return DashboardService(session)


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    service = _service(session)
    return await service.get_summary(current_user)


@router.get("/messages-trend", response_model=MessagesTrendResponse)
async def get_messages_trend(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MessagesTrendResponse:
    service = _service(session)
    return await service.get_messages_trend(current_user)


@router.get("/activity", response_model=ActivityFeedResponse)
async def get_activity_feed(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ActivityFeedResponse:
    service = _service(session)
    return await service.get_activity_feed(current_user)

