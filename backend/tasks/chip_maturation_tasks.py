"""
Celery tasks para aquecimento automático de chips.

Estratégia: Chips se aquecem conversando entre si, simulando comunicação
interna de uma equipe/empresa com comportamento humano (typing, delays, etc).
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.models.chip import Chip, ChipStatus, ChipEvent, ChipEventType
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
    Envia mensagem de aquecimento via WAHA Plus com simulação humana.
    
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
        session_id = chip.extra_data.get("waha_session") if chip.extra_data else None
        if not session_id:
            session_id = f"chip_{chip.id}"
        
        # Verificar se a sessão está pronta (WORKING)
        waha_status = chip.extra_data.get("waha_status", "") if chip.extra_data else ""
        if waha_status != "WORKING":
            # Tentar verificar status real antes de desistir
            try:
                waha_client = WAHAClient(base_url=waha_base_url, api_key=waha_api_key)
                session_info = await waha_client.get_session_status(session_id)
                real_status = session_info.get("status")
                
                if real_status == "WORKING":
                    # Atualizar status localmente para esta execução
                    waha_status = "WORKING"
                    # (A persistência no banco será feita pela task principal se necessário)
            except Exception:
                pass

        if waha_status != "WORKING":
            import logging
            log = logging.getLogger("whago.chip_maturation")
            log.warning(f"⚠️  Sessão {chip.alias} não está pronta (status: {waha_status})")
            return False
        
        waha_client = WAHAClient(
            base_url=waha_base_url,
            api_key=waha_api_key
        )
        
        # Preparar chatId
        phone = target_phone.replace("+", "").replace("@c.us", "")
        chat_id = f"{phone}@c.us"
        
        # 🎭 SIMULAÇÃO DE COMPORTAMENTO HUMANO AVANÇADO
        
        # 1. Ficar Online (Presence Available)
        await waha_client.set_presence(session_id, available=True)
        
        # 2. Delay aleatório antes de abrir a conversa (pegar o celular)
        await asyncio.sleep(random.uniform(2.0, 5.0))
        
        # 3. Marcar como Lido (Visualizado)
        await waha_client.mark_seen(session_id, chat_id)
        
        # 4. Delay de leitura (tempo para ler a mensagem anterior ou pensar)
        await asyncio.sleep(random.uniform(1.5, 4.0))
        
        # 5. Iniciar "digitando..."
        await waha_client.send_typing(session_id, chat_id)
        
        # 6. Calcular tempo de digitação realista com hesitação
        # Velocidade humana: 30-50 WPM (~2.5-4.5 chars/s)
        chars_per_sec = random.uniform(2.5, 4.5)
        base_typing_time = len(message) / chars_per_sec
        
        # Implementar "Efeito Distração/Hesitação" para mensagens médias/longas
        if len(message) > 20 and random.random() < 0.4:  # 40% de chance de hesitar
            # Começa a digitar...
            part1_time = base_typing_time * 0.4
            await asyncio.sleep(part1_time)
            
            # ...para de digitar (pensando/distração)...
            await waha_client.stop_typing(session_id, chat_id)
            pause_time = random.uniform(2.0, 5.0)
            await asyncio.sleep(pause_time)
            
            # ...volta a digitar
            await waha_client.send_typing(session_id, chat_id)
            await asyncio.sleep(base_typing_time * 0.6)
        else:
            # Digitação contínua
            await asyncio.sleep(base_typing_time)
            
        # 7. Parar "digitando..."
        await waha_client.stop_typing(session_id, chat_id)
        
        # Delay curto antes de apertar enviar
        await asyncio.sleep(random.uniform(0.3, 0.8))
        
        # 8. Enviar mensagem
        await waha_client.send_message(
            session_id=session_id,
            to=target_phone,
            text=message
        )
        
        # 9. Ficar Online mais um pouco (esperando resposta ou saindo)
        await asyncio.sleep(random.uniform(2.0, 6.0))
        
        # 10. Ficar Offline (Presence Unavailable)
        await waha_client.set_presence(session_id, available=False)
        
        return True
    
    except Exception as e:
        import logging
        log = logging.getLogger("whago.chip_maturation")
        log.error(f"Erro ao enviar mensagem de aquecimento: {e}")
        
        # Se o erro for "getChat", significa que o número não está nos contatos
        error_msg = str(e).lower()
        if "getchat" in error_msg or "cannot read properties" in error_msg:
            log.warning(f"💡 DICA: O número {target_phone} não está nos contatos do WhatsApp. "
                       f"Envie uma mensagem manual primeiro para criar o chat.")
        
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
    
    # REFRESH para garantir status atualizado do banco
    await session.refresh(first_chip)
    
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
    
    from sqlalchemy.orm.attributes import flag_modified
    logger.info(f"📍 Fase {current_phase}/{len(plan)}: {messages_per_hour} msgs/hora por {duration_hours}h")
    
    # Usar mensagens customizadas ou padrão
    if custom_messages and len(custom_messages) > 0:
        available_messages = custom_messages
        logger.info(f"💬 Usando {len(custom_messages)} mensagens customizadas")
    else:
        available_messages = [msg for msgs in MATURATION_MESSAGES.values() for msg in msgs]
        logger.info(f"💬 Usando {len(available_messages)} mensagens padrão")
    
    # Calcular quantas mensagens enviar nesta execução
    # Task roda a cada 3 min (20 execuções/hora), então envia msgs/hora dividido por 20
    messages_to_send = max(1, messages_per_hour // 20)
    
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
    
    # Buscar números de telefone do WAHA para chips que não têm e VERIFICAR STATUS REAL
    waha_client = WAHAClient(base_url=waha_base_url, api_key=waha_api_key)
    
    for chip in group_chips:
        # Verificação Ativa de Sanidade (Active Health Check)
        current_status = chip.extra_data.get("waha_status") if chip.extra_data else None
        
        # Se status não é WORKING, verificar ativamente
        if current_status != "WORKING":
            try:
                session_id = chip.extra_data.get("waha_session") if chip.extra_data else None
                if not session_id:
                    session_id = f"chip_{chip.id}"
                
                # Consulta ativa ao WAHA
                session_info = await waha_client.get_session_status(session_id)
                real_status = session_info.get("status")
                
                if real_status and real_status != current_status:
                    logger.info(f"🔄 Auto-correção de status para {chip.alias}: {current_status} -> {real_status}")
                    if not chip.extra_data: chip.extra_data = {}
                    chip.extra_data["waha_status"] = real_status
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(chip, "extra_data")
                    
                    # Se ficou WORKING e não tem número, pegar agora
                    if real_status == "WORKING" and not chip.phone_number:
                         if session_info.get("me"):
                            phone = session_info["me"].get("id", "").split("@")[0]
                            if phone:
                                chip.phone_number = f"+{phone}"
                                flag_modified(chip, "phone_number")
                                logger.info(f"📱 Número recuperado para {chip.alias}: {chip.phone_number}")

            except Exception as e:
                logger.warning(f"Falha na verificação ativa de status para {chip.alias}: {e}")

        # Backup: Se ainda não tem número mas está WORKING (caso o if acima não tenha pego)
        if not chip.phone_number and chip.extra_data.get("waha_status") == "WORKING":
            try:
                session_id = chip.extra_data.get("waha_session") if chip.extra_data else None
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
        # Filtrar apenas chips com phone_number E com sessão WORKING
        chips_ready = [
            c for c in group_chips 
            if c.phone_number and c.extra_data and c.extra_data.get("waha_status") == "WORKING"
        ]
        
        if len(chips_ready) < 2:
            logger.warning(f"⚠️  Grupo tem apenas {len(chips_ready)} chip(s) prontos (WORKING). Aguardando próxima execução...")
            
            # Registrar evento de aviso para chips do grupo que não estão prontos
            for chip in group_chips:
                is_ready = any(c.id == chip.id for c in chips_ready)
                if not is_ready:
                    # Evitar spam de eventos: checar se já teve aviso recente (opcional, mas bom)
                    # Por simplicidade, vamos registrar sempre que falhar o ciclo, o usuário verá no histórico
                    event = ChipEvent(
                        chip_id=chip.id,
                        type=ChipEventType.WARNING,
                        description="Aquecimento pausado: Chip desconectado ou sessão inválida. Reconecte para continuar.",
                        created_at=datetime.now(timezone.utc)
                    )
                    session.add(event)
            
            await session.commit()
            break
        
        sender = random.choice(chips_ready)
        receiver = random.choice([c for c in chips_ready if c.id != sender.id])
        
        # Escolher mensagem aleatória
        message = random.choice(available_messages)
        
        logger.info(f"📤 {sender.alias} → {receiver.alias}: '{message[:30]}...'")
        
        # 1. ENVIAR MENSAGEM INICIAL (PERGUNTA/SAUDAÇÃO)
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
                "phase": current_phase,
                "type": "sent"
            })

            # -------------------------------------------------------------------------
            # 2. ENVIAR RESPOSTA (PING-PONG) PARA GARANTIR INTERAÇÃO
            # -------------------------------------------------------------------------
            # Simular tempo de leitura/pensamento da outra pessoa
            read_delay = random.uniform(10.0, 25.0)
            logger.info(f"   ⏳ {receiver.alias} lendo e pensando ({read_delay:.1f}s)...")
            await asyncio.sleep(read_delay)

            # Escolher mensagem de resposta adequada
            reply_msg = get_random_message("responses") if random.random() > 0.3 else get_random_message()
            
            logger.info(f"↩️  RESPOSTA {receiver.alias} → {sender.alias}: '{reply_msg[:30]}...'")
            
            reply_success = await send_maturation_message(
                chip=receiver,
                target_phone=sender.phone_number,
                message=reply_msg,
                waha_api_key=waha_api_key,
                waha_base_url=waha_base_url
            )
            
            if reply_success:
                messages_sent_count += 1
                logger.info(f"   ✅ Resposta enviada com sucesso!")
                
                # Salvar no histórico do receiver (que agora enviou)
                if not receiver.extra_data.get("heat_up", {}).get("message_history"):
                    receiver.extra_data.setdefault("heat_up", {})["message_history"] = []
                
                receiver.extra_data["heat_up"]["message_history"].append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "to": sender.alias,
                    "to_phone": sender.phone_number,
                    "message": reply_msg,
                    "phase": current_phase,
                    "type": "reply"
                })
            else:
                logger.error(f"   ❌ Falha ao enviar resposta")

            # -------------------------------------------------------------------------
            
            # Manter apenas últimas 50 mensagens
            sender.extra_data["heat_up"]["message_history"] = \
                sender.extra_data["heat_up"]["message_history"][-50:]
            
            if reply_success:
                 # Se houve resposta, salvar historico do receiver tambem
                 receiver.extra_data["heat_up"]["message_history"] = \
                    receiver.extra_data["heat_up"]["message_history"][-50:]
                 flag_modified(receiver, "extra_data")

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
            logger.info(f"🎉 Fase {current_phase} completa!")
            
            # Se completou a última fase (5), marcar como completo
            if current_phase >= len(plan):
                logger.info(f"✨ Aquecimento COMPLETO! Chip pronto para campanhas")
                new_phase = current_phase
                new_phase_started_at = phase_started_at
                
                # Marcar todos os chips como CONNECTED e completo
                for chip in group_chips:
                    chip.status = ChipStatus.CONNECTED
                    if chip.extra_data and "heat_up" in chip.extra_data:
                        chip.extra_data["heat_up"]["status"] = "completed"
                        chip.extra_data["heat_up"]["completed_at"] = datetime.now(timezone.utc).isoformat()
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(chip, "extra_data")
                        flag_modified(chip, "status")
            else:
                # Avançar para próxima fase
                new_phase = current_phase + 1
                new_phase_started_at = datetime.now(timezone.utc).isoformat()
                logger.info(f"➡️  Avançando para fase {new_phase}")
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
    
    # VERIFICAÇÃO FINAL ANTES DO COMMIT
    # Para evitar sobrescrever status "stopped" ou "paused" se o usuário parou durante a execução
    try:
        # Consultar status atual no banco (sem refresh no objeto para não perder alterações locais)
        check_result = await session.execute(
            select(Chip.extra_data).where(Chip.id == first_chip.id)
        )
        current_db_data = check_result.scalar_one_or_none()
        current_db_status = current_db_data.get("heat_up", {}).get("status") if current_db_data else None
        
        if current_db_status != "in_progress":
            logger.warning(f"⚠️ Status mudou para '{current_db_status}' durante a execução. Abortando salvamento para não sobrescrever.")
            return
    except Exception as e:
        logger.error(f"Erro ao verificar status final: {e}")
        # Em caso de erro na verificação, melhor não salvar por segurança
        return

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
            
            # Check DB status before committing
            check_result = await session.execute(
                select(Chip.extra_data).where(Chip.id == UUID(chip_id))
            )
            current_db_data = check_result.scalar_one_or_none()
            current_db_status = current_db_data.get("heat_up", {}).get("status") if current_db_data else None
            
            if current_db_status != "in_progress":
                 return

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
            # Buscar todos os chips em aquecimento ou com processo em andamento
            result = await session.execute(
                select(Chip).where(
                    or_(
                        Chip.status == ChipStatus.MATURING,
                        Chip.extra_data["heat_up"]["status"].astext == "in_progress"
                    )
                )
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
