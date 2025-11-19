"""
Serviço responsável pelas operações com campanhas.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from uuid import UUID, uuid4
from contextlib import suppress

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tasks.campaign_tasks import (
    resume_campaign_dispatch,
    start_campaign_dispatch,
    _start_campaign_dispatch,
)
from ..config import settings
from ..core.redis import get_redis_client
from ..models.campaign import (
    Campaign,
    CampaignContact,
    CampaignMedia,
    CampaignMessage,
    CampaignStatus,
    CampaignType,
    MessageStatus,
)
from ..models.chip import Chip
from ..models.plan import PlanTier
from ..models.user import User
from .notification_service import NotificationService, NotificationType
from .audit_service import AuditService
from .webhook_service import WebhookEvent, WebhookService
from ..schemas.campaign import (
    CampaignActionResponse,
    CampaignCreate,
    CampaignDetail,
    CampaignMediaResponse,
    CampaignMessageResponse,
    CampaignSettings,
    CampaignSummary,
    CampaignUpdate,
    ContactUploadResponse,
)

logger = logging.getLogger("whago.campaigns")

MEDIA_SUBDIR = "campaigns"


class CampaignService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _media_directory(self, campaign_id: UUID) -> Path:
        base_dir = Path(settings.media_root)
        campaign_dir = base_dir / MEDIA_SUBDIR / str(campaign_id)
        campaign_dir.mkdir(parents=True, exist_ok=True)
        return campaign_dir

    def _media_to_schema(self, campaign_id: UUID, media: CampaignMedia) -> CampaignMediaResponse:
        return CampaignMediaResponse(
            id=media.id,
            original_name=media.original_name,
            stored_name=media.stored_name,
            content_type=media.content_type,
            size_bytes=media.size_bytes,
            created_at=media.created_at,
            url=f"/api/v1/campaigns/{campaign_id}/media/{media.id}",
        )

    async def _build_campaign_detail(self, campaign: Campaign) -> CampaignDetail:
        await self.session.refresh(campaign, attribute_names=["media"])
        detail = CampaignDetail.model_validate(campaign)
        detail.media = [self._media_to_schema(campaign.id, media) for media in campaign.media]
        return detail

    async def list_campaigns(self, user: User) -> list[CampaignSummary]:
        result = await self.session.execute(
            select(Campaign)
            .where(Campaign.user_id == user.id)
            .order_by(Campaign.created_at.desc())
        )
        campaigns = result.scalars().all()
        return [CampaignSummary.model_validate(c) for c in campaigns]

    async def get_campaign(self, user: User, campaign_id: UUID) -> CampaignDetail:
        campaign = await self._get_user_campaign(user, campaign_id)
        return await self._build_campaign_detail(campaign)

    async def create_campaign(
        self,
        user: User,
        data: CampaignCreate,
    ) -> CampaignDetail:
        db_user = await self._get_user_with_plan(user)
        self._ensure_campaign_type_allowed(db_user, data.type)
        if data.type == CampaignType.AB_TEST and not data.message_template_b:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campanhas A/B Test exigem a segunda variação de mensagem.",
            )
        if data.scheduled_for is not None:
            self._ensure_scheduling_allowed(db_user)

        settings = self._normalize_settings(db_user, data.settings, data.type)
        await self._validate_chip_limits(db_user, settings.chip_ids)

        campaign = Campaign(
            user_id=db_user.id,
            name=data.name,
            description=data.description,
            type=data.type,
            status=CampaignStatus.SCHEDULED if data.scheduled_for else CampaignStatus.DRAFT,
            message_template=data.message_template,
            message_template_b=data.message_template_b,
            settings=settings.model_dump(mode="json"),
            scheduled_for=data.scheduled_for,
        )
        self.session.add(campaign)
        try:
            await self.session.flush()
        except Exception as e:
            if "uq_campaigns_user_name" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Você já possui uma campanha com o nome '{data.name}'. Por favor, escolha outro nome.",
                )
            raise
        notifier = NotificationService(self.session)
        await notifier.create(
            user_id=db_user.id,
            title="Campanha criada",
            message=f"{campaign.name} foi criada com status {campaign.status.value}.",
            type_=NotificationType.SUCCESS,
            extra_data={"campaign_id": str(campaign.id)},
            auto_commit=False,
        )
        audit = AuditService(self.session)
        await audit.record(
            user_id=db_user.id,
            action="campaign.create",
            entity_type="campaign",
            entity_id=str(campaign.id),
            description="Campanha criada pelo usuário.",
            extra_data={"status": campaign.status.value},
            auto_commit=False,
        )
        await self.session.commit()
        await self.session.refresh(campaign)
        return await self._build_campaign_detail(campaign)

    async def update_campaign(
        self,
        user: User,
        campaign_id: UUID,
        data: CampaignUpdate,
    ) -> CampaignDetail:
        campaign = await self._get_user_campaign(user, campaign_id)
        db_user = await self._get_user_with_plan(user)
        
        # Permitir editar DRAFT, SCHEDULED e PAUSED
        # NÃO permitir editar RUNNING, COMPLETED ou CANCELLED
        if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED, CampaignStatus.PAUSED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pause a campanha antes de editá-la. Não é possível editar campanhas em andamento, completas ou canceladas.",
            )

        if data.name is not None:
            campaign.name = data.name
        if data.description is not None:
            campaign.description = data.description
        if data.message_template is not None:
            campaign.message_template = data.message_template
        if data.message_template_b is not None:
            campaign.message_template_b = data.message_template_b
        if data.scheduled_for is not None:
            if data.scheduled_for and data.scheduled_for < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data de agendamento não pode estar no passado.",
                )
            if data.scheduled_for is not None:
                self._ensure_scheduling_allowed(db_user)
            campaign.scheduled_for = data.scheduled_for
        if data.settings is not None:
            settings = self._normalize_settings(db_user, data.settings, campaign.type)
            await self._validate_chip_limits(db_user, settings.chip_ids)
            
            # Validar que os chips não estão sendo usados por outra campanha ativa
            # (DRAFT, SCHEDULED, RUNNING, PAUSED)
            chip_ids = settings.chip_ids or []
            if chip_ids:
                from app.models.chip import Chip, ChipStatus
                from uuid import UUID
                import logging
                logger = logging.getLogger("whago.campaign_validation")
                
                # ⚠️ IMPORTANTE: Converter todos os chip_ids para strings para comparação
                chip_ids_str = [str(chip_id) for chip_id in chip_ids]
                
                logger.info(f"Validando chips para campanha {campaign.id} | Status: {campaign.status} | Chips: {chip_ids_str}")
                
                # Buscar todas as campanhas ATIVAS do usuário (excluindo a atual)
                # ATIVAS = DRAFT, SCHEDULED, RUNNING, PAUSED
                # NÃO ATIVAS = COMPLETED, CANCELLED
                result_active = await self.session.execute(
                    select(Campaign).where(
                        Campaign.user_id == user.id,
                        Campaign.status.in_([
                            CampaignStatus.DRAFT,
                            CampaignStatus.SCHEDULED,
                            CampaignStatus.RUNNING,
                            CampaignStatus.PAUSED
                        ]),
                        Campaign.id != campaign.id
                    )
                )
                active_campaigns = result_active.scalars().all()
                
                logger.info(f"Encontradas {len(active_campaigns)} campanhas ATIVAS do usuário")
                
                # Extrair todos os chip_ids em uso por outras campanhas ATIVAS
                # ⚠️ IMPORTANTE: Converter chip_ids para strings
                chips_in_use = {}  # chip_id_str -> (campaign_name, campaign_status)
                for active_campaign in active_campaigns:
                    active_settings = active_campaign.settings or {}
                    active_chip_ids = active_settings.get("chip_ids") or []
                    # Converter para strings
                    active_chip_ids_str = [str(chip_id) for chip_id in active_chip_ids]
                    for chip_id_str in active_chip_ids_str:
                        if chip_id_str not in chips_in_use:
                            chips_in_use[chip_id_str] = []
                        chips_in_use[chip_id_str].append({
                            'name': active_campaign.name,
                            'status': active_campaign.status.value
                        })
                    if active_chip_ids_str:
                        logger.info(f"Campanha {active_campaign.name} ({active_campaign.status.value}) usa chips: {active_chip_ids_str}")
                
                logger.info(f"Chips em uso por campanhas ATIVAS: {list(chips_in_use.keys())}")
                
                # Verificar se algum chip da campanha atual já está em uso
                # ⚠️ IMPORTANTE: Agora ambos são strings
                chip_ids_set_str = set(chip_ids_str)
                chips_in_use_set = set(chips_in_use.keys())
                conflicting_chip_ids = chip_ids_set_str & chips_in_use_set
                
                logger.info(f"🔍 Comparando: {chip_ids_set_str} ∩ {chips_in_use_set} = {conflicting_chip_ids}")
                
                if conflicting_chip_ids:
                    logger.warning(f"❌ Chips conflitantes detectados: {conflicting_chip_ids}")
                    
                    # Buscar os aliases dos chips conflitantes (converter strings de volta para UUIDs)
                    conflicting_uuids = [UUID(chip_id_str) for chip_id_str in conflicting_chip_ids]
                    result_chip_aliases = await self.session.execute(
                        select(Chip.alias).where(Chip.id.in_(conflicting_uuids))
                    )
                    chip_aliases = [row[0] for row in result_chip_aliases.all()]
                    
                    # Montar mensagem detalhada
                    conflict_details = []
                    for chip_id_str in conflicting_chip_ids:
                        campaigns_using = chips_in_use[chip_id_str]
                        for camp in campaigns_using:
                            conflict_details.append(f"{camp['name']} ({camp['status']})")
                    
                    campaigns_str = ", ".join(conflict_details)
                    
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Chip já está sendo usado por outra campanha: {campaigns_str}. Um chip não pode ser usado por múltiplas campanhas simultaneamente.",
                    )
                
                logger.info(f"✅ Validação OK - Nenhum conflito de chips")
            
            campaign.settings = settings.model_dump(mode="json")

        await self.session.commit()
        await self.session.refresh(campaign)
        return await self._build_campaign_detail(campaign)

    async def delete_campaign(self, user: User, campaign_id: UUID) -> None:
        """
        Deleta uma campanha e todos os recursos associados:
        1. Cancela task do Celery (se rodando)
        2. Deleta mídias (arquivos + registros)
        3. Deleta mensagens
        4. Deleta contatos
        5. Deleta campanha
        
        IMPORTANTE: Chips, proxies e sessões WAHA não são deletados,
        pois são recursos do usuário que existem independentemente das campanhas.
        """
        campaign = await self._get_user_campaign(user, campaign_id)
        
        # Apenas campanhas em DRAFT, CANCELLED ou COMPLETED podem ser deletadas
        if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.CANCELLED, CampaignStatus.COMPLETED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Só é possível excluir campanhas em rascunho, canceladas ou completas. Cancele a campanha antes de excluir.",
            )
        
        logger.info(f"Iniciando deleção da campanha {campaign_id} (nome: {campaign.name})")
        
        # 1. Cancelar task do Celery se estiver rodando
        try:
            from tasks.celery_app import celery_app
            # Tentar revocar task do Celery
            task_name = f"campaign.start_dispatch"
            celery_app.control.revoke(str(campaign_id), terminate=True, signal='SIGKILL')
            logger.info(f"Task Celery revogada para campanha {campaign_id}")
        except Exception as e:
            logger.warning(f"Erro ao revogar task Celery: {e}")
        
        # 2. Deletar mídias (arquivos físicos + registros do banco)
        try:
            result_media = await self.session.execute(
                select(CampaignMedia).where(CampaignMedia.campaign_id == campaign.id)
            )
            medias = result_media.scalars().all()
            
            for media in medias:
                # Deletar arquivo físico
                media_path = Path(media.file_path)
                if media_path.exists():
                    media_path.unlink()
                    logger.info(f"Arquivo de mídia deletado: {media.file_path}")
                
                # Deletar registro
                await self.session.delete(media)
            
            logger.info(f"{len(medias)} mídias deletadas da campanha {campaign_id}")
        except Exception as e:
            logger.error(f"Erro ao deletar mídias: {e}")
        
        # 3. Deletar mensagens (em lote para performance)
        try:
            result = await self.session.execute(
                delete(CampaignMessage).where(CampaignMessage.campaign_id == campaign.id)
            )
            messages_deleted = result.rowcount or 0
            logger.info(f"{messages_deleted} mensagens deletadas da campanha {campaign_id}")
        except Exception as e:
            logger.error(f"Erro ao deletar mensagens: {e}")
        
        # 4. Deletar contatos (em lote para performance)
        try:
            result = await self.session.execute(
                delete(CampaignContact).where(CampaignContact.campaign_id == campaign.id)
            )
            contacts_deleted = result.rowcount or 0
            logger.info(f"{contacts_deleted} contatos deletados da campanha {campaign_id}")
        except Exception as e:
            logger.error(f"Erro ao deletar contatos: {e}")
        
        # 5. Registrar auditoria antes de deletar
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="campaign.delete",
            entity_type="campaign",
            entity_id=str(campaign.id),
            description=f"Campanha '{campaign.name}' deletada.",
            extra_data={
                "campaign_name": campaign.name,
                "status": campaign.status.value,
                "total_contacts": campaign.total_contacts,
                "sent_count": campaign.sent_count,
            },
            auto_commit=False,
        )
        
        # 6. Deletar campanha (cascade vai cuidar de relacionamentos restantes)
        await self.session.delete(campaign)
        await self.session.commit()
        
        logger.info(f"Campanha {campaign_id} deletada com sucesso")

    async def upload_contacts(
        self,
        user: User,
        campaign_id: UUID,
        file: UploadFile,
    ) -> ContactUploadResponse:
        campaign = await self._get_user_campaign(user, campaign_id)
        db_user = await self._get_user_with_plan(user)
        contacts_limit = self._get_contacts_limit(db_user)
        
        # Permitir upload em DRAFT, SCHEDULED e PAUSED
        # NÃO permitir em RUNNING, COMPLETED ou CANCELLED
        if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED, CampaignStatus.PAUSED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pause a campanha antes de importar novos contatos. Não é possível modificar campanhas em andamento, completas ou canceladas.",
            )

        content = await file.read()
        decoded = content.decode("utf-8-sig")
        
        # ✅ Detectar se o CSV tem cabeçalho válido
        lines = decoded.strip().split('\n')
        has_header = False
        
        if lines:
            first_line = lines[0].lower()
            # Verificar se a primeira linha contém palavras-chave de cabeçalho
            if any(keyword in first_line for keyword in ['numero', 'number', 'telefone', 'phone', 'nome', 'name']):
                has_header = True
        
        result_existing = await self.session.execute(
            select(func.count(CampaignContact.id)).where(CampaignContact.campaign_id == campaign.id)
        )
        existing_contacts = result_existing.scalar_one()

        total = 0
        valid = 0
        invalid = 0
        duplicated = 0
        preview: list[dict] = []
        seen_numbers: set[str] = set()
        detected_variables: set[str] = set()

        if has_header:
            # CSV com cabeçalho - usar DictReader
            reader = csv.DictReader(io.StringIO(decoded))
            
            for row in reader:
                total += 1
                number = (row.get("numero") or row.get("number") or row.get("telefone") or row.get("phone") or "").strip()
                if not number:
                    invalid += 1
                    continue
                
                normalized = self._normalize_phone(number)
                if not normalized:
                    invalid += 1
                    continue

                if normalized in seen_numbers:
                    duplicated += 1
                    continue

                if contacts_limit is not None and existing_contacts + valid + 1 > contacts_limit:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Limite de {contacts_limit} contatos por campanha atingido para o seu plano. "
                            "Considere remover contatos ou fazer upgrade de plano."
                        ),
                    )

                seen_numbers.add(normalized)
                name = (row.get("nome") or row.get("name") or "").strip() or None
                company = (row.get("empresa") or row.get("company") or "").strip() or None
                variables = {
                    key: value
                    for key, value in row.items()
                    if key not in {"numero", "number", "telefone", "phone", "nome", "name", "empresa", "company"}
                }
                variables = {k: v for k, v in variables.items() if v}
                if variables:
                    detected_variables.update(variables.keys())

                contact = CampaignContact(
                    campaign_id=campaign.id,
                    phone_number=normalized,
                    name=name,
                    company=company,
                    variables=variables or None,
                )
                self.session.add(contact)
                valid += 1

                if len(preview) < 10:
                    preview.append({"numero": normalized, "nome": name, "empresa": company})
        else:
            # CSV sem cabeçalho - processar cada campo como número de telefone
            reader = csv.reader(io.StringIO(decoded))
            
            for row in reader:
                # Cada campo da linha pode ser um número de telefone
                for field in row:
                    total += 1
                    number = field.strip()
                    if not number:
                        invalid += 1
                        continue
                    
                    normalized = self._normalize_phone(number)
                    if not normalized:
                        invalid += 1
                        continue

                    if normalized in seen_numbers:
                        duplicated += 1
                        continue

                    if contacts_limit is not None and existing_contacts + valid + 1 > contacts_limit:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                f"Limite de {contacts_limit} contatos por campanha atingido para o seu plano. "
                                "Considere remover contatos ou fazer upgrade de plano."
                            ),
                        )

                    seen_numbers.add(normalized)
                    
                    contact = CampaignContact(
                        campaign_id=campaign.id,
                        phone_number=normalized,
                        name=None,
                        company=None,
                        variables=None,
                    )
                    self.session.add(contact)
                    valid += 1

                    if len(preview) < 10:
                        preview.append({"numero": normalized, "nome": None, "empresa": None})

        result_total = await self.session.execute(
            select(func.count(CampaignContact.id)).where(CampaignContact.campaign_id == campaign.id)
        )
        campaign.total_contacts = result_total.scalar_one()
        await self.session.commit()

        await self._publish_event(
            campaign.id,
            {
                "type": "contacts_updated",
                "total_contacts": campaign.total_contacts,
                "added": valid,
            },
        )

        return ContactUploadResponse(
            total_processed=total,
            valid_contacts=valid,
            invalid_contacts=invalid,
            duplicated=duplicated,
            preview=preview,
            variables=sorted(detected_variables),
        )

    async def start_campaign(self, user: User, campaign_id: UUID) -> CampaignActionResponse:
        campaign = await self._get_user_campaign(user, campaign_id)
        db_user = await self._get_user_with_plan(user)
        self._ensure_campaign_type_allowed(db_user, campaign.type)
        if campaign.status == CampaignStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campanha já está em andamento.",
            )
        if campaign.status in {CampaignStatus.CANCELLED, CampaignStatus.COMPLETED, CampaignStatus.ERROR}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível iniciar uma campanha encerrada.",
            )

        audit = AuditService(self.session)

        result_contacts = await self.session.execute(
            select(func.count(CampaignContact.id)).where(CampaignContact.campaign_id == campaign.id)
        )
        total_contacts = result_contacts.scalar_one()
        if total_contacts == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campanha precisa ter contatos válidos antes de iniciar.",
            )

        settings_data = campaign.settings or {}
        chip_ids = settings_data.get("chip_ids") or []
        if not chip_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Configure ao menos um chip para a campanha.",
            )

        campaign.total_contacts = total_contacts

        remaining_to_send = max(total_contacts - campaign.sent_count, 0)
        if remaining_to_send == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não há mensagens pendentes para envio nesta campanha.",
            )

        await self._ensure_active_campaign_limit(db_user, campaign)
        await self._ensure_credit_balance(db_user, remaining_to_send)
        await self._ensure_monthly_limit(db_user, remaining_to_send)

        now = datetime.now(timezone.utc)

        # Validar chips conectados TANTO ao iniciar QUANTO ao retomar
        from app.models.chip import Chip, ChipStatus
        result_connected = await self.session.execute(
            select(func.count(Chip.id)).where(
                Chip.id.in_(chip_ids),
                Chip.status == ChipStatus.CONNECTED
            )
        )
        connected_chips = result_connected.scalar_one()
        
        if connected_chips == 0:
            if campaign.status == CampaignStatus.PAUSED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nenhum chip está conectado. Conecte pelo menos um chip antes de retomar a campanha.",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nenhum chip está conectado. Conecte pelo menos um chip antes de iniciar a campanha.",
                )
        
        # Validar que os chips não estão sendo usados por outra campanha ATIVA
        # Buscar todas as campanhas ATIVAS do usuário (excluindo a atual)
        result_active = await self.session.execute(
            select(Campaign).where(
                Campaign.user_id == user.id,
                Campaign.status.in_([
                    CampaignStatus.DRAFT,
                    CampaignStatus.SCHEDULED,
                    CampaignStatus.RUNNING,
                    CampaignStatus.PAUSED
                ]),
                Campaign.id != campaign.id
            )
        )
        active_campaigns = result_active.scalars().all()
        
        # Extrair todos os chip_ids em uso por outras campanhas ATIVAS
        # ⚠️ IMPORTANTE: Converter para strings para comparação
        chips_in_use = set()
        for active_campaign in active_campaigns:
            active_settings = active_campaign.settings or {}
            active_chip_ids = active_settings.get("chip_ids") or []
            # Converter para strings
            active_chip_ids_str = [str(chip_id) for chip_id in active_chip_ids]
            chips_in_use.update(active_chip_ids_str)
        
        # Verificar se algum chip da campanha atual já está em uso
        # ⚠️ IMPORTANTE: Converter chip_ids para strings
        chip_ids_str_set = set([str(chip_id) for chip_id in chip_ids])
        conflicting_chips_str = chip_ids_str_set & chips_in_use
        
        if conflicting_chips_str:
            # Buscar os aliases dos chips conflitantes para mensagem amigável
            # Converter strings de volta para UUIDs
            from uuid import UUID
            conflicting_uuids = [UUID(chip_id_str) for chip_id_str in conflicting_chips_str]
            result_chip_aliases = await self.session.execute(
                select(Chip.alias).where(Chip.id.in_(conflicting_uuids))
            )
            chip_aliases = [row[0] for row in result_chip_aliases.all()]
            chips_str = ", ".join(chip_aliases)
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Os seguintes chips já estão sendo usados por outra campanha: {chips_str}. Um chip não pode ser usado por múltiplas campanhas simultaneamente.",
            )

        if campaign.status == CampaignStatus.PAUSED:
            campaign.status = CampaignStatus.RUNNING
            await audit.record(
                user_id=user.id,
                action="campaign.resume",
                entity_type="campaign",
                entity_id=str(campaign.id),
                description="Campanha retomada após pausa.",
                extra_data=None,
                auto_commit=False,
            )
            await self.session.commit()
            resume_campaign_dispatch.delay(str(campaign.id))
            await self._publish_status(campaign.id, CampaignStatus.RUNNING, resumed_at=now)
            await self.session.refresh(campaign)
            return CampaignActionResponse(status=campaign.status, message="Campanha retomada.")

        if campaign.scheduled_for:
            eta = campaign.scheduled_for
            if eta.tzinfo is None:
                eta = eta.replace(tzinfo=timezone.utc)
            if eta > now:
                campaign.status = CampaignStatus.SCHEDULED
                campaign.started_at = None
                await audit.record(
                    user_id=user.id,
                    action="campaign.schedule",
                    entity_type="campaign",
                    entity_id=str(campaign.id),
                    description="Campanha agendada para execução futura.",
                    extra_data={"scheduled_for": eta.isoformat()},
                    auto_commit=False,
                )
                await self.session.commit()
                start_campaign_dispatch.apply_async((str(campaign.id),), eta=eta)
                await self._publish_status(
                    campaign.id,
                    CampaignStatus.SCHEDULED,
                    scheduled_for=eta,
                )
                await self.session.refresh(campaign)
                return CampaignActionResponse(
                    status=campaign.status,
                    message=f"Campanha agendada para {eta.isoformat()}",
                )

        campaign.status = CampaignStatus.RUNNING
        campaign.started_at = now
        await audit.record(
            user_id=user.id,
            action="campaign.start",
            entity_type="campaign",
            entity_id=str(campaign.id),
            description="Campanha iniciada para envio imediato.",
            extra_data={"remaining_contacts": remaining_to_send},
            auto_commit=False,
        )
        await self.session.commit()
        start_campaign_dispatch.delay(str(campaign.id))
        await self._publish_status(campaign.id, CampaignStatus.RUNNING, started_at=now)
        await self.session.refresh(campaign)
        await self._emit_webhook_event(
            db_user,
            WebhookEvent.CAMPAIGN_STARTED,
            {
                "campaign_id": str(campaign.id),
                "name": campaign.name,
                "status": campaign.status.value,
                "total_contacts": campaign.total_contacts,
                "remaining_to_send": remaining_to_send,
                "started_at": campaign.started_at.isoformat() if campaign.started_at else None,
            },
        )
        return CampaignActionResponse(status=campaign.status, message="Campanha iniciada.")

    async def dispatch_sync(self, user: User, campaign_id: UUID) -> CampaignActionResponse:
        if settings.environment.lower() == "production":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operação permitida apenas em ambientes não produtivos.",
            )
        campaign = await self._get_user_campaign(user, campaign_id)
        await _start_campaign_dispatch(campaign.id)
        await self.session.refresh(campaign)
        return CampaignActionResponse(status=campaign.status, message="Dispatch síncrono executado.")

    async def pause_campaign(self, user: User, campaign_id: UUID) -> CampaignActionResponse:
        """
        Pausa uma campanha em andamento:
        1. Revoga task do Celery (interrompe envios)
        2. Atualiza status para PAUSED
        
        IMPORTANTE: Mensagens pendentes permanecem pendentes (não são canceladas).
        """
        db_user = await self._get_user_with_plan(user)
        campaign = await self._get_user_campaign(user, campaign_id)
        if campaign.status != CampaignStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Só é possível pausar campanhas em andamento.",
            )

        # 1. Revogar task do Celery para interromper envios
        try:
            from tasks.celery_app import celery_app
            celery_app.control.revoke(str(campaign_id), terminate=True, signal='SIGKILL')
            logger.info(f"Task Celery revogada para pausar campanha {campaign_id}")
        except Exception as e:
            logger.warning(f"Erro ao revogar task Celery ao pausar: {e}")

        campaign.status = CampaignStatus.PAUSED
        audit = AuditService(self.session)
        paused_at = datetime.now(timezone.utc)
        await audit.record(
            user_id=user.id,
            action="campaign.pause",
            entity_type="campaign",
            entity_id=str(campaign.id),
            description="Campanha pausada pelo usuário.",
            extra_data=None,
            auto_commit=False,
        )
        await self.session.commit()
        await self._publish_status(campaign.id, CampaignStatus.PAUSED, paused_at=paused_at)
        await self.session.refresh(campaign)
        await self._emit_webhook_event(
            db_user,
            WebhookEvent.CAMPAIGN_PAUSED,
            {
                "campaign_id": str(campaign.id),
                "name": campaign.name,
                "status": campaign.status.value,
                "paused_at": paused_at.isoformat(),
            },
        )
        return CampaignActionResponse(status=campaign.status, message="Campanha pausada.")

    async def cancel_campaign(self, user: User, campaign_id: UUID) -> CampaignActionResponse:
        """
        Cancela uma campanha em andamento:
        1. Revoga task do Celery (para envios)
        2. Marca mensagens pendentes como falhas
        3. Atualiza status da campanha
        
        IMPORTANTE: Não libera chips/proxies, apenas interrompe envios.
        """
        db_user = await self._get_user_with_plan(user)
        campaign = await self._get_user_campaign(user, campaign_id)
        if campaign.status not in {CampaignStatus.RUNNING, CampaignStatus.PAUSED, CampaignStatus.SCHEDULED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campanha não está em estado que permita cancelamento.",
            )

        # 1. Revogar task do Celery imediatamente
        try:
            from tasks.celery_app import celery_app
            celery_app.control.revoke(str(campaign_id), terminate=True, signal='SIGKILL')
            logger.info(f"Task Celery revogada para campanha {campaign_id}")
        except Exception as e:
            logger.warning(f"Erro ao revogar task Celery ao cancelar: {e}")

        now = datetime.now(timezone.utc)
        update_result = await self.session.execute(
            update(CampaignMessage)
            .where(
                CampaignMessage.campaign_id == campaign.id,
                CampaignMessage.status.in_(
                    [MessageStatus.PENDING, MessageStatus.SENDING, MessageStatus.FAILED]
                ),
            )
            .values(
                status=MessageStatus.FAILED,
                failure_reason="Campanha cancelada pelo usuário.",
            )
        )
        affected = update_result.rowcount or 0
        campaign.failed_count += affected
        campaign.status = CampaignStatus.CANCELLED
        campaign.completed_at = now
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="campaign.cancel",
            entity_type="campaign",
            entity_id=str(campaign.id),
            description="Campanha cancelada pelo usuário.",
            extra_data={"messages_marked_failed": affected},
            auto_commit=False,
        )
        await self.session.commit()
        await self._publish_status(campaign.id, CampaignStatus.CANCELLED, cancelled_at=now)
        await self.session.refresh(campaign)
        await self._emit_webhook_event(
            db_user,
            WebhookEvent.CAMPAIGN_CANCELLED,
            {
                "campaign_id": str(campaign.id),
                "name": campaign.name,
                "status": campaign.status.value,
                "cancelled_at": now.isoformat(),
                "failed_messages": affected,
            },
        )
        return CampaignActionResponse(status=campaign.status, message="Campanha cancelada.")

    async def list_messages(
        self,
        user: User,
        campaign_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CampaignMessageResponse]:
        await self._get_user_campaign(user, campaign_id)
        result = await self.session.execute(
            select(CampaignMessage, CampaignContact.phone_number, Chip.alias)
            .join(CampaignContact, CampaignMessage.contact_id == CampaignContact.id)
            .join(Chip, CampaignMessage.chip_id == Chip.id, isouter=True)
            .where(CampaignMessage.campaign_id == campaign_id)
            .order_by(CampaignMessage.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = result.all()
        responses: list[CampaignMessageResponse] = []
        for message, phone_number, chip_alias in rows:
            payload = {
                "id": message.id,
                "contact_id": message.contact_id,
                "phone_number": phone_number,
                "status": message.status,
                "content": message.content,
                "failure_reason": message.failure_reason,
                "sent_at": message.sent_at,
                "delivered_at": message.delivered_at,
                "read_at": message.read_at,
                "created_at": message.created_at,
                "chip_id": message.chip_id,
                "chip_alias": chip_alias,
            }
            responses.append(CampaignMessageResponse.model_validate(payload))
        return responses

    async def list_media(self, user: User, campaign_id: UUID) -> list[CampaignMediaResponse]:
        campaign = await self._get_user_campaign(user, campaign_id)
        await self.session.refresh(campaign, attribute_names=["media"])
        return [self._media_to_schema(campaign.id, media) for media in campaign.media]

    async def upload_media(
        self,
        user: User,
        campaign_id: UUID,
        file: UploadFile,
    ) -> CampaignMediaResponse:
        if file is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum arquivo foi enviado.",
            )
        filename = file.filename or "arquivo"
        payload = await file.read()
        size = len(payload)
        if size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo enviado está vazio.",
            )
        max_bytes = settings.media_max_file_size_mb * 1024 * 1024
        if size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Arquivo excede o limite de {settings.media_max_file_size_mb}MB.",
            )
        allowed_types = set(settings.media_allowed_content_types or [])
        content_type = file.content_type or "application/octet-stream"
        if allowed_types and content_type not in allowed_types:
            allowed_readable = ", ".join(sorted(allowed_types))
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Tipo de arquivo não permitido. Formatos aceitos: {allowed_readable}.",
            )

        campaign = await self._get_user_campaign(user, campaign_id)
        directory = self._media_directory(campaign.id)
        extension = Path(filename).suffix
        stored_name = f"{uuid4().hex}{extension}" if extension else uuid4().hex
        file_path = directory / stored_name
        file_path.write_bytes(payload)

        media = CampaignMedia(
            campaign_id=campaign.id,
            original_name=filename,
            stored_name=stored_name,
            content_type=content_type,
            size_bytes=size,
        )
        self.session.add(media)
        await self.session.commit()
        await self.session.refresh(media)
        return self._media_to_schema(campaign.id, media)

    async def download_media(
        self,
        user: User,
        campaign_id: UUID,
        media_id: UUID,
    ) -> FileResponse:
        await self._get_user_campaign(user, campaign_id)
        media = await self._get_media_record(campaign_id, media_id)
        file_path = self._media_directory(campaign_id) / media.stored_name
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo de mídia não encontrado no armazenamento.",
            )
        return FileResponse(
            path=file_path,
            media_type=media.content_type,
            filename=media.original_name,
        )

    async def delete_media(
        self,
        user: User,
        campaign_id: UUID,
        media_id: UUID,
    ) -> None:
        await self._get_user_campaign(user, campaign_id)
        media = await self._get_media_record(campaign_id, media_id)
        file_path = self._media_directory(campaign_id) / media.stored_name
        await self.session.delete(media)
        await self.session.commit()
        if file_path.exists():
            with suppress(OSError):
                file_path.unlink()

    async def _get_user_campaign(self, user: User, campaign_id: UUID) -> Campaign:
        campaign = await self.session.get(Campaign, campaign_id)
        if not campaign or campaign.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campanha não encontrada.",
            )
        return campaign

    async def _get_user_with_plan(self, user: User) -> User:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.plan))
            .where(User.id == user.id)
        )
        db_user = result.scalar_one_or_none()
        if db_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado.",
            )
        return db_user

    def _ensure_campaign_type_allowed(self, user: User, campaign_type: CampaignType) -> None:
        if campaign_type == CampaignType.AB_TEST:
            if user.plan is None or user.plan.tier != PlanTier.ENTERPRISE:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Campanhas A/B Test estão disponíveis apenas no plano Enterprise.",
                )

    def _ensure_scheduling_allowed(self, user: User) -> None:
        features = self._get_plan_features(user)
        scheduling_allowed = bool(features.get("scheduling", False))
        if not scheduling_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu plano não permite agendamento de campanhas. Faça upgrade para liberar este recurso.",
            )

    def _get_plan_features(self, user: User) -> dict:
        if user.plan and user.plan.features:
            return user.plan.features
        return {}

    def _parse_limit_value(self, raw_value) -> int | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, bool):
            return 1 if raw_value else 0
        if isinstance(raw_value, (int, float)):
            return int(raw_value)
        if isinstance(raw_value, str):
            digits = "".join(ch for ch in raw_value if ch.isdigit())
            if digits:
                return int(digits)
        return None

    def _get_contacts_limit(self, user: User) -> int | None:
        features = self._get_plan_features(user)
        return self._parse_limit_value(features.get("contacts_per_list"))

    async def _ensure_active_campaign_limit(self, user: User, campaign: Campaign) -> None:
        features = self._get_plan_features(user)
        limit = self._parse_limit_value(features.get("campaigns_active"))
        if limit is None or limit <= 0:
            return

        result = await self.session.execute(
            select(func.count(Campaign.id)).where(
                Campaign.user_id == user.id,
                Campaign.id != campaign.id,
                Campaign.status.in_(
                    [CampaignStatus.RUNNING, CampaignStatus.SCHEDULED]
                ),
            )
        )
        active_count = result.scalar_one() or 0
        if active_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Você atingiu o limite de campanhas ativas para o seu plano. "
                    "Finalize uma campanha ativa ou faça upgrade para iniciar outra."
                ),
            )

    async def _ensure_credit_balance(self, user: User, messages_needed: int) -> None:
        if messages_needed <= 0:
            return
        if user.credits < messages_needed:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    f"Créditos insuficientes. São necessários {messages_needed} créditos e você possui "
                    f"{user.credits}. Compre créditos adicionais ou reduza a campanha."
                ),
            )

    async def _ensure_monthly_limit(self, user: User, messages_needed: int) -> None:
        if messages_needed <= 0:
            return
        plan = user.plan
        if plan is None or plan.monthly_messages <= 0:
            return

        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = await self.session.execute(
            select(func.count(CampaignMessage.id))
            .join(Campaign, CampaignMessage.campaign_id == Campaign.id)
            .where(
                Campaign.user_id == user.id,
                CampaignMessage.sent_at.is_not(None),
                CampaignMessage.sent_at >= month_start,
                CampaignMessage.status.in_(
                    [MessageStatus.SENT, MessageStatus.DELIVERED, MessageStatus.READ]
                ),
            )
        )
        messages_sent = result.scalar_one() or 0
        remaining = plan.monthly_messages - messages_sent
        if remaining < messages_needed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Limite mensal de mensagens do plano excedido. "
                    f"Disponível neste mês: {max(remaining, 0)} mensagem(ns). "
                    "Faça upgrade ou aguarde o próximo ciclo."
                ),
            )

    async def _publish_event(self, campaign_id: UUID, payload: dict) -> None:
        redis = get_redis_client()
        channel = f"{settings.redis_campaign_updates_channel}:{campaign_id}"
        try:
            await redis.publish(channel, json.dumps(payload, default=str))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao publicar evento da campanha %s: %s", campaign_id, exc)

    async def _emit_webhook_event(
        self,
        user: User,
        event: WebhookEvent,
        payload: dict,
    ) -> None:
        features = self._get_plan_features(user)
        if not features.get("webhooks"):
            return
        service = WebhookService(self.session)
        await service.dispatch(user_id=user.id, event=event, payload=payload)

    async def _publish_status(
        self,
        campaign_id: UUID,
        status: CampaignStatus,
        **metadata,
    ) -> None:
        await self._publish_event(
            campaign_id,
            {
                "type": "status",
                "status": status,
                "metadata": metadata,
            },
        )

    def _normalize_settings(
        self,
        user: User,
        settings: CampaignSettings | None,
        campaign_type: CampaignType,
    ) -> CampaignSettings:
        if settings is None:
            settings = CampaignSettings()
        if campaign_type != CampaignType.AB_TEST:
            settings.randomize_interval = bool(settings.randomize_interval)

        features = self._get_plan_features(user)
        min_interval = self._parse_limit_value(features.get("min_interval_seconds"))
        if min_interval is not None:
            settings.interval_seconds = max(settings.interval_seconds, min_interval)

        return settings

    async def _validate_chip_limits(self, user: User, chip_ids: Iterable[UUID]) -> None:
        chip_ids = list({chip_id for chip_id in chip_ids})
        if not chip_ids:
            return
        result = await self.session.execute(
            select(func.count(Chip.id)).where(
                Chip.user_id == user.id,
                Chip.id.in_(chip_ids),
            )
        )
        if result.scalar_one() != len(chip_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível validar os chips selecionados.",
            )

    def _normalize_phone(self, number: str) -> str | None:
        digits = "".join(filter(str.isdigit, number))
        if len(digits) == 13 and digits.startswith("55"):
            return digits
        if len(digits) == 11:
            return f"55{digits}"
        if len(digits) == 12 and digits.startswith("55"):
            return digits
        return None

    async def _get_media_record(self, campaign_id: UUID, media_id: UUID) -> CampaignMedia:
        result = await self.session.execute(
            select(CampaignMedia).where(
                CampaignMedia.id == media_id,
                CampaignMedia.campaign_id == campaign_id,
            )
        )
        media = result.scalar_one_or_none()
        if media is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo de mídia não encontrado.",
            )
        return media


__all__ = ("CampaignService",)


