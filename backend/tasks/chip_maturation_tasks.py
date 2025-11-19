"""
Celery tasks para aquecimento automático de chips.

Estratégia: Chips se aquecem conversando entre si, simulando comunicação
interna de uma equipe/empresa.
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.models.chip import Chip, ChipStatus
from app.models.user import User
from app.services.waha_container_manager import WahaContainerManager
from app.services.waha_client import WAHAClient
from tasks.celery_app import celery_app


# Templates de mensagens naturais para aquecimento
MATURATION_MESSAGES = {
    "greetings": [
        "Oi! Tudo bem?",
        "Bom dia! Como vai?",
        "Boa tarde!",
        "E aí, tudo certo?",
        "Olá! Tudo bem com você?",
    ],
    "confirmations": [
        "Ok, entendido!",
        "Perfeito, obrigado!",
        "Combinado então",
        "Pode deixar!",
        "Beleza, valeu!",
    ],
    "questions": [
        "Conseguiu ver o documento?",
        "Recebeu o email?",
        "Tudo certo aí?",
        "Precisa de alguma coisa?",
        "Posso ajudar em algo?",
    ],
    "responses": [
        "Sim, recebi!",
        "Tudo ok por aqui",
        "Não precisa, obrigado",
        "Já resolvi, valeu!",
        "Tudo certo, pode seguir",
    ],
}


def get_random_message(category: str = None) -> str:
    """Retorna mensagem aleatória de uma categoria."""
    if category and category in MATURATION_MESSAGES:
        return random.choice(MATURATION_MESSAGES[category])
    
    # Escolhe categoria aleatória
    all_messages = []
    for msgs in MATURATION_MESSAGES.values():
        all_messages.extend(msgs)
    return random.choice(all_messages)


def calculate_interval_seconds(phase: int) -> tuple[int, int]:
    """
    Calcula intervalo min/max entre mensagens baseado na fase.
    
    Fase 1: 3-6 min
    Fase 2: 1.5-3 min
    Fase 3: 1-2 min
    Fase 4: 45-90 seg
    Fase 5: 30-60 seg
    """
    intervals = {
        1: (180, 360),   # 3-6 min
        2: (90, 180),    # 1.5-3 min
        3: (60, 120),    # 1-2 min
        4: (45, 90),     # 45-90 seg
        5: (30, 60),     # 30-60 seg
    }
    return intervals.get(phase, (60, 120))


async def get_target_chips(session, user_id: UUID, source_chip_id: UUID) -> list[Chip]:
    """
    Busca outros chips CONNECTED do mesmo usuário para serem destinatários.
    
    Args:
        session: Sessão do banco
        user_id: ID do usuário
        source_chip_id: ID do chip que está aquecendo (excluir)
    
    Returns:
        Lista de chips disponíveis como destino
    """
    result = await session.execute(
        select(Chip).where(
            Chip.user_id == user_id,
            Chip.status == ChipStatus.CONNECTED,
            Chip.id != source_chip_id
        )
    )
    return result.scalars().all()


async def send_maturation_message(
    chip: Chip,
    target_phone: str,
    message: str,
    waha_api_key: str,
    waha_base_url: str
) -> bool:
    """
    Envia mensagem de aquecimento via WAHA Plus.
    
    Args:
        chip: Chip remetente
        target_phone: Número de destino
        message: Texto da mensagem
        waha_api_key: API key do container WAHA Plus
        waha_base_url: URL base do container
    
    Returns:
        True se enviou com sucesso, False caso contrário
    """
    try:
        session_id = chip.extra_data.get("session_id") if chip.extra_data else None
        if not session_id:
            session_id = f"chip_{chip.id}"
        
        waha_client = WAHAClient(
            base_url=waha_base_url,
            api_key=waha_api_key
        )
        
        await waha_client.send_message(
            session_id=session_id,
            phone=target_phone,
            text=message
        )
        
        return True
    
    except Exception as e:
        import logging
        logger = logging.getLogger("whago.chip_maturation")
        logger.error(f"Erro ao enviar mensagem de aquecimento: {e}")
        return False


async def process_chip_maturation(chip_id: str):
    """
    Processa o aquecimento de um chip específico.
    
    Args:
        chip_id: UUID do chip em aquecimento
    """
    # Criar engine isolada para essa task
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session_maker() as session:
        try:
            # Buscar chip
            result = await session.execute(
                select(Chip).where(Chip.id == UUID(chip_id))
            )
            chip = result.scalar_one_or_none()
            
            if not chip or chip.status != ChipStatus.MATURING:
                return
            
            # Verificar se tem dados de heat_up
            heat_up_data = chip.extra_data.get("heat_up", {}) if chip.extra_data else {}
            if heat_up_data.get("status") != "in_progress":
                return
            
            # Fase atual
            current_phase = heat_up_data.get("current_phase", 1)
            plan = heat_up_data.get("plan", [])
            
            if not plan or current_phase > len(plan):
                # Aquecimento concluído
                chip.status = ChipStatus.CONNECTED
                chip.extra_data["heat_up"]["status"] = "completed"
                chip.extra_data["heat_up"]["completed_at"] = datetime.now(timezone.utc).isoformat()
                await session.commit()
                return
            
            # Dados da fase atual
            phase_info = plan[current_phase - 1]
            messages_per_hour = phase_info.get("messages_per_hour", 20)
            
            # Verificar se deve enviar nesta execução (executa 1x por hora, envia metade das msgs)
            messages_to_send = messages_per_hour // 2  # Metade envia, metade recebe
            
            # Buscar chips destino
            target_chips = await get_target_chips(session, chip.user_id, chip.id)
            
            if not target_chips:
                # Sem chips para conversar, pausa aquecimento
                import logging
                logger = logging.getLogger("whago.chip_maturation")
                logger.warning(f"Chip {chip.id} sem chips destino para aquecimento")
                return
            
            # Buscar container WAHA Plus do usuário
            container_manager = WahaContainerManager()
            waha_container = await container_manager.get_user_container(str(chip.user_id))
            
            if not waha_container:
                return
            
            waha_base_url = f"http://{waha_container['name']}:{waha_container['port']}"
            waha_api_key = waha_container.get("api_key", "")
            
            # Calcular intervalo entre mensagens
            min_interval, max_interval = calculate_interval_seconds(current_phase)
            
            # Enviar mensagens
            messages_sent = 0
            for i in range(messages_to_send):
                # Escolher chip destino aleatório
                target_chip = random.choice(target_chips)
                target_phone = target_chip.phone_number
                
                if not target_phone:
                    continue
                
                # Gerar mensagem natural
                message = get_random_message()
                
                # Enviar via WAHA Plus
                success = await send_maturation_message(
                    chip=chip,
                    target_phone=target_phone,
                    message=message,
                    waha_api_key=waha_api_key,
                    waha_base_url=waha_base_url
                )
                
                if success:
                    messages_sent += 1
                
                # Aguardar intervalo aleatório antes da próxima
                if i < messages_to_send - 1:  # Não aguardar após última msg
                    interval = random.randint(min_interval, max_interval)
                    await asyncio.sleep(interval)
            
            # Atualizar progresso
            messages_sent_in_phase = heat_up_data.get("messages_sent_in_phase", 0) + messages_sent
            phase_started_at = heat_up_data.get("phase_started_at")
            
            if not phase_started_at:
                phase_started_at = datetime.now(timezone.utc).isoformat()
            
            # Verificar se completou a fase (baseado em tempo)
            phase_start = datetime.fromisoformat(phase_started_at.replace("Z", "+00:00"))
            phase_duration_hours = phase_info.get("duration_hours", 4)
            
            if datetime.now(timezone.utc) >= phase_start + timedelta(hours=phase_duration_hours):
                # Avançar para próxima fase
                current_phase += 1
                messages_sent_in_phase = 0
                phase_started_at = datetime.now(timezone.utc).isoformat()
            
            # Salvar progresso
            chip.extra_data["heat_up"]["current_phase"] = current_phase
            chip.extra_data["heat_up"]["messages_sent_in_phase"] = messages_sent_in_phase
            chip.extra_data["heat_up"]["phase_started_at"] = phase_started_at
            chip.extra_data["heat_up"]["last_execution"] = datetime.now(timezone.utc).isoformat()
            
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(chip, "extra_data")
            
            await session.commit()
        
        finally:
            await engine.dispose()


@celery_app.task(name="execute_chip_maturation_cycle")
def execute_chip_maturation_cycle():
    """
    Task periódica que executa o aquecimento de todos os chips em MATURING.
    
    Executada a cada 1 hora pelo Celery Beat.
    """
    import logging
    logger = logging.getLogger("whago.chip_maturation")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(_execute_maturation_cycle())
    finally:
        loop.close()


async def _execute_maturation_cycle():
    """Função assíncrona que executa o ciclo de aquecimento."""
    import logging
    logger = logging.getLogger("whago.chip_maturation")
    
    # Criar engine isolada
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session_maker() as session:
        try:
            # Buscar todos os chips em aquecimento
            result = await session.execute(
                select(Chip).where(Chip.status == ChipStatus.MATURING)
            )
            chips = result.scalars().all()
            
            logger.info(f"Encontrados {len(chips)} chips em aquecimento")
            
            # Processar cada chip
            for chip in chips:
                try:
                    await process_chip_maturation(str(chip.id))
                except Exception as e:
                    logger.error(f"Erro ao processar chip {chip.id}: {e}")
        
        finally:
            await engine.dispose()

