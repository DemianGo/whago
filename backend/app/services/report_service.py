"""Serviço responsável pela geração de relatórios e exportações."""

from __future__ import annotations

import asyncio
import io
import textwrap
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable, Sequence
from uuid import UUID

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from fastapi import HTTPException, status
from sqlalchemy import and_, desc, func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.campaign import (
    Campaign,
    CampaignContact,
    CampaignMessage,
    CampaignStatus,
    MessageStatus,
)
from ..models.chip import Chip, ChipEvent, ChipEventType, ChipStatus
from ..models.credit import CreditLedger
from ..models.invoice import Invoice
from ..models.plan import Plan
from ..models.transaction import Transaction, TransactionStatus, TransactionType
from ..models.user import User
from ..schemas.report import (
    CampaignMessageReportItem,
    CampaignReportSummary,
    ChipsReportResponse,
    ExecutiveHighlight,
    ExecutiveReportResponse,
    FinancialReportItem,
    FinancialReportResponse,
    LedgerReportItem,
    PlanComparisonResponse,
    PlanFeatureComparison,
    ReportFormat,
)


@dataclass(slots=True)
class ReportExport:
    filename: str
    content_type: str
    payload: bytes


class ReportService:
    """Camada de domínio para relatórios avançados descritos no PRD."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_campaign_report(self, user: User, campaign_id: UUID) -> CampaignReportSummary:
        campaign = await self.session.get(Campaign, campaign_id)
        if campaign is None or campaign.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campanha não encontrada.")

        counts = await self._campaign_status_counts(campaign_id)
        total_messages = max(1, counts["total"])
        success_rate = round(((counts["delivered"] + counts["read"]) / total_messages) * 100, 2)

        timeline_rows = await self.session.execute(
            select(
                func.date_trunc(
                    "hour", func.coalesce(CampaignMessage.sent_at, CampaignMessage.created_at)
                ).label("bucket"),
                func.count(CampaignMessage.id).label("count"),
            )
            .where(CampaignMessage.campaign_id == campaign_id)
            .group_by("bucket")
            .order_by("bucket")
        )
        timeline = [
            {
                "bucket": row.bucket.isoformat() if row.bucket else None,
                "count": int(row.count or 0),
            }
            for row in timeline_rows
        ]

        distribution_rows = await self.session.execute(
            select(
                Chip.alias,
                func.count(CampaignMessage.id).label("count"),
                func.sum(
                    case((CampaignMessage.status == MessageStatus.FAILED, 1), else_=0)
                ).label("failed"),
            )
            .select_from(CampaignMessage)
            .join(Chip, CampaignMessage.chip_id == Chip.id, isouter=True)
            .where(CampaignMessage.campaign_id == campaign_id)
            .group_by(Chip.alias)
        )
        distribution = []
        for row in distribution_rows:
            alias = row.alias or "-"
            failed = int(row.failed or 0)
            sent = int(row.count or 0)
            success_rate_chip = round(((sent - failed) / sent) * 100, 2) if sent else 0.0
            distribution.append(
                {
                    "chip_alias": alias,
                    "messages": sent,
                    "failed": failed,
                    "success_rate": success_rate_chip,
                }
            )

        message_rows = await self.session.execute(
            select(
                CampaignMessage.id,
                CampaignMessage.status,
                CampaignMessage.failure_reason,
                CampaignMessage.sent_at,
                CampaignMessage.delivered_at,
                CampaignMessage.read_at,
                CampaignMessage.content,
                Chip.alias,
                CampaignContact.phone_number,
            )
            .join(CampaignContact, CampaignMessage.contact_id == CampaignContact.id)
            .join(Chip, CampaignMessage.chip_id == Chip.id, isouter=True)
            .where(CampaignMessage.campaign_id == campaign_id)
            .order_by(CampaignMessage.created_at)
        )
        messages = [
            CampaignMessageReportItem(
                message_id=row.id,
                recipient=row.phone_number,
                chip_alias=row.alias,
                status=row.status.value if isinstance(row.status, MessageStatus) else str(row.status),
                sent_at=row.sent_at,
                delivered_at=row.delivered_at,
                read_at=row.read_at,
                failure_reason=row.failure_reason,
            )
            for row in message_rows
        ]

        return CampaignReportSummary(
            campaign_id=campaign.id,
            name=campaign.name,
            status=campaign.status.value if isinstance(campaign.status, CampaignStatus) else str(campaign.status),
            type=campaign.type.value,
            started_at=campaign.started_at,
            completed_at=campaign.completed_at,
            total_contacts=campaign.total_contacts,
            sent=counts["sent"],
            delivered=counts["delivered"],
            read=counts["read"],
            failed=counts["failed"],
            credits_consumed=campaign.credits_consumed,
            success_rate=success_rate,
            timeline=timeline,
            distribution_by_chip=distribution,
            messages=messages,
        )

    async def get_chips_report(
        self,
        user: User,
        start_date: datetime,
        end_date: datetime,
    ) -> ChipsReportResponse:
        start, end = _normalize_interval(start_date, end_date)
        rows = await self.session.execute(
            select(
                Chip.id,
                Chip.alias,
                Chip.status,
                Chip.health_score,
                Chip.last_activity_at,
                func.count(CampaignMessage.id)
                .filter(
                    and_(
                        CampaignMessage.id.isnot(None),
                        func.coalesce(CampaignMessage.sent_at, CampaignMessage.created_at).between(start, end),
                    )
                )
                .label("sent"),
                func.sum(case((CampaignMessage.status == MessageStatus.FAILED, 1), else_=0))
                .filter(
                    and_(
                        CampaignMessage.id.isnot(None),
                        func.coalesce(CampaignMessage.sent_at, CampaignMessage.created_at).between(start, end),
                    )
                )
                .label("failed"),
            )
            .select_from(Chip)
            .outerjoin(CampaignMessage, CampaignMessage.chip_id == Chip.id)
            .where(Chip.user_id == user.id)
            .group_by(Chip.id)
        )
        chips = []
        for row in rows:
            sent = int(row.sent or 0)
            failed = int(row.failed or 0)
            success_rate = round(((sent - failed) / sent) * 100, 2) if sent else 0.0
            chips.append(
                {
                    "chip_id": row.id,
                    "alias": row.alias,
                    "status": row.status.value if isinstance(row.status, ChipStatus) else str(row.status),
                    "messages_sent": sent,
                    "messages_failed": failed,
                    "success_rate": success_rate,
                    "health_score": row.health_score,
                    "last_activity_at": row.last_activity_at,
                }
            )

        return ChipsReportResponse(start_date=start, end_date=end, chips=chips)

    async def get_financial_report(
        self,
        user: User,
        start_date: datetime,
        end_date: datetime,
    ) -> FinancialReportResponse:
        start, end = _normalize_interval(start_date, end_date)
        tx_rows = await self.session.execute(
            select(Transaction)
            .where(Transaction.user_id == user.id)
            .where(Transaction.created_at.between(start, end))
            .order_by(desc(Transaction.created_at))
        )
        transactions = [
            FinancialReportItem(
                transaction_id=tx.id,
                type=tx.type.value if isinstance(tx.type, TransactionType) else str(tx.type),
                status=tx.status.value if isinstance(tx.status, TransactionStatus) else str(tx.status),
                amount=float(tx.amount or 0),
                credits=tx.credits,
                payment_method=tx.payment_method,
                reference_code=tx.reference_code,
                created_at=tx.created_at,
                processed_at=tx.processed_at,
            )
            for tx in tx_rows.scalars()
        ]

        ledger_rows = await self.session.execute(
            select(CreditLedger)
            .where(CreditLedger.user_id == user.id)
            .where(CreditLedger.created_at.between(start, end))
            .order_by(desc(CreditLedger.created_at))
        )
        ledger = [
            LedgerReportItem(
                entry_id=entry.id,
                source=entry.source.value,
                amount=entry.amount,
                balance_after=entry.balance_after,
                description=entry.description,
                created_at=entry.created_at,
            )
            for entry in ledger_rows.scalars()
        ]

        summary = {
            "transactions_total": sum(item.amount for item in transactions),
            "credits_purchased": sum(item.credits for item in transactions if item.credits > 0),
            "last_transaction": transactions[0].created_at if transactions else None,
        }

        return FinancialReportResponse(
            start_date=start,
            end_date=end,
            summary=summary,
            transactions=transactions,
            ledger=ledger,
        )

    async def get_executive_report(
        self,
        user: User,
        start_date: datetime,
        end_date: datetime,
    ) -> ExecutiveReportResponse:
        start, end = _normalize_interval(start_date, end_date)
        # Resumo de campanhas
        campaign_rows = await self.session.execute(
            select(
                Campaign.id,
                Campaign.name,
                Campaign.status,
                Campaign.sent_count,
                Campaign.delivered_count,
                Campaign.failed_count,
                Campaign.credits_consumed,
            )
            .where(Campaign.user_id == user.id)
            .where(Campaign.created_at.between(start, end))
        )
        campaigns = campaign_rows.all()

        total_sent = sum(row.sent_count or 0 for row in campaigns)
        total_delivered = sum(row.delivered_count or 0 for row in campaigns)
        total_failed = sum(row.failed_count or 0 for row in campaigns)
        success_rate = round(((total_delivered) / total_sent) * 100, 2) if total_sent else 0.0

        highlights = [
            ExecutiveHighlight(title="Mensagens enviadas", value=str(total_sent)),
            ExecutiveHighlight(title="Entrega média", value=f"{success_rate:.2f}%"),
            ExecutiveHighlight(title="Créditos restantes", value=str(user.credits)),
        ]

        top_campaigns = [
            {
                "campaign_id": row.id,
                "name": row.name,
                "status": row.status.value if isinstance(row.status, CampaignStatus) else str(row.status),
                "sent": row.sent_count,
                "delivered": row.delivered_count,
                "failed": row.failed_count,
                "credits_consumed": row.credits_consumed,
            }
            for row in sorted(campaigns, key=lambda r: r.sent_count or 0, reverse=True)[:5]
        ]

        chip_metrics = await self.session.execute(
            select(
                Chip.alias,
                Chip.status,
                Chip.health_score,
                func.count(ChipEvent.id).label("events"),
            )
            .select_from(Chip)
            .join(ChipEvent, ChipEvent.chip_id == Chip.id, isouter=True)
            .where(Chip.user_id == user.id)
            .group_by(Chip.id)
        )
        chip_overview = [
            {
                "alias": row.alias,
                "status": row.status.value if isinstance(row.status, ChipStatus) else str(row.status),
                "health_score": row.health_score,
                "events": int(row.events or 0),
            }
            for row in chip_metrics
        ]

        recommendations = _build_recommendations(total_failed, success_rate, user.credits)

        return ExecutiveReportResponse(
            start_date=start,
            end_date=end,
            highlights=highlights,
            top_campaigns=top_campaigns,
            chip_overview=chip_overview,
            recommendations=recommendations,
        )

    async def get_plan_comparison(self) -> PlanComparisonResponse:
        rows = await self.session.execute(select(Plan))
        plans = [
            PlanFeatureComparison(
                plan_slug=plan.slug,
                name=plan.name,
                price=float(plan.price or 0),
                features=plan.features or {},
            )
            for plan in rows.scalars()
        ]
        plans.sort(key=lambda item: item.price)
        return PlanComparisonResponse(plans=plans)

    async def export_campaign_report(
        self,
        user: User,
        campaign_id: UUID,
        fmt: ReportFormat,
    ) -> ReportExport:
        summary = await self.get_campaign_report(user, campaign_id)
        records = [message.model_dump() for message in summary.messages]
        return await self._export_records(
            records,
            fmt,
            filename=f"campaign-report-{summary.campaign_id}",
            pdf_title=f"Relatório de Campanha: {summary.name}",
            pdf_sections=[
                ("Resumo", _summary_lines(summary)),
            ],
        )

    async def export_chips_report(
        self,
        user: User,
        start_date: datetime,
        end_date: datetime,
        fmt: ReportFormat,
    ) -> ReportExport:
        report = await self.get_chips_report(user, start_date, end_date)
        records = report.model_dump()["chips"]
        return await self._export_records(
            records,
            fmt,
            filename="chips-report",
            pdf_title="Relatório de Chips",
            pdf_sections=[
                (
                    "Período",
                    [
                        f"Início: {report.start_date.isoformat()}",
                        f"Fim: {report.end_date.isoformat()}",
                        f"Total de chips: {len(records)}",
                    ],
                )
            ],
        )

    async def export_financial_report(
        self,
        user: User,
        start_date: datetime,
        end_date: datetime,
        fmt: ReportFormat,
    ) -> ReportExport:
        report = await self.get_financial_report(user, start_date, end_date)
        transactions = [item.model_dump() for item in report.transactions]
        ledger = [item.model_dump() for item in report.ledger]
        sections = [
            (
                "Resumo",
                [
                    f"Total movimentado: R$ {report.summary['transactions_total']:.2f}",
                    f"Créditos comprados: {report.summary['credits_purchased']}",
                ],
            )
        ]
        return await self._export_records(
            transactions if fmt != ReportFormat.XLSX else {"Transações": transactions, "Ledger": ledger},
            fmt,
            filename="financial-report",
            pdf_title="Relatório Financeiro",
            pdf_sections=sections,
        )

    async def export_executive_report(
        self,
        user: User,
        start_date: datetime,
        end_date: datetime,
        fmt: ReportFormat,
    ) -> ReportExport:
        report = await self.get_executive_report(user, start_date, end_date)
        records = report.model_dump()
        sections = [
            (
                "Highlights",
                [f"{highlight.title}: {highlight.value}" + (f" ({highlight.variation})" if highlight.variation else "")
                 for highlight in report.highlights],
            ),
            (
                "Recomendações",
                report.recommendations or ["Sem recomendações adicionais."],
            ),
        ]
        return await self._export_records(
            records,
            fmt,
            filename="executive-report",
            pdf_title="Relatório Executivo",
            pdf_sections=sections,
        )

    async def export_plan_comparison(self, fmt: ReportFormat) -> ReportExport:
        report = await self.get_plan_comparison()
        records = [plan.model_dump() for plan in report.plans]
        return await self._export_records(
            records,
            fmt,
            filename="plan-comparison",
            pdf_title="Comparativo de Planos",
            pdf_sections=[("Planos", [f"{plan.name}: R$ {plan.price:.2f}" for plan in report.plans])],
        )

    async def _campaign_status_counts(self, campaign_id: UUID) -> dict[str, int]:
        rows = await self.session.execute(
            select(
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
                ).label("sent"),
                func.sum(
                    case((CampaignMessage.status == MessageStatus.DELIVERED, 1), else_=0)
                ).label("delivered"),
                func.sum(case((CampaignMessage.status == MessageStatus.READ, 1), else_=0)).label("read"),
                func.sum(case((CampaignMessage.status == MessageStatus.FAILED, 1), else_=0)).label("failed"),
                func.count(CampaignMessage.id).label("total"),
            )
            .where(CampaignMessage.campaign_id == campaign_id)
        )
        row = rows.one()
        return {
            "sent": int(row.sent or 0),
            "delivered": int(row.delivered or 0),
            "read": int(row.read or 0),
            "failed": int(row.failed or 0),
            "total": int(row.total or 0),
        }

    async def _export_records(
        self,
        records: Any,
        fmt: ReportFormat,
        *,
        filename: str,
        pdf_title: str,
        pdf_sections: Sequence[tuple[str, Iterable[str]]],
    ) -> ReportExport:
        if fmt == ReportFormat.JSON:
            payload = _to_json_bytes(records)
            return ReportExport(
                filename=f"{filename}.json",
                content_type="application/json",
                payload=payload,
            )

        if fmt == ReportFormat.CSV:
            df = _ensure_dataframe(records)
            payload = await asyncio.to_thread(lambda: df.to_csv(index=False).encode("utf-8"))
            return ReportExport(
                filename=f"{filename}.csv",
                content_type="text/csv; charset=utf-8",
                payload=payload,
            )

        if fmt == ReportFormat.XLSX:
            payload = await asyncio.to_thread(_dataframes_to_excel, records)
            return ReportExport(
                filename=f"{filename}.xlsx",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                payload=payload,
            )

        if fmt == ReportFormat.PDF:
            payload = await asyncio.to_thread(_render_pdf, pdf_title, pdf_sections)
            return ReportExport(
                filename=f"{filename}.pdf",
                content_type="application/pdf",
                payload=payload,
            )

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de relatório inválido.")


def _normalize_interval(start: datetime | None, end: datetime | None) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if end is None:
        end = now
    if start is None:
        start = end - timedelta(days=30)
    if start > end:
        start, end = end, start
    return start, end


def _to_json_bytes(data: Any) -> bytes:
    import json

    return json.dumps(data, default=_json_serializer, ensure_ascii=False, indent=2).encode("utf-8")


def _json_serializer(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    return obj


def _ensure_dataframe(records: Any) -> pd.DataFrame:
    if isinstance(records, pd.DataFrame):
        return records
    if isinstance(records, dict):
        return pd.DataFrame([records])
    return pd.DataFrame(list(records) if isinstance(records, Iterable) else [])


def _dataframes_to_excel(records: Any) -> bytes:
    buffer = io.BytesIO()

    def _prepare(df: pd.DataFrame) -> pd.DataFrame:
        for column in df.columns:
            series = df[column]
            if pd.api.types.is_datetime64tz_dtype(series):
                df[column] = series.dt.tz_convert(None)
            elif pd.api.types.is_datetime64_any_dtype(series):
                df[column] = series.dt.tz_localize(None)
        return df

    if isinstance(records, dict) and all(isinstance(v, Iterable) for v in records.values()):
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for sheet_name, rows in records.items():
                df = _prepare(_ensure_dataframe(rows))
                df.to_excel(writer, index=False, sheet_name=sheet_name[:31] or "Sheet1")
    else:
        df = _prepare(_ensure_dataframe(records))
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Relatorio")
    buffer.seek(0)
    return buffer.getvalue()


def _render_pdf(title: str, sections: Sequence[tuple[str, Iterable[str]]]) -> bytes:
    lines: list[str] = [title, "", ""]
    for header, entries in sections:
        lines.append(header)
        lines.append("=" * len(header))
        for entry in entries:
            for wrapped in textwrap.wrap(str(entry), width=90):
                lines.append(wrapped)
        lines.append("")

    font = ImageFont.load_default()
    line_height = font.getbbox("Ag")[3] + 6
    width = 1200
    height = max(200, (len(lines) + 2) * line_height)

    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)
    y = 40
    for line in lines:
        draw.text((40, y), line, fill="black", font=font)
        y += line_height

    buffer = io.BytesIO()
    image.save(buffer, format="PDF", resolution=150)
    buffer.seek(0)
    return buffer.getvalue()


def _summary_lines(summary: CampaignReportSummary) -> list[str]:
    return [
        f"Total contatos: {summary.total_contacts}",
        f"Mensagens enviadas: {summary.sent}",
        f"Entregues: {summary.delivered}",
        f"Lidas: {summary.read}",
        f"Falhas: {summary.failed}",
        f"Taxa de sucesso: {summary.success_rate:.2f}%",
    ]


def _build_recommendations(total_failed: int, success_rate: float, credits: int) -> list[str]:
    recommendations: list[str] = []
    if total_failed > 0:
        recommendations.append(
            "Analise as mensagens com falha e reavalie o conteúdo ou o horário de envio."
        )
    if success_rate < 80:
        recommendations.append(
            "Considere pausar campanhas com baixa performance e realizar testes A/B."
        )
    if credits < 200:
        recommendations.append("Saldo de créditos baixo: programe uma recarga para evitar interrupções.")
    if not recommendations:
        recommendations.append("Operação saudável. Continue monitorando performance regularmente.")
    return recommendations


__all__ = ("ReportService", "ReportExport")
