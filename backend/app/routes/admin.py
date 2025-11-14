"""Admin Routes - Painel Administrativo"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, or_
from sqlalchemy.orm import selectinload
from typing import List

from ..database import get_db
from ..dependencies.admin import get_current_admin, require_super_admin, log_admin_action
from ..models.admin import Admin, AdminAuditLog
from ..models.user import User
from ..models.plan import Plan
from ..models.coupon import Coupon
from ..models.transaction import Transaction
from ..models.payment_gateway_config import PaymentGatewayConfig
from ..services.admin_service import AdminService
from ..services.auth_service import AuthService
from ..schemas.admin import *
from ..schemas.plan import PlanResponse

# Import específico para evitar conflitos
from ..schemas.admin import UserCreateAdmin

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ============================================================================
# DASHBOARD
# ============================================================================
@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Dashboard com estatísticas principais"""
    service = AdminService(session)
    return await service.get_dashboard_stats()


# ============================================================================
# USERS CRUD
# ============================================================================
@router.get("/users", response_model=List[UserListItem])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    plan_id: int | None = None,
    status: str | None = None,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Lista usuários com filtros"""
    query = select(User).options(selectinload(User.plan))
    
    if search:
        query = query.where(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
    if plan_id:
        query = query.where(User.plan_id == plan_id)
    
    if status == "active":
        query = query.where(User.is_active == True, User.is_suspended == False)
    elif status == "suspended":
        query = query.where(User.is_suspended == True)
    elif status == "inactive":
        query = query.where(User.is_active == False)
    
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
    result = await session.execute(query)
    users = result.scalars().all()
    
    return [
        UserListItem(
            id=u.id,
            name=u.name,
            email=u.email,
            plan_name=u.plan.name if u.plan else "Free",
            credits=u.credits,
            is_active=u.is_active,
            is_suspended=u.is_suspended,
            created_at=u.created_at
        )
        for u in users
    ]


@router.post("/users", response_model=UserDetail)
async def create_user(
    data: UserCreateAdmin,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Cria um novo usuário"""
    # Verificar se email já existe
    stmt = select(User).where(User.email == data.email)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Importar AuthService para hash de senha
    auth_service = AuthService(session)
    
    # Criar usuário
    user = User(
        email=data.email,
        password_hash=auth_service._hash_password(data.password),
        name=data.name,
        phone=data.phone or "+5511999999999",
        company_name=data.company_name,
        plan_id=data.plan_id or 1,
        credits=data.credits if data.credits is not None else 100,
        is_active=data.is_active,
        is_suspended=data.is_suspended,
        is_verified=True
    )
    
    session.add(user)
    await session.commit()
    await session.refresh(user, ["plan"])
    
    await log_admin_action(request, session, "user_created", "user", user.id, {"email": data.email, "name": data.name})
    
    return UserDetail(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        company_name=user.company_name,
        document=user.document,
        plan_name=user.plan.name if user.plan else "Free",
        credits=user.credits,
        is_active=user.is_active,
        is_suspended=user.is_suspended,
        subscription_id=user.subscription_id,
        subscription_status=user.subscription_status,
        subscription_gateway=user.subscription_gateway,
        last_login_at=user.last_login_at,
        created_at=user.created_at
    )


@router.get("/users/{user_id}", response_model=UserDetail)
async def get_user_detail(
    user_id: str,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Detalhes completos do usuário"""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    await session.refresh(user, ["plan"])
    
    return UserDetail(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        company_name=user.company_name,
        document=user.document,
        plan_name=user.plan.name if user.plan else "Free",
        credits=user.credits,
        is_active=user.is_active,
        is_suspended=user.is_suspended,
        subscription_id=user.subscription_id,
        subscription_status=user.subscription_status,
        subscription_gateway=user.subscription_gateway,
        last_login_at=user.last_login_at,
        created_at=user.created_at
    )


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UserUpdateAdmin,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Atualiza dados do usuário"""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    
    await session.commit()
    await log_admin_action(request, session, "user_updated", "user", user_id, update_data)
    
    return {"message": "Usuário atualizado com sucesso"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    admin: Admin = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db)
):
    """Deleta usuário permanentemente"""
    stmt = delete(User).where(User.id == user_id)
    result = await session.execute(stmt)
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    await session.commit()
    await log_admin_action(request, session, "user_deleted", "user", user_id)
    
    return {"message": "Usuário deletado com sucesso"}


@router.post("/users/{user_id}/impersonate")
async def impersonate_user(
    user_id: str,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Gera token de acesso para impersonar usuário"""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    from ..services.auth_service import create_tokens
    tokens = create_tokens(user.id)
    
    await log_admin_action(request, session, "user_impersonated", "user", user_id)
    
    return {"tokens": tokens, "user": {"id": str(user.id), "email": user.email, "name": user.name}}


# ============================================================================
# PLANS CRUD
# ============================================================================
@router.get("/plans", response_model=List[PlanResponse])
async def list_plans(
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Lista todos os planos"""
    result = await session.execute(select(Plan).order_by(Plan.tier))
    return result.scalars().all()


@router.post("/plans", response_model=PlanResponse)
async def create_plan(
    data: PlanCreateUpdate,
    request: Request,
    admin: Admin = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db)
):
    """Cria novo plano"""
    plan = Plan(**data.model_dump())
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    await log_admin_action(request, session, "plan_created", "plan", plan.id, data.model_dump())
    return plan


@router.put("/plans/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: int,
    data: PlanCreateUpdate,
    request: Request,
    admin: Admin = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db)
):
    """Atualiza plano"""
    stmt = select(Plan).where(Plan.id == plan_id)
    result = await session.execute(stmt)
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    for key, value in data.model_dump().items():
        setattr(plan, key, value)
    
    await session.commit()
    await log_admin_action(request, session, "plan_updated", "plan", plan_id, data.model_dump())
    return plan


# ============================================================================
# COUPONS CRUD
# ============================================================================
@router.get("/coupons", response_model=List[CouponResponse])
async def list_coupons(
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Lista cupons"""
    result = await session.execute(select(Coupon).order_by(Coupon.created_at.desc()))
    return result.scalars().all()


@router.post("/coupons", response_model=CouponResponse)
async def create_coupon(
    data: CouponCreate,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Cria cupom"""
    coupon = Coupon(**data.model_dump())
    session.add(coupon)
    await session.commit()
    await session.refresh(coupon)
    await log_admin_action(request, session, "coupon_created", "coupon", coupon.id, data.model_dump())
    return coupon


@router.put("/coupons/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    coupon_id: str,
    data: CouponUpdate,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Atualiza cupom"""
    stmt = select(Coupon).where(Coupon.id == coupon_id)
    result = await session.execute(stmt)
    coupon = result.scalar_one_or_none()
    
    if not coupon:
        raise HTTPException(status_code=404, detail="Cupom não encontrado")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(coupon, key, value)
    
    await session.commit()
    await log_admin_action(request, session, "coupon_updated", "coupon", coupon_id, update_data)
    return coupon


@router.delete("/coupons/{coupon_id}")
async def delete_coupon(
    coupon_id: str,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Deleta cupom"""
    stmt = delete(Coupon).where(Coupon.id == coupon_id)
    result = await session.execute(stmt)
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Cupom não encontrado")
    
    await session.commit()
    await log_admin_action(request, session, "coupon_deleted", "coupon", coupon_id)
    return {"message": "Cupom deletado"}


# ============================================================================
# TRANSACTIONS
# ============================================================================
@router.get("/transactions", response_model=List[TransactionListItem])
async def list_transactions(
    skip: int = 0,
    limit: int = 50,
    gateway: str | None = None,
    status: str | None = None,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Lista transações"""
    query = select(Transaction).options(selectinload(Transaction.user))
    
    if gateway:
        query = query.where(Transaction.payment_method == gateway)
    if status:
        query = query.where(Transaction.status == status)
    
    query = query.offset(skip).limit(limit).order_by(Transaction.created_at.desc())
    result = await session.execute(query)
    transactions = result.scalars().all()
    
    return [
        TransactionListItem(
            id=t.id,
            user_id=t.user_id,
            user_name=t.user.name,
            user_email=t.user.email,
            type=t.type,
            amount=float(t.amount),
            status=t.status,
            payment_method=t.payment_method,
            reference_code=t.reference_code,
            created_at=t.created_at
        )
        for t in transactions
    ]


@router.get("/transactions/{transaction_id}", response_model=TransactionDetail)
async def get_transaction_detail(
    transaction_id: str,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Detalhes da transação"""
    stmt = select(Transaction).where(Transaction.id == transaction_id)
    result = await session.execute(stmt)
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    
    await session.refresh(transaction, ["user"])
    
    return TransactionDetail(
        id=transaction.id,
        user_id=transaction.user_id,
        user_name=transaction.user.name,
        user_email=transaction.user.email,
        type=transaction.type,
        amount=float(transaction.amount),
        status=transaction.status,
        payment_method=transaction.payment_method,
        reference_code=transaction.reference_code,
        plan_id=transaction.plan_id,
        credits=transaction.credits,
        extra_data=transaction.extra_data,
        processed_at=transaction.processed_at,
        created_at=transaction.created_at
    )


# ============================================================================
# GATEWAY CONFIGS
# ============================================================================
@router.get("/gateways", response_model=List[GatewayConfigResponse])
async def list_gateways(
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Lista configurações de gateways"""
    result = await session.execute(select(PaymentGatewayConfig))
    return result.scalars().all()


@router.get("/gateways/{gateway_id}", response_model=GatewayConfigResponse)
async def get_gateway(
    gateway_id: UUID,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Busca configuração de um gateway específico"""
    result = await session.execute(
        select(PaymentGatewayConfig).where(PaymentGatewayConfig.id == gateway_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Gateway não encontrado")
    
    return config


@router.put("/gateways/{gateway_id}", response_model=GatewayConfigResponse)
async def update_gateway(
    gateway_id: UUID,
    data: GatewayConfigUpdate,
    request: Request,
    admin: Admin = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db)
):
    """Atualiza configuração do gateway"""
    result = await session.execute(
        select(PaymentGatewayConfig).where(PaymentGatewayConfig.id == gateway_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Gateway não encontrado")
    
    update_data = data.model_dump(exclude_unset=True)
    
    # Process sandbox_config
    if "sandbox_config" in update_data:
        sandbox = update_data.pop("sandbox_config")
        if sandbox:
            config.sandbox_access_token = sandbox.get("access_token")
            config.sandbox_public_key = sandbox.get("public_key")
            config.sandbox_client_id = sandbox.get("client_id")
            config.sandbox_client_secret = sandbox.get("client_secret")
            config.sandbox_webhook_secret = sandbox.get("webhook_secret")
    
    # Process production_config
    if "production_config" in update_data:
        production = update_data.pop("production_config")
        if production:
            config.production_access_token = production.get("access_token")
            config.production_public_key = production.get("public_key")
            config.production_client_id = production.get("client_id")
            config.production_client_secret = production.get("client_secret")
            config.production_webhook_secret = production.get("webhook_secret")
    
    # Update remaining fields
    for key, value in update_data.items():
        setattr(config, key, value)
    
    config.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(config)
    
    await log_admin_action(
        request, session, "gateway_updated", "gateway", 
        str(gateway_id), {"name": config.gateway, "updated_fields": list(update_data.keys())}
    )
    
    return config


# ============================================================================
# ADMINS CRUD
# ============================================================================
@router.get("/admins", response_model=List[AdminResponse])
async def list_admins(
    admin: Admin = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db)
):
    """Lista administradores"""
    stmt = select(Admin).options(selectinload(Admin.user))
    result = await session.execute(stmt)
    admins = result.scalars().all()
    
    return [
        AdminResponse(
            id=a.id,
            user_id=a.user_id,
            role=a.role,
            permissions=a.permissions,
            is_active=a.is_active,
            created_at=a.created_at,
            user_email=a.user.email,
            user_name=a.user.name
        )
        for a in admins
    ]


@router.post("/admins", response_model=AdminResponse)
async def create_admin(
    data: AdminCreate,
    request: Request,
    admin: Admin = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db)
):
    """Cria novo admin"""
    # Verificar se email já existe
    stmt = select(User).where(User.email == data.email)
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Criar usuário
    auth_service = AuthService(session)
    user = await auth_service.register_user(
        email=data.email,
        password=data.password,
        name=data.email.split("@")[0],
        phone="+5511999999999"
    )
    
    # Criar admin
    new_admin = Admin(
        user_id=user.id,
        role=data.role,
        permissions=data.permissions,
        is_active=data.is_active,
        created_by_id=admin.id
    )
    session.add(new_admin)
    await session.commit()
    await session.refresh(new_admin)
    
    await log_admin_action(request, session, "admin_created", "admin", new_admin.id)
    
    return AdminResponse(
        id=new_admin.id,
        user_id=new_admin.user_id,
        role=new_admin.role,
        permissions=new_admin.permissions,
        is_active=new_admin.is_active,
        created_at=new_admin.created_at,
        user_email=user.email,
        user_name=user.name
    )


@router.put("/admins/{admin_id}")
async def update_admin(
    admin_id: str,
    data: AdminUpdate,
    request: Request,
    admin: Admin = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db)
):
    """Atualiza admin"""
    stmt = select(Admin).where(Admin.id == admin_id)
    result = await session.execute(stmt)
    target_admin = result.scalar_one_or_none()
    
    if not target_admin:
        raise HTTPException(status_code=404, detail="Admin não encontrado")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(target_admin, key, value)
    
    await session.commit()
    await log_admin_action(request, session, "admin_updated", "admin", admin_id, update_data)
    return {"message": "Admin atualizado"}


@router.delete("/admins/{admin_id}")
async def delete_admin(
    admin_id: str,
    request: Request,
    admin: Admin = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db)
):
    """Deleta admin"""
    if str(admin.id) == admin_id:
        raise HTTPException(status_code=400, detail="Não pode deletar a si mesmo")
    
    stmt = delete(Admin).where(Admin.id == admin_id)
    result = await session.execute(stmt)
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Admin não encontrado")
    
    await session.commit()
    await log_admin_action(request, session, "admin_deleted", "admin", admin_id)
    return {"message": "Admin deletado"}


# ============================================================================
# AUDIT LOGS
# ============================================================================
@router.get("/logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action: str | None = None,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db)
):
    """Lista logs de auditoria"""
    query = select(AdminAuditLog).options(
        selectinload(AdminAuditLog.admin).selectinload(Admin.user)
    )
    
    if action:
        query = query.where(AdminAuditLog.action == action)
    
    query = query.offset(skip).limit(limit).order_by(AdminAuditLog.created_at.desc())
    result = await session.execute(query)
    logs = result.scalars().all()
    
    response_logs = []
    for log in logs:
        try:
            admin_name = log.admin.user.name if log.admin and log.admin.user else "Admin Desconhecido"
        except:
            admin_name = "Admin Desconhecido"
        
        try:
            ip_str = str(log.ip_address) if log.ip_address else None
        except:
            ip_str = None
        
        response_logs.append(
            AuditLogResponse(
                id=log.id,
                admin_id=log.admin_id,
                admin_name=admin_name,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                details=log.details,
                ip_address=ip_str,
                created_at=log.created_at
            )
        )
    
    return response_logs

