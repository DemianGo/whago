"""
Serviço responsável por operações de billing, assinaturas e créditos.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.credit import CreditLedger, CreditSource
from ..models.invoice import Invoice, InvoiceStatus, PaymentAttempt, PaymentAttemptStatus
from ..models.plan import Plan
from ..models.transaction import (
    Transaction,
    TransactionStatus,
    TransactionType,
)
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
from .payment_gateway import PaymentGatewayClient, PaymentGatewayError

CREDIT_PACKAGES = {
    "credits_1000": {"credits": 1000, "price": Decimal("30.00")},
    "credits_5000": {"credits": 5000, "price": Decimal("120.00")},
    "credits_10000": {"credits": 10000, "price": Decimal("200.00")},
    "credits_50000": {"credits": 50000, "price": Decimal("750.00")},
}

SUBSCRIPTION_CYCLE_DAYS = 30
PAYMENT_FAILURE_LIMIT = 3
DOWNGRADE_GRACE_DAYS = 7


class BillingService:
    """Camada de domínio para regras de billing descritas no PRD."""

    def __init__(self, session: AsyncSession, gateway: PaymentGatewayClient | None = None):
        self.session = session
        self.gateway = gateway or PaymentGatewayClient()

    async def get_subscription_status(self, user: User) -> SubscriptionStatusResponse:
        await self.session.refresh(user, attribute_names=["plan", "pending_plan"])
        pending_plan_slug = user.pending_plan.slug if user.pending_plan else None
        pending_plan_name = user.pending_plan.name if user.pending_plan else None
        billing_status = "suspended" if user.is_suspended else "active"

        return SubscriptionStatusResponse(
            current_plan=user.plan.slug if user.plan else None,
            plan_name=user.plan.name if user.plan else None,
            renewal_at=user.subscription_renewal_at,
            pending_plan=pending_plan_slug,
            pending_plan_name=pending_plan_name,
            failed_payment_attempts=user.failed_payment_attempts,
            billing_status=billing_status,
            suspension_started_at=user.billing_suspension_started_at,
        )

    async def change_plan(self, user: User, payload: PlanChangeRequest) -> PlanChangeResponse:
        target_plan = await self.session.scalar(select(Plan).where(Plan.slug == payload.plan_slug.lower()))
        if target_plan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plano solicitado não foi encontrado.",
            )

        await self.session.refresh(user, attribute_names=["plan"])
        now = datetime.now(timezone.utc)
        current_plan = user.plan

        if current_plan and current_plan.id == target_plan.id:
            pending_slug = user.pending_plan.slug if user.pending_plan_id else None
            return PlanChangeResponse(
                status="unchanged",
                message="Você já está no plano solicitado.",
                current_plan=current_plan.slug,
                pending_plan=pending_slug,
                renewal_at=user.subscription_renewal_at,
            )

        # Upgrade ou primeira assinatura
        if current_plan is None or target_plan.price >= current_plan.price:
            amount_to_charge = self._calculate_upgrade_amount(
                current_price=Decimal(current_plan.price) if current_plan else Decimal("0.00"),
                new_price=Decimal(target_plan.price),
                renewal_at=user.subscription_renewal_at,
                now=now,
            )

            user.plan = target_plan
            user.pending_plan_id = None
            user.subscription_renewal_at = now + timedelta(days=SUBSCRIPTION_CYCLE_DAYS)
            user.failed_payment_attempts = 0
            user.is_suspended = False
            user.billing_suspension_started_at = None
            user.default_payment_method = payload.payment_method
            user.billing_customer_reference = payload.payment_reference

            transaction = Transaction(
                user_id=user.id,
                plan_id=target_plan.id,
                type=TransactionType.SUBSCRIPTION,
                status=TransactionStatus.COMPLETED,
                amount=amount_to_charge,
                credits=0,
                payment_method=payload.payment_method,
                reference_code=payload.payment_reference,
                processed_at=now,
                due_at=user.subscription_renewal_at,
                extra_data={
                    "pro_rata": bool(current_plan),
                    "charged_value": str(amount_to_charge),
                },
            )
            self.session.add(transaction)
            await self.session.flush()
            await self._issue_invoice(user, transaction, status=InvoiceStatus.PAID)
            await self.session.commit()

            return PlanChangeResponse(
                status="subscribed" if current_plan is None else "upgraded",
                message="Plano atualizado com sucesso.",
                current_plan=target_plan.slug,
                renewal_at=user.subscription_renewal_at,
            )

        # Downgrade: agenda para o próximo ciclo
        user.pending_plan_id = target_plan.id
        effective_at = user.subscription_renewal_at or (now + timedelta(days=SUBSCRIPTION_CYCLE_DAYS))
        await self.session.commit()

        return PlanChangeResponse(
            status="scheduled_downgrade",
            message="Downgrade agendado para o próximo ciclo de cobrança.",
            current_plan=current_plan.slug if current_plan else None,
            pending_plan=target_plan.slug,
            renewal_at=effective_at,
        )

    async def cancel_pending_downgrade(self, user: User) -> CancelDowngradeResponse:
        if not user.pending_plan_id:
            return CancelDowngradeResponse(
                status="no_pending_downgrade",
                message="Nenhum downgrade agendado para este usuário.",
            )

        user.pending_plan_id = None
        await self.session.commit()
        return CancelDowngradeResponse(status="cancelled", message="Downgrade agendado foi cancelado.")

    async def purchase_credits(self, user: User, payload: CreditPurchaseRequest) -> CreditPurchaseResponse:
        package = CREDIT_PACKAGES.get(payload.package_code)
        if package is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pacote de créditos inválido.",
            )

        credits_added = package["credits"]
        amount = package["price"]

        result = await self.gateway.authorize_credit_purchase(
            user=user,
            amount=amount,
            payment_method=payload.payment_method,
            payment_reference=payload.payment_reference,
        )
        if not result.success:
            raise HTTPException(status_code=400, detail="Pagamento não autorizado para compra de créditos.")

        transaction = Transaction(
            user_id=user.id,
            type=TransactionType.CREDIT_PURCHASE,
            status=TransactionStatus.COMPLETED,
            amount=amount,
            credits=credits_added,
            payment_method=payload.payment_method,
            reference_code=result.transaction_reference,
            processed_at=datetime.now(timezone.utc),
        )
        self.session.add(transaction)
        await self.session.flush()

        user.credits += credits_added
        ledger_entry = CreditLedger(
            user_id=user.id,
            transaction_id=transaction.id,
            source=CreditSource.PURCHASE,
            amount=credits_added,
            balance_after=user.credits,
            description=f"Compra de {credits_added} créditos.",
        )
        self.session.add(ledger_entry)
        await self._issue_invoice(user, transaction, status=InvoiceStatus.PAID)
        await self.session.commit()

        return CreditPurchaseResponse(
            credits_added=credits_added,
            new_balance=user.credits,
            transaction_id=transaction.id,
            payment_status=transaction.status.value,
        )

    async def list_transactions(self, user: User, limit: int = 50, offset: int = 0) -> Sequence[TransactionResponse]:
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.user_id == user.id)
            .order_by(Transaction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        transactions = result.scalars().all()
        return [
            TransactionResponse(
                id=tx.id,
                type=tx.type.value,
                status=tx.status.value,
                amount=float(tx.amount or 0),
                credits=tx.credits,
                payment_method=tx.payment_method,
                reference_code=tx.reference_code,
                created_at=tx.created_at,
                processed_at=tx.processed_at,
            )
            for tx in transactions
        ]

    async def list_credit_history(self, user: User, limit: int = 100, offset: int = 0) -> Sequence[CreditLedgerEntryResponse]:
        result = await self.session.execute(
            select(CreditLedger)
            .where(CreditLedger.user_id == user.id)
            .order_by(CreditLedger.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        entries = result.scalars().all()
        return [
            CreditLedgerEntryResponse(
                id=entry.id,
                source=entry.source.value,
                amount=entry.amount,
                balance_after=entry.balance_after,
                description=entry.description,
                created_at=entry.created_at,
            )
            for entry in entries
        ]

    async def list_invoices(self, user: User, limit: int = 50, offset: int = 0) -> Sequence[InvoiceResponse]:
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.user_id == user.id)
            .order_by(Invoice.issued_at.desc())
            .offset(offset)
            .limit(limit)
        )
        invoices = result.scalars().all()
        return [
            InvoiceResponse(
                id=invoice.id,
                number=invoice.number,
                status=invoice.status.value,
                amount=float(invoice.amount or 0),
                pdf_url=invoice.pdf_url,
                issued_at=invoice.issued_at,
                due_at=invoice.due_at,
            )
            for invoice in invoices
        ]

    async def process_subscription_cycle(self) -> None:
        now = datetime.now(timezone.utc)
        query = (
            select(User)
            .where(
                and_(
                    User.subscription_renewal_at.is_not(None),
                    User.subscription_renewal_at <= now,
                    User.plan_id.isnot(None),
                    User.default_payment_method.is_not(None),
                )
            )
        )
        result = await self.session.execute(query)
        users = result.scalars().unique().all()

        for user in users:
            await self.session.refresh(user, attribute_names=["plan"])
            if not user.plan:
                continue
            transaction = await self._get_or_create_subscription_transaction(user)
            await self._attempt_subscription_charge(user, transaction)

    async def process_pending_downgrades(self) -> None:
        now = datetime.now(timezone.utc)
        free_plan = await self._get_plan_by_slug("free")
        if not free_plan:
            return

        result = await self.session.execute(
            select(User)
            .where(
                and_(
                    User.pending_plan_id == free_plan.id,
                    User.billing_suspension_started_at.isnot(None),
                    User.billing_suspension_started_at <= now - timedelta(days=DOWNGRADE_GRACE_DAYS),
                )
            )
        )
        users = result.scalars().all()
        for user in users:
            user.plan_id = free_plan.id
            user.pending_plan_id = None
            user.subscription_renewal_at = None
            user.is_suspended = False
            user.billing_suspension_started_at = None
            await self.session.commit()

    def _calculate_upgrade_amount(
        self,
        current_price: Decimal,
        new_price: Decimal,
        renewal_at: datetime | None,
        now: datetime,
    ) -> Decimal:
        if current_price == Decimal("0.00"):
            return new_price
        if renewal_at is None or renewal_at <= now:
            return new_price

        remaining_seconds = (renewal_at - now).total_seconds()
        cycle_seconds = SUBSCRIPTION_CYCLE_DAYS * 24 * 3600
        fraction = Decimal(remaining_seconds / cycle_seconds).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        pro_rata = (new_price - current_price) * fraction
        if pro_rata <= Decimal("0.00"):
            return Decimal("0.00")
        return pro_rata.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    async def _get_or_create_subscription_transaction(self, user: User) -> Transaction:
        existing = await self.session.execute(
            select(Transaction)
            .where(
                and_(
                    Transaction.user_id == user.id,
                    Transaction.type == TransactionType.SUBSCRIPTION,
                    Transaction.status == TransactionStatus.PENDING,
                )
            )
            .order_by(Transaction.created_at.desc())
        )
        transaction = existing.scalars().first()
        if transaction:
            return transaction

        amount = Decimal(user.plan.price or 0)
        transaction = Transaction(
            user_id=user.id,
            plan_id=user.plan.id if user.plan else None,
            type=TransactionType.SUBSCRIPTION,
            status=TransactionStatus.PENDING,
            amount=amount,
            credits=0,
            payment_method=user.default_payment_method,
            due_at=user.subscription_renewal_at or datetime.now(timezone.utc),
        )
        self.session.add(transaction)
        await self.session.flush()
        return transaction

    async def _attempt_subscription_charge(self, user: User, transaction: Transaction) -> None:
        await self.session.refresh(user, attribute_names=["plan"])
        if not user.plan:
            return

        attempt_number = transaction.attempt_count + 1
        payment_attempt = PaymentAttempt(
            transaction_id=transaction.id,
            attempt_number=attempt_number,
            status=PaymentAttemptStatus.FAILED,
        )

        try:
            result = await self.gateway.charge_subscription(
                user=user,
                plan=user.plan,
                amount=Decimal(transaction.amount or 0),
            )
        except PaymentGatewayError as exc:  # pragma: no cover - caminho alternativo
            transaction.status = TransactionStatus.FAILED
            user.failed_payment_attempts += 1
            payment_attempt.failure_reason = str(exc)
            payment_attempt.response_code = "gateway-error"
        else:
            if result.success:
                transaction.status = TransactionStatus.COMPLETED
                transaction.processed_at = datetime.now(timezone.utc)
                transaction.reference_code = result.transaction_reference
                transaction.attempt_count = attempt_number
                user.failed_payment_attempts = 0
                user.is_suspended = False
                user.billing_suspension_started_at = None
                user.subscription_renewal_at = (transaction.due_at or datetime.now(timezone.utc)) + timedelta(
                    days=SUBSCRIPTION_CYCLE_DAYS
                )
                payment_attempt.status = PaymentAttemptStatus.SUCCESS
                payment_attempt.response_code = result.response_code
                payment_attempt.failure_reason = None
                await self._issue_invoice(user, transaction, status=InvoiceStatus.PAID)
            else:
                transaction.status = TransactionStatus.FAILED
                transaction.attempt_count = attempt_number
                user.failed_payment_attempts += 1
                payment_attempt.failure_reason = result.message or "Pagamento recusado"
                payment_attempt.response_code = result.response_code

        transaction.attempt_count = attempt_number
        self.session.add(payment_attempt)

        if user.failed_payment_attempts >= PAYMENT_FAILURE_LIMIT:
            user.is_suspended = True
            if not user.billing_suspension_started_at:
                user.billing_suspension_started_at = datetime.now(timezone.utc)
            free_plan = await self._get_plan_by_slug("free")
            if free_plan:
                user.pending_plan_id = free_plan.id

        await self.session.commit()

    async def _get_plan_by_slug(self, slug: str) -> Plan | None:
        return await self.session.scalar(select(Plan).where(Plan.slug == slug))

    async def _issue_invoice(
        self,
        user: User,
        transaction: Transaction,
        *,
        status: InvoiceStatus,
    ) -> Invoice:
        number = f"INV-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:6]}"
        invoice = Invoice(
            transaction_id=transaction.id,
            user_id=user.id,
            number=number,
            status=status,
            amount=transaction.amount,
            pdf_url=f"https://billing.whago.local/invoices/{number}.pdf",
            due_at=transaction.due_at,
        )
        self.session.add(invoice)
        await self.session.flush()
        return invoice


