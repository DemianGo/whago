"""
Rotas de proxy para usuários (visualização de uso).
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.user import User
from ..schemas.proxy import ProxyUsageStatsResponse
from ..services.proxy_service import ProxyService

router = APIRouter(prefix="/api/v1/user/proxy", tags=["User - Proxy"])


@router.get("/usage", response_model=ProxyUsageStatsResponse)
async def get_my_proxy_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna uso de proxy do usuário no mês atual."""
    service = ProxyService(db)
    usage = await service.get_user_monthly_usage(current_user.id)
    
    # Buscar limite do plano
    await db.refresh(current_user, ["plan"])
    limit_gb = float(current_user.plan.proxy_gb_limit) if current_user.plan else 0.1
    
    bytes_used = usage["bytes_used"]
    gb_used = usage["gb_used"]
    cost = usage["cost"]
    
    percentage_used = (gb_used / limit_gb * 100) if limit_gb > 0 else 0
    
    return ProxyUsageStatsResponse(
        bytes_used=bytes_used,
        gb_used=round(gb_used, 3),
        cost=Decimal(str(cost)),
        limit_gb=Decimal(str(limit_gb)),
        percentage_used=round(percentage_used, 2),
    )


__all__ = ["router"]

