"""Admin Dependencies"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.user import User
from ..models.admin import Admin, AdminAuditLog


async def get_current_admin(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
) -> Admin:
    """Verifica se usuário atual é admin"""
    stmt = select(Admin).where(
        Admin.user_id == current_user.id,
        Admin.is_active == True
    )
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores."
        )
    
    # Armazenar admin no request state para log de auditoria
    request.state.admin = admin
    return admin


async def require_super_admin(admin: Admin = Depends(get_current_admin)) -> Admin:
    """Requer role de super_admin"""
    if admin.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas super administradores."
        )
    return admin


async def log_admin_action(
    request: Request,
    session: AsyncSession,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict | None = None
):
    """Registra ação administrativa"""
    admin = getattr(request.state, "admin", None)
    if not admin:
        return
    
    log = AdminAuditLog(
        admin_id=admin.id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        details=details,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    session.add(log)
    await session.commit()

