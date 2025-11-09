"""
Rotas de autenticação (registro, login, logout).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..schemas.user import (
    AuthResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserCreate,
    UserLogin,
)
from ..services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticação"])


def _set_auth_cookies(response: Response, auth: AuthResponse) -> None:
    """Define cookies HTTPOnly para tokens JWT."""

    secure_cookie = settings.environment.lower() == "production"
    response.set_cookie(
        key="whago_access_token",
        value=auth.tokens.access_token,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="whago_refresh_token",
        value=auth.tokens.refresh_token,
        max_age=settings.jwt_refresh_token_expire_minutes * 60,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("whago_access_token", path="/")
    response.delete_cookie("whago_refresh_token", path="/")


def _extract_client_context(request: Request) -> tuple[str | None, str | None]:
    """Obtém user-agent e IP do cliente."""

    user_agent = request.headers.get("user-agent")
    client_host = request.client.host if request.client else None
    return user_agent, client_host


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    payload: UserCreate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Registra novo usuário e retorna tokens."""

    service = AuthService(session)
    user_agent, ip_address = _extract_client_context(request)
    auth = await service.register_user(
        payload,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    _set_auth_cookies(response, auth)
    return auth


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
)
async def login_user(
    payload: UserLogin,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Realiza login e retorna tokens."""

    service = AuthService(session)
    user_agent, ip_address = _extract_client_context(request)
    auth = await service.login(
        payload,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    _set_auth_cookies(response, auth)
    return auth


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
)
async def logout_user(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Realiza logout (limpeza de cookies)."""

    refresh_token = request.cookies.get("whago_refresh_token")
    service = AuthService(session)
    await service.logout(refresh_token)
    _clear_auth_cookies(response)
    return {"message": "Logout realizado com sucesso."}


@router.post(
    "/refresh",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh_tokens(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Rotaciona tokens de acesso a partir do refresh token."""

    refresh_cookie = request.cookies.get("whago_refresh_token")
    if not refresh_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token não encontrado.",
        )

    user_agent, ip_address = _extract_client_context(request)
    service = AuthService(session)
    auth = await service.refresh_session(
        refresh_cookie,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    _set_auth_cookies(response, auth)
    return auth


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Solicita recuperação de senha."""

    user_agent, ip_address = _extract_client_context(request)
    service = AuthService(session)
    reset_token = await service.request_password_reset(
        payload,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    response_body: dict[str, str] = {
        "message": "Se o email estiver cadastrado, enviaremos instruções de recuperação.",
    }
    if settings.debug and reset_token:
        response_body["debug_reset_token"] = reset_token
    return response_body


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
)
async def reset_password(
    payload: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Redefine a senha do usuário a partir de um token válido."""

    service = AuthService(session)
    await service.reset_password(payload)
    return {"message": "Senha redefinida com sucesso. Faça login novamente."}


