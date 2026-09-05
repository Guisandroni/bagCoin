"""Web ↔ WhatsApp/Telegram pairing via short-lived opaque tokens."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.parse import quote

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.db.models.integration_link_token import IntegrationLinkToken
from app.db.models.user import User
from app.db.session import sync_session_maker
from app.schemas.integration import IntegrationStatus, LinkTokenResponse

logger = logging.getLogger(__name__)

PAIR_KEY_PREFIX = "pair:tok:"

LINK_TOKEN_RE = re.compile(
    r"^\s*(?:Enviando token para autenticacao\.\s*)?(?:#bagcoin\s+link|/start)\s+([A-Za-z0-9_-]{16,})\s*$",
    re.IGNORECASE,
)

IntegrationChannel = Literal["whatsapp", "telegram"]


def _whatsapp_bot_digits() -> str:
    """E.164 digits only for wa.me deeplinks."""
    return (settings.BOT_WHATSAPP_NUMBER or "").strip().replace("+", "").replace(" ", "")


def _telegram_bot_username() -> str:
    """Telegram bot username without @."""
    return (settings.BOT_TELEGRAM_USERNAME or "").strip().lstrip("@")


def parse_link_token_from_message(message: str) -> str | None:
    """Return opaque token if message is a pairing command, else None."""
    m = LINK_TOKEN_RE.match(message or "")
    return m.group(1) if m else None


REDACT_PAIRING_RE = re.compile(
    r"(#bagcoin\s+link\s+|/start\s+)([A-Za-z0-9_-]{16,})",
    re.IGNORECASE,
)


def redact_message_for_log(message: str | None, max_preview: int = 120) -> str:
    """Strip opaque pairing tokens from log lines (bridge/webhook must not leak tokens)."""
    if not message:
        return ""
    tail = "..." if len(message) > max_preview else ""
    s = message[:max_preview]
    s = REDACT_PAIRING_RE.sub(r"\1[REDACTED]", s)
    return s + tail


def _sync_redis():
    try:
        import redis as redis_sync

        r = redis_sync.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=2)
        r.ping()
        return r
    except Exception as e:
        logger.warning("Redis unavailable for integration tokens: %s", e)
        return None


def _redis_set_nx(token: str, payload: str, ttl: int) -> bool | None:
    """Return True if set, False if key exists, None if Redis unavailable."""
    r = _sync_redis()
    if not r:
        return None
    key = f"{PAIR_KEY_PREFIX}{token}"
    ok = r.set(key, payload, nx=True, ex=ttl)
    return bool(ok)


def _redis_getdel(token: str) -> str | None:
    """Atomically read and remove token payload from Redis."""
    r = _sync_redis()
    if not r:
        return None
    key = f"{PAIR_KEY_PREFIX}{token}"
    try:
        return r.getdel(key)  # type: ignore[no-any-return]
    except Exception:
        pipe = r.pipeline()
        pipe.get(key)
        pipe.delete(key)
        res = pipe.execute()
        return res[0] if res else None


def _merge_channel_user_into_web_user_sync(db: Session, web_user: User, channel_user: User) -> None:
    """Move channel-owned data into the web user and remove the duplicate row."""
    if web_user.id == channel_user.id:
        return

    from app.db.models.account import Account
    from app.db.models.agent_log import AgentLog
    from app.db.models.budget import Budget
    from app.db.models.category import Category
    from app.db.models.chat_file import ChatFile
    from app.db.models.conversation import Conversation
    from app.db.models.conversation_share import ConversationShare
    from app.db.models.credit_card import CreditCard
    from app.db.models.goal import Goal
    from app.db.models.integration_link_token import IntegrationLinkToken
    from app.db.models.message_rating import MessageRating
    from app.db.models.phone_conversation import PhoneConversation
    from app.db.models.recurring_transaction import RecurringTransaction
    from app.db.models.report import Report
    from app.db.models.transaction import Transaction

    source_id = channel_user.id
    target_id = web_user.id

    if channel_user.phone_number and not web_user.phone_number:
        # Free the unique phone_number before assigning it to the web user.
        phone_number = channel_user.phone_number
        channel_user.phone_number = None
        db.flush()
        web_user.phone_number = phone_number
    if channel_user.telegram_chat_id and not web_user.telegram_chat_id:
        telegram_chat_id = channel_user.telegram_chat_id
        channel_user.telegram_chat_id = None
        db.flush()
        web_user.telegram_chat_id = telegram_chat_id
    if not web_user.platform and channel_user.platform:
        web_user.platform = channel_user.platform
    if not web_user.preferences and channel_user.preferences:
        web_user.preferences = channel_user.preferences
    if not web_user.financial_profile and channel_user.financial_profile:
        web_user.financial_profile = channel_user.financial_profile

    for model in (
        Account,
        AgentLog,
        Budget,
        Category,
        ChatFile,
        Conversation,
        CreditCard,
        Goal,
        IntegrationLinkToken,
        MessageRating,
        PhoneConversation,
        RecurringTransaction,
        Report,
        Transaction,
    ):
        db.execute(update(model).where(model.user_id == source_id).values(user_id=target_id))

    db.execute(
        update(ConversationShare)
        .where(ConversationShare.shared_by == source_id)
        .values(shared_by=target_id)
    )
    db.execute(
        update(ConversationShare)
        .where(ConversationShare.shared_with == source_id)
        .values(shared_with=target_id)
    )
    db.flush()
    db.delete(channel_user)


def try_consume_link_pairing_sync(
    *,
    phone_number: str,
    message: str,
    channel: IntegrationChannel,
    source_format: str,
) -> str | None:
    """If message is a pairing command, consume token and merge; else None.

    Returns a user-facing reply string when handled, or None when not a link command.
    """
    if source_format != "text":
        return None
    token = parse_link_token_from_message(message)
    if not token:
        return None

    from app.agents.persistence import ensure_default_categories_sync

    err_invalid = (
        "Não consegui validar o link. O código pode ter expirado ou já foi usado. "
        "Gere um novo em Configurações → Integrações no site."
    )
    err_channel = (
        "Este link foi gerado para outro canal. Use o botão certo (WhatsApp ou Telegram) no site."
    )

    db = sync_session_maker()
    raw_redis: str | None = None
    try:
        raw_redis = _redis_getdel(token)
        data: dict[str, Any] | None = None
        db_row: IntegrationLinkToken | None = None

        if raw_redis:
            try:
                data = json.loads(raw_redis)
            except json.JSONDecodeError:
                return err_invalid
            if data.get("channel") != channel:
                return err_channel
        else:
            now = datetime.now(UTC)
            db_row = (
                db.query(IntegrationLinkToken)
                .filter(
                    IntegrationLinkToken.token == token,
                    IntegrationLinkToken.consumed_at.is_(None),
                    IntegrationLinkToken.expires_at > now,
                )
                .with_for_update()
                .one_or_none()
            )
            if db_row:
                if db_row.channel != channel:
                    return err_channel
                data = {"user_id": str(db_row.user_id), "channel": db_row.channel}

        if not data:
            return err_invalid

        try:
            target_user_id = int(data["user_id"])
        except (TypeError, ValueError):
            return err_invalid
        web_user = db.query(User).filter(User.id == target_user_id).with_for_update().one_or_none()
        if not web_user:
            return "Conta não encontrada. Gere um novo link no site."

        channel_user = db.query(User).filter(User.phone_number == phone_number).one_or_none()

        if channel_user is None:
            web_user.phone_number = phone_number
            web_user.platform = web_user.platform or channel
            web_user.preferences = web_user.preferences or {"language": "pt-BR", "currency": "BRL"}
            web_user.financial_profile = web_user.financial_profile or {}
            ensure_default_categories_sync(db, web_user)
            name = web_user.full_name or "pronto"
            reply = (
                f"Tudo certo, {name}! Sua conta foi conectada. "
                "Pode lançar transações por aqui e ver tudo no painel web."
            )
        elif web_user.id == channel_user.id:
            name = web_user.full_name or "tudo certo"
            reply = f"Olá, {name}! Sua conta já estava conectada. Pode lançar transações por aqui. 😊"
        elif web_user.phone_number and web_user.phone_number != phone_number:
            return (
                "Sua conta web já está vinculada a outro número. "
                "Desvincule ou use a mesma conta no site."
            )
        else:
            _merge_channel_user_into_web_user_sync(db, web_user, channel_user)
            ensure_default_categories_sync(db, web_user)
            name = web_user.full_name or "pronto"
            reply = (
                f"Tudo certo, {name}! Sua conta foi conectada. "
                "Pode lançar transações por aqui e ver tudo no painel web."
            )

        if db_row is not None:
            db_row.consumed_at = datetime.now(UTC)
        db.commit()

        return reply
    except Exception as e:
        db.rollback()
        logger.exception("Pairing merge failed: %s", e)
        return "Não consegui concluir o vínculo agora. Tente de novo em instantes ou gere outro código no site."
    finally:
        db.close()


def _store_token_db_fallback(db: Session, token: str, user_id: int, channel: str, expires_at: datetime) -> None:
    row = IntegrationLinkToken(
        token=token,
        user_id=user_id,
        channel=channel,
        expires_at=expires_at,
    )
    db.add(row)
    db.flush()


class IntegrationService:
    """Create pairing tokens (async API) and expose status."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _build_deeplinks(self, token: str) -> tuple[str | None, str | None, str, str]:
        wa_cmd = f"Enviando token para autenticacao. #bagcoin link {token}"
        tg_cmd = f"/start {token}"
        wa_num = _whatsapp_bot_digits()
        deeplink_wa = (
            f"https://wa.me/{wa_num}?text={quote(wa_cmd, safe='')}" if wa_num else None
        )
        tg_user = _telegram_bot_username()
        deeplink_tg = f"https://t.me/{tg_user}?start={token}" if tg_user else None
        return deeplink_wa, deeplink_tg, wa_cmd, tg_cmd

    async def create_link_token(
        self,
        user_id: int,
        channel: IntegrationChannel,
    ) -> LinkTokenResponse:
        if channel == "whatsapp" and not _whatsapp_bot_digits():
            raise ValidationError(
                message=(
                    "O número do bot WhatsApp não está configurado no servidor. "
                    "Peça ao administrador para definir BOT_WHATSAPP_NUMBER."
                ),
                code="INTEGRATION_BOT_NOT_CONFIGURED",
                details={"channel": "whatsapp", "missing_env": "BOT_WHATSAPP_NUMBER"},
            )
        if channel == "telegram" and not _telegram_bot_username():
            raise ValidationError(
                message=(
                    "O bot Telegram não está configurado no servidor. "
                    "Peça ao administrador para definir BOT_TELEGRAM_USERNAME."
                ),
                code="INTEGRATION_BOT_NOT_CONFIGURED",
                details={"channel": "telegram", "missing_env": "BOT_TELEGRAM_USERNAME"},
            )

        ttl = settings.INTEGRATION_LINK_TOKEN_TTL_SECONDS
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl)

        for _ in range(8):
            token = secrets.token_urlsafe(16)
            payload = json.dumps({"user_id": str(user_id), "channel": channel})
            stored = await asyncio.to_thread(_redis_set_nx, token, payload, ttl)
            if stored is True:
                break
            if stored is None:
                await self.db.run_sync(
                    lambda s, token=token: _store_token_db_fallback(
                        s, token, user_id, channel, expires_at
                    )
                )
                await self.db.commit()
                break
            # collision — retry
        else:
            raise RuntimeError("Could not allocate unique pairing token")

        deeplink_wa, deeplink_tg, wa_cmd, tg_cmd = self._build_deeplinks(token)
        return LinkTokenResponse(
            token=token,
            expires_at=expires_at,
            deeplink_whatsapp=deeplink_wa,
            deeplink_telegram=deeplink_tg,
            manual_command_whatsapp=wa_cmd,
            manual_command_telegram=tg_cmd,
        )

    async def status(self, user: User) -> IntegrationStatus:
        phone = user.phone_number
        wa = bool(phone and not phone.startswith("telegram:"))
        tg = bool(phone and phone.startswith("telegram:"))
        return IntegrationStatus(
            whatsapp_linked=wa,
            telegram_linked=tg,
            phone_number=phone,
        )
