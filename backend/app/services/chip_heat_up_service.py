"""
Serviço dedicado para gerenciar heat-up de chips em grupo.

Permite que múltiplos chips aqueçam conversando entre si,
com mensagens customizadas e controle de parada.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from fastapi import HTTPException, status

from app.models.chip import Chip, ChipStatus, ChipEventType
from app.models.user import User
from app.schemas.chip import ChipHeatUpGroupRequest, ChipHeatUpGroupResponse, ChipHeatUpStage
from app.services.notification_service import NotificationService, NotificationType
from app.services.audit_service import AuditService


# Mensagens padrão caso não sejam fornecidas customizadas
DEFAULT_MATURATION_MESSAGES = [
    "Oi! Tudo bem?",
    "Bom dia! Como vai?",
    "Boa tarde!",
    "E aí, tudo certo?",
    "Olá! Tudo bem com você?",
    "Ok, entendido!",
    "Perfeito, obrigado!",
    "Combinado então",
    "Pode deixar!",
    "Beleza, valeu!",
    "Conseguiu ver o documento?",
    "Recebeu o email?",
    "Tudo certo aí?",
    "Precisa de alguma coisa?",
    "Posso ajudar em algo?",
    "Sim, recebi!",
    "Tudo ok por aqui",
    "Não precisa, obrigado",
    "Já resolvi, valeu!",
    "Tudo certo, pode seguir",
]


class ChipHeatUpService:
    """Serviço para gerenciar aquecimento de chips em grupo."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def start_group_heat_up(
        self,
        user: User,
        request: ChipHeatUpGroupRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> ChipHeatUpGroupResponse:
        """
        Inicia aquecimento para um grupo de chips.
        
        Os chips vão conversar entre si seguindo o plano de aquecimento.
        
        Args:
            user: Usuário dono dos chips
            request: Dados do request (chip_ids, custom_messages)
            user_agent: User agent da requisição
            ip_address: IP da requisição
        
        Returns:
            Response com detalhes do grupo de aquecimento
        """
        # Validar permissão de aquecimento
        await self._ensure_maturation_allowed(user)
        
        # Validar que todos os chips pertencem ao usuário e estão conectados
        result = await self.session.execute(
            select(Chip).where(
                Chip.id.in_(request.chip_ids),
                Chip.user_id == user.id
            )
        )
        chips = result.scalars().all()
        
        if len(chips) != len(request.chip_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Um ou mais chips não foram encontrados."
            )
        
        # Verificar se todos estão conectados
        disconnected = [chip.alias for chip in chips if chip.status != ChipStatus.CONNECTED]
        if disconnected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Os seguintes chips não estão conectados: {', '.join(disconnected)}. Conecte todos antes de iniciar o aquecimento."
            )
        
        # Gerar ID do grupo
        group_id = uuid4()
        
        # Plano de aquecimento
        stages = self._build_heat_up_plan()
        
        # Mensagens (custom ou padrão)
        messages = request.custom_messages if request.custom_messages else DEFAULT_MATURATION_MESSAGES
        
        # Configurar cada chip do grupo
        for chip in chips:
            chip.status = ChipStatus.MATURING
            chip.last_activity_at = datetime.now(timezone.utc)
            
            extra = chip.extra_data.copy() if chip.extra_data else {}
            extra["heat_up"] = {
                "status": "in_progress",
                "group_id": str(group_id),
                "chip_ids": [str(cid) for cid in request.chip_ids],
                "plan": stages,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "current_phase": 1,
                "phase_started_at": datetime.now(timezone.utc).isoformat(),
                "messages_sent_in_phase": 0,
                "custom_messages": messages,
            }
            chip.extra_data = extra
            flag_modified(chip, "extra_data")
            
            # Adicionar evento
            from app.models.chip import ChipEvent
            event = ChipEvent(
                chip_id=chip.id,
                type=ChipEventType.SYSTEM,
                description=f"Entrou no grupo de aquecimento {group_id} com {len(chips)} chips.",
                extra_data={"group_id": str(group_id), "total_chips": len(chips)}
            )
            self.session.add(event)
        
        # Notificar usuário
        notifier = NotificationService(self.session)
        await notifier.create(
            user_id=user.id,
            title="Aquecimento em grupo iniciado",
            message=f"{len(chips)} chips entraram em aquecimento automático.",
            type_=NotificationType.INFO,
            extra_data={"group_id": str(group_id), "chip_count": len(chips)},
            auto_commit=False,
        )
        
        # Auditar
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="chip.heat_up_group_start",
            entity_type="chip_group",
            entity_id=str(group_id),
            description=f"Grupo de {len(chips)} chips iniciou aquecimento.",
            extra_data={"chip_ids": [str(c.id) for c in chips], "stages": stages},
            ip_address=ip_address,
            user_agent=user_agent,
            auto_commit=False,
        )
        
        await self.session.commit()
        
        # Preparar response
        stage_models = [ChipHeatUpStage(**stage) for stage in stages]
        recommended_total = sum(stage["duration_hours"] for stage in stages)
        
        return ChipHeatUpGroupResponse(
            group_id=group_id,
            chip_ids=request.chip_ids,
            message=f"Grupo de aquecimento iniciado com {len(chips)} chips.",
            stages=stage_models,
            recommended_total_hours=recommended_total,
            preview_messages=messages[:10],  # Primeiras 10 para preview
        )
    
    async def stop_heat_up(
        self,
        user: User,
        chip_id: UUID,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> dict:
        """
        Para o aquecimento de um chip.
        
        Args:
            user: Usuário dono do chip
            chip_id: ID do chip
            user_agent: User agent da requisição
            ip_address: IP da requisição
        
        Returns:
            Dicionário com mensagem de sucesso
        """
        # Buscar chip
        result = await self.session.execute(
            select(Chip).where(
                Chip.id == chip_id,
                Chip.user_id == user.id
            )
        )
        chip = result.scalar_one_or_none()
        
        if not chip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chip não encontrado."
            )
        
        if chip.status != ChipStatus.MATURING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chip não está em aquecimento."
            )
        
        # Parar aquecimento
        chip.status = ChipStatus.CONNECTED
        
        extra = chip.extra_data.copy() if chip.extra_data else {}
        if "heat_up" in extra:
            extra["heat_up"]["status"] = "stopped"
            extra["heat_up"]["stopped_at"] = datetime.now(timezone.utc).isoformat()
        chip.extra_data = extra
        flag_modified(chip, "extra_data")
        
        # Adicionar evento
        from app.models.chip import ChipEvent
        event = ChipEvent(
            chip_id=chip.id,
            type=ChipEventType.SYSTEM,
            description="Aquecimento parado manualmente.",
            extra_data={}
        )
        self.session.add(event)
        
        # Auditar
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="chip.heat_up_stop",
            entity_type="chip",
            entity_id=str(chip.id),
            description="Aquecimento parado manualmente.",
            extra_data={},
            ip_address=ip_address,
            user_agent=user_agent,
            auto_commit=False,
        )
        
        await self.session.commit()
        
        return {"message": f"Aquecimento do chip {chip.alias} parado com sucesso."}
    
    async def _ensure_maturation_allowed(self, user: User) -> None:
        """Verifica se o plano do usuário permite aquecimento."""
        await self.session.refresh(user, attribute_names=["plan"])
        features = user.plan.features if user.plan else {}
        allowed = features.get("chip_maturation")
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu plano não possui suporte ao aquecimento automático de chips.",
            )
    
    @staticmethod
    def _build_heat_up_plan() -> list[dict]:
        """Constrói plano padrão de aquecimento."""
        return [
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
            {
                "stage": 5,
                "duration_hours": 24,
                "messages_per_hour": 120,
                "description": "Habilite IA para respostas automáticas e priorize horários de maior engajamento.",
            },
        ]

