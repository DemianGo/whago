"""
Serviço para gerenciamento de proxies e atribuições.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from ..models.proxy import (
    ProxyProvider,
    Proxy,
    ChipProxyAssignment,
    ProxyUsageLog,
    UserProxyCost,
)
from ..models.chip import Chip
from .smartproxy_client import SmartproxyClient


class ProxyService:
    """Serviço para gerenciar proxies e atribuições a chips."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_rotating_proxy(
        self, region: str = "BR"
    ) -> Optional[Proxy]:
        """
        Retorna proxy ativo (mobile ou rotating) com melhor health.
        """
        result = await self.session.execute(
            select(Proxy)
            .where(Proxy.proxy_type.in_(["rotating", "mobile"]))
            .where(Proxy.region == region)
            .where(Proxy.is_active == True)
            .order_by(Proxy.health_score.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def assign_proxy_to_chip(self, chip: Chip, force_new: bool = False) -> str:
        """
        Atribui proxy ao chip e retorna URL completa.
        
        IMPORTANTE: 
        - Cada CONEXÃO ganha um novo session_identifier (novo IP)
        - Session format: chip-{chip_id}-{timestamp}
        - Isso garante IP único por conexão e evita repetição
        
        Args:
            chip: Chip a ser atribuído
            force_new: Se True, força criação de novo assignment
            
        Returns:
            URL completa do proxy com sticky session
            
        Raises:
            ValueError: Se nenhum proxy disponível
        """
        # Verifica se já tem proxy ATIVO atribuído
        existing = await self.get_chip_assignment(chip.id)
        
        # Se existe e não forçar novo, reutiliza (mesma sessão ativa)
        if existing and existing.proxy_id and not force_new:
            proxy = await self.session.get(Proxy, existing.proxy_id)
            if proxy:
                return self._build_proxy_url(proxy, existing.session_identifier)

        # Busca proxy rotativo
        proxy = await self.get_active_rotating_proxy()
        if not proxy:
            raise ValueError("Nenhum proxy ativo disponível")

        # ✅ NOVO SESSION ID a cada conexão = IP diferente
        # Format: 8 chars do UUID (para ser curto e compatível com DataImpulse)
        chip_suffix = str(chip.id).split('-')[-1][:8]  # Primeiros 8 chars do último segmento
        timestamp_suffix = str(int(datetime.now(timezone.utc).timestamp()))[-4:]  # Últimos 4 dígitos do timestamp
        session_id = f"{chip_suffix}{timestamp_suffix}"  # Ex: bafbcbec1234 (12 chars total)
        
        # ✅ VALIDAR: Verificar se session_id já existe (improvável mas seguro)
        collision_check = await self.session.execute(
            select(ChipProxyAssignment)
            .where(ChipProxyAssignment.session_identifier == session_id)
            .where(ChipProxyAssignment.released_at.is_(None))
        )
        if collision_check.scalar_one_or_none():
            # Adiciona sufixo aleatório
            import random
            session_id = f"{chip_suffix}{timestamp}{random.randint(100, 999)}"

        # Cria ou atualiza assignment
        if existing:
            existing.proxy_id = proxy.id
            existing.session_identifier = session_id
            existing.assigned_at = datetime.now(timezone.utc)
            existing.released_at = None
        else:
            assignment = ChipProxyAssignment(
                chip_id=chip.id,
                proxy_id=proxy.id,
                session_identifier=session_id,
            )
            self.session.add(assignment)

        await self.session.commit()

        # Gera URL com sticky session
        return self._build_proxy_url(proxy, session_id)

    async def get_chip_proxy_url(self, chip_id: UUID) -> Optional[str]:
        """
        Retorna URL do proxy atribuído ao chip.
        
        Args:
            chip_id: ID do chip
            
        Returns:
            URL do proxy ou None
        """
        assignment = await self.get_chip_assignment(chip_id)
        if not assignment or not assignment.proxy_id:
            return None

        proxy = await self.session.get(Proxy, assignment.proxy_id)
        if not proxy:
            return None

        return self._build_proxy_url(proxy, assignment.session_identifier)

    async def get_chip_assignment(
        self, chip_id: UUID
    ) -> Optional[ChipProxyAssignment]:
        """
        Retorna assignment ativo do chip.
        
        Args:
            chip_id: ID do chip
            
        Returns:
            ChipProxyAssignment ou None
        """
        result = await self.session.execute(
            select(ChipProxyAssignment)
            .where(ChipProxyAssignment.chip_id == chip_id)
            .where(ChipProxyAssignment.released_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def release_proxy_from_chip(self, chip_id: UUID) -> None:
        """
        Libera proxy do chip (marca como released).
        
        Args:
            chip_id: ID do chip
        """
        assignment = await self.get_chip_assignment(chip_id)
        if assignment:
            assignment.released_at = datetime.now(timezone.utc)
            await self.session.commit()

    async def health_check_proxy(self, proxy: Proxy) -> int:
        """
        Testa saúde do proxy retornando score 0-100.
        
        Args:
            proxy: Proxy a ser testado
            
        Returns:
            Score de 0-100
        """
        try:
            provider = await self.session.get(ProxyProvider, proxy.provider_id)
            if not provider:
                return 0

            client = SmartproxyClient.from_credentials_dict(provider.credentials)
            success = await client.test_connection()

            proxy.last_health_check = datetime.now(timezone.utc)
            proxy.health_score = 100 if success else 0
            await self.session.commit()

            return proxy.health_score
        except Exception:
            proxy.health_score = 0
            await self.session.commit()
            return 0

    async def get_user_monthly_usage(
        self, user_id: UUID, month: Optional[datetime] = None
    ) -> dict:
        """
        Retorna uso de proxy do usuário no mês.
        
        Args:
            user_id: ID do usuário
            month: Mês a consultar (default: atual)
            
        Returns:
            Dict com bytes_used, gb_used, cost
        """
        if not month:
            month = datetime.now(timezone.utc)

        month_date = month.replace(day=1).date()

        result = await self.session.execute(
            select(UserProxyCost)
            .where(UserProxyCost.user_id == user_id)
            .where(UserProxyCost.month == month_date)
        )
        cost_entry = result.scalar_one_or_none()

        if not cost_entry:
            return {"bytes_used": 0, "gb_used": 0.0, "cost": 0.0}

        return {
            "bytes_used": cost_entry.total_bytes,
            "gb_used": cost_entry.total_bytes / (1024**3),
            "cost": float(cost_entry.total_cost),
        }

    def _build_proxy_url(self, proxy: Proxy, session_identifier: str) -> str:
        """
        Constrói URL do proxy com sticky session.
        
        Formato esperado de proxy.proxy_url:
        - http://username:password@host:port
        - socks5://username:password@host:port
        
        Args:
            proxy: Proxy object
            session_identifier: Identificador de sessão único
            
        Returns:
            URL completa com session identifier
        """
        # Mobile proxies não precisam de session ID (já rotacionam)
        if proxy.proxy_type == "mobile":
            return proxy.proxy_url
        
        # Parse proxy URL
        parts = proxy.proxy_url.split("://")
        protocol = parts[0]
        auth_host = parts[1] if len(parts) > 1 else parts[0]
        
        # Extrair auth e host
        auth_parts = auth_host.split("@")
        if len(auth_parts) > 1:
            credentials = auth_parts[0]
            server_address = auth_parts[1]
            
            # Adicionar session_identifier ao username
            user_pass = credentials.split(":")
            username = user_pass[0]
            password = user_pass[1] if len(user_pass) > 1 else ""
            
            # ✅ FORMATO DATAIMPULSE: username_session-{session_id}
            # Nota: DataImpulse usa UNDERSCORE antes de "session", não hífen
            username_with_session = f"{username}_session-{session_identifier}"
            
            return f"{protocol}://{username_with_session}:{password}@{server_address}"
        
        # Fallback: proxy sem auth
        return proxy.proxy_url


__all__ = ["ProxyService"]

