"""Admin Service"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta

from ..models.user import User
from ..models.transaction import Transaction
from ..models.chip import Chip
from ..models.campaign import CampaignMessage
from ..schemas.admin import DashboardStats


class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_dashboard_stats(self) -> DashboardStats:
        """Retorna estatísticas do dashboard admin"""
        
        # Total de usuários
        total_users = await self.session.scalar(select(func.count(User.id)))
        active_users = await self.session.scalar(
            select(func.count(User.id)).where(User.is_active == True)
        )
        suspended_users = await self.session.scalar(
            select(func.count(User.id)).where(User.is_suspended == True)
        )
        
        # MRR - soma de preços dos planos ativos
        from ..models.plan import Plan
        mrr_query = select(func.sum(Plan.price)).select_from(User).join(
            Plan, User.plan_id == Plan.id
        ).where(
            and_(User.plan_id.isnot(None), User.is_active == True)
        )
        mrr = await self.session.scalar(mrr_query) or 0
        
        # Mensagens
        today = datetime.utcnow().date()
        month_start = datetime.utcnow().replace(day=1)
        
        messages_today = await self.session.scalar(
            select(func.count(CampaignMessage.id)).where(
                func.date(CampaignMessage.created_at) == today
            )
        ) or 0
        
        messages_month = await self.session.scalar(
            select(func.count(CampaignMessage.id)).where(
                CampaignMessage.created_at >= month_start
            )
        ) or 0
        
        # Novos usuários
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        new_users_7d = await self.session.scalar(
            select(func.count(User.id)).where(User.created_at >= seven_days_ago)
        ) or 0
        
        new_users_30d = await self.session.scalar(
            select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
        ) or 0
        
        # Total de chips
        total_chips = await self.session.scalar(select(func.count(Chip.id))) or 0
        
        # Churn rate (simplificado - usuários cancelados nos últimos 30 dias)
        churn_rate = 0.0  # TODO: implementar lógica real de churn
        
        return DashboardStats(
            total_users=total_users or 0,
            active_users=active_users or 0,
            suspended_users=suspended_users or 0,
            mrr=float(mrr),
            messages_today=messages_today,
            messages_month=messages_month,
            churn_rate=churn_rate,
            new_users_7d=new_users_7d,
            new_users_30d=new_users_30d,
            total_chips=total_chips
        )

