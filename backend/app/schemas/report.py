"""Schemas para relatórios e exportações."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


class CampaignMessageReportItem(BaseModel):
    message_id: UUID
    recipient: str
    chip_alias: Optional[str]
    status: str
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    read_at: Optional[datetime]
    failure_reason: Optional[str]


class CampaignReportSummary(BaseModel):
    campaign_id: UUID
    name: str
    status: str
    type: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_contacts: int
    sent: int
    delivered: int
    read: int
    failed: int
    credits_consumed: int
    success_rate: float
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    distribution_by_chip: list[dict[str, Any]] = Field(default_factory=list)
    messages: list[CampaignMessageReportItem] = Field(default_factory=list)


class ChipReportItem(BaseModel):
    chip_id: UUID
    alias: str
    status: str
    messages_sent: int
    messages_failed: int
    success_rate: float
    health_score: int
    last_activity_at: Optional[datetime]


class ChipsReportResponse(BaseModel):
    start_date: datetime
    end_date: datetime
    chips: list[ChipReportItem]


class FinancialReportItem(BaseModel):
    transaction_id: UUID
    type: str
    status: str
    amount: float
    credits: int
    payment_method: Optional[str]
    reference_code: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]


class LedgerReportItem(BaseModel):
    entry_id: UUID
    source: str
    amount: int
    balance_after: int
    description: Optional[str]
    created_at: datetime


class FinancialReportResponse(BaseModel):
    start_date: datetime
    end_date: datetime
    summary: dict[str, Any]
    transactions: list[FinancialReportItem]
    ledger: list[LedgerReportItem]


class ExecutiveHighlight(BaseModel):
    title: str
    value: str
    variation: Optional[str] = None


class ExecutiveReportResponse(BaseModel):
    start_date: datetime
    end_date: datetime
    highlights: list[ExecutiveHighlight]
    top_campaigns: list[dict[str, Any]]
    chip_overview: list[dict[str, Any]]
    recommendations: list[str]


class PlanFeatureComparison(BaseModel):
    plan_slug: str
    name: str
    price: float
    features: dict[str, Any]


class PlanComparisonResponse(BaseModel):
    plans: list[PlanFeatureComparison]


__all__ = [
    "ReportFormat",
    "CampaignReportSummary",
    "ChipsReportResponse",
    "FinancialReportResponse",
    "ExecutiveReportResponse",
    "PlanComparisonResponse",
]
