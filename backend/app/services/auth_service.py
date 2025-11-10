"""
Serviço de autenticação responsável por registro, login e gestão de tokens.
"""

from __future__ import annotations

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..core.redis import get_redis_client
from ..models.plan import Plan, PlanTier
from ..models.token import TokenType, UserToken
from ..models.user import User
from .audit_service import AuditService
from ..schemas.user import (
    AuthResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenPair,
    UserCreate,
    UserLogin,
    UserPublic,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger("whago.auth")


class AuthService:
    """Encapsula regras de negócio de autenticação."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_user(
        self,
        data: UserCreate,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthResponse:
        """Registra um novo usuário conforme especificações do PRD."""

        existing_user = await self.session.scalar(
            select(User).where(User.email == data.email.lower())
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este email já está cadastrado.",
            )

        plan = await self._resolve_plan(data.plan_slug)
        self._enforce_plan_requirements(plan, data)

        user = User(
            name=data.name.strip(),
            email=data.email.lower(),
            password_hash=self._hash_password(data.password),
            phone=data.phone,
            company_name=data.company_name,
            document=data.document,
            plan=plan,
            credits=100,
            is_active=True,
            is_verified=False,
        )

        self.session.add(user)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível criar o usuário.",
            ) from exc

        await self.session.refresh(user)
        await self.session.refresh(user, attribute_names=["plan"])
        try:
            tokens = await self._issue_auth_tokens(user, user_agent, ip_address, commit=False)
        except Exception as exc:  # noqa: BLE001
            await self.session.delete(user)
            await self.session.commit()
            raise
        auth_response = self._build_auth_response(user, tokens)
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="user.registered",
            entity_type="user",
            entity_id=str(user.id),
            description="Usuário registrado com sucesso.",
            extra_data={"plan": plan.slug if plan else None},
            ip_address=ip_address,
            user_agent=user_agent,
            auto_commit=False,
        )
        await self.session.commit()
        return auth_response

    async def login(
        self,
        data: UserLogin,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthResponse:
        """Realiza login e retorna tokens."""

        identifier = self._build_login_identifier(data.email, ip_address)
        await self._check_login_rate_limit(identifier)

        user = await self.session.scalar(
            select(User).where(User.email == data.email.lower())
        )
        if not user or not self._verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sua conta está suspensa. Entre em contato com o suporte.",
            )

        user.last_login_at = datetime.utcnow()
        tokens = await self._issue_auth_tokens(user, user_agent, ip_address, commit=False)
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="user.login",
            entity_type="user",
            entity_id=str(user.id),
            description="Login realizado com sucesso.",
            extra_data={"ip": ip_address, "user_agent": user_agent},
            ip_address=ip_address,
            user_agent=user_agent,
            auto_commit=False,
        )
        await self.session.commit()
        await self.session.refresh(user)
        await self.session.refresh(user, attribute_names=["plan"])

        await self._reset_login_attempts(identifier)
        return self._build_auth_response(user, tokens)

    async def logout(self, refresh_token: Optional[str]) -> dict[str, str]:
        """Revoga refresh token informado e retorna mensagem padrão."""

        if refresh_token:
            await self._revoke_refresh_token(refresh_token)
        return {"message": "Logout realizado com sucesso."}

    async def refresh_session(
        self,
        refresh_token: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthResponse:
        """Gera novo par de tokens a partir de um refresh token válido."""

        token_hash = self._hash_token(refresh_token)
        token_record = await self.session.scalar(
            select(UserToken)
            .where(
                UserToken.token_hash == token_hash,
                UserToken.token_type == TokenType.REFRESH,
            )
            .with_for_update()
        )

        if not token_record or not token_record.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido ou expirado.",
            )

        user = await self.session.get(User, token_record.user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário inválido ou inativo.",
            )

        token_record.revoked_at = datetime.utcnow()
        await self.session.flush()

        tokens = await self._issue_auth_tokens(
            user,
            user_agent,
            ip_address,
            commit=False,
        )
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="user.token_refresh",
            entity_type="user",
            entity_id=str(user.id),
            description="Tokens de sessão renovados.",
            extra_data={"ip": ip_address},
            ip_address=ip_address,
            user_agent=user_agent,
            auto_commit=False,
        )
        await self.session.commit()
        await self.session.refresh(user)
        await self.session.refresh(user, attribute_names=["plan"])
        auth_response = self._build_auth_response(user, tokens)
        return auth_response

    async def request_password_reset(
        self,
        payload: ForgotPasswordRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> Optional[str]:
        """Gera token de recuperação de senha (mock de envio de email)."""

        user = await self.session.scalar(
            select(User).where(User.email == payload.email.lower())
        )
        if not user:
            # Resposta genérica para evitar enumeração de emails.
            return None

        await self._invalidate_tokens(user.id, TokenType.RESET_PASSWORD)
        reset_token = await self._create_token(
            user_id=user.id,
            token_type=TokenType.RESET_PASSWORD,
            expires_delta=timedelta(
                minutes=settings.password_reset_token_expire_minutes
            ),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="user.password_reset_requested",
            entity_type="user",
            entity_id=str(user.id),
            description="Usuário solicitou recuperação de senha.",
            extra_data={"email": user.email},
            ip_address=ip_address,
            user_agent=user_agent,
            auto_commit=False,
        )
        await self.session.commit()
        return reset_token

    async def reset_password(self, payload: ResetPasswordRequest) -> None:
        """Reseta a senha de um usuário a partir de um token válido."""

        token_hash = self._hash_token(payload.token)
        token_record = await self.session.scalar(
            select(UserToken)
            .where(
                UserToken.token_hash == token_hash,
                UserToken.token_type == TokenType.RESET_PASSWORD,
            )
            .with_for_update()
        )

        if not token_record or not token_record.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de recuperação inválido ou expirado.",
            )

        user = await self.session.get(User, token_record.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado.",
            )

        user.password_hash = self._hash_password(payload.new_password)
        user.is_active = True
        token_record.consumed_at = datetime.utcnow()

        await self._invalidate_tokens(user.id, TokenType.REFRESH)
        audit = AuditService(self.session)
        await audit.record(
            user_id=user.id,
            action="user.password_reset",
            entity_type="user",
            entity_id=str(user.id),
            description="Senha redefinida via token de recuperação.",
            extra_data=None,
            ip_address=None,
            user_agent=None,
            auto_commit=False,
        )
        await self.session.commit()

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def _verify_password(self, password: str, password_hash: str) -> bool:
        return pwd_context.verify(password, password_hash)

    def _build_login_identifier(self, email: str, ip_address: Optional[str]) -> str:
        normalized_email = email.lower()
        ip = ip_address or "unknown"
        return f"{normalized_email}:{ip}"

    def _encode_access_token(self, user_id: UUID) -> str:
        now = datetime.utcnow()
        payload = {
            "sub": str(user_id),
            "type": "access",
            "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
            "iat": now,
            "jti": secrets.token_urlsafe(16),
        }
        return jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    async def _resolve_plan(self, plan_slug: Optional[str]) -> Plan:
        normalized_slug = (plan_slug or "free").lower()

        plan = await self.session.scalar(
            select(Plan).where(Plan.slug == normalized_slug)
        )
        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plano selecionado é inválido.",
            )
        return plan

    def _enforce_plan_requirements(self, plan: Plan, data: UserCreate) -> None:
        """Valida campos obrigatórios conforme tipo de plano."""

        if plan.tier in {PlanTier.BUSINESS, PlanTier.ENTERPRISE}:
            if not data.company_name:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Nome da empresa é obrigatório para este plano.",
                )
            if not data.document:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Documento (CNPJ/CPF) é obrigatório para este plano.",
                )

    def _build_auth_response(self, user: User, tokens: TokenPair) -> AuthResponse:
        plan_name = user.plan.name if user.plan else None
        plan_slug = user.plan.slug if user.plan else None
        plan_features = user.plan.features if user.plan else None
        user_public = UserPublic.model_validate(
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "phone": user.phone,
                "company_name": user.company_name,
                "document": user.document,
                "credits": user.credits,
                "plan": plan_name,
                 "plan_slug": plan_slug,
                 "plan_features": plan_features,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            }
        )
        return AuthResponse(user=user_public, tokens=tokens)

    async def _issue_auth_tokens(
        self,
        user: User,
        user_agent: str | None,
        ip_address: str | None,
        *,
        commit: bool = True,
    ) -> TokenPair:
        """Cria tokens JWT + refresh persistido."""

        access_token = self._encode_access_token(user.id)
        refresh_token_value = secrets.token_urlsafe(64)
        expires_delta = timedelta(minutes=settings.jwt_refresh_token_expire_minutes)

        token_record = UserToken(
            user_id=user.id,
            token_hash=self._hash_token(refresh_token_value),
            token_type=TokenType.REFRESH,
            expires_at=datetime.utcnow() + expires_delta,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.session.add(token_record)

        if commit:
            await self.session.commit()
        else:
            await self.session.flush()

        return TokenPair(access_token=access_token, refresh_token=refresh_token_value)

    async def _revoke_refresh_token(self, refresh_token: str) -> None:
        token_hash = self._hash_token(refresh_token)
        token_record = await self.session.scalar(
            select(UserToken).where(
                UserToken.token_hash == token_hash,
                UserToken.token_type == TokenType.REFRESH,
                UserToken.revoked_at.is_(None),
            )
        )
        if not token_record:
            return
        token_record.revoked_at = datetime.utcnow()
        await self.session.commit()

    async def _invalidate_tokens(self, user_id: UUID, token_type: TokenType) -> None:
        await self.session.execute(
            update(UserToken)
            .where(
                UserToken.user_id == user_id,
                UserToken.token_type == token_type,
                UserToken.revoked_at.is_(None),
                UserToken.consumed_at.is_(None),
            )
            .values(revoked_at=datetime.utcnow())
        )
        await self.session.flush()

    async def _create_token(
        self,
        *,
        user_id: UUID,
        token_type: TokenType,
        expires_delta: timedelta,
        user_agent: str | None,
        ip_address: str | None,
    ) -> str:
        raw_token = secrets.token_urlsafe(48)
        token_record = UserToken(
            user_id=user_id,
            token_hash=self._hash_token(raw_token),
            token_type=token_type,
            expires_at=datetime.utcnow() + expires_delta,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.session.add(token_record)
        return raw_token

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def _check_login_rate_limit(self, identifier: str) -> None:
        if not settings.rate_limit_enabled:
            return
        try:
            redis = get_redis_client()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao inicializar Redis para rate limit: %s", exc)
            return

        key = f"login_attempts:{identifier}"
        try:
            attempts = await redis.incr(key)
            if attempts == 1:
                await redis.expire(
                    key, settings.rate_limit_login_window_minutes * 60
                )
            if attempts > settings.rate_limit_login_attempts:
                ttl = await redis.ttl(key)
                ttl = ttl if ttl and ttl > 0 else settings.rate_limit_login_window_minutes * 60
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        "Muitas tentativas de login. "
                        f"Tente novamente em {ttl} segundos."
                    ),
                )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("Erro ao aplicar rate limit de login: %s", exc)

    async def _reset_login_attempts(self, identifier: str) -> None:
        if not settings.rate_limit_enabled:
            return
        try:
            redis = get_redis_client()
            await redis.delete(f"login_attempts:{identifier}")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Erro ao limpar contador de login: %s", exc)


