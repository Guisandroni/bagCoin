"""Password reset service."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.redis import RedisClient
from app.core.config import settings
from app.core.exceptions import AuthenticationError, BadRequestError, RateLimitError
from app.core.security import get_password_hash, verify_password
from app.repositories import user_repo
from app.schemas.user import _validate_password_complexity
from app.services.email_delivery import send_plain_email


class PasswordResetService:
    """Issue and consume password reset links."""

    def __init__(self, db: AsyncSession, redis: RedisClient):
        self.db = db
        self.redis = redis

    async def request_reset(self, email: str, *, ip_address: str) -> None:
        """Send a reset link when the user exists; avoid account enumeration."""
        await self._ensure_rate_limit(email, ip_address)
        user = await user_repo.get_by_email(self.db, email.lower())
        if not user or not user.hashed_password:
            return

        token = secrets.token_urlsafe(48)
        expires_at = datetime.now(UTC) + timedelta(seconds=settings.PASSWORD_RESET_TTL_SECONDS)
        await user_repo.update(
            self.db,
            db_user=user,
            update_data={
                "password_reset_token_hash": get_password_hash(token),
                "password_reset_expires_at": expires_at,
                "password_reset_sent_at": datetime.now(UTC),
            },
        )
        await self.db.commit()
        reset_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?token={token}"
        await send_plain_email(
            to_email=user.email,
            subject="BagCoin - Redefinição de senha",
            body="\n".join(
                [
                    "Recebemos uma solicitação para redefinir sua senha no BagCoin.",
                    "",
                    "Acesse o link abaixo para criar uma nova senha:",
                    reset_url,
                    "",
                    f"Esse link expira em {settings.PASSWORD_RESET_TTL_SECONDS // 60} minutos.",
                    "Se você não solicitou essa alteração, ignore este email.",
                ]
            ),
        )

    async def reset_password(self, token: str, password: str) -> None:
        """Reset a password using a valid token."""
        try:
            _validate_password_complexity(password)
        except ValueError as exc:
            raise BadRequestError(message=str(exc), code="PASSWORD_POLICY_INVALID") from exc
        users = await user_repo.get_multi(self.db, limit=1000)
        now = datetime.now(UTC)
        for user in users:
            expires_at = user.password_reset_expires_at
            token_hash = user.password_reset_token_hash
            if not expires_at or not token_hash:
                continue
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= now:
                continue
            if verify_password(token, token_hash):
                await user_repo.update(
                    self.db,
                    db_user=user,
                    update_data={
                        "hashed_password": get_password_hash(password),
                        "password_reset_token_hash": None,
                        "password_reset_expires_at": None,
                        "password_reset_sent_at": None,
                    },
                )
                await self.db.commit()
                return
        raise AuthenticationError(
            message="Link de redefinição inválido ou expirado",
            code="PASSWORD_RESET_INVALID",
        )

    async def _ensure_rate_limit(self, email: str, ip_address: str) -> None:
        cooldown_keys = (
            f"password-reset:cooldown:email:{email.lower()}",
            f"password-reset:cooldown:ip:{ip_address}",
        )
        for key in cooldown_keys:
            retry_after = await self.redis.ttl(key)
            if retry_after > 0:
                raise RateLimitError(
                    message="Aguarde 3 minutos antes de solicitar outro link.",
                    code="PASSWORD_RESET_COOLDOWN",
                    details={"retry_after_seconds": retry_after},
                )

        for key in (
            f"password-reset:email:{email.lower()}",
            f"password-reset:ip:{ip_address}",
        ):
            current = await self.redis.incr(key)
            if current == 1:
                await self.redis.expire(key, 3600)
            if current > settings.PASSWORD_RESET_SEND_LIMIT_PER_HOUR:
                retry_after = await self.redis.ttl(key)
                raise RateLimitError(
                    message="Muitas solicitações de redefinição. Aguarde um pouco antes de tentar novamente.",
                    code="PASSWORD_RESET_RATE_LIMITED",
                    details={"retry_after_seconds": max(retry_after, 0)},
                )

        for key in cooldown_keys:
            await self.redis.set(key, "1", ttl=settings.PASSWORD_RESET_REQUEST_COOLDOWN_SECONDS)
