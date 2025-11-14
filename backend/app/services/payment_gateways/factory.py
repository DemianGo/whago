"""
Payment Gateway Factory

Factory para criar instâncias de gateways de pagamento.
Facilita adição de novos provedores.
"""

from typing import Dict, Any
from .base import PaymentMethod, PaymentGateway
from .mercadopago_gateway import MercadoPagoGateway


class PaymentGatewayFactory:
    """
    Factory para criar gateways de pagamento.
    """
    
    _gateways = {
        PaymentMethod.MERCADOPAGO: MercadoPagoGateway,
        # PaymentMethod.PAYPAL: PayPalGateway,  # A implementar
        # PaymentMethod.STRIPE: StripeGateway,  # A implementar
    }
    
    @classmethod
    def create(cls, method: PaymentMethod, config: Dict[str, Any]) -> PaymentGateway:
        """
        Cria instância de gateway de pagamento.
        
        Args:
            method: Método de pagamento (mercadopago, paypal, stripe)
            config: Configurações do gateway
            
        Returns:
            Instância do gateway
            
        Raises:
            ValueError: Se método não suportado
        """
        gateway_class = cls._gateways.get(method)
        
        if not gateway_class:
            raise ValueError(f"Gateway {method} não suportado")
        
        return gateway_class(config)
    
    @classmethod
    def get_available_methods(cls) -> list:
        """
        Retorna lista de métodos de pagamento disponíveis.
        """
        return list(cls._gateways.keys())

