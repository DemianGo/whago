"""
Serviço para operações relacionadas a chips.
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Iterable
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.chip import Chip, ChipEvent, ChipEventType, ChipStatus
from ..models.plan import Plan, PlanTier
from ..models.user import User
from .notification_service import NotificationService, NotificationType
from .audit_service import AuditService
from .proxy_service import ProxyService
from ..middleware.proxy_limit_middleware import check_proxy_quota
from ..schemas.chip import (
    ChipCreate,
    ChipEventResponse,
    ChipHeatUpResponse,
    ChipHeatUpStage,
    ChipQrResponse,
    ChipResponse,
)
from .baileys_client import BaileysClient, get_baileys_client


logger = logging.getLogger("whago.chips")


class ChipService:
    def __init__(
        self,
        session: AsyncSession,
        baileys_client: BaileysClient | None = None,
    ):
        self.session = session
        self.baileys = baileys_client or get_baileys_client()

    async def list_chips(self, user: User) -> list[ChipResponse]:
        result = await self.session.execute(
            select(Chip).where(Chip.user_id == user.id).order_by(Chip.created_at.asc())
        )
        chips = result.scalars().all()
        return [ChipResponse.model_validate(chip) for chip in chips]

    async def get_chip(self, user: User, chip_id: UUID) -> ChipResponse:
        chip = await self._get_user_chip(user, chip_id)
        return ChipResponse.model_validate(chip)

    async def get_chip_events(self, user: User, chip_id: UUID) -> list[ChipEventResponse]:
        chip = await self._get_user_chip(user, chip_id)
        await self.session.refresh(chip, attribute_names=["events"])
        events = sorted(chip.events, key=lambda ev: ev.created_at, reverse=True)
        return [ChipEventResponse.model_validate(event) for event in events]

    async def create_chip(
        self,
        user: User,
        payload: ChipCreate,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> ChipResponse:
        await self._ensure_alias_unique(user, payload.alias)
        await self._enforce_plan_limits(user)
        
        # ✅ NOVO: Verificar quota de proxy
        await check_proxy_quota(user, self.session)

        fallback = False
        session_id: str | None = None
        proxy_url: str | None = None

        # ✅ NOVO: Criar chip primeiro para ter ID
        chip = Chip(
            user_id=user.id,
            alias=payload.alias,
            session_id=f"temp-{uuid4()}",  # Temporário
            status=ChipStatus.WAITING_QR,
            extra_data={
                "created_via": "api",
                "user_agent": user_agent,
                "ip": ip_address,
                "baileys_fallback": False,
            },
        )
        self.session.add(chip)
        await self.session.flush()

        # ✅ NOVO: Atribuir proxy ao chip (sticky session com chip.id)
        try:
            proxy_service = ProxyService(self.session)
            proxy_url = await proxy_service.assign_proxy_to_chip(chip)
            logger.info(f"Proxy atribuído ao chip {chip.id}: {proxy_url.split('@')[1] if '@' in proxy_url else 'mascarado'}")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Falha ao atribuir proxy ao chip {chip.id}: {exc}. Continuando sem proxy.")
            proxy_url = None

        # ✅ CRIAR SESSÃO COM SISTEMA ANTI-BLOCK
        try:
            # Determinar perfis baseado no plano do usuário
            await self.session.refresh(user, attribute_names=["plan"])
            
            timing_profile = "normal"  # Padrão
            activity_pattern = "balanced"  # Padrão
            preferred_manufacturer = None
            
            if user.plan:
                # Enterprise: perfil mais rápido e ativo
                if user.plan.tier == PlanTier.ENTERPRISE:
                    timing_profile = "fast"
                    activity_pattern = "corporate"
                    preferred_manufacturer = "Samsung"  # Devices mais comuns em corporativo
                # Business: balanceado
                elif user.plan.tier == PlanTier.BUSINESS:
                    timing_profile = "normal"
                    activity_pattern = "balanced"
                # Starter/Free: mais conservador
                else:
                    timing_profile = "casual"
                    activity_pattern = "casual"
            
            logger.info(
                f"Criando sessão com Anti-Block - Tenant: {user.id}, "
                f"Timing: {timing_profile}, Pattern: {activity_pattern}"
            )
            
            baileys_response = await self.baileys.create_session(
                alias=payload.alias,
                proxy_url=proxy_url,
                tenant_id=str(user.id),
                user_id=str(user.id),
                preferred_manufacturer=preferred_manufacturer,
                timing_profile=timing_profile,
                activity_pattern=activity_pattern
            )
            
            session_id = baileys_response.get("session_id") or baileys_response.get("sessionId")
            if not session_id:
                raise ValueError("Resposta do Baileys sem session_id.")
                
            # Logar informações do anti-block
            if "anti_block" in baileys_response:
                logger.info(f"Anti-Block aplicado: {baileys_response['anti_block']}")
                chip.extra_data["anti_block"] = baileys_response["anti_block"]
            
            if "fingerprint" in baileys_response:
                logger.info(f"Fingerprint: {baileys_response['fingerprint']}")
                chip.extra_data["fingerprint"] = baileys_response["fingerprint"]
                
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Falha ao criar sessão no Baileys para alias %s: %s. Aplicando fallback local.",
                payload.alias,
                exc,
            )
            fallback = True
            session_id = f"fallback-{uuid4()}"

        # Atualizar chip com session_id real
        chip.session_id = session_id
        chip.extra_data["baileys_fallback"] = fallback
        chip.extra_data["proxy_used"] = proxy_url is not None
        await self.session.flush()

        await self._add_event(
            chip,
            ChipEventType.SYSTEM,
            f"Chip criado e aguardando QR (sessão {session_id}).",
        )

        notifier = NotificationService(self.session)
        await notifier.create(
            user_id=user.id,
            title="Novo chip aguardando QR",
            message=f"O chip {payload.alias} foi criado e precisa ser conectado.",
            type_=NotificationType.INFO,
            extra_data={"chip_id": str(chip.id), "session_id": session_id},
            auto_commit=False,
        )
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="chip.create",
            entity_type="chip",
            entity_id=str(chip.id),
            description=f"Chip {payload.alias} criado.",
            extra_data={"session_id": session_id},
            ip_address=ip_address,
            user_agent=user_agent,
            auto_commit=False,
        )

        await self.session.commit()
        await self.session.refresh(chip)
        return ChipResponse.model_validate(chip)

    async def get_qr_code(self, user: User, chip_id: UUID) -> ChipQrResponse:
        chip = await self._get_user_chip(user, chip_id)
        data = await self.baileys.get_qr_code(chip.session_id)
        expires_raw = data.get("expires_at") or data.get("expiresAt")
        expires_at = None
        if isinstance(expires_raw, str):
            try:
                expires_at = datetime.fromisoformat(expires_raw)
            except ValueError:
                expires_at = None
        # Baileys returns 'qr_code', normalize to 'qr'
        qr_data = data.get("qr") or data.get("qr_code")
        return ChipQrResponse(qr=qr_data, expires_at=expires_at)

    async def delete_chip(self, user: User, chip_id: UUID) -> None:
        """
        Deleta um chip e sua sessão do Baileys.
        
        Fluxo correto:
        1. Se chip está conectado, desconecta primeiro
        2. Libera proxy (IP fica disponível)
        3. Deleta sessão do Baileys
        4. Deleta arquivos de sessão do disco
        5. Deleta registro do banco de dados
        """
        chip = await self._get_user_chip(user, chip_id)
        
        # Se chip está conectado, desconectar primeiro
        if chip.status == ChipStatus.CONNECTED:
            try:
                await self.baileys.disconnect_session(chip.session_id)
            except HTTPException as e:
                # Se retornar 404, a sessão já não existe no Baileys
                if e.status_code != 404:
                    raise
        
        # ✅ LIBERAR PROXY antes de deletar
        proxy_service = ProxyService(self.session)
        await proxy_service.release_proxy_from_chip(chip.id)
        
        # Deletar sessão do Baileys (remove do cache e desconecta)
        try:
            await self.baileys.delete_session(chip.session_id)
        except HTTPException as e:
            # Se retornar 404, a sessão já foi deletada ou nunca existiu
            if e.status_code != 404:
                raise
        
        # Deletar do banco de dados (cascade vai remover assignment)
        await self.session.delete(chip)
        await self.session.commit()

    async def disconnect_chip(
        self,
        user: User,
        chip_id: UUID,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> ChipResponse:
        chip = await self._get_user_chip(user, chip_id)
        await self.baileys.disconnect_session(chip.session_id)
        chip.status = ChipStatus.DISCONNECTED
        
        # ✅ LIBERAR PROXY - IP fica disponível para outro chip
        proxy_service = ProxyService(self.session)
        await proxy_service.release_proxy_from_chip(chip.id)
        
        await self._add_event(
            chip,
            ChipEventType.STATUS_CHANGE,
            "Chip desconectado manualmente pelo usuário.",
        )
        notifier = NotificationService(self.session)
        await notifier.create(
            user_id=user.id,
            title="Chip desconectado",
            message=f"O chip {chip.alias} foi desconectado.",
            type_=NotificationType.WARNING,
            extra_data={"chip_id": str(chip.id)},
            auto_commit=False,
        )
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="chip.disconnect",
            entity_type="chip",
            entity_id=str(chip.id),
            description=f"Chip {chip.alias} desconectado pelo usuário.",
            extra_data=None,
            ip_address=ip_address,
            user_agent=user_agent,
            auto_commit=False,
        )
        await self.session.commit()
        await self.session.refresh(chip)
        return ChipResponse.model_validate(chip)

    async def start_heat_up(
        self,
        user: User,
        chip_id: UUID,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> ChipHeatUpResponse:
        chip = await self._get_user_chip(user, chip_id)
        await self._ensure_maturation_allowed(user)
        stages = self._build_heat_up_plan(user.plan)

        chip.status = ChipStatus.MATURING
        chip.last_activity_at = datetime.utcnow()
        extra = chip.extra_data.copy() if chip.extra_data else {}
        extra["heat_up"] = {
            "status": "in_progress",
            "plan": stages,
            "started_at": datetime.utcnow().isoformat(),
        }
        chip.extra_data = extra

        await self._add_event(
            chip,
            ChipEventType.SYSTEM,
            "Plano de aquecimento iniciado.",
            {"plan": stages},
        )
        for stage in stages:
            await self._add_event(
                chip,
                ChipEventType.INFO,
                f"Estágio {stage['stage']}: {stage['messages_per_hour']} msgs/h por {stage['duration_hours']}h.",
                {"stage": stage},
            )

        notifier = NotificationService(self.session)
        await notifier.create(
            user_id=user.id,
            title="Heat-up iniciado",
            message=f"O chip {chip.alias} entrou em aquecimento automático.",
            type_=NotificationType.INFO,
            extra_data={"chip_id": str(chip.id)},
            auto_commit=False,
        )
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="chip.heat_up_start",
            entity_type="chip",
            entity_id=str(chip.id),
            description="Plano de aquecimento automático iniciado.",
            extra_data={"stages": stages},
            ip_address=ip_address,
            user_agent=user_agent,
            auto_commit=False,
        )
        await self.session.commit()
        await self.session.refresh(chip)

        stage_models = [ChipHeatUpStage(**stage) for stage in stages]
        recommended_total = sum(stage["duration_hours"] for stage in stages)
        return ChipHeatUpResponse(
            chip_id=chip.id,
            message="Plano de aquecimento iniciado com sucesso.",
            stages=stage_models,
            recommended_total_hours=recommended_total,
        )

    async def _get_user_chip(self, user: User, chip_id: UUID) -> Chip:
        chip = await self.session.get(Chip, chip_id)
        if not chip or chip.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chip não encontrado.",
            )
        return chip

    async def _ensure_alias_unique(self, user: User, alias: str) -> None:
        result = await self.session.execute(
            select(func.count(Chip.id)).where(
                Chip.user_id == user.id,
                func.lower(Chip.alias) == alias.lower(),
            )
        )
        if result.scalar_one() > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um chip com esse apelido.",
            )

    async def _enforce_plan_limits(self, user: User) -> None:
        await self.session.refresh(user, attribute_names=["plan"])
        max_chips = self._get_plan_max_chips(user.plan)
        result = await self.session.execute(
            select(func.count(Chip.id)).where(Chip.user_id == user.id)
        )
        current = result.scalar_one()
        if current >= max_chips:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Limite de chips do plano atingido.",
            )

    @staticmethod
    def _get_plan_max_chips(plan: Plan | None) -> int:
        if not plan:
            return 1
        return plan.max_chips or 1

    async def _ensure_maturation_allowed(self, user: User) -> None:
        await self.session.refresh(user, attribute_names=["plan"])
        features = user.plan.features if user.plan else {}
        allowed = features.get("chip_maturation")
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu plano não possui suporte ao aquecimento automático de chips.",
            )

    @staticmethod
    def _build_heat_up_plan(plan: Plan | None) -> list[dict]:
        base_plan = [
            {
                "stage": 1,
                "duration_hours": 4,
                "messages_per_hour": 20,
                "description": "Envie apenas mensagens de confirmação e saudações para contatos internos.",
            },
            {
                "stage": 2,
                "duration_hours": 8,
                "messages_per_hour": 40,
                "description": "Ative pequenos grupos de clientes com respostas rápidas e monitoradas.",
            },
            {
                "stage": 3,
                "duration_hours": 12,
                "messages_per_hour": 60,
                "description": "Escalone para listas segmentadas utilizando templates aprovados.",
            },
            {
                "stage": 4,
                "duration_hours": 24,
                "messages_per_hour": 80,
                "description": "Libere campanhas completas mantendo intervalos mínimos e monitoramento.",
            },
        ]

        if plan and plan.tier == PlanTier.ENTERPRISE:
            base_plan.append(
                {
                    "stage": 5,
                    "duration_hours": 24,
                    "messages_per_hour": 120,
                    "description": "Habilite IA para respostas automáticas e priorize horários de maior engajamento.",
                }
            )
        return base_plan

    async def _add_event(
        self,
        chip: Chip,
        event_type: ChipEventType,
        description: str,
        extra: dict | None = None,
    ) -> None:
        event = ChipEvent(
            chip_id=chip.id,
            type=event_type,
            description=description,
            extra_data=extra or {},
        )
        self.session.add(event)
        await self.session.flush()


__all__ = ("ChipService",)


