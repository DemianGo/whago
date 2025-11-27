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
from .waha_client import WAHAClient, get_waha_client
from .waha_container_manager import WahaContainerManager, get_waha_container_manager


logger = logging.getLogger("whago.chips")


class ChipService:
    def __init__(
        self,
        session: AsyncSession,
        waha_client: WAHAClient | None = None,
        container_manager: WahaContainerManager | None = None,
    ):
        self.session = session
        self.waha = waha_client or get_waha_client()
        self.container_manager = container_manager or get_waha_container_manager()
        self.waha_client_cache: dict[str, WAHAClient] = {}  # user_id -> WAHAClient

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
            },
        )
        self.session.add(chip)
        await self.session.flush()

        # ✅ NOVO: Atribuir proxy ao chip (sticky session com chip.id)
        # DESATIVADO TEMPORARIAMENTE PARA DIAGNÓSTICO DE QR CODE
        proxy_url = None
        # try:
        #     proxy_service = ProxyService(self.session)
        #     proxy_url = await proxy_service.assign_proxy_to_chip(chip)
        #     logger.info(f"Proxy atribuído ao chip {chip.id}: {proxy_url.split('@')[1] if '@' in proxy_url else 'mascarado'}")
        # except Exception as exc:  # noqa: BLE001
        #     logger.warning(f"Falha ao atribuir proxy ao chip {chip.id}: {exc}. Continuando sem proxy.")
        #     proxy_url = None

        # ✅ CRIAR CONTAINER WAHA PLUS E SESSÃO
        try:
            # 1. Garantir que usuário tem container WAHA Plus
            logger.info(f"Verificando/criando container WAHA Plus para user {user.id}")
            container = await self.container_manager.get_user_container(str(user.id))
            
            if not container:
                logger.info(f"Container não existe, criando novo para user {user.id}")
                container = await self.container_manager.create_user_container(str(user.id))
                logger.info(
                    f"Container WAHA Plus criado: {container['container_name']} "
                    f"(Porta: {container['port']})"
                )
            else:
                logger.info(f"Container existente encontrado: {container['container_name']}")
            
            # 2. Obter cliente WAHA específico do container do usuário
            waha_client = await self._get_waha_client_for_user(str(user.id))
            
            # 3. Criar sessão no WAHA Plus (nome único por chip)
            session_name = f"chip_{chip.id}"
            
            logger.info(
                f"Criando sessão WAHA Plus - User: {user.id}, "
                f"Chip: {chip.id}, Alias: {payload.alias}, "
                f"Proxy: {'Sim' if proxy_url else 'Não'}, "
                f"Container: {container['container_name']}"
            )
            
            # Criar sessão com proxy
            from .waha_client import WAHAClient
            
            waha_response = await waha_client.create_session(
                alias=session_name,
                name=session_name,
                proxy_url=proxy_url,
                tenant_id=str(user.id),
                user_id=str(user.id),
            )
            
            # Sessão já inicia automaticamente no create_session
            session_id = session_name  # WAHA Plus usa nome da sessão como ID
                
            # Logar informações da sessão WAHA
            logger.info(
                f"Sessão WAHA Plus criada e iniciada: {session_id} | "
                f"Status: {waha_response.get('status')} | "
                f"Container: {container['container_name']}"
            )
            
            chip.extra_data["waha_plus_container"] = container['container_name']
            chip.extra_data["waha_plus_port"] = container['port']
            chip.extra_data["waha_session"] = session_name
            chip.extra_data["waha_status"] = waha_response.get("status")
            chip.extra_data["proxy_enabled"] = bool(proxy_url)
            chip.extra_data["fingerprint"] = waha_response.get("fingerprint")  # Salvar fingerprint usado
            
            # ✅ Marcar extra_data como modificado para o SQLAlchemy detectar as mudanças
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(chip, "extra_data")
            
            # Atualizar chip com session_id real
            chip.session_id = session_name
            chip.extra_data["proxy_used"] = proxy_url is not None
            
            # ✅ Marcar extra_data como modificado novamente
            flag_modified(chip, "extra_data")
            await self.session.flush()
                
        except Exception as exc:  # noqa: BLE001
            # SOFT-FAIL: Se falhar ao criar sessão (ex: container iniciando), não abortar criação do chip.
            # O sistema tentará criar a sessão novamente ao buscar o QR Code.
            logger.warning(
                "Sessão WAHA não criada imediatamente para alias %s (container iniciando?): %s",
                payload.alias,
                exc,
            )
            
            # Garantir que session_id está definido para tentativas futuras
            if not chip.session_id or chip.session_id.startswith("temp-"):
                chip.session_id = session_name
            
            chip.extra_data["waha_status"] = "STARTING"
            chip.extra_data["waha_plus_container"] = container['container_name']
            chip.extra_data["waha_session"] = session_name
            chip.extra_data["proxy_enabled"] = bool(proxy_url)
            chip.extra_data["proxy_used"] = proxy_url is not None
            
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(chip, "extra_data")
            await self.session.flush()

        await self._add_event(
            chip,
            ChipEventType.SYSTEM,
            f"Chip criado e aguardando QR (sessão {chip.session_id}).",
        )

        notifier = NotificationService(self.session)
        await notifier.create(
            user_id=user.id,
            title="Novo chip aguardando QR",
            message=f"O chip {payload.alias} foi criado e precisa ser conectado.",
            type_=NotificationType.INFO,
            extra_data={"chip_id": str(chip.id), "session_id": chip.session_id},
            auto_commit=False,
        )
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="chip.create",
            entity_type="chip",
            entity_id=str(chip.id),
            description=f"Chip {payload.alias} criado.",
            extra_data={"session_id": chip.session_id},
            ip_address=ip_address,
            user_agent=user_agent,
            auto_commit=False,
        )

        await self.session.commit()
        await self.session.refresh(chip)
        return ChipResponse.model_validate(chip)

    async def get_qr_code(self, user: User, chip_id: UUID) -> ChipQrResponse:
        chip = await self._get_user_chip(user, chip_id)
        
        # Obter cliente WAHA do container do usuário
        waha_client = await self._get_waha_client_for_user(str(user.id))
        
        # session_id = chip_{chip_id}
        session_name = chip.extra_data.get("waha_session", f"chip_{chip.id}")
        
        data = await waha_client.get_qr_code(session_name)
        
        # ✅ LAZY CREATION: Se sessão não existe (ex: falhou na criação do chip), criar agora
        if data.get("status") == "NOT_FOUND":
            logger.info(f"Sessão {session_name} não encontrada no WAHA. Tentando recriar (Lazy Creation)...")
            try:
                # Obter proxy se houver
                proxy_service = ProxyService(self.session)
                proxy_url = await proxy_service.get_chip_proxy_url(chip.id)
                
                # Criar sessão
                await waha_client.create_session(
                    alias=session_name,
                    proxy_url=proxy_url,
                    tenant_id=str(user.id),
                    user_id=str(user.id),
                )
                
                # Aguardar brevemente e tentar buscar QR de novo
                import asyncio
                await asyncio.sleep(1)
                data = await waha_client.get_qr_code(session_name)
                
            except Exception as e:
                logger.error(f"Falha na recriação lazy da sessão {session_name}: {e}")
                # Retornar erro ou status STARTING para frontend tentar de novo
                data = {"status": "STARTING", "message": "Tentando criar sessão..."}
        
        # WAHA Plus retorna QR code diretamente como base64 PNG
        qr_data = data.get("qr_code") or data.get("qr")
        expires_at = None  # WAHA Plus não fornece expiração explícita
        
        logger.info(
            f"QR Code obtido para chip {chip_id} | "
            f"Container: {chip.extra_data.get('waha_plus_container')} | "
            f"Status: {data.get('status')}"
        )
        
        return ChipQrResponse(
            qr=qr_data, 
            expires_at=expires_at,
            status=data.get("status"),
            message=data.get("message")
        )

    async def delete_chip(self, user: User, chip_id: UUID) -> None:
        """
        Deleta um chip e sua sessão WAHA Plus.
        
        Fluxo correto:
        1. Se chip está conectado, desconecta primeiro
        2. Libera proxy (IP fica disponível)
        3. Deleta sessão do WAHA Plus
        4. Deleta registro do banco de dados
        """
        chip = await self._get_user_chip(user, chip_id)
        
        # Obter cliente WAHA do container do usuário
        try:
            waha_client = await self._get_waha_client_for_user(str(user.id))
            session_name = chip.extra_data.get("waha_session", f"chip_{chip.id}")
            
            # Deletar sessão do WAHA Plus
            await waha_client.delete_session(session_name)
            logger.info(
                f"Sessão WAHA Plus deletada: {session_name} | "
                f"Container: {chip.extra_data.get('waha_plus_container')}"
            )
        except Exception as e:
            logger.warning(f"Erro ao deletar sessão WAHA {chip.session_id}: {e}")
        
        # ✅ LIBERAR PROXY antes de deletar
        proxy_service = ProxyService(self.session)
        await proxy_service.release_proxy_from_chip(chip.id)
        
        # Deletar do banco de dados (cascade vai remover assignment)
        await self.session.delete(chip)
        await self.session.commit()
        
        # ✅ VERIFICAR SE O USUÁRIO AINDA TEM CHIPS
        # Se não tiver mais nenhum chip, remover o container para economizar recursos
        result = await self.session.execute(
            select(func.count(Chip.id)).where(Chip.user_id == user.id)
        )
        remaining_chips = result.scalar_one()
        
        if remaining_chips == 0:
            logger.info(f"Usuário {user.id} não possui mais chips. Removendo container WAHA Plus para liberar recursos.")
            try:
                await self.container_manager.delete_user_container(str(user.id))
            except Exception as e:
                logger.error(f"Erro ao remover container ocioso do usuário {user.id}: {e}")

    async def reconnect_chip(
        self,
        user: User,
        chip_id: UUID,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> ChipResponse:
        """
        Reconecta um chip desconectado:
        1. Deleta sessão WAHA antiga (se existir)
        2. Cria nova sessão WAHA
        3. Atualiza status para WAITING_QR
        4. Registra eventos
        """
        # Capture IDs early to avoid expiration issues after commits
        user_id_str = str(user.id)
        user_id_uuid = user.id

        chip = await self._get_user_chip(user, chip_id)
        
        # Obter cliente WAHA do container do usuário
        waha_client = await self._get_waha_client_for_user(user_id_str)
        session_name = chip.extra_data.get("waha_session", f"chip_{chip.id}")
        
        # 1. Deletar sessão antiga (se existir)
        old_session_name = chip.extra_data.get("waha_session", f"chip_{chip.id}")
        try:
            await waha_client.delete_session(old_session_name)
            logger.info(f"Sessão WAHA antiga deletada: {old_session_name}")
        except Exception as e:
            logger.warning(f"Sessão antiga não encontrada ou erro ao deletar: {e}")
        
        # 2. ROTACIONAR PROXY (Garantir IP novo/funcional)
        # Se o usuário está reconectando, é provável que a conexão atual (Proxy) esteja ruim.
        # Vamos liberar o proxy atual e solicitar um novo, imitando o comportamento de "Excluir e Adicionar Novo".
        proxy_service = ProxyService(self.session)
        
        # Tentar liberar proxy atual se existir
        try:
            await proxy_service.release_proxy_from_chip(chip.id)
            logger.info(f"Proxy antigo liberado para o chip {chip.id}")
        except Exception as e:
            logger.warning(f"Erro ao liberar proxy antigo: {e}")

        # Atribuir novo proxy
        try:
            proxy_url = await proxy_service.assign_proxy_to_chip(chip)
            logger.info(f"Novo proxy atribuído ao chip {chip.id} para reconexão")
            
            # 🔄 REFRESH CRÍTICO: O proxy_service.assign fez commit, o que pode ter expirado o objeto chip.
            # Vamos recarregar via query direta para evitar MissingGreenlet
            result = await self.session.execute(select(Chip).where(Chip.id == chip_id))
            chip = result.scalar_one()
            
        except Exception as exc:
            logger.error(f"Falha crítica ao atribuir proxy na reconexão: {exc}")
            # Tentar rollback para salvar a sessão se possível
            try:
                await self.session.rollback()
                result = await self.session.execute(select(Chip).where(Chip.id == chip_id))
                chip = result.scalar_one()
            except:
                pass
            proxy_url = None
        
        # 3. Criar nova sessão WAHA com nome ÚNICO para evitar conflito de cache
        # Adicionamos um sufixo curto (timestamp) para garantir uma sessão limpa no WAHA
        import time
        timestamp_suffix = int(time.time()) % 100000  # Últimos 5 dígitos
        session_name = f"chip_{chip.id}_{timestamp_suffix}"

        # Pequeno delay para garantir estabilidade
        import asyncio
        await asyncio.sleep(1.0)

        try:
            waha_response = await waha_client.create_session(
                alias=session_name,
                name=session_name,
                proxy_url=proxy_url,
                tenant_id=user_id_str,
                user_id=user_id_str,
                engine="noweb", # Forçar NOWEB explicitamente
            )
            logger.info(f"Nova sessão WAHA criada: {session_name}")
            chip.extra_data["waha_status"] = waha_response.get("status")
            chip.extra_data["fingerprint"] = waha_response.get("fingerprint")
        except Exception as exc:
            logger.warning(f"Erro ao recriar sessão WAHA {session_name} (Soft-Fail): {exc}")
            chip.extra_data["waha_status"] = "STARTING"
        
        # 4. Atualizar status DO CHIP
        chip.status = ChipStatus.WAITING_QR
        chip.phone_number = None
        chip.connected_at = None
        chip.extra_data["waha_session"] = session_name
        chip.extra_data["proxy_enabled"] = bool(proxy_url)
        chip.extra_data["proxy_used"] = proxy_url is not None
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(chip, "extra_data")
        await self.session.flush()  # Persistir mudanças antes de adicionar eventos
        
        await self._add_event(
            chip,
            ChipEventType.STATUS_CHANGE,
            "Chip reconectado - aguardando QR Code.",
        )
        
        notifier = NotificationService(self.session)
        await notifier.create(
            user_id=user_id_uuid,
            title="Chip reconectando",
            message=f"O chip {chip.alias} está aguardando novo QR Code.",
            type_=NotificationType.INFO,
            extra_data={"chip_id": str(chip.id)},
            auto_commit=False,
        )
        
        audit = AuditService(self.session)
        await audit.record(
            user_id=user_id_uuid,
            action="chip.reconnect",
            entity_type="chip",
            entity_id=str(chip.id),
            description=f"Chip {chip.alias} reconectado pelo usuário.",
            extra_data={"session_name": session_name},
            ip_address=ip_address,
            user_agent=user_agent,
            auto_commit=False,
        )
        
        await self.session.commit()
        await self.session.refresh(chip)
        return ChipResponse.model_validate(chip)

    async def disconnect_chip(
        self,
        user: User,
        chip_id: UUID,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> ChipResponse:
        chip = await self._get_user_chip(user, chip_id)
        
        # Obter cliente WAHA do container do usuário
        try:
            waha_client = await self._get_waha_client_for_user(str(user.id))
            session_name = chip.extra_data.get("waha_session", f"chip_{chip.id}")
            
            # Parar sessão no WAHA Plus
            await waha_client.stop_session(session_name)
            logger.info(
                f"Sessão WAHA Plus parada: {session_name} | "
                f"Container: {chip.extra_data.get('waha_plus_container')}"
            )
        except Exception as e:
            logger.warning(f"Erro ao parar sessão WAHA {chip.session_id}: {e}")
        
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
            "current_phase": 1,
            "phase_started_at": datetime.utcnow().isoformat(),
            "messages_sent_in_phase": 0,
        }
        chip.extra_data = extra
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(chip, "extra_data")

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

    async def _get_waha_client_for_user(self, user_id: str) -> WAHAClient:
        """
        Obtém ou cria cliente WAHA específico para o container do usuário.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            WAHAClient: Cliente configurado para o container do usuário
        """
        # Cache para evitar recriar cliente
        if user_id in self.waha_client_cache:
            return self.waha_client_cache[user_id]
        
        # Obter informações do container
        container = await self.container_manager.get_user_container(user_id)
        
        if not container:
            raise RuntimeError(f"Container WAHA Plus não encontrado para user {user_id}")
        
        # Criar cliente específico para este container
        waha_client = WAHAClient(
            base_url=container["base_url"],
            api_key=container["api_key"]
        )
        
        # Cachear
        self.waha_client_cache[user_id] = waha_client
        
        logger.info(
            f"Cliente WAHA criado para user {user_id}: "
            f"{container['base_url']} (Container: {container['container_name']})"
        )
        
        return waha_client

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


