"""Rotas para relatórios avançados e exportações."""

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.user import User
from ..schemas.report import (
    CampaignReportSummary,
    ChipsReportResponse,
    ExecutiveReportResponse,
    FinancialReportResponse,
    PlanComparisonResponse,
    ReportFormat,
)
from ..services.report_service import ReportService

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


def _service(session: AsyncSession) -> ReportService:
    return ReportService(session)


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _normalize(start: Optional[str], end: Optional[str]) -> tuple[datetime, datetime]:
    end_dt = _parse_date(end) or datetime.now(timezone.utc)
    start_dt = _parse_date(start) or (end_dt - timedelta(days=30))
    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt
    return start_dt, end_dt


def _stream(export) -> StreamingResponse:
    return StreamingResponse(
        content=io.BytesIO(export.payload),
        media_type=export.content_type,
        headers={"Content-Disposition": f"attachment; filename={export.filename}"},
    )


@router.get("/campaign/{campaign_id}", response_model=CampaignReportSummary)
async def get_campaign_report(
    campaign_id: UUID,
    format: ReportFormat = Query(ReportFormat.JSON, alias="format"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = _service(session)
    if format == ReportFormat.JSON:
        return await service.get_campaign_report(current_user, campaign_id)
    export = await service.export_campaign_report(current_user, campaign_id, format)
    return _stream(export)


@router.get("/chips", response_model=ChipsReportResponse)
async def get_chips_report(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: ReportFormat = Query(ReportFormat.JSON),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = _service(session)
    start, end = _normalize(start_date, end_date)
    if format == ReportFormat.JSON:
        return await service.get_chips_report(current_user, start, end)
    export = await service.export_chips_report(current_user, start, end, format)
    return _stream(export)


@router.get("/financial", response_model=FinancialReportResponse)
async def get_financial_report(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: ReportFormat = Query(ReportFormat.JSON),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = _service(session)
    start, end = _normalize(start_date, end_date)
    if format == ReportFormat.JSON:
        return await service.get_financial_report(current_user, start, end)
    export = await service.export_financial_report(current_user, start, end, format)
    return _stream(export)


@router.get("/executive", response_model=ExecutiveReportResponse)
async def get_executive_report(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: ReportFormat = Query(ReportFormat.JSON),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = _service(session)
    start, end = _normalize(start_date, end_date)
    if format == ReportFormat.JSON:
        return await service.get_executive_report(current_user, start, end)
    export = await service.export_executive_report(current_user, start, end, format)
    return _stream(export)


@router.get("/plans/comparison", response_model=PlanComparisonResponse)
async def get_plan_comparison(
    format: ReportFormat = Query(ReportFormat.JSON),
    session: AsyncSession = Depends(get_db),
):
    service = _service(session)
    if format == ReportFormat.JSON:
        return await service.get_plan_comparison()
    export = await service.export_plan_comparison(format)
    return _stream(export)
