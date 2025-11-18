"""
Tasks Celery para limpeza automática de recursos antigos.
"""

from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy import select
from celery import shared_task

from app.database import AsyncSessionLocal
from app.models.chip import Chip, ChipStatus
from app.services.baileys_client import get_baileys_client

logger = logging.getLogger("whago.cleanup")


@shared_task(name="cleanup_stale_chips")
async def cleanup_stale_chips():
    """
    Limpa chips antigos que ficaram travados em 'waiting_qr'.
    
    Remove chips que:
    - Status = waiting_qr
    - Criados há mais de 10 minutos
    
    Isso previne acúmulo de sessões antigas no Baileys.
    """
    async with AsyncSessionLocal() as session:
        # Buscar chips antigos em waiting_qr
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        result = await session.execute(
            select(Chip)
            .where(Chip.status == ChipStatus.WAITING_QR)
            .where(Chip.created_at < cutoff_time)
        )
        stale_chips = result.scalars().all()
        
        if not stale_chips:
            logger.info("Nenhum chip antigo para limpar")
            return {"cleaned": 0}
        
        baileys = get_baileys_client()
        cleaned_count = 0
        
        for chip in stale_chips:
            try:
                # Deletar sessão do Baileys
                try:
                    await baileys.delete_session(chip.session_id)
                    logger.info(f"Sessão Baileys deletada: {chip.session_id}")
                except Exception as e:
                    logger.warning(f"Erro ao deletar sessão {chip.session_id}: {e}")
                
                # Deletar do banco
                await session.delete(chip)
                cleaned_count += 1
                
                logger.info(
                    f"Chip antigo removido: {chip.id} "
                    f"(alias={chip.alias}, criado={chip.created_at})"
                )
                
            except Exception as e:
                logger.error(f"Erro ao limpar chip {chip.id}: {e}")
        
        await session.commit()
        
        logger.info(f"Limpeza concluída: {cleaned_count} chips removidos")
        return {"cleaned": cleaned_count}


__all__ = ["cleanup_stale_chips"]

