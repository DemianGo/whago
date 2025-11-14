"""
WHAGO Payment Gateways Module

Módulo modular para integração com múltiplos gateways de pagamento.
Suporta: Mercado Pago, PayPal, Stripe
"""

from .base import PaymentGateway, PaymentMethod, PaymentStatus
from .mercadopago_gateway import MercadoPagoGateway
from .factory import PaymentGatewayFactory

__all__ = [
    "PaymentGateway",
    "PaymentMethod",
    "PaymentStatus",
    "MercadoPagoGateway",
    "PaymentGatewayFactory",
]

