"""
Tarefas Celery relacionadas ao envio de campanhas.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from typing import Iterable, Sequence
from uuid import UUID

from celery import shared_task
from redis import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.campaign import (
    Campaign,
    CampaignContact,
    CampaignMessage,
    CampaignStatus,
    CampaignType,
    MessageStatus,
)
from app.models.chip import Chip, ChipStatus
from app.models.credit import CreditLedger, CreditSource
from app.models.user import User
from app.services.waha_container_manager import WahaContainerManager
from app.services.webhook_service import WebhookEvent, WebhookService

logger = logging.getLogger("whago.campaign.tasks")


class InsufficientCreditsError(Exception):
    """Erro lançado quando o usuário não possui créditos suficientes."""


def _get_sync_redis() -> Redis:
    return Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


def _publish_update(campaign_id: UUID, payload: dict) -> None:
    channel = f"{settings.redis_campaign_updates_channel}:{campaign_id}"
    redis_client = _get_sync_redis()
    try:
        redis_client.publish(channel, json.dumps(payload, default=str))
    finally:
        redis_client.close()


async def _dispatch_campaign_webhook(
    session: AsyncSession,
    campaign: Campaign,
    status: CampaignStatus,
    metadata: dict,
) -> None:
    user = await session.get(User, campaign.user_id)
    if user is None:
        return
    await session.refresh(user, attribute_names=["plan"])
    event_map = {
        CampaignStatus.COMPLETED: WebhookEvent.CAMPAIGN_COMPLETED,
        CampaignStatus.CANCELLED: WebhookEvent.CAMPAIGN_CANCELLED,
    }
    event = event_map.get(status)
    if event is None:
        return
    payload = {
        "campaign_id": str(campaign.id),
        "name": campaign.name,
        "status": status.value,
        "metadata": metadata,
        "stats": {
            "total_contacts": campaign.total_contacts,
            "sent": campaign.sent_count,
            "delivered": campaign.delivered_count,
            "read": campaign.read_count,
            "failed": campaign.failed_count,
        },
    }
    service = WebhookService(session)
    await service.dispatch(user_id=user.id, event=event, payload=payload)


def _render_message(
    template: str,
    contact: CampaignContact,
) -> str:
    variables = {
        "nome": contact.name or "",
        "name": contact.name or "",
        "empresa": contact.company or "",
        "company": contact.company or "",
    }
    if contact.variables:
        variables.update(contact.variables)

    text = template
    for key, value in variables.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
    return text


async def _prepare_campaign_messages(
    session: AsyncSession,
    campaign: Campaign,
) -> list[UUID]:
    result = await session.execute(
        select(CampaignMessage.id)
        .where(CampaignMessage.campaign_id == campaign.id)
        .order_by(CampaignMessage.created_at.asc())
    )
    existing_ids = [row[0] for row in result.all()]
    if existing_ids:
        return existing_ids

    result_contacts = await session.execute(
        select(CampaignContact).where(CampaignContact.campaign_id == campaign.id)
    )
    contacts: list[CampaignContact] = result_contacts.scalars().all()
    if not contacts:
        raise ValueError("Campanha não possui contatos para envio.")

    settings_data = campaign.settings or {}
    chip_ids: list[str] = settings_data.get("chip_ids") or []
    if not chip_ids:
        raise ValueError("Nenhum chip configurado para esta campanha.")

    chip_cycle = [UUID(str(value)) for value in chip_ids]
    random.shuffle(chip_cycle)
    total_contacts = len(contacts)
    created_ids: list[UUID] = []

    for idx, contact in enumerate(contacts):
        template = campaign.message_template
        variant = None

        if campaign.type == CampaignType.AB_TEST and campaign.message_template_b:
            variant = "A" if idx % 2 == 0 else "B"
            template = campaign.message_template if variant == "A" else campaign.message_template_b

        rendered = _render_message(template, contact)
        chip_id = chip_cycle[idx % len(chip_cycle)]

        message = CampaignMessage(
            campaign_id=campaign.id,
            contact_id=contact.id,
            chip_id=chip_id,
            content=rendered,
            variant=variant,
        )
        session.add(message)
        await session.flush()
        created_ids.append(message.id)

    campaign.total_contacts = total_contacts
    campaign.sent_count = 0
    campaign.delivered_count = 0
    campaign.read_count = 0
    campaign.failed_count = 0
    campaign.credits_consumed = 0
    await session.commit()
    return created_ids


async def _update_campaign_status(
    session: AsyncSession,
    campaign_id: UUID,
    status: CampaignStatus,
    **metadata,
) -> None:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        return
    await session.execute(
        update(Campaign)
        .where(Campaign.id == campaign_id)
        .values(status=status, **metadata)
    )
    await session.commit()
    await session.refresh(campaign)
    _publish_update(
        campaign_id,
        {
            "type": "status",
            "status": status,
            "metadata": metadata,
        },
    )
    await _dispatch_campaign_webhook(session, campaign, status, metadata)


async def _deduct_user_credit(
    session: AsyncSession,
    campaign: Campaign,
    description: str,
) -> None:
    result = await session.execute(
        select(User).where(User.id == campaign.user_id).with_for_update()
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise RuntimeError("Usuário associado à campanha não encontrado.")
    if user.credits <= 0:
        raise InsufficientCreditsError

    user.credits -= 1
    ledger_entry = CreditLedger(
        user_id=user.id,
        source=CreditSource.CONSUMPTION,
        amount=-1,
        balance_after=user.credits,
        description=description,
    )
    session.add(ledger_entry)
    await session.flush()


async def _execute_send_message(message_id: UUID) -> bool:
    async with AsyncSessionLocal() as session:
        message = await session.get(CampaignMessage, message_id)
        if message is None:
            logger.warning("Mensagem %s não encontrada.", message_id)
            return False

        campaign = await session.get(Campaign, message.campaign_id)
        if campaign is None:
            logger.warning("Campanha %s não encontrada.", message.campaign_id)
            return False

        if campaign.status != CampaignStatus.RUNNING:
            logger.info(
                "Ignorando mensagem %s pois campanha está em estado %s",
                message_id,
                campaign.status,
            )
            return False

        contact = await session.get(CampaignContact, message.contact_id)
        if contact is None:
            logger.warning("Contato %s não encontrado.", message.contact_id)
            return False

        if message.status not in {MessageStatus.PENDING, MessageStatus.FAILED}:
            return False

        message.status = MessageStatus.SENDING
        await session.commit()

        try:
            # Obter container WAHA Plus do usuário do chip
            chip = await session.get(Chip, message.chip_id)
            if not chip:
                raise Exception("Chip não encontrado")
            
            # Verificar se o chip está conectado
            if chip.status != ChipStatus.CONNECTED:
                raise Exception(f"Chip não está conectado (status: {chip.status})")
            
            container_manager = WahaContainerManager()
            waha_container = await container_manager.get_user_container(str(chip.user_id))
            
            if not waha_container:
                raise Exception("Container WAHA Plus não encontrado para o usuário")
            
            # Obter cliente WAHA Plus
            from app.services.waha_client import WAHAClient
            waha_client = WAHAClient(
                base_url=waha_container['base_url'],
                api_key=waha_container['api_key']
            )
            
            # Enviar mensagem via WAHA Plus
            session_name = chip.extra_data.get("waha_session", f"chip_{chip.id}")
            try:
                response = await waha_client.send_message(
                    session_id=session_name,
                    to=contact.phone_number,
                    text=message.content
                )
                logger.debug("Resposta WAHA Plus %s", response)
            finally:
                # Fechar conexões HTTP
                await waha_client.close()

            message.status = MessageStatus.SENT
            message.sent_at = datetime.now(timezone.utc)
            campaign.sent_count += 1
            campaign.credits_consumed += 1

            await _deduct_user_credit(
                session,
                campaign,
                f"Envio de mensagem para {contact.phone_number} na campanha '{campaign.name}'",
            )
            await session.commit()

            _publish_update(
                campaign.id,
                {
                    "type": "message_sent",
                    "message_id": str(message.id),
                    "contact_id": str(contact.id),
                    "status": message.status,
                },
            )
            return True
        except InsufficientCreditsError:
            logger.warning(
                "Créditos insuficientes para usuário %s durante envio da campanha %s.",
                campaign.user_id,
                campaign.id,
            )
            message.status = MessageStatus.FAILED
            message.failure_reason = "Créditos insuficientes."
            campaign.failed_count += 1
            await session.commit()
            _publish_update(
                campaign.id,
                {
                    "type": "message_failed",
                    "message_id": str(message.id),
                    "contact_id": str(contact.id),
                    "status": message.status,
                    "reason": message.failure_reason,
                },
            )
            await _update_campaign_status(
                session,
                campaign.id,
                CampaignStatus.PAUSED,
                paused_at=datetime.now(timezone.utc),
                reason="insufficient_credits",
            )
            return False
        except Exception as exc:  # noqa: BLE001
            logger.exception("Falha ao enviar mensagem %s: %s", message_id, exc)
            message.status = MessageStatus.FAILED
            message.failure_reason = str(exc)[:250]  # Trunca para 250 chars (limite DB: 255)
            campaign.failed_count += 1
            await session.commit()
            _publish_update(
                campaign.id,
                {
                    "type": "message_failed",
                    "message_id": str(message.id),
                    "contact_id": str(contact.id),
                    "status": message.status,
                    "reason": message.failure_reason,
                },
            )
            return False


def _compute_interval(base_interval: int, randomize: bool) -> float:
    if base_interval <= 0:
        return 0.0
    if not randomize:
        return float(base_interval)
    lower = max(base_interval * 0.8, 0.5)
    upper = max(base_interval * 1.2, lower)
    return random.uniform(lower, upper)


async def _is_campaign_running(campaign_id: UUID) -> bool:
    async with AsyncSessionLocal() as session:
        campaign = await session.get(Campaign, campaign_id)
        if campaign is None:
            return False
        return campaign.status == CampaignStatus.RUNNING


async def _dispatch_messages(
    campaign_id: UUID,
    message_ids: Sequence[UUID],
    settings: dict,
) -> None:
    interval = int(settings.get("interval_seconds") or 10)
    randomize_interval = bool(settings.get("randomize_interval"))
    retry_attempts = int(settings.get("retry_attempts") or 0)
    retry_interval = int(settings.get("retry_interval_seconds") or 60)

    for index, message_id in enumerate(message_ids):
        attempts = 0
        while True:
            if not await _is_campaign_running(campaign_id):
                return
            success = await _execute_send_message(message_id)
            if success or attempts >= retry_attempts:
                break
            attempts += 1
            await asyncio.sleep(max(retry_interval, 1))

        if not await _is_campaign_running(campaign_id):
            return

        if index < len(message_ids) - 1:
            await asyncio.sleep(_compute_interval(interval, randomize_interval))


async def _finalize_campaign_if_complete(campaign_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        campaign = await session.get(Campaign, campaign_id)
        if campaign is None:
            return
        result = await session.execute(
            select(CampaignMessage.id).where(
                CampaignMessage.campaign_id == campaign.id,
                CampaignMessage.status.in_(
                    [MessageStatus.PENDING, MessageStatus.SENDING, MessageStatus.FAILED]
                ),
            )
        )
        remaining = result.all()
        if campaign.status == CampaignStatus.RUNNING and not remaining:
            await _update_campaign_status(
                session,
                campaign_id,
                CampaignStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc),
            )


@shared_task(name="campaign.start_dispatch")
def start_campaign_dispatch(campaign_id: str) -> None:
    """Inicia o dispatch de uma campanha (Celery task síncrona)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_start_campaign_dispatch(UUID(campaign_id)))
    except Exception as e:
        logger.exception(f"Erro no dispatch da campanha {campaign_id}: {e}")
        raise
    finally:
        # Aguardar todas as tarefas pendentes antes de fechar
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        finally:
            loop.close()


async def _start_campaign_dispatch(campaign_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        campaign = await session.get(Campaign, campaign_id)
        if campaign is None:
            logger.error("Campanha %s não encontrada para dispatch.", campaign_id)
            return
        if campaign.status not in {
            CampaignStatus.RUNNING,
            CampaignStatus.SCHEDULED,
            CampaignStatus.DRAFT,
        }:
            logger.info(
                "Campanha %s em estado %s não será processada.",
                campaign_id,
                campaign.status,
            )
            return

        if campaign.status != CampaignStatus.RUNNING:
            campaign.status = CampaignStatus.RUNNING
            campaign.started_at = datetime.now(timezone.utc)
            await session.commit()
            _publish_update(
                campaign.id,
                {
                    "type": "status",
                    "status": CampaignStatus.RUNNING,
                    "metadata": {"started_at": campaign.started_at},
                },
            )
            await session.refresh(campaign)

        settings_data = campaign.settings or {}
        message_ids = await _prepare_campaign_messages(session, campaign)

    await _dispatch_messages(campaign_id, message_ids, settings_data)
    await _finalize_campaign_if_complete(campaign_id)


@shared_task(name="campaign.resume_dispatch")
def resume_campaign_dispatch(campaign_id: str) -> None:
    """Retoma o dispatch de uma campanha (Celery task síncrona)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_resume_campaign_dispatch(UUID(campaign_id)))
    except Exception as e:
        logger.exception(f"Erro ao retomar dispatch da campanha {campaign_id}: {e}")
        raise
    finally:
        # Aguardar todas as tarefas pendentes antes de fechar
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        finally:
            loop.close()


async def _resume_campaign_dispatch(campaign_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        campaign = await session.get(Campaign, campaign_id)
        if campaign is None:
            return
        if campaign.status != CampaignStatus.RUNNING:
            return

        result = await session.execute(
            select(CampaignMessage.id)
            .where(
                CampaignMessage.campaign_id == campaign.id,
                CampaignMessage.status.in_(
                    [MessageStatus.PENDING, MessageStatus.FAILED]
                ),
            )
            .order_by(CampaignMessage.created_at.asc())
        )
        message_ids = [row[0] for row in result.all()]
        settings_data = campaign.settings or {}

    await _dispatch_messages(campaign_id, message_ids, settings_data)
    await _finalize_campaign_if_complete(campaign_id)


__all__ = ("start_campaign_dispatch", "resume_campaign_dispatch")


