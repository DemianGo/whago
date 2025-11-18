"""
Tasks Celery para monitoramento de uso de proxies.

Coleta estatísticas de tráfego e atualiza custos por usuário.
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.proxy import (
    ProxyProvider,
    Proxy,
    ChipProxyAssignment,
    ProxyUsageLog,
    UserProxyCost,
)
from app.models.chip import Chip, ChipStatus
from app.services.smartproxy_client import SmartproxyClient
from .celery_app import app

logger = logging.getLogger("whago.proxy_monitor")


@app.task(name="monitor_proxy_usage")
def monitor_proxy_usage():
    """
    Task executada a cada 5 minutos para coletar uso de proxies.
    
    Coleta estatísticas via API dos provedores e registra consumo.
    """
    logger.info("Iniciando monitoramento de uso de proxies...")
    asyncio.run(_async_monitor_proxy_usage())
    logger.info("Monitoramento de proxies concluído.")


async def _async_monitor_proxy_usage():
    """Implementação assíncrona do monitoramento."""
    async with AsyncSessionLocal() as session:
        try:
            # Busca chips conectados
            result = await session.execute(
                select(Chip)
                .where(Chip.status == ChipStatus.CONNECTED)
                .limit(100)  # Processar em lotes
            )
            chips = result.scalars().all()
            
            logger.info(f"Monitorando {len(chips)} chips conectados...")
            
            monitored = 0
            errors = 0
            
            for chip in chips:
                try:
                    await _monitor_chip_proxy(session, chip)
                    monitored += 1
                except Exception as exc:
                    logger.error(f"Erro ao monitorar chip {chip.id}: {exc}")
                    errors += 1
            
            await session.commit()
            logger.info(f"Monitoramento concluído: {monitored} sucesso, {errors} erros")
            
        except Exception as exc:
            logger.error(f"Erro no monitoramento de proxies: {exc}")
            await session.rollback()


async def _monitor_chip_proxy(session: AsyncSession, chip: Chip):
    """
    Monitora uso de proxy de um chip específico.
    
    Args:
        session: Sessão do banco
        chip: Chip a ser monitorado
    """
    # Busca assignment do chip
    result = await session.execute(
        select(ChipProxyAssignment)
        .where(ChipProxyAssignment.chip_id == chip.id)
        .where(ChipProxyAssignment.released_at.is_(None))
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment or not assignment.proxy_id:
        logger.debug(f"Chip {chip.id} sem proxy atribuído")
        return
    
    # Busca proxy e provider
    proxy = await session.get(Proxy, assignment.proxy_id)
    if not proxy:
        logger.warning(f"Proxy {assignment.proxy_id} não encontrado")
        return
    
    provider = await session.get(ProxyProvider, proxy.provider_id)
    if not provider or not provider.is_active:
        logger.debug(f"Provider {proxy.provider_id} inativo")
        return
    
    # ⚠️ NOTA: API Smartproxy não fornece uso por sessão individual
    # Solução: estimar baseado em mensagens enviadas (aprox 5KB por mensagem)
    # OU aguardar implementação de API específica do provedor
    
    # Por enquanto, registrar log com valores estimados
    await _create_estimated_usage_log(session, chip, proxy, provider)


async def _create_estimated_usage_log(
    session: AsyncSession,
    chip: Chip,
    proxy: Proxy,
    provider: ProxyProvider,
):
    """
    Cria log de uso estimado baseado em atividade do chip.
    
    NOTA: Estimativa até integração com API real do provedor.
    """
    # Buscar mensagens enviadas nas últimas 5 minutos
    five_min_ago = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    five_min_ago = five_min_ago.replace(minute=(five_min_ago.minute // 5) * 5)
    
    # Estimar: 5KB por mensagem de texto (conservador)
    # Se tiver mídia, seria muito mais, mas não temos info aqui
    estimated_bytes_per_message = 5 * 1024  # 5KB
    
    # Por simplicidade, registrar uso base de 1KB por intervalo se chip conectado
    # Isso cobre overhead de manter conexão
    base_bytes = 1024  # 1KB
    
    total_bytes = base_bytes
    cost_per_gb = float(provider.cost_per_gb)
    cost = Decimal((total_bytes / (1024**3)) * cost_per_gb)
    
    # Criar log
    log = ProxyUsageLog(
        user_id=chip.user_id,
        chip_id=chip.id,
        proxy_id=proxy.id,
        bytes_sent=total_bytes // 2,
        bytes_received=total_bytes // 2,
        total_bytes=total_bytes,
        cost=cost,
        session_start=five_min_ago,
        session_end=datetime.now(timezone.utc),
    )
    session.add(log)
    
    # Atualizar agregação mensal
    await _update_user_proxy_cost(session, chip.user_id, total_bytes, cost)
    
    # Atualizar total do proxy
    proxy.total_bytes_used += total_bytes
    
    logger.debug(f"Log criado para chip {chip.id}: {total_bytes} bytes, R$ {cost}")


async def _update_user_proxy_cost(
    session: AsyncSession,
    user_id,
    bytes_delta: int,
    cost_delta: Decimal,
):
    """
    Atualiza custo mensal agregado do usuário.
    
    Args:
        session: Sessão do banco
        user_id: ID do usuário
        bytes_delta: Bytes a adicionar
        cost_delta: Custo a adicionar
    """
    month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_date = month.date()
    
    result = await session.execute(
        select(UserProxyCost)
        .where(UserProxyCost.user_id == user_id)
        .where(UserProxyCost.month == month_date)
    )
    cost_entry = result.scalar_one_or_none()
    
    if cost_entry:
        cost_entry.total_bytes += bytes_delta
        cost_entry.total_cost += cost_delta
        cost_entry.updated_at = datetime.now(timezone.utc)
    else:
        cost_entry = UserProxyCost(
            user_id=user_id,
            month=month_date,
            total_bytes=bytes_delta,
            total_cost=cost_delta,
        )
        session.add(cost_entry)


@app.task(name="health_check_proxies")
def health_check_proxies():
    """
    Task para verificar saúde dos proxies ativos.
    
    Executada a cada 15 minutos.
    """
    logger.info("Iniciando health check de proxies...")
    asyncio.run(_async_health_check_proxies())
    logger.info("Health check de proxies concluído.")


async def _async_health_check_proxies():
    """Implementação assíncrona do health check."""
    async with AsyncSessionLocal() as session:
        try:
            # Busca proxies ativos
            result = await session.execute(
                select(Proxy)
                .where(Proxy.is_active == True)
                .limit(50)
            )
            proxies = result.scalars().all()
            
            logger.info(f"Verificando saúde de {len(proxies)} proxies...")
            
            healthy = 0
            unhealthy = 0
            
            for proxy in proxies:
                try:
                    provider = await session.get(ProxyProvider, proxy.provider_id)
                    if not provider:
                        continue
                    
                    client = SmartproxyClient.from_credentials_dict(provider.credentials)
                    success = await client.test_connection()
                    
                    proxy.last_health_check = datetime.now(timezone.utc)
                    
                    if success:
                        proxy.health_score = min(100, proxy.health_score + 10)
                        healthy += 1
                    else:
                        proxy.health_score = max(0, proxy.health_score - 20)
                        unhealthy += 1
                        
                        if proxy.health_score < 30:
                            proxy.is_active = False
                            logger.warning(f"Proxy {proxy.id} desativado (health: {proxy.health_score})")
                    
                except Exception as exc:
                    logger.error(f"Erro ao verificar proxy {proxy.id}: {exc}")
                    proxy.health_score = max(0, proxy.health_score - 10)
                    unhealthy += 1
            
            await session.commit()
            logger.info(f"Health check concluído: {healthy} saudáveis, {unhealthy} com problemas")
            
        except Exception as exc:
            logger.error(f"Erro no health check de proxies: {exc}")
            await session.rollback()


__all__ = ["monitor_proxy_usage", "health_check_proxies"]

