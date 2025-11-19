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
            to=target_phone,
            text=message
        )
        
        return True
    
    except Exception as e:
        import logging
        logger = logging.getLogger("whago.chip_maturation")
        logger.error(f"Erro ao enviar mensagem de aquecimento: {e}")
        return False


async def process_group_maturation(group_chips: list[Chip], session):
    """
    Processa aquecimento de um grupo de chips.
    Chips enviam mensagens entre si.
    
    Args:
        group_chips: Lista de chips do mesmo grupo
        session: Sessão do banco de dados
    """
    import logging
    logger = logging.getLogger("whago.chip_maturation")
    
    if len(group_chips) < 2:
        logger.warning(f"Grupo tem apenas {len(group_chips)} chip(s), mínimo 2 necessário")
        return
    
    # Pegar dados do primeiro chip (todos do grupo compartilham o mesmo plano)
    first_chip = group_chips[0]
    heat_up_data = first_chip.extra_data.get("heat_up", {}) if first_chip.extra_data else {}
    
    if heat_up_data.get("status") != "in_progress":
        logger.info(f"Grupo não está em progresso (status: {heat_up_data.get('status')})")
        return
    
    # Dados do grupo
    group_id = heat_up_data.get("group_id")
    current_phase = heat_up_data.get("current_phase", 1)
    plan = heat_up_data.get("plan", [])
    custom_messages = heat_up_data.get("custom_messages", [])
    
    if not plan:
        logger.error("Plano de aquecimento não encontrado!")
        return
    
    if current_phase > len(plan):
        logger.info("Aquecimento completo! Finalizando...")
        for chip in group_chips:
            chip.status = ChipStatus.CONNECTED
            if chip.extra_data:
                chip.extra_data["heat_up"]["status"] = "completed"
                chip.extra_data["heat_up"]["completed_at"] = datetime.now(timezone.utc).isoformat()
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(chip, "extra_data")
        await session.commit()
        return
    
    # Dados da fase atual
    phase_info = plan[current_phase - 1]
    messages_per_hour = phase_info.get("messages_per_hour", 20)
    duration_hours = phase_info.get("duration_hours", 4)
    
    logger.info(f"📍 Fase {current_phase}/{len(plan)}: {messages_per_hour} msgs/hora por {duration_hours}h")
    
    # Usar mensagens customizadas ou padrão
    if custom_messages and len(custom_messages) > 0:
        available_messages = custom_messages
        logger.info(f"💬 Usando {len(custom_messages)} mensagens customizadas")
    else:
        available_messages = [msg for msgs in MATURATION_MESSAGES.values() for msg in msgs]
        logger.info(f"💬 Usando {len(available_messages)} mensagens padrão")
    
    # Calcular quantas mensagens enviar nesta execução
    # Task roda a cada 2 min (ou 1h), então envia uma fração das msgs/hora
    messages_to_send = max(1, messages_per_hour // 30)  # A cada 2 min, envia ~1/30 da hora
    
    logger.info(f"📨 Enviando {messages_to_send} mensagens nesta execução")
    
    # Buscar container WAHA Plus do usuário
    container_manager = WahaContainerManager()
    waha_container = await container_manager.get_user_container(str(first_chip.user_id))
    
    if not waha_container:
        logger.error("Container WAHA Plus não encontrado!")
        return
    
    waha_base_url = waha_container.get("base_url", f"http://{waha_container['container_name']}:3000")
    waha_api_key = waha_container.get("api_key", "")
    
    logger.info(f"🐳 Container WAHA: {waha_container['container_name']}")
    
    # Calcular intervalos
    min_interval, max_interval = calculate_interval_seconds(current_phase)
    logger.info(f"⏱️  Intervalo entre mensagens: {min_interval}-{max_interval} segundos")
    
    # Buscar números de telefone do WAHA para chips que não têm
    waha_client = WAHAClient(base_url=waha_base_url, api_key=waha_api_key)
    for chip in group_chips:
        if not chip.phone_number:
            try:
                session_id = chip.extra_data.get("session_id") if chip.extra_data else None
                if not session_id:
                    session_id = f"chip_{chip.id}"
                
                session_info = await waha_client.get_session_status(session_id)
                if session_info and session_info.get("me"):
                    phone = session_info["me"].get("id", "").split("@")[0]
                    if phone:
                        chip.phone_number = f"+{phone}"
                        logger.info(f"📱 Número de {chip.alias}: {chip.phone_number}")
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(chip, "phone_number")
            except Exception as e:
                logger.warning(f"Não foi possível obter número de {chip.alias}: {e}")
    
    await session.commit()
    
    # Enviar mensagens
    messages_sent_count = 0
    
    for i in range(messages_to_send):
        # Escolher remetente e destinatário aleatórios (diferentes)
        # Filtrar apenas chips com phone_number
        chips_with_phone = [c for c in group_chips if c.phone_number]
        
        if len(chips_with_phone) < 2:
            logger.warning(f"⚠️  Grupo tem apenas {len(chips_with_phone)} chip(s) com número. Aguardando próxima execução...")
            break
        
        sender = random.choice(chips_with_phone)
        receiver = random.choice([c for c in chips_with_phone if c.id != sender.id])
        
        # Escolher mensagem aleatória
        message = random.choice(available_messages)
        
        logger.info(f"📤 {sender.alias} → {receiver.alias}: '{message[:30]}...'")
        
        # ENVIAR VIA WAHA PLUS
        success = await send_maturation_message(
            chip=sender,
            target_phone=receiver.phone_number,
            message=message,
            waha_api_key=waha_api_key,
            waha_base_url=waha_base_url
        )
        
        if success:
            messages_sent_count += 1
            logger.info(f"   ✅ Enviada com sucesso!")
            
            # Salvar no histórico do sender
            if not sender.extra_data.get("heat_up", {}).get("message_history"):
                sender.extra_data.setdefault("heat_up", {})["message_history"] = []
            
            sender.extra_data["heat_up"]["message_history"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "to": receiver.alias,
                "to_phone": receiver.phone_number,
                "message": message,
                "phase": current_phase
            })
            
            # Manter apenas últimas 50 mensagens
            sender.extra_data["heat_up"]["message_history"] = \
                sender.extra_data["heat_up"]["message_history"][-50:]
            
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(sender, "extra_data")
        else:
            logger.error(f"   ❌ Falha ao enviar")
        
        # Aguardar intervalo antes da próxima (exceto última)
        if i < messages_to_send - 1:
            interval = random.randint(min_interval, max_interval)
            logger.info(f"   ⏳ Aguardando {interval}s...")
            await asyncio.sleep(interval)
    
    logger.info(f"✅ Total enviado: {messages_sent_count}/{messages_to_send} mensagens")
    
    # Atualizar progresso de TODOS os chips do grupo
    phase_started_at = heat_up_data.get("phase_started_at")
    if not phase_started_at:
        phase_started_at = datetime.now(timezone.utc).isoformat()
    
    # Verificar se completou a fase (baseado em tempo)
    try:
        phase_start = datetime.fromisoformat(phase_started_at.replace("Z", "+00:00"))
        elapsed_hours = (datetime.now(timezone.utc) - phase_start).total_seconds() / 3600
        
        logger.info(f"⏰ Fase iniciada há {elapsed_hours:.1f}h de {duration_hours}h")
        
        if elapsed_hours >= duration_hours:
            logger.info(f"🎉 Fase {current_phase} completa! Avançando para fase {current_phase + 1}")
            new_phase = current_phase + 1
            new_phase_started_at = datetime.now(timezone.utc).isoformat()
        else:
            new_phase = current_phase
            new_phase_started_at = phase_started_at
    except Exception as e:
        logger.error(f"Erro ao calcular progresso: {e}")
        new_phase = current_phase
        new_phase_started_at = phase_started_at
    
    # Atualizar todos os chips do grupo
    for chip in group_chips:
        if chip.extra_data and "heat_up" in chip.extra_data:
            chip.extra_data["heat_up"]["current_phase"] = new_phase
            chip.extra_data["heat_up"]["phase_started_at"] = new_phase_started_at
            chip.extra_data["heat_up"]["last_execution"] = datetime.now(timezone.utc).isoformat()
            chip.extra_data["heat_up"]["total_messages_sent"] = chip.extra_data["heat_up"].get("total_messages_sent", 0) + messages_sent_count
            
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(chip, "extra_data")
    
    await session.commit()
    logger.info("💾 Progresso salvo no banco de dados")


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
    
    logger.info("=" * 80)
    logger.info("🔥 INICIANDO CICLO DE AQUECIMENTO")
    logger.info("=" * 80)
    
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
            
            logger.info(f"📊 Encontrados {len(chips)} chips em MATURING")
            
            if len(chips) == 0:
                logger.info("⚠️  Nenhum chip em aquecimento no momento")
                return
            
            # Agrupar chips por group_id
            from collections import defaultdict
            groups = defaultdict(list)
            
            for chip in chips:
                heat_up_data = chip.extra_data.get("heat_up", {}) if chip.extra_data else {}
                group_id = heat_up_data.get("group_id")
                if group_id:
                    groups[group_id].append(chip)
                    logger.info(f"   • {chip.alias} (ID: {chip.id}) - Grupo: {group_id}")
            
            logger.info(f"📦 {len(groups)} grupos de aquecimento encontrados")
            
            # Processar cada grupo
            for group_id, group_chips in groups.items():
                logger.info(f"\n🔄 Processando grupo {group_id} com {len(group_chips)} chips:")
                for chip in group_chips:
                    logger.info(f"   → {chip.alias}")
                
                try:
                    await process_group_maturation(group_chips, session)
                except Exception as e:
                    logger.error(f"❌ Erro ao processar grupo {group_id}: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"❌ Erro crítico no ciclo de aquecimento: {e}", exc_info=True)
        finally:
            await engine.dispose()
            logger.info("=" * 80)

