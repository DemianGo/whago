"""
Payment Schemas

Schemas Pydantic para validação de dados de pagamento.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class PaymentMethodInfo(BaseModel):
    """Informações de um método de pagamento"""
    id: str
    name: str
    logo: str
    enabled: bool


class PaymentMethodsResponse(BaseModel):
    """Lista de métodos de pagamento disponíveis"""
    methods: List[PaymentMethodInfo]


class CreateSubscriptionRequest(BaseModel):
    """Request para criar assinatura"""
    plan_id: int = Field(..., description="ID do plano")
    payment_method: str = Field(..., description="Método de pagamento (mercadopago, paypal, stripe)")


class CreateSubscriptionResponse(BaseModel):
    """Response de criação de assinatura"""
    subscription_id: str
    payment_url: str
    status: str
    plan: Dict[str, Any]


class CancelSubscriptionResponse(BaseModel):
    """Response de cancelamento de assinatura"""
    subscription_id: str
    status: str
    cancelled_at: str


class PurchaseCreditsRequest(BaseModel):
    """Request para comprar créditos"""
    credits: int = Field(..., gt=0, description="Quantidade de créditos")
    payment_method: str = Field(..., description="Método de pagamento (mercadopago, paypal, stripe)")


class PurchaseCreditsResponse(BaseModel):
    """Response de compra de créditos"""
    payment_id: str
    payment_url: str
    status: str
    amount: float
    credits: int


class SubscriptionInfo(BaseModel):
    """Informações de assinatura do usuário"""
    subscription_id: Optional[str] = None
    status: Optional[str] = None
    gateway: Optional[str] = None
    started_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None
    can_cancel: bool = False
    
    class Config:
        from_attributes = True

