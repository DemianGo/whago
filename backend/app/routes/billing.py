"""
Rotas relacionadas a billing, assinaturas e compra de créditos.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.user import User
from ..schemas.billing import (
    CancelDowngradeResponse,
    CreditLedgerEntryResponse,
    CreditPurchaseRequest,
    CreditPurchaseResponse,
    InvoiceResponse,
    PlanChangeRequest,
    PlanChangeResponse,
    SubscriptionStatusResponse,
    TransactionResponse,
)
from ..services.billing_service import BillingService

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])


def _service(session: AsyncSession) -> BillingService:
    return BillingService(session)


@router.get(
    "/subscription",
    response_model=SubscriptionStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SubscriptionStatusResponse:
    service = _service(session)
    return await service.get_subscription_status(current_user)


@router.post(
    "/plan/change",
    response_model=PlanChangeResponse,
    status_code=status.HTTP_200_OK,
)
async def change_plan(
    payload: PlanChangeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PlanChangeResponse:
    service = _service(session)
    return await service.change_plan(current_user, payload)


@router.post(
    "/plan/downgrade/cancel",
    response_model=CancelDowngradeResponse,
    status_code=status.HTTP_200_OK,
)
async def cancel_downgrade(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CancelDowngradeResponse:
    service = _service(session)
    return await service.cancel_pending_downgrade(current_user)


@router.post(
    "/credits/purchase",
    response_model=CreditPurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def purchase_credits(
    payload: CreditPurchaseRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CreditPurchaseResponse:
    service = _service(session)
    return await service.purchase_credits(current_user, payload)


@router.get(
    "/transactions",
    response_model=list[TransactionResponse],
    status_code=status.HTTP_200_OK,
)
async def list_transactions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[TransactionResponse]:
    service = _service(session)
    return list(await service.list_transactions(current_user))


@router.get(
    "/credits/history",
    response_model=list[CreditLedgerEntryResponse],
    status_code=status.HTTP_200_OK,
)
async def list_credit_history(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CreditLedgerEntryResponse]:
    service = _service(session)
    return list(await service.list_credit_history(current_user))


@router.get(
    "/invoices",
    response_model=list[InvoiceResponse],
    status_code=status.HTTP_200_OK,
)
async def list_invoices(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[InvoiceResponse]:
    service = _service(session)
    return list(await service.list_invoices(current_user))


