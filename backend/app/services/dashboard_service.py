"""
Serviço responsável por fornecer dados consolidados para o dashboard.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.campaign import (
    Campaign,
    CampaignStatus,
    CampaignMessage,
    MessageStatus,
)
from ..models.chip import Chip, ChipEvent, ChipStatus
from ..models.transaction import Transaction, TransactionStatus, TransactionType
from ..models.user import User
from ..schemas.dashboard import (
    ActivityFeedResponse,
    ActivityItem,
    DashboardSummary,
    MessagesTrendResponse,
    TrendPoint,
)


class DashboardService:
    """Agrega métricas e eventos relevantes para o painel do usuário."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_summary(self, user: User) -> DashboardSummary:
        """Retorna métricas principais do dashboard."""

        today_start = _start_of_day(datetime.now(timezone.utc))
        tomorrow_start = today_start + timedelta(days=1)
        yesterday_start = today_start - timedelta(days=1)

        month_start = today_start.replace(day=1)
        previous_month_end = month_start - timedelta(seconds=1)
        previous_month_start = previous_month_end.replace(day=1)

        messages_today = await self._count_messages_between(
            user.id, today_start, tomorrow_start
        )
        messages_yesterday = await self._count_messages_between(
            user.id, yesterday_start, today_start
        )

        messages_month = await self._count_messages_between(
            user.id,
            month_start,
            tomorrow_start,
        )
        messages_prev_month = await self._count_messages_between(
            user.id,
            previous_month_start,
            previous_month_end + timedelta(seconds=1),
        )

        success_rate = await self._compute_success_rate(user.id)
        chips_connected, chips_total = await self._count_chips(user.id)
        campaigns_active, campaigns_total = await self._count_campaigns(user.id)

        return DashboardSummary(
            credits_available=user.credits,
            messages_today=messages_today,
            messages_today_variation=_compute_variation(
                messages_today, messages_yesterday
            ),
            messages_month=messages_month,
            messages_month_variation=_compute_variation(
                messages_month, messages_prev_month
            ),
            success_rate=success_rate,
            chips_connected=chips_connected,
            chips_total=chips_total,
            campaigns_active=campaigns_active,
            campaigns_total=campaigns_total,
        )

    async def get_messages_trend(
        self,
        user: User,
        *,
        days: int = 30,
    ) -> MessagesTrendResponse:
        """Retorna série temporal de mensagens para gráficos."""

        days = max(1, min(days, 90))
        end = _start_of_day(datetime.now(timezone.utc)) + timedelta(days=1)
        start = end - timedelta(days=days)

        rows = await self.session.execute(
            select(
                func.date_trunc(
                    "day", func.coalesce(CampaignMessage.sent_at, CampaignMessage.created_at)
                ).label("bucket"),
                func.sum(
                    case(
                        (CampaignMessage.status == MessageStatus.SENT, 1),
                        else_=0,
                    )
                ).label("sent"),
                func.sum(
                    case(
                        (CampaignMessage.status == MessageStatus.DELIVERED, 1),
                        else_=0,
                    )
                ).label("delivered"),
                func.sum(
                    case(
                        (CampaignMessage.status == MessageStatus.READ, 1),
                        else_=0,
                    )
                ).label("read"),
                func.sum(
                    case(
                        (CampaignMessage.status == MessageStatus.FAILED, 1),
                        else_=0,
                    )
                ).label("failed"),
            )
            .select_from(CampaignMessage)
            .join(Campaign, CampaignMessage.campaign_id == Campaign.id)
            .where(Campaign.user_id == user.id)
            .where(
                func.coalesce(CampaignMessage.sent_at, CampaignMessage.created_at)
                >= start
            )
            .where(
                func.coalesce(CampaignMessage.sent_at, CampaignMessage.created_at)
                < end
            )
            .group_by("bucket")
            .order_by("bucket")
        )

        data_map = {
            row.bucket.date(): {
                "sent": row.sent or 0,
                "delivered": row.delivered or 0,
                "read": row.read or 0,
                "failed": row.failed or 0,
            }
            for row in rows
        }

        points: list[TrendPoint] = []
        cursor = start
        while cursor < end:
            day_key = cursor.date()
            values = data_map.get(
                day_key,
                {"sent": 0, "delivered": 0, "read": 0, "failed": 0},
            )
            points.append(
                TrendPoint(
                    date=datetime.combine(day_key, datetime.min.time(), tzinfo=timezone.utc),
                    sent=values["sent"],
                    delivered=values["delivered"],
                    read=values["read"],
                    failed=values["failed"],
                )
            )
            cursor += timedelta(days=1)

        return MessagesTrendResponse(points=points)

    async def get_activity_feed(
        self,
        user: User,
        limit: int = 20,
    ) -> ActivityFeedResponse:
        """Combina eventos recentes para alimentar a timeline do dashboard."""

        limit = max(1, min(limit, 50))
        events: list[ActivityItem] = []

        # Eventos de chips
        chip_rows = await self.session.execute(
            select(
                ChipEvent.created_at,
                ChipEvent.type,
                ChipEvent.description,
                Chip.alias,
            )
            .join(Chip, ChipEvent.chip_id == Chip.id)
            .where(Chip.user_id == user.id)
            .order_by(ChipEvent.created_at.desc())
            .limit(limit)
        )
        for row in chip_rows:
            events.append(
                ActivityItem(
                    timestamp=row.created_at,
                    type=f"chip_{row.type.value}",
                    title=f"Chip {row.alias}",
                    description=row.description,
                )
            )

        # Eventos de campanhas
        campaign_rows = await self.session.execute(
            select(
                Campaign.name,
                Campaign.status,
                Campaign.created_at,
                Campaign.started_at,
                Campaign.completed_at,
            )
            .where(Campaign.user_id == user.id)
            .order_by(Campaign.created_at.desc())
            .limit(limit)
        )
        for row in campaign_rows:
            events.append(
                ActivityItem(
                    timestamp=row.created_at,
                    type="campaign_created",
                    title=f"Campanha {row.name}",
                    description="Campanha criada.",
                )
            )
            if row.started_at:
                events.append(
                    ActivityItem(
                        timestamp=row.started_at,
                        type="campaign_started",
                        title=f"Campanha {row.name}",
                        description="Envio iniciado.",
                    )
                )
            if row.completed_at:
                events.append(
                    ActivityItem(
                        timestamp=row.completed_at,
                        type="campaign_completed",
                        title=f"Campanha {row.name}",
                        description="Campanha concluída.",
                    )
                )

        # Eventos de billing
        transaction_rows = await self.session.execute(
            select(
                Transaction.created_at,
                Transaction.type,
                Transaction.status,
                Transaction.amount,
                Transaction.credits,
            )
            .where(Transaction.user_id == user.id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        for row in transaction_rows:
            description = (
                f"Transação {row.status.value}."
                if row.status != TransactionStatus.COMPLETED
                else f"Pagamento de R$ {float(row.amount):.2f} confirmado."
            )
            if row.credits:
                description += f" Créditos adicionados: {row.credits}."

            events.append(
                ActivityItem(
                    timestamp=row.created_at,
                    type=f"billing_{row.type.value}",
                    title="Movimentação financeira",
                    description=description,
                )
            )

        events.sort(key=lambda item: item.timestamp, reverse=True)
        return ActivityFeedResponse(items=events[:limit])

    async def _count_messages_between(
        self,
        user_id: UUID,
        start: datetime,
        end: datetime,
    ) -> int:
        """Conta mensagens dentro do intervalo informado."""

        result = await self.session.execute(
            select(func.count(CampaignMessage.id))
            .select_from(CampaignMessage)
            .join(Campaign, CampaignMessage.campaign_id == Campaign.id)
            .where(Campaign.user_id == user_id)
            .where(
                func.coalesce(CampaignMessage.sent_at, CampaignMessage.created_at)
                >= start
            )
            .where(
                func.coalesce(CampaignMessage.sent_at, CampaignMessage.created_at)
                < end
            )
        )
        return int(result.scalar_one() or 0)

    async def _compute_success_rate(self, user_id: UUID) -> float:
        """Calcula taxa de sucesso global das mensagens."""

        result = await self.session.execute(
            select(
                func.sum(
                    case(
                        (
                            CampaignMessage.status.in_(
                                [MessageStatus.DELIVERED, MessageStatus.READ]
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("success"),
                func.sum(
                    case(
                        (
                            CampaignMessage.status.in_(
                                [
                                    MessageStatus.SENT,
                                    MessageStatus.DELIVERED,
                                    MessageStatus.READ,
                                    MessageStatus.FAILED,
                                ]
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("base"),
            )
            .select_from(CampaignMessage)
            .join(Campaign, CampaignMessage.campaign_id == Campaign.id)
            .where(Campaign.user_id == user_id)
        )
        row = result.one()
        success = int(row.success or 0)
        base = int(row.base or 0)
        return float(round(success / base * 100, 2)) if base else 0.0

    async def _count_chips(self, user_id: UUID) -> tuple[int, int]:
        result = await self.session.execute(
            select(
                func.sum(
                    case(
                        (Chip.status == ChipStatus.CONNECTED, 1),
                        else_=0,
                    )
                ).label("connected"),
                func.count(Chip.id).label("total"),
            ).where(Chip.user_id == user_id)
        )
        row = result.one()
        return int(row.connected or 0), int(row.total or 0)

    async def _count_campaigns(self, user_id: UUID) -> tuple[int, int]:
        result = await self.session.execute(
            select(
                func.sum(
                    case(
                        (
                            Campaign.status.in_(
                                [CampaignStatus.RUNNING, CampaignStatus.SCHEDULED]
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("active"),
                func.count(Campaign.id).label("total"),
            ).where(Campaign.user_id == user_id)
        )
        row = result.one()
        return int(row.active or 0), int(row.total or 0)


def _start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _compute_variation(current: int, previous: int) -> float | None:
    if previous == 0:
        return None if current == 0 else 100.0
    return round(((current - previous) / previous) * 100, 2)

