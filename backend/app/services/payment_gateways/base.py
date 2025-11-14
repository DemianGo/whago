"""
Base Payment Gateway

Interface abstrata para todos os gateways de pagamento.
Garante consistência e facilita adição de novos provedores.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime


class PaymentMethod(str, Enum):
    """Métodos de pagamento suportados"""
    MERCADOPAGO = "mercadopago"
    PAYPAL = "paypal"
    STRIPE = "stripe"


class PaymentStatus(str, Enum):
    """Status de pagamento padronizado"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    IN_PROCESS = "in_process"


class SubscriptionStatus(str, Enum):
    """Status de assinatura padronizado"""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    PENDING = "pending"


class PaymentGateway(ABC):
    """
    Interface abstrata para gateways de pagamento.
    
    Todos os gateways devem implementar estes métodos para garantir
    compatibilidade com o sistema WHAGO.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o gateway com configurações.
        
        Args:
            config: Dicionário com credenciais e configurações do gateway
        """
        self.config = config
        self.gateway_name = self.__class__.__name__
    
    @abstractmethod
    async def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        amount: Decimal,
        currency: str = "BRL",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cria uma assinatura recorrente.
        
        Args:
            user_id: ID do usuário
            plan_id: ID do plano
            amount: Valor da assinatura
            currency: Moeda (BRL, USD, etc)
            metadata: Dados adicionais
            
        Returns:
            Dict com:
                - subscription_id: ID da assinatura no gateway
                - payment_url: URL para pagamento
                - status: Status inicial
                - external_id: ID externo do gateway
        """
        pass
    
    @abstractmethod
    async def cancel_subscription(
        self,
        subscription_id: str
    ) -> Dict[str, Any]:
        """
        Cancela uma assinatura recorrente.
        
        Args:
            subscription_id: ID da assinatura no gateway
            
        Returns:
            Dict com status da operação
        """
        pass
    
    @abstractmethod
    async def create_one_time_payment(
        self,
        user_id: str,
        amount: Decimal,
        description: str,
        currency: str = "BRL",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cria um pagamento único (ex: compra de créditos).
        
        Args:
            user_id: ID do usuário
            amount: Valor do pagamento
            description: Descrição do pagamento
            currency: Moeda
            metadata: Dados adicionais
            
        Returns:
            Dict com:
                - payment_id: ID do pagamento no gateway
                - payment_url: URL para pagamento
                - status: Status inicial
                - external_id: ID externo do gateway
        """
        pass
    
    @abstractmethod
    async def get_payment_status(
        self,
        payment_id: str
    ) -> Dict[str, Any]:
        """
        Consulta o status de um pagamento.
        
        Args:
            payment_id: ID do pagamento no gateway
            
        Returns:
            Dict com status atualizado
        """
        pass
    
    @abstractmethod
    async def process_webhook(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Processa webhook do gateway.
        
        Args:
            payload: Dados do webhook
            headers: Headers da requisição
            
        Returns:
            Dict com dados processados:
                - event_type: Tipo do evento
                - payment_id: ID do pagamento
                - status: Status do pagamento
                - data: Dados adicionais
        """
        pass
    
    @abstractmethod
    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Realiza estorno de um pagamento.
        
        Args:
            payment_id: ID do pagamento
            amount: Valor a estornar (None = total)
            
        Returns:
            Dict com status do estorno
        """
        pass
    
    def normalize_status(self, gateway_status: str) -> PaymentStatus:
        """
        Normaliza status do gateway para status padrão WHAGO.
        
        Args:
            gateway_status: Status retornado pelo gateway
            
        Returns:
            PaymentStatus padronizado
        """
        # Implementação padrão, pode ser sobrescrita
        status_map = {
            "approved": PaymentStatus.APPROVED,
            "pending": PaymentStatus.PENDING,
            "rejected": PaymentStatus.REJECTED,
            "cancelled": PaymentStatus.CANCELLED,
            "refunded": PaymentStatus.REFUNDED,
            "in_process": PaymentStatus.IN_PROCESS,
        }
        return status_map.get(gateway_status.lower(), PaymentStatus.PENDING)

