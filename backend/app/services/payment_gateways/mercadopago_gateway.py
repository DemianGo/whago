"""
Mercado Pago Gateway Implementation

Integração completa com Mercado Pago:
- Assinaturas recorrentes
- Pagamentos únicos (créditos avulsos)
- Webhooks
- Estornos
"""

import httpx
import hmac
import hashlib
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta

from .base import PaymentGateway, PaymentStatus, SubscriptionStatus


class MercadoPagoGateway(PaymentGateway):
    """
    Gateway de pagamento Mercado Pago.
    
    Documentação: https://www.mercadopago.com.br/developers/pt/docs
    """
    
    BASE_URL = "https://api.mercadopago.com"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token = config.get("access_token")
        self.public_key = config.get("public_key")
        self.webhook_secret = config.get("webhook_secret")
        
        if not self.access_token:
            raise ValueError("Mercado Pago access_token é obrigatório")
    
    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers padrão para requisições"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": f"whago-{datetime.utcnow().timestamp()}"
        }
    
    async def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        amount: Decimal,
        currency: str = "BRL",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cria assinatura recorrente no Mercado Pago.
        
        Usa: Mercado Pago Subscriptions API
        """
        async with httpx.AsyncClient() as client:
            # Criar assinatura no Mercado Pago (preapproval)
            # Mercado Pago exige URL pública válida, não aceita localhost
            # Em sandbox, usar uma URL de exemplo ou página estática
            back_url = metadata.get("success_url", "")
            
            # Se a URL for localhost ou inválida, usar página do Mercado Pago
            if not back_url or "localhost" in back_url or not back_url.startswith("http"):
                back_url = "https://www.mercadopago.com.br"
            
            preference_data = {
                "reason": metadata.get("plan_name", f"Plano {plan_id}"),
                "auto_recurring": {
                    "frequency": 1,
                    "frequency_type": "months",
                    "transaction_amount": float(amount),
                    "currency_id": currency,
                },
                "back_url": back_url,
                "payer_email": metadata.get("user_email", ""),
                "external_reference": f"sub_{user_id}_{plan_id}",
            }
            
            print(f"[MercadoPago] Creating subscription with data: {preference_data}")
            
            response = await client.post(
                f"{self.BASE_URL}/preapproval",
                json=preference_data,
                headers=self._get_headers(),
                timeout=30.0
            )
            
            print(f"[MercadoPago] Response status: {response.status_code}, body: {response.text}")
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Erro ao criar assinatura: {response.text}")
            
            data = response.json()
            
            return {
                "subscription_id": data.get("id"),
                "payment_url": data.get("init_point"),  # URL para pagamento
                "status": self._normalize_subscription_status(data.get("status")),
                "external_id": data.get("id"),
                "gateway": "mercadopago",
            }
    
    async def cancel_subscription(
        self,
        subscription_id: str
    ) -> Dict[str, Any]:
        """
        Cancela assinatura no Mercado Pago.
        """
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.BASE_URL}/preapproval/{subscription_id}",
                json={"status": "cancelled"},
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if response.status_code not in [200, 204]:
                raise Exception(f"Erro ao cancelar assinatura: {response.text}")
            
            return {
                "subscription_id": subscription_id,
                "status": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat(),
            }
    
    async def create_one_time_payment(
        self,
        user_id: str,
        amount: Decimal,
        description: str,
        currency: str = "BRL",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cria pagamento único (compra de créditos).
        
        Usa: Mercado Pago Checkout Pro
        """
        async with httpx.AsyncClient() as client:
            # Garantir URLs válidas (Mercado Pago exige HTTPS público, não aceita localhost)
            success_url = metadata.get("success_url", "")
            failure_url = metadata.get("failure_url", "")
            pending_url = metadata.get("pending_url", "")
            
            # Validar URLs - se for localhost ou HTTP, usar fallback
            if not success_url or "localhost" in success_url or not success_url.startswith("https://"):
                success_url = "https://www.mercadopago.com.br"
            if not failure_url or "localhost" in failure_url or not failure_url.startswith("https://"):
                failure_url = "https://www.mercadopago.com.br"
            if not pending_url or "localhost" in pending_url or not pending_url.startswith("https://"):
                pending_url = "https://www.mercadopago.com.br"
            
            preference_data = {
                "items": [
                    {
                        "title": description,
                        "quantity": 1,
                        "unit_price": float(amount),
                        "currency_id": currency,
                    }
                ],
                "back_urls": {
                    "success": success_url,
                    "failure": failure_url,
                    "pending": pending_url,
                },
                "auto_return": "approved",
                "external_reference": f"credit_{user_id}_{datetime.utcnow().timestamp()}",
                "notification_url": metadata.get("webhook_url", ""),
                "payer": {
                    "email": metadata.get("user_email", ""),
                    "name": metadata.get("user_name", ""),
                },
                "metadata": {
                    "user_id": user_id,
                    "type": "one_time_credit",
                    "credits": metadata.get("credits", 0),
                },
                "statement_descriptor": "WHAGO - Créditos",
            }
            
            print(f"[MercadoPago] Creating preference with data: {preference_data}")
            
            response = await client.post(
                f"{self.BASE_URL}/checkout/preferences",
                json=preference_data,
                headers=self._get_headers(),
                timeout=30.0
            )
            
            print(f"[MercadoPago] Response status: {response.status_code}, body: {response.text}")
            
            if response.status_code not in [200, 201]:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("message", response.text)
                if "PA_UNAUTHORIZED_RESULT_FROM_POLICIES" in response.text:
                    error_msg = "Pagamento rejeitado pelo Mercado Pago. Verifique se você não está tentando pagar para si mesmo (mesmo email da conta vendedora)."
                raise Exception(f"Erro MP: {error_msg}")
            
            data = response.json()
            
            return {
                "payment_id": data.get("id"),
                "payment_url": data.get("init_point"),  # URL para pagamento
                "status": PaymentStatus.PENDING,
                "external_id": data.get("id"),
                "gateway": "mercadopago",
            }
    
    async def get_payment_status(
        self,
        payment_id: str
    ) -> Dict[str, Any]:
        """
        Consulta status de um pagamento.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/v1/payments/{payment_id}",
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Erro ao consultar pagamento: {response.text}")
            
            data = response.json()
            
            return {
                "payment_id": payment_id,
                "status": self.normalize_status(data.get("status")),
                "amount": Decimal(str(data.get("transaction_amount", 0))),
                "currency": data.get("currency_id"),
                "paid_at": data.get("date_approved"),
                "external_reference": data.get("external_reference"),
                "metadata": data.get("metadata", {}),
            }
    
    async def process_webhook(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Processa webhook do Mercado Pago.
        
        Eventos suportados:
        - payment: Pagamento único
        - subscription_preapproval: Assinatura
        """
        # Validar assinatura (se configurado)
        if self.webhook_secret:
            signature = headers.get("x-signature")
            if not self._validate_webhook_signature(payload, signature):
                raise ValueError("Assinatura do webhook inválida")
        
        event_type = payload.get("type")
        
        if event_type == "payment":
            # Pagamento único (créditos)
            payment_id = payload.get("data", {}).get("id")
            payment_data = await self.get_payment_status(payment_id)
            
            return {
                "event_type": "payment",
                "payment_id": payment_id,
                "status": payment_data["status"],
                "data": payment_data,
            }
        
        elif event_type in ["subscription_preapproval", "subscription_authorized_payment"]:
            # Assinatura recorrente
            subscription_id = payload.get("data", {}).get("id")
            
            return {
                "event_type": "subscription",
                "subscription_id": subscription_id,
                "status": payload.get("action"),
                "data": payload.get("data", {}),
            }
        
        else:
            return {
                "event_type": "unknown",
                "data": payload,
            }
    
    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Realiza estorno de pagamento.
        """
        async with httpx.AsyncClient() as client:
            refund_data = {}
            if amount:
                refund_data["amount"] = float(amount)
            
            response = await client.post(
                f"{self.BASE_URL}/v1/payments/{payment_id}/refunds",
                json=refund_data,
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Erro ao estornar pagamento: {response.text}")
            
            data = response.json()
            
            return {
                "refund_id": data.get("id"),
                "payment_id": payment_id,
                "status": "refunded",
                "amount": Decimal(str(data.get("amount", 0))),
                "refunded_at": data.get("date_created"),
            }
    
    def _validate_webhook_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        Valida assinatura do webhook.
        """
        if not signature or not self.webhook_secret:
            return True  # Não validar se não configurado
        
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            str(payload).encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _normalize_subscription_status(self, mp_status: str) -> str:
        """
        Normaliza status de assinatura do Mercado Pago.
        """
        status_map = {
            "authorized": "active",
            "paused": "paused",
            "cancelled": "cancelled",
            "pending": "pending",
        }
        return status_map.get(mp_status, "pending")

