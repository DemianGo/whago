"""
Payment Service

Serviço de alto nível para gerenciar pagamentos, assinaturas e créditos.
Integra com múltiplos gateways de pagamento.
"""

from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.user import User
from ..models.plan import Plan
from ..models.transaction import Transaction, TransactionType, TransactionStatus
from ..models.credit import CreditLedger, CreditSource
from ..models.payment_gateway_config import PaymentGatewayConfig
from ..config import settings
from .payment_gateways import PaymentGatewayFactory, PaymentMethod, PaymentStatus


class PaymentService:
    """
    Serviço para gerenciar pagamentos e assinaturas.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def _get_gateway_config(self, method: PaymentMethod) -> Dict[str, Any]:
        """
        Retorna configuração do gateway baseado no método.
        
        Prioridade:
        1. Configuração do banco de dados (se existir e estiver habilitada)
        2. Variáveis de ambiente (fallback)
        """
        gateway_name = method.value
        
        # Tentar buscar do banco de dados
        stmt = select(PaymentGatewayConfig).where(
            PaymentGatewayConfig.gateway == gateway_name,
            PaymentGatewayConfig.is_enabled == True
        )
        result = await self.session.execute(stmt)
        db_config = result.scalar_one_or_none()
        
        if db_config:
            # Usar configuração do banco (permite alternar sandbox/production via admin)
            credentials = db_config.get_active_credentials()
            return {
                "access_token": credentials.get("access_token"),
                "public_key": credentials.get("public_key"),
                "client_id": credentials.get("client_id"),
                "client_secret": credentials.get("client_secret"),
                "webhook_secret": credentials.get("webhook_secret"),
                "mode": credentials.get("mode"),
            }
        
        # Fallback para variáveis de ambiente
        if method == PaymentMethod.MERCADOPAGO:
            return {
                "access_token": settings.mercadopago_access_token,
                "public_key": settings.mercadopago_public_key,
                "webhook_secret": settings.mercadopago_webhook_secret,
                "mode": "sandbox",
            }
        elif method == PaymentMethod.PAYPAL:
            return {
                "client_id": settings.paypal_client_id,
                "client_secret": settings.paypal_client_secret,
                "webhook_id": settings.paypal_webhook_id,
                "mode": settings.paypal_mode,
            }
        elif method == PaymentMethod.STRIPE:
            return {
                "api_key": settings.stripe_api_key,
                "webhook_secret": settings.stripe_webhook_secret,
                "mode": "test",
            }
        else:
            raise ValueError(f"Gateway {method} não configurado")
    
    async def create_subscription(
        self,
        user: User,
        plan_id: int,
        payment_method: PaymentMethod
    ) -> Dict[str, Any]:
        """
        Cria assinatura recorrente para um plano.
        
        Args:
            user: Usuário
            plan_id: ID do plano
            payment_method: Método de pagamento (mercadopago, paypal, stripe)
            
        Returns:
            Dict com dados da assinatura e URL de pagamento
        """
        # Buscar plano
        plan_stmt = select(Plan).where(Plan.id == plan_id)
        plan_result = await self.session.execute(plan_stmt)
        plan = plan_result.scalar_one_or_none()
        
        if not plan:
            raise ValueError("Plano não encontrado")
        
        # Criar gateway
        gateway_config = await self._get_gateway_config(payment_method)
        gateway = PaymentGatewayFactory.create(payment_method, gateway_config)
        
        # Preparar metadata
        # Mercado Pago sandbox aceita localhost para testes
        metadata = {
            "user_id": str(user.id),
            "user_email": user.email,
            "user_name": user.name,
            "plan_name": plan.name,
            "plan_id": plan_id,
            "success_url": f"{settings.frontend_url}/billing?payment=success",
            "failure_url": f"{settings.frontend_url}/billing?payment=failure",
            "pending_url": f"{settings.frontend_url}/billing?payment=pending",
            "webhook_url": f"{settings.api_url}/api/v1/payments/webhook/{payment_method.value}",
        }
        
        # Criar assinatura no gateway
        subscription_data = await gateway.create_subscription(
            user_id=str(user.id),
            plan_id=str(plan_id),
            amount=plan.price,
            currency="BRL",
            metadata=metadata
        )
        
        # Atualizar usuário com dados da assinatura (status pendente até confirmação do webhook)
        user.subscription_id = subscription_data["subscription_id"]
        user.subscription_status = "pending"  # Sempre pending até webhook confirmar
        user.subscription_gateway = payment_method.value
        user.subscription_started_at = None  # Só define após pagamento confirmado
        user.next_billing_date = None  # Só define após pagamento confirmado
        user.default_payment_method = payment_method.value
        
        # Criar transação pendente
        transaction = Transaction(
            user_id=user.id,
            plan_id=plan_id,
            type=TransactionType.SUBSCRIPTION,
            amount=plan.price,
            status=TransactionStatus.PENDING,
            payment_method=payment_method.value,
            reference_code=subscription_data["subscription_id"],
            extra_data={
                "subscription_id": subscription_data["subscription_id"],
                "plan_id": plan_id,
                "gateway": payment_method.value,
                "description": f"Assinatura {plan.name}",
            }
        )
        self.session.add(transaction)
        
        await self.session.commit()
        await self.session.refresh(user)
        
        return {
            "subscription_id": subscription_data["subscription_id"],
            "payment_url": subscription_data["payment_url"],
            "status": subscription_data["status"],
            "plan": {
                "id": plan.id,
                "name": plan.name,
                "price": float(plan.price),
            }
        }
    
    async def cancel_subscription(
        self,
        user: User
    ) -> Dict[str, Any]:
        """
        Cancela assinatura recorrente do usuário.
        """
        if not user.subscription_id:
            raise ValueError("Usuário não possui assinatura ativa")
        
        # Criar gateway
        payment_method = PaymentMethod(user.subscription_gateway)
        gateway_config = self._get_gateway_config(payment_method)
        gateway = PaymentGatewayFactory.create(payment_method, gateway_config)
        
        # Cancelar no gateway
        result = await gateway.cancel_subscription(user.subscription_id)
        
        # Atualizar usuário
        user.subscription_status = "cancelled"
        user.subscription_cancelled_at = datetime.utcnow()
        
        await self.session.commit()
        
        return {
            "subscription_id": user.subscription_id,
            "status": "cancelled",
            "cancelled_at": user.subscription_cancelled_at.isoformat(),
        }
    
    async def purchase_credits(
        self,
        user: User,
        credits: int,
        payment_method: PaymentMethod
    ) -> Dict[str, Any]:
        """
        Compra créditos avulsos.
        
        Args:
            user: Usuário
            credits: Quantidade de créditos
            payment_method: Método de pagamento
            
        Returns:
            Dict com dados do pagamento e URL
        """
        # Calcular valor (R$ 0.10 por crédito)
        amount = Decimal(credits) * Decimal("0.10")
        
        # Criar gateway
        gateway_config = await self._get_gateway_config(payment_method)
        gateway = PaymentGatewayFactory.create(payment_method, gateway_config)
        
        # Preparar metadata
        metadata = {
            "user_id": str(user.id),
            "user_email": user.email,
            "user_name": user.name,
            "credits": credits,
            "success_url": f"{settings.frontend_url}/billing?payment=success&type=credits",
            "failure_url": f"{settings.frontend_url}/billing?payment=failure",
            "pending_url": f"{settings.frontend_url}/billing?payment=pending",
            "webhook_url": f"{settings.api_url}/api/v1/payments/webhook/{payment_method.value}",
        }
        
        # Criar pagamento no gateway
        payment_data = await gateway.create_one_time_payment(
            user_id=str(user.id),
            amount=amount,
            description=f"Compra de {credits} créditos",
            currency="BRL",
            metadata=metadata
        )
        
        # Criar transação pendente
        transaction = Transaction(
            user_id=user.id,
            type=TransactionType.CREDIT_PURCHASE,
            amount=amount,
            credits=credits,
            status=TransactionStatus.PENDING,
            payment_method=payment_method.value,
            reference_code=payment_data["payment_id"],
            extra_data={
                "payment_id": payment_data["payment_id"],
                "credits": credits,
                "gateway": payment_method.value,
                "description": f"Compra de {credits} créditos",
            }
        )
        self.session.add(transaction)
        
        await self.session.commit()
        
        return {
            "payment_id": payment_data["payment_id"],
            "payment_url": payment_data["payment_url"],
            "status": payment_data["status"],
            "amount": float(amount),
            "credits": credits,
            "public_key": gateway_config.get("public_key"), # Retornar chave pública para frontend
        }
    
    async def process_webhook(
        self,
        payment_method: PaymentMethod,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Processa webhook de pagamento.
        """
        # Criar gateway
        gateway_config = await self._get_gateway_config(payment_method)
        gateway = PaymentGatewayFactory.create(payment_method, gateway_config)
        
        # Processar webhook
        webhook_data = await gateway.process_webhook(payload, headers)
        
        event_type = webhook_data.get("event_type")
        
        if event_type == "payment":
            # Pagamento único (créditos)
            await self._process_payment_webhook(webhook_data)
        elif event_type == "subscription":
            # Assinatura recorrente
            await self._process_subscription_webhook(webhook_data)
        
        return webhook_data
    
    async def _process_payment_webhook(self, webhook_data: Dict[str, Any]) -> None:
        """
        Processa webhook de pagamento único.
        """
        payment_id = webhook_data.get("payment_id")
        status = webhook_data.get("status")
        data = webhook_data.get("data", {})
        
        # Buscar transação
        stmt = select(Transaction).where(Transaction.reference_code == payment_id)
        result = await self.session.execute(stmt)
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return
        
        # Atualizar status
        transaction.status = status.value if isinstance(status, PaymentStatus) else status
        transaction.processed_at = datetime.utcnow() if status == PaymentStatus.APPROVED else None
        
        # Se aprovado, adicionar créditos
        if status == PaymentStatus.APPROVED:
            credits = transaction.extra_data.get("credits", 0)
            
            # Buscar usuário
            user_stmt = select(User).where(User.id == transaction.user_id)
            user_result = await self.session.execute(user_stmt)
            user = user_result.scalar_one()
            
            # Adicionar créditos
            user.credits += credits
            
            # Criar entrada no ledger
            ledger_entry = CreditLedger(
                user_id=user.id,
                transaction_id=transaction.id,
                source=CreditSource.PURCHASE,
                amount=credits,
                balance_after=user.credits,
                description=f"Compra de {credits} créditos",
            )
            self.session.add(ledger_entry)
        
        await self.session.commit()
    
    async def _process_subscription_webhook(self, webhook_data: Dict[str, Any]) -> None:
        """
        Processa webhook de assinatura.
        
        IMPORTANTE: A assinatura só é ativada após confirmação de pagamento via webhook.
        """
        subscription_id = webhook_data.get("subscription_id")
        status = webhook_data.get("status")
        
        # Buscar usuário pela subscription_id
        stmt = select(User).where(User.subscription_id == subscription_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return
        
        # Atualizar status da assinatura
        old_status = user.subscription_status
        user.subscription_status = status
        
        # Se foi um pagamento aprovado/autorizado (primeira vez ou recorrente)
        if status in ["authorized", "approved", "active"]:
            # Se era pending, é o primeiro pagamento - ativar assinatura
            if old_status == "pending":
                user.subscription_status = "active"
                user.subscription_started_at = datetime.utcnow()
            
            # Atualizar próxima cobrança
            user.next_billing_date = datetime.utcnow() + timedelta(days=30)
            
            # Buscar transação pendente ou criar nova
            trans_stmt = select(Transaction).where(
                Transaction.reference_code == subscription_id,
                Transaction.user_id == user.id,
                Transaction.type == TransactionType.SUBSCRIPTION
            ).order_by(Transaction.created_at.desc())
            trans_result = await self.session.execute(trans_stmt)
            transaction = trans_result.scalar_one_or_none()
            
            if transaction and transaction.status == TransactionStatus.PENDING:
                # Atualizar transação existente
                transaction.status = TransactionStatus.COMPLETED
                transaction.processed_at = datetime.utcnow()
            else:
                # Criar nova transação (pagamento recorrente)
                transaction = Transaction(
                    user_id=user.id,
                    plan_id=user.plan_id,
                    type=TransactionType.SUBSCRIPTION,
                    amount=user.plan.price if user.plan else Decimal("0"),
                    status=TransactionStatus.COMPLETED,
                    payment_method=user.subscription_gateway,
                    reference_code=subscription_id,
                    processed_at=datetime.utcnow(),
                    extra_data={
                        "description": f"Pagamento recorrente - {user.plan.name if user.plan else 'Plano'}",
                        "subscription_id": subscription_id,
                    }
                )
                self.session.add(transaction)
        
        # Se foi cancelado ou rejeitado
        elif status in ["cancelled", "rejected", "refunded"]:
            user.subscription_status = status
            if status == "cancelled":
                user.subscription_cancelled_at = datetime.utcnow()
        
        await self.session.commit()

