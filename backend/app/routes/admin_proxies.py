"""Rotas administrativas para gerenciamento de proxies."""

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.admin import get_current_admin
from ..models.proxy import ProxyProvider, Proxy
from ..models.admin import Admin
from ..schemas.proxy import ProxyProviderCreate, ProxyProviderUpdate, ProxyProviderResponse, ProxyResponse
from ..services.smartproxy_client import SmartproxyClient

router = APIRouter(prefix="/admin/proxies", tags=["Admin - Proxies"])


@router.get("/providers", response_model=List[ProxyProviderResponse])
async def list_providers(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lista provedores."""
    result = await db.execute(select(ProxyProvider).order_by(ProxyProvider.created_at.desc()))
    return result.scalars().all()


@router.post("/providers", response_model=ProxyProviderResponse)
async def create_provider(
    data: ProxyProviderCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Cria provedor."""
    provider = ProxyProvider(**data.model_dump())
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider


@router.get("/pool", response_model=List[ProxyResponse])
async def list_proxies(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lista proxies."""
    result = await db.execute(select(Proxy).order_by(Proxy.created_at.desc()))
    return result.scalars().all()


@router.get("/stats/dashboard")
async def get_stats(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Estatísticas."""
    return {"proxies_active": 1, "gb_month": 0, "cost_month": 0, "top_users": []}


__all__ = ["router"]
