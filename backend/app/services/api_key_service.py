"""Serviço para gerenciamento e autenticação de API Keys."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..core.redis import get_redis_client
from ..models.api_key import ApiKey
from ..models.user import User

_api_key_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class ApiKeyService:
    """Regras de negócio para chaves de API."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_keys(self, user: User) -> Sequence[ApiKey]:
        return await self._query_keys(user)

    async def create_key(self, user: User, name: str) -> tuple[ApiKey, str]:
        user = await self._ensure_plan_loaded(user)
        if not self._user_has_api_access(user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Recurso disponível apenas no plano Enterprise.")
        raw_key, prefix, hashed = self._generate_key()
        api_key = ApiKey(user_id=user.id, name=name, prefix=prefix, hashed_key=hashed)
        self.session.add(api_key)
        await self.session.flush()
        await self.session.refresh(api_key)
        return api_key, raw_key

    async def revoke_key(self, user: User, key_id: UUID) -> ApiKey:
        query = (
            update(ApiKey)
            .where(ApiKey.id == key_id, ApiKey.user_id == user.id, ApiKey.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
            .returning(ApiKey)
        )
        result = await self.session.execute(query)
        api_key = result.scalar_one_or_none()
        if api_key is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chave de API não encontrada ou já revogada.")
        await self.session.commit()
        return api_key

    async def authenticate(self, raw_key: str) -> ApiKey:
        if not raw_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key ausente.")
        prefix = self._extract_prefix(raw_key)
        result = await self.session.execute(
            select(ApiKey)
            .options(selectinload(ApiKey.user).selectinload(User.plan))
            .where(ApiKey.prefix == prefix)
        )
        candidates = result.scalars().all()
        for candidate in candidates:
            if candidate.revoked_at is not None:
                continue
            if _api_key_context.verify(raw_key, candidate.hashed_key):
                if not self._user_has_api_access(candidate.user):
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Plano atual não possui acesso à API.")
                await self._enforce_rate_limit(candidate)
                await self._touch_usage(candidate)
                return candidate
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key inválida.")

    async def _query_keys(self, user: User) -> Sequence[ApiKey]:
        result = await self.session.execute(
            select(ApiKey)
            .options(selectinload(ApiKey.user))
            .where(ApiKey.user_id == user.id)
            .order_by(ApiKey.created_at.desc())
        )
        return result.scalars().all()

    async def _touch_usage(self, api_key: ApiKey) -> None:
        api_key.last_used_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def _enforce_rate_limit(self, api_key: ApiKey) -> None:
        if not settings.rate_limit_enabled:
            return
        limit = settings.api_key_rate_limit_per_minute
        if limit <= 0:
            return
        redis = get_redis_client()
        now_bucket = datetime.utcnow().strftime("%Y%m%d%H%M")
        redis_key = f"rate:api_key:{api_key.id}:{now_bucket}"
        current = await redis.incr(redis_key)
        if current == 1:
            await redis.expire(redis_key, 120)
        if current > limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Limite de requisições por minuto atingido para esta API Key.")

    @staticmethod
    def _generate_key() -> tuple[str, str, str]:
        prefix = secrets.token_hex(4)
        secret = secrets.token_hex(32)
        raw = f"whago_{prefix}_{secret}"
        hashed = _api_key_context.hash(raw)
        return raw, prefix, hashed

    @staticmethod
    def _extract_prefix(raw_key: str) -> str:
        try:
            _, prefix, _ = raw_key.split("_", 2)
        except ValueError as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key inválida.") from exc
        return prefix

    @staticmethod
    def _user_has_api_access(user: User | None) -> bool:
        if user is None or user.plan is None:
            return False
        features = user.plan.features or {}
        return bool(features.get("api_access"))

    async def _ensure_plan_loaded(self, user: User) -> User:
        if user.plan is None and user.plan_id is not None:
            await self.session.refresh(user, attribute_names=["plan"])
        return user


__all__ = ("ApiKeyService",)
