"""Integração simulada com gateways de pagamento (Stripe/Mercado Pago/PIX)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from ..models.user import User
from ..models.plan import Plan


class PaymentGatewayError(RuntimeError):
    """Erro genérico retornado pelos gateways simulados."""


@dataclass(slots=True)
class PaymentResult:
    success: bool
    provider: str
    transaction_reference: Optional[str] = None
    response_code: Optional[str] = None
    message: Optional[str] = None


class PaymentGatewayClient:
    """Cliente fake que representa interação com serviços externos de pagamento."""

    provider_map = {
        "card": "stripe",
        "pix": "pix",
        "boleto": "boleto",
    }

    async def charge_subscription(self, *, user: User, plan: Plan, amount: Decimal) -> PaymentResult:
        method = user.default_payment_method or "card"
        provider = self.provider_map.get(method, "stripe")
        reference = f"{provider}-{datetime.utcnow().timestamp():.0f}-{user.id.hex[:6]}"

        # Por padrão nossos testes consideram sucesso. Falhas podem ser simuladas
        # sobrescrevendo este método nos testes.
        return PaymentResult(
            success=True,
            provider=provider,
            transaction_reference=reference,
            response_code="200",
            message="Cobrança aprovada",
        )

    async def authorize_credit_purchase(
        self,
        *,
        user: User,
        amount: Decimal,
        payment_method: str,
        payment_reference: Optional[str] = None,
    ) -> PaymentResult:
        provider = self.provider_map.get(payment_method, "pix")
        reference = payment_reference or f"{provider}-{datetime.utcnow().timestamp():.0f}-{user.id.hex[:6]}"

        return PaymentResult(
            success=True,
            provider=provider,
            transaction_reference=reference,
            response_code="200",
            message="Pagamento confirmado",
        )


__all__ = ("PaymentGatewayClient", "PaymentGatewayError", "PaymentResult")
