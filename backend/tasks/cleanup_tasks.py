"""
Tasks Celery para limpeza automática de recursos e Garbage Collection de Browsers/Containers.
Implementa a lógica de "BrowserManager" para evitar leaks de Chromium.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from celery import shared_task

from app.database import AsyncSessionLocal
from app.models.chip import Chip, ChipStatus
from app.models.user import User
from app.services.waha_container_manager import get_waha_container_manager
# from app.services.waha_client import get_waha_client # Evitar circular imports se possivel

logger = logging.getLogger("whago.cleanup")


@shared_task(name="cleanup_zombie_resources")
def cleanup_zombie_resources():
    """
    Garbage Collector Central:
    1. Remove containers órfãos (sem dono no DB).
    2. Remove containers de usuários sem chips.
    3. Reinicia containers com alto consumo de RAM (Memory Leak de Chromium).
    4. Mata processos zumbis se detectados (via restart do container).
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_cleanup_zombie_resources_async())
    finally:
        loop.close()


async def _cleanup_zombie_resources_async():
    manager = get_waha_container_manager()
    
    # Listar todos os containers WAHA
    containers = await manager.list_all_containers()
    logger.info(f"🧹 [GC] Iniciando varredura em {len(containers)} containers...")
    
    async with AsyncSessionLocal() as session:
        for container in containers:
            container_name = container.get("container_name")
            user_id = container.get("user_id")
            
            # 1. Container sem user_id (Órfão total)
            if not user_id:
                # Tentar extrair ID do nome antes de considerar órfão
                if container_name and container_name.startswith("waha_plus_user_"):
                    potential_user_id = container_name.replace("waha_plus_user_", "")
                    logger.info(f"⚠️ [GC] Container {container_name} sem label de user_id. Tentando recuperar pelo nome: {potential_user_id}")
                    user_id = potential_user_id
                    # Se recuperou o ID, segue para validação de usuário (passo 2) em vez de deletar
                else:
                    logger.warning(f"🗑️ [GC] Removendo container realmente órfão (sem ID nem nome padrão): {container_name}")
                    try:
                        derived_id = container_name.replace("waha_plus_user_", "") if container_name else "unknown"
                        await manager.delete_user_container(derived_id)
                    except Exception as e:
                        logger.error(f"Erro ao remover órfão {container_name}: {e}")
                    continue

            # 2. Validar se usuário existe e tem chips
            try:
                # Verificar usuário
                user = await session.get(User, user_id)
                if not user:
                    logger.warning(f"🗑️ [GC] Usuário {user_id} não existe mais. Removendo container {container_name}")
                    await manager.delete_user_container(user_id)
                    continue
                
                # Verificar chips
                result = await session.execute(
                    select(func.count(Chip.id)).where(Chip.user_id == user_id)
                )
                chip_count = result.scalar_one()
                
                if chip_count == 0:
                    # Grace Period: Se o container foi criado há menos de 5 minutos, não deletar ainda
                    # Pode estar no processo de criação de chip (race condition)
                    created_str = container.get("created")
                    if created_str:
                         try:
                            # 2024-11-26T14:42:04.919Z ou similar
                            # Simplificar parsing
                            created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                            now = datetime.now(timezone.utc)
                            uptime_seconds = (now - created_dt).total_seconds()
                            
                            if uptime_seconds < 300: # 5 minutos
                                logger.info(f"⏳ [GC] Container {container_name} sem chips, mas em grace period ({int(uptime_seconds)}s). Mantendo.")
                                continue
                         except Exception as e:
                            logger.warning(f"Erro ao parsear data container {container_name}: {e}")

                    logger.info(f"🗑️ [GC] Usuário {user_id} não tem chips ativos. Liberando recursos ({container_name}).")
                    await manager.delete_user_container(user_id)
                    continue
                    
                # 3. Memory Leak Protection (O "Browser Killer")
                # Se o container estiver usando muito RAM, provavel leak do Chromium/Node
                stats = await manager.get_container_stats(user_id)
                if stats:
                    mem_mb = stats.get("memory_usage_mb", 0)
                    # Limite seguro: 4096MB (4GB) para suportar até 10 chips com folga
                    # Servidor tem 16GB RAM, então podemos ser generosos para evitar restarts
                    if mem_mb > 4096:
                        logger.warning(
                            f"⚠️ [GC] ALTO CONSUMO DE RAM DETECTADO em {container_name}: {mem_mb}MB gastos. "
                            "Reiniciando para prevenir travamento do servidor..."
                        )
                        await manager.restart_user_container(user_id)
                        
            except Exception as e:
                logger.error(f"❌ [GC] Erro ao processar container {container_name}: {e}")

    logger.info("🧹 [GC] Limpeza concluída.")


@shared_task(name="cleanup_stale_chips")
def cleanup_stale_chips():
    """
    Limpa chips antigos que ficaram travados em 'waiting_qr'.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_cleanup_stale_chips_async())
    finally:
        loop.close()


async def _cleanup_stale_chips_async():
    async with AsyncSessionLocal() as session:
        # Buscar chips antigos em waiting_qr (> 30 min)
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        
        result = await session.execute(
            select(Chip)
            .where(Chip.status == ChipStatus.WAITING_QR)
            .where(Chip.created_at < cutoff_time)
        )
        stale_chips = result.scalars().all()
        
        if not stale_chips:
            return

        logger.info(f"🧹 Limpando {len(stale_chips)} chips estagnados em WAITING_QR...")
        
        from app.services.chip_service import ChipService
        service = ChipService(session)
        
        # Precisamos do user para chamar delete_chip corretamente
        for chip in stale_chips:
            try:
                user = await session.get(User, chip.user_id)
                if user:
                    logger.info(f"Removendo chip estagnado: {chip.alias} ({chip.id})")
                    await service.delete_chip(user, chip.id)
                else:
                    # Se user não existe, deleta direto
                    await session.delete(chip)
            except Exception as e:
                logger.error(f"Erro ao limpar chip estagnado {chip.id}: {e}")
        
        await session.commit()

__all__ = ["cleanup_zombie_resources", "cleanup_stale_chips"]
