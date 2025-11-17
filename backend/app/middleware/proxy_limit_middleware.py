"""
Middleware para verificar limites de proxy antes de ações críticas.
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..services.proxy_service import ProxyService
from ..services.notification_service import NotificationService, NotificationType


async def check_proxy_quota(user: User, session: AsyncSession) -> None:
    """
    Verifica se usuário ainda tem quota de proxy disponível.
    
    Raises:
        HTTPException: Se limite excedido
    """
    # Buscar plano
    await session.refresh(user, ["plan"])
    
    if not user.plan:
        return  # Sem plano, sem restrição
    
    limit_gb = float(user.plan.proxy_gb_limit)
    
    if limit_gb <= 0:
        return  # Sem limite configurado
    
    # Buscar uso atual
    proxy_service = ProxyService(session)
    usage = await proxy_service.get_user_monthly_usage(user.id)
    
    gb_used = usage["gb_used"]
    percentage = (gb_used / limit_gb * 100) if limit_gb > 0 else 0
    
    # Alertar em 80%
    if percentage >= 80 and percentage < 100:
        notifier = NotificationService(session)
        await notifier.create(
            user_id=user.id,
            title="⚠️ Limite de Proxy (80%)",
            message=f"Você já usou {gb_used:.2f} GB de {limit_gb} GB de proxy este mês.",
            type_=NotificationType.WARNING,
            auto_commit=False,
        )
    
    # Bloquear em 100%
    if gb_used >= limit_gb:
        # Notificar
        notifier = NotificationService(session)
        await notifier.create(
            user_id=user.id,
            title="🚫 Limite de Proxy Excedido",
            message=f"Você atingiu o limite de {limit_gb} GB de proxy. Faça upgrade ou aguarde o próximo ciclo.",
            type_=NotificationType.ERROR,
            auto_commit=False,
        )
        await session.commit()
        
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Limite de proxy excedido ({gb_used:.2f}/{limit_gb} GB). Faça upgrade ou aguarde renovação mensal.",
        )


__all__ = ["check_proxy_quota"]

