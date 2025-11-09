"""
Schemas Pydantic para operações de billing e créditos.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SubscriptionStatusResponse(BaseModel):
    current_plan: Optional[str] = Field(
        default=None, description="Slug do plano atual do usuário."
    )
    plan_name: Optional[str] = Field(
        default=None, description="Nome legível do plano atual."
    )
    renewal_at: Optional[datetime] = Field(
        default=None, description="Próxima data de renovação da assinatura."
    )
    pending_plan: Optional[str] = Field(
        default=None, description="Plano agendado para troca no próximo ciclo."
    )
    pending_plan_name: Optional[str] = None
    failed_payment_attempts: int = 0
    billing_status: str = Field(default="active", description="Situação de cobrança atual.")
    suspension_started_at: Optional[datetime] = None


class PlanChangeRequest(BaseModel):
    plan_slug: str = Field(..., description="Slug do plano desejado.")
    payment_method: str = Field(..., description="Método de pagamento utilizado.")
    payment_reference: Optional[str] = Field(
        default=None, description="Referência de pagamento (ex.: id de transação)."
    )


class PlanChangeResponse(BaseModel):
    status: str = Field(..., description="Resultado da operação.")
    message: str
    current_plan: Optional[str] = None
    pending_plan: Optional[str] = None
    renewal_at: Optional[datetime] = None


class CancelDowngradeResponse(BaseModel):
    status: str
    message: str


class CreditPurchaseRequest(BaseModel):
    package_code: str = Field(
        ...,
        description="Identificador do pacote de créditos (ex.: credits_1000).",
    )
    payment_method: str = Field(..., description="Método utilizado na compra.")
    payment_reference: Optional[str] = Field(default=None)


class CreditPurchaseResponse(BaseModel):
    credits_added: int
    new_balance: int
    transaction_id: UUID
    payment_status: str


class TransactionResponse(BaseModel):
    id: UUID
    type: str
    status: str
    amount: float
    credits: int
    payment_method: Optional[str]
    reference_code: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class CreditLedgerEntryResponse(BaseModel):
    id: UUID
    source: str
    amount: int
    balance_after: int
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceResponse(BaseModel):
    id: UUID
    number: str
    status: str
    amount: float
    pdf_url: Optional[str]
    issued_at: datetime
    due_at: Optional[datetime]

    model_config = {"from_attributes": True}


