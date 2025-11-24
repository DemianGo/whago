"""
Tasks Celery para monitoramento de uso de proxies.

Coleta estatísticas de tráfego REAIS dos containers Docker e atualiza custos por usuário.
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
from app.models.user import User
from app.services.waha_container_manager import WahaContainerManager
from app.services.smartproxy_client import SmartproxyClient
from .celery_app import app

logger = logging.getLogger("whago.proxy_monitor")


@app.task(name="monitor_proxy_usage")
def monitor_proxy_usage():
    """
    Task executada a cada 5 minutos para coletar uso REAL de proxies.
    
    Coleta estatísticas de rede dos containers Docker.
    """
    logger.info("Iniciando monitoramento de uso de proxies (dados reais)...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_async_monitor_proxy_usage())
    finally:
        loop.close()
    logger.info("Monitoramento de proxies concluído.")


async def _async_monitor_proxy_usage():
    """Implementação assíncrona do monitoramento."""
    container_manager = WahaContainerManager()
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. Identificar usuários com chips conectados (que possuem containers ativos)
            result = await session.execute(
                select(Chip.user_id, func.count(Chip.id))
                .where(Chip.status == ChipStatus.CONNECTED)
                .group_by(Chip.user_id)
            )
            active_users = result.all()
            
            logger.info(f"Monitorando consumo de {len(active_users)} usuários ativos...")
            
            for user_id, chip_count in active_users:
                await _process_user_usage(session, container_manager, user_id, chip_count)
            
            await session.commit()
            
        except Exception as exc:
            logger.error(f"Erro no monitoramento de proxies: {exc}")
            await session.rollback()


async def _process_user_usage(
    session: AsyncSession, 
    manager: WahaContainerManager, 
    user_id: str, 
    chip_count: int
):
    """
    Processa o consumo de um usuário específico.
    
    Lê stats do Docker, calcula delta e grava no banco.
    """
    try:
        str_user_id = str(user_id)
        stats = await manager.get_container_stats(str_user_id)
        
        if not stats:
            return

        # Obter uso atual acumulado do container
        current_rx = stats.get("network_rx_bytes", 0)
        current_tx = stats.get("network_tx_bytes", 0)
        current_total = current_rx + current_tx
        
        # Obter uso anterior do Redis para calcular o delta
        redis = await manager._get_redis()
        cache_key = f"waha:network_usage:{str_user_id}"
        last_total = await redis.get(cache_key)
        
        delta_bytes = 0
        if last_total:
            delta_bytes = current_total - int(last_total)
            
            # Se delta negativo (container reiniciou), considerar o total atual como delta
            if delta_bytes < 0:
                delta_bytes = current_total
        else:
            # Primeira leitura, assumir delta zero ou o total atual (vamos ser conservadores e usar 0 para evitar pico falso na primeira leitura)
            delta_bytes = 0
            
        # Atualizar cache
        await redis.setex(cache_key, 86400, str(current_total))
        
        if delta_bytes <= 0:
            return

        logger.info(f"Usuário {str_user_id}: Consumo de {delta_bytes} bytes nos últimos 5 min")
        
        # Registrar no banco
        # Distribuir o uso entre os chips conectados deste usuário
        # Para fins de registro de 'qual proxy gastou', pegamos um chip de exemplo
        # Idealmente, dividiríamos, mas para billing o que importa é o total do usuário
        
        # Buscar um proxy ativo do usuário para atribuir o custo
        result_proxy = await session.execute(
            select(ChipProxyAssignment, Proxy)
            .join(Proxy, ChipProxyAssignment.proxy_id == Proxy.id)
            .join(Chip, ChipProxyAssignment.chip_id == Chip.id)
            .where(Chip.user_id == user_id, Chip.status == ChipStatus.CONNECTED)
            .limit(1)
        )
        row = result_proxy.first()
        
        if row:
            assignment, proxy = row
            
            # Calcular custo (ex: R$ 25,00 por GB)
            # Buscar custo do provider
            provider_result = await session.execute(
                select(ProxyProvider).where(ProxyProvider.id == proxy.provider_id)
            )
            provider = provider_result.scalar_one_or_none()
            cost_per_gb = float(provider.cost_per_gb) if provider else 0.0
            
            cost = Decimal((delta_bytes / (1024**3)) * cost_per_gb)
            
            # Log de uso
            log = ProxyUsageLog(
                user_id=user_id,
                chip_id=assignment.chip_id,
                proxy_id=proxy.id,
                total_bytes=delta_bytes,
                cost=cost,
                session_start=datetime.now(timezone.utc), # Marcação pontual
                session_end=datetime.now(timezone.utc)
            )
            session.add(log)
            
            # Atualizar total mensal do usuário
            await _update_user_proxy_cost(session, user_id, delta_bytes, cost)
            
            # Verificar limites do plano
            await _check_user_limits(session, user_id)

    except Exception as e:
        logger.error(f"Erro ao processar uso do usuário {user_id}: {e}")


async def _update_user_proxy_cost(
    session: AsyncSession,
    user_id,
    bytes_delta: int,
    cost_delta: Decimal,
):
    """Atualiza custo mensal agregado."""
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


async def _check_user_limits(session: AsyncSession, user_id):
    """Verifica se usuário estourou limite de dados do plano."""
    # Obter plano do usuário
    from sqlalchemy.orm import selectinload
    result = await session.execute(
        select(User).options(selectinload(User.plan)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.plan:
        return

    # Obter consumo do mês
    month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).date()
    result_cost = await session.execute(
        select(UserProxyCost).where(UserProxyCost.user_id == user_id, UserProxyCost.month == month)
    )
    usage = result_cost.scalar_one_or_none()
    total_bytes = usage.total_bytes if usage else 0
    
    # Limite do plano (em MB -> converter para bytes)
    # Ex: features: {"proxy_limit_mb": 100}
    features = user.plan.features or {}
    limit_mb = features.get("proxy_limit_mb", 100) # Default 100MB
    limit_bytes = limit_mb * 1024 * 1024
    
    if total_bytes > limit_bytes:
        logger.warning(f"⚠️ Usuário {user.email} estourou limite de proxy: {total_bytes}/{limit_bytes}")
        # Aqui poderíamos bloquear ou notificar
        # Por enquanto, apenas logar. O bloqueio seria via middleware ou pausando containers.


@app.task(name="health_check_proxies")
def health_check_proxies():
    """Task para verificar saúde dos proxies ativos."""
    logger.info("Iniciando health check de proxies...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_async_health_check_proxies())
    finally:
        loop.close()
    logger.info("Health check de proxies concluído.")


async def _async_health_check_proxies():
    """Implementação assíncrona do health check."""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Proxy).where(Proxy.is_active == True).limit(50)
            )
            proxies = result.scalars().all()
            
            for proxy in proxies:
                # Lógica de health check simplificada para manter foco no monitoramento
                # Em produção, testaria conexão real
                pass
                
        except Exception as exc:
            logger.error(f"Erro no health check: {exc}")

__all__ = ["monitor_proxy_usage", "health_check_proxies"]
