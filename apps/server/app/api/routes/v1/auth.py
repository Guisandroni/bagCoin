"""Authentication routes."""

import secrets
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, Redis, UserSvc
from app.core.exceptions import AuthenticationError
from app.core.security import create_access_token, create_refresh_token, verify_token
from app.schemas.auth import (
    AuthPendingResponse,
    EmailVerificationRequest,
    EmailVerificationResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.schemas.token import RefreshTokenRequest, Token
from app.schemas.user import GoogleLoginRequest, UserCreate, UserRead
from app.services.email_verification import EmailVerificationService
from app.services.password_reset import PasswordResetService

router = APIRouter()


def _make_token(user_id: str) -> Token:
    return Token(
        access_token=create_access_token(subject=user_id),
        refresh_token=create_refresh_token(subject=user_id),
        csrf_token=secrets.token_urlsafe(32),
    )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserSvc,
) -> Any:
    user = await user_service.authenticate(form_data.username, form_data.password)
    return _make_token(str(user.id))


@router.post("/register", response_model=AuthPendingResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    request: Request,
    user_service: UserSvc,
    redis: Redis,
) -> Any:
    user = await user_service.register(user_in)
    verification_service = EmailVerificationService(user_service.db, redis)
    dispatch = await verification_service.issue_code_for_user(
        user,
        ip_address=_client_ip(request),
        enforce_cooldown=False,
    )
    return AuthPendingResponse(
        email=user.email,
        auth_provider="email",
        expires_in_seconds=dispatch.expires_in_seconds,
        resend_available_in_seconds=dispatch.resend_available_in_seconds,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    body: RefreshTokenRequest,
    user_service: UserSvc,
) -> Any:
    payload = verify_token(body.refresh_token)
    if payload is None:
        raise AuthenticationError(message="Token de atualização inválido ou expirado")
    if payload.get("type") != "refresh":
        raise AuthenticationError(message="Tipo de token inválido")
    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(message="Conteúdo do token inválido")
    user = await user_service.get_by_id(int(user_id))
    if not user.is_active:
        raise AuthenticationError(message="Sua conta está desativada")
    return _make_token(str(user.id))


@router.post("/google", response_model=Token | AuthPendingResponse)
async def google_login(
    body: GoogleLoginRequest,
    request: Request,
    user_service: UserSvc,
    redis: Redis,
) -> Any:
    user = await user_service.google_auth(body)
    if not user.is_active:
        raise AuthenticationError(message="Sua conta está desativada")
    if user.email_verified:
        return _make_token(str(user.id))

    verification_service = EmailVerificationService(user_service.db, redis)
    if (
        user.email_verification_code_hash
        and user.email_verification_expires_at
        and user.email_verification_expires_at > datetime.now(UTC)
    ):
        return await verification_service.build_pending_response(user)

    dispatch = await verification_service.issue_code_for_user(
        user,
        ip_address=_client_ip(request),
        enforce_cooldown=False,
    )
    return AuthPendingResponse(
        email=user.email,
        auth_provider="google",
        expires_in_seconds=dispatch.expires_in_seconds,
        resend_available_in_seconds=dispatch.resend_available_in_seconds,
    )


@router.post("/verify-email", response_model=EmailVerificationResponse)
async def verify_email(
    body: EmailVerificationRequest,
    request: Request,
    user_service: UserSvc,
    redis: Redis,
) -> Any:
    verification_service = EmailVerificationService(user_service.db, redis)
    user = await verification_service.verify_code(
        body.email,
        body.code,
        ip_address=_client_ip(request),
    )
    token = _make_token(str(user.id))
    return EmailVerificationResponse(
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        token_type=token.token_type,
        csrf_token=token.csrf_token,
    )


@router.post("/resend-verification", response_model=ResendVerificationResponse)
async def resend_verification(
    body: ResendVerificationRequest,
    request: Request,
    user_service: UserSvc,
    redis: Redis,
) -> Any:
    verification_service = EmailVerificationService(user_service.db, redis)
    return await verification_service.resend_code(
        body.email,
        ip_address=_client_ip(request),
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    user_service: UserSvc,
    redis: Redis,
) -> Any:
    reset_service = PasswordResetService(user_service.db, redis)
    await reset_service.request_reset(body.email, ip_address=_client_ip(request))
    return ForgotPasswordResponse()


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    body: ResetPasswordRequest,
    user_service: UserSvc,
    redis: Redis,
) -> Any:
    reset_service = PasswordResetService(user_service.db, redis)
    await reset_service.reset_password(body.token, body.password)
    return ResetPasswordResponse()


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: CurrentUser) -> Any:
    """Get current authenticated user information."""
    return current_user
