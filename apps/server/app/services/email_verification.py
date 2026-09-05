"""Email verification service."""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.redis import RedisClient
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    BadRequestError,
    ExternalServiceError,
    RateLimitError,
)
from app.core.security import get_password_hash, verify_password
from app.db.models.user import User
from app.repositories import user_repo
from app.schemas.auth import AuthPendingResponse, ResendVerificationResponse

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VerificationDispatchResult:
    """Metadata returned after issuing a verification code."""

    expires_in_seconds: int
    resend_available_in_seconds: int


class EmailVerificationService:
    """Handle verification code issuance, rate limits, and confirmation."""

    def __init__(self, db: AsyncSession, redis: RedisClient):
        self.db = db
        self.redis = redis

    async def build_pending_response(self, user: User) -> AuthPendingResponse:
        """Build the auth-pending payload for an unverified user."""
        return AuthPendingResponse(
            email=user.email,
            auth_provider="google" if user.google_id else "email",
            expires_in_seconds=self._expires_in_seconds(user),
            resend_available_in_seconds=max(await self._resend_available_seconds(user.email), 0),
        )

    async def issue_code_for_user(
        self,
        user: User,
        *,
        ip_address: str,
        enforce_cooldown: bool = True,
    ) -> VerificationDispatchResult:
        """Generate and send a fresh verification code."""
        if user.email_verified:
            raise BadRequestError(
                message="Email já verificado",
                code="EMAIL_ALREADY_VERIFIED",
            )

        locked_retry_after = await self._lock_retry_after_seconds(user.email)
        if locked_retry_after > 0:
            raise RateLimitError(
                message=f"Você atingiu o limite de tentativas. Aguarde {locked_retry_after} segundos antes de solicitar um novo código.",
                code="EMAIL_VERIFICATION_RATE_LIMITED",
                details={"retry_after_seconds": locked_retry_after},
            )

        resend_available = await self._resend_available_seconds(user.email)
        if enforce_cooldown and resend_available > 0:
            raise RateLimitError(
                message=f"Aguarde {resend_available} segundos antes de solicitar outro código.",
                code="EMAIL_VERIFICATION_SEND_RATE_LIMITED",
                details={"retry_after_seconds": resend_available},
            )

        await self._ensure_send_allowed(user.email, ip_address)

        now = self._now()
        expires_at = now + timedelta(seconds=settings.EMAIL_VERIFICATION_TTL_SECONDS)
        code = self._generate_code()
        await user_repo.update(
            self.db,
            db_user=user,
            update_data={
                "email_verification_code_hash": get_password_hash(code),
                "email_verification_expires_at": expires_at,
                "email_verification_sent_at": now,
                "email_verification_attempts": 0,
            },
        )

        await self._send_email(user.email, code)
        await self.redis.set(
            self._cooldown_key(user.email),
            "1",
            ttl=settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS,
        )

        logger.info(
            "[email_verification] code issued",
            extra={"email": user.email, "provider": "google" if user.google_id else "email"},
        )
        return VerificationDispatchResult(
            expires_in_seconds=settings.EMAIL_VERIFICATION_TTL_SECONDS,
            resend_available_in_seconds=settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS,
        )

    async def resend_code(self, email: str, *, ip_address: str) -> ResendVerificationResponse:
        """Send a fresh verification code for a pending user."""
        user = await self._get_pending_user(email)
        dispatch = await self.issue_code_for_user(user, ip_address=ip_address, enforce_cooldown=True)
        return ResendVerificationResponse(
            resend_available_in_seconds=dispatch.resend_available_in_seconds,
            expires_in_seconds=dispatch.expires_in_seconds,
        )

    async def verify_code(self, email: str, code: str, *, ip_address: str) -> User:
        """Confirm a verification code and mark the user verified."""
        await self._ensure_verify_allowed(ip_address)
        user = await self._get_pending_user(email)
        locked_retry_after = await self._lock_retry_after_seconds(user.email)
        if locked_retry_after > 0:
            raise RateLimitError(
                message=f"Você atingiu o limite de tentativas. Aguarde {locked_retry_after} segundos antes de solicitar um novo código.",
                code="EMAIL_VERIFICATION_RATE_LIMITED",
                details={
                    "retry_after_seconds": locked_retry_after,
                    "attempts_remaining": 0,
                    "max_attempts": settings.EMAIL_VERIFICATION_MAX_ATTEMPTS,
                },
            )

        expires_at = user.email_verification_expires_at
        code_hash = user.email_verification_code_hash
        if not expires_at or not code_hash:
            raise AuthenticationError(
                message="A verificação de email é obrigatória",
                code="EMAIL_VERIFICATION_REQUIRED",
            )

        if expires_at <= self._now():
            await user_repo.update(
                self.db,
                db_user=user,
                update_data={
                    "email_verification_code_hash": None,
                    "email_verification_expires_at": None,
                    "email_verification_sent_at": None,
                    "email_verification_attempts": 0,
                },
            )
            await self.db.commit()
            raise AuthenticationError(
                message="Código expirado",
                code="EMAIL_VERIFICATION_EXPIRED",
            )

        if not verify_password(code, code_hash):
            attempts = user.email_verification_attempts + 1
            attempts_remaining = max(settings.EMAIL_VERIFICATION_MAX_ATTEMPTS - attempts, 0)
            update_data = {"email_verification_attempts": attempts}
            if attempts >= settings.EMAIL_VERIFICATION_MAX_ATTEMPTS:
                update_data.update(
                    {
                        "email_verification_code_hash": None,
                        "email_verification_expires_at": None,
                        "email_verification_sent_at": None,
                    }
                )
            await user_repo.update(self.db, db_user=user, update_data=update_data)
            if attempts >= settings.EMAIL_VERIFICATION_MAX_ATTEMPTS:
                await self.redis.set(
                    self._lock_key(user.email),
                    "1",
                    ttl=settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS,
                )
            await self.db.commit()
            if attempts >= settings.EMAIL_VERIFICATION_MAX_ATTEMPTS:
                retry_after = settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS
                raise RateLimitError(
                    message=f"Você excedeu o limite de tentativas. Aguarde {retry_after} segundos para solicitar um novo código.",
                    code="EMAIL_VERIFICATION_RATE_LIMITED",
                    details={
                        "attempts_used": attempts,
                        "attempts_remaining": 0,
                        "max_attempts": settings.EMAIL_VERIFICATION_MAX_ATTEMPTS,
                        "retry_after_seconds": retry_after,
                    },
                )
            raise AuthenticationError(
                message="Código incorreto",
                code="EMAIL_VERIFICATION_INVALID",
                details={
                    "attempts_used": attempts,
                    "attempts_remaining": attempts_remaining,
                    "max_attempts": settings.EMAIL_VERIFICATION_MAX_ATTEMPTS,
                },
            )

        verified_at = self._now()
        await user_repo.update(
            self.db,
            db_user=user,
            update_data={
                "email_verified_at": verified_at,
                "email_verification_code_hash": None,
                "email_verification_expires_at": None,
                "email_verification_sent_at": None,
                "email_verification_attempts": 0,
            },
        )
        await self.db.commit()
        logger.info("[email_verification] email verified", extra={"email": user.email})
        return user

    async def _get_pending_user(self, email: str) -> User:
        user = await user_repo.get_by_email(self.db, email.lower())
        if not user:
            raise AuthenticationError(
                message="A verificação de email é obrigatória",
                code="EMAIL_VERIFICATION_REQUIRED",
            )
        if user.email_verified:
            raise BadRequestError(
                message="Email já verificado",
                code="EMAIL_ALREADY_VERIFIED",
            )
        return user

    async def _ensure_send_allowed(self, email: str, ip_address: str) -> None:
        await self._increment_window(
            self._hourly_email_limit_key(email),
            settings.EMAIL_VERIFICATION_SEND_LIMIT_PER_HOUR,
            3600,
            "EMAIL_VERIFICATION_SEND_RATE_LIMITED",
            "Muitos códigos já foram enviados para este email. Aguarde um pouco antes de tentar novamente.",
        )
        await self._increment_window(
            self._hourly_ip_limit_key(ip_address),
            settings.EMAIL_VERIFICATION_SEND_LIMIT_PER_IP_PER_HOUR,
            3600,
            "EMAIL_VERIFICATION_SEND_RATE_LIMITED",
            "Muitas solicitações de verificação foram feitas deste endereço. Aguarde um pouco antes de tentar novamente.",
        )

    async def _ensure_verify_allowed(self, ip_address: str) -> None:
        await self._increment_window(
            self._verify_ip_limit_key(ip_address),
            settings.EMAIL_VERIFICATION_VERIFY_LIMIT_PER_10_MIN,
            600,
            "EMAIL_VERIFICATION_RATE_LIMITED",
            "Muitas tentativas de verificação foram feitas deste endereço. Aguarde um pouco antes de tentar novamente.",
        )

    async def _increment_window(
        self,
        key: str,
        limit: int,
        ttl: int,
        code: str,
        message: str,
    ) -> None:
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, ttl)
        if current > limit:
            retry_after = await self.redis.ttl(key)
            raise RateLimitError(
                message=message,
                code=code,
                details={"retry_after_seconds": max(retry_after, 0)},
            )

    async def _send_email(self, email: str, code: str) -> None:
        provider = (settings.EMAIL_PROVIDER or "smtp").strip().lower()
        if provider == "smtp":
            await self._send_email_smtp(email, code)
            return
        if provider == "resend_api":
            await self._send_email_resend_api(email, code)
            return
        raise ExternalServiceError(
            message="Provedor de email inválido",
            code="EMAIL_DELIVERY_NOT_CONFIGURED",
            details={"provider": provider},
        )

    def _build_verification_email_content(self, code: str) -> str:
        return "\n".join(
            [
                "Seu codigo de verificacao do BagCoin e:",
                "",
                code,
                "",
                f"Esse codigo expira em {settings.EMAIL_VERIFICATION_TTL_SECONDS // 60} minutos.",
                "Se voce nao solicitou este acesso, ignore este email.",
            ]
        )

    async def _send_email_smtp(self, email: str, code: str) -> None:
        if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
            raise ExternalServiceError(
                message="SMTP não está configurado",
                code="EMAIL_DELIVERY_NOT_CONFIGURED",
            )

        try:
            import aiosmtplib
        except ImportError as exc:
            raise ExternalServiceError(
                message="A dependência de SMTP não está instalada",
                code="EMAIL_DELIVERY_NOT_CONFIGURED",
            ) from exc

        message = EmailMessage()
        message["Subject"] = "BagCoin - Seu codigo de verificacao"
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = email
        message.set_content(self._build_verification_email_content(code))

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER or None,
                password=settings.SMTP_PASSWORD or None,
                start_tls=settings.SMTP_USE_TLS,
            )
        except Exception as exc:  # pragma: no cover - network failure path
            logger.exception("[email_verification] smtp send failed", extra={"email": email})
            raise ExternalServiceError(
                message="Não foi possível enviar o email de verificação",
                code="EMAIL_DELIVERY_FAILED",
            ) from exc

    async def _send_email_resend_api(self, email: str, code: str) -> None:
        if not settings.RESEND_API_KEY or not settings.RESEND_FROM_EMAIL:
            raise ExternalServiceError(
                message="Resend não está configurado",
                code="EMAIL_DELIVERY_NOT_CONFIGURED",
            )

        payload = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [email],
            "subject": "BagCoin - Seu codigo de verificacao",
            "text": self._build_verification_email_content(code),
        }
        headers = {
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{settings.RESEND_API_BASE_URL.rstrip('/')}/emails"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network failure path
            logger.exception("[email_verification] resend send failed", extra={"email": email})
            raise ExternalServiceError(
                message="Não foi possível enviar o email de verificação",
                code="EMAIL_DELIVERY_FAILED",
            ) from exc

    async def _resend_available_seconds(self, email: str) -> int:
        ttl = await self.redis.ttl(self._cooldown_key(email.lower()))
        return ttl if ttl > 0 else 0

    async def _lock_retry_after_seconds(self, email: str) -> int:
        ttl = await self.redis.ttl(self._lock_key(email.lower()))
        return ttl if ttl > 0 else 0

    def _expires_in_seconds(self, user: User) -> int:
        if not user.email_verification_expires_at:
            return settings.EMAIL_VERIFICATION_TTL_SECONDS
        remaining = int((user.email_verification_expires_at - self._now()).total_seconds())
        return max(remaining, 0)

    def _cooldown_key(self, email: str) -> str:
        return f"email-verify:send:cooldown:{email.lower()}"

    def _hourly_email_limit_key(self, email: str) -> str:
        return f"email-verify:send:hour:{email.lower()}"

    def _lock_key(self, email: str) -> str:
        return f"email-verify:lock:{email.lower()}"

    def _hourly_ip_limit_key(self, ip_address: str) -> str:
        return f"email-verify:send:ip:{ip_address}"

    def _verify_ip_limit_key(self, ip_address: str) -> str:
        return f"email-verify:verify:ip:{ip_address}"

    def _generate_code(self) -> str:
        return "".join(secrets.choice("0123456789") for _ in range(6))

    def _now(self) -> datetime:
        return datetime.now(UTC)
