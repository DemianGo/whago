"""
Schemas de resposta para os endpoints de dashboard.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    credits_available: int
    messages_today: int
    messages_today_variation: Optional[float] = Field(
        default=None,
        description="Variação percentual em relação ao dia anterior.",
    )
    messages_month: int
    messages_month_variation: Optional[float] = Field(
        default=None,
        description="Variação percentual em relação ao mês anterior.",
    )
    success_rate: float = Field(description="Percentual de sucesso geral (0-100).")
    chips_connected: int
    chips_total: int
    campaigns_active: int
    campaigns_total: int


class TrendPoint(BaseModel):
    date: datetime
    sent: int
    delivered: int
    read: int
    failed: int


class MessagesTrendResponse(BaseModel):
    points: list[TrendPoint]


class ActivityItem(BaseModel):
    timestamp: datetime
    type: str
    title: str
    description: str


class ActivityFeedResponse(BaseModel):
    items: list[ActivityItem]

