"""
Schemas Pydantic relacionados a planos.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from ..models.plan import PlanTier


class PlanResponse(BaseModel):
    """Representação pública de um plano."""

    id: int
    name: str
    slug: str
    tier: PlanTier
    price: Decimal
    max_chips: int
    monthly_messages: int
    features: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


__all__ = ("PlanResponse",)


