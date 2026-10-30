"""Webhook routes for BagCoin WhatsApp message processing.

Receives Evolution API events and processes them via the LangGraph orchestrator.
"""

import base64
import json
import logging
import os
import re
import secrets

from fastapi import APIRouter, Header, HTTPException, Request

from app.agents.graph import orchestrator
from app.agents.tenant_context import tenant_phone_error
from app.core.config import settings
from app.services.evolution_events import (
    claim_reply,
    finish_event,
    finish_reply,
    mark_event_uncertain,
    reserve_event,
)
from app.services.whatsapp_service import (
    get_whatsapp_media,
    send_whatsapp_document,
    send_whatsapp_message,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])

# Redis client para deduplicação (lazy init)
_redis = None
_redis_initialized = False


def _get_redis():
    global _redis, _redis_initialized
    if _redis_initialized:
        return _redis
    _redis_initialized = True
    try:
        import redis as redis_module

        _redis = redis_module.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=2)
        _redis.ping()
        logger.info("Redis conectado para deduplicação")
    except Exception as e:
        logger.warning(f"Redis indisponível para deduplicação: {e}")
        _redis = None
    return _redis


def _source_format_from_payload(message_type: str | None, media: dict | None = None) -> str:
    """Normalize WhatsApp message types into BagCoin source formats."""
    media_type = str((media or {}).get("mimetype") or "").lower()
    raw_type = str(message_type or "").lower()

    if media_type.startswith("audio/") or raw_type in {"ptt", "audio", "voice"}:
        return "audio"
    if media_type.startswith("image/") or raw_type in {"image", "sticker"}:
        return "image"
    if media_type or raw_type in {"document", "file"}:
        return "document"
    return "text"


@router.post("/evolution", tags=["csrf-exempt"])
async def receive_evolution_message(
    request: Request,
    x_evolution_webhook_secret: str = Header(default=""),
):
    """Receive one Evolution event without retrying ambiguous financial actions."""
    secret = settings.EVOLUTION_WEBHOOK_SECRET
    if not secret or not secrets.compare_digest(x_evolution_webhook_secret, secret):
        raise HTTPException(status_code=401, detail="Credencial inválida")

    body = bytearray()
    limit = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 * 4 // 3 + 524288
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            raise HTTPException(status_code=413, detail="Mensagem excede o limite")
    try:
        event = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Evento inválido") from None
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="Evento inválido")
    if not settings.EVOLUTION_INSTANCE_NAME or event.get("instance") != settings.EVOLUTION_INSTANCE_NAME:
        raise HTTPException(status_code=403, detail="Instância inválida")
    if str(event.get("event", "")).lower().replace("_", ".") != "messages.upsert":
        return {"status": "ignored"}
    data = event.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("key"), dict):
        raise HTTPException(status_code=400, detail="Mensagem inválida")
    key = data["key"]
    if key.get("fromMe") is not False:
        return {"status": "ignored"}
    jid = key.get("remoteJid")
    if not isinstance(jid, str) or jid.endswith("@g.us"):
        return {"status": "ignored"}
    if jid.endswith("@lid"):
        jid = key.get("remoteJidAlt", "")
    if not isinstance(jid, str) or not re.fullmatch(r"[0-9]{8,15}@s\.whatsapp\.net", jid):
        return {"status": "ignored"}
    phone = jid.split("@")[0]
    if tenant_phone_error(phone):
        return {"status": "ignored"}
    message_id = key.get("id")
    if not isinstance(message_id, str) or not message_id.strip() or len(message_id) > 255:
        raise HTTPException(status_code=400, detail="Identificador inválido")
    message = data.get("message")
    if not isinstance(message, dict):
        return {"status": "ignored"}
    text = message.get("conversation")
    if not isinstance(text, str):
        extended = message.get("extendedTextMessage")
        text = extended.get("text", "") if isinstance(extended, dict) else ""
    if not isinstance(text, str):
        raise HTTPException(status_code=400, detail="Texto inválido")
    media_type = next((name for name in ("imageMessage", "audioMessage", "documentMessage") if isinstance(message.get(name), dict)), None)
    if not text and not media_type:
        return {"status": "ignored"}

    from sqlalchemy import select

    from app.db.models.evolution_event import EvolutionReply
    from app.db.session import sync_session_maker

    try:
        with sync_session_maker() as db:
            reservation = reserve_event(db, settings.EVOLUTION_INSTANCE_NAME, message_id)
            db.commit()
        if reservation is None:
            return {"status": "duplicate"}
    except Exception:
        logger.error("Falha ao reservar evento Evolution")
        raise HTTPException(status_code=503, detail="Processamento indisponível") from None
    event_id, owner = reservation
    try:
        media = None
        if media_type:
            retrieved = await get_whatsapp_media(data)
            if not retrieved:
                raise ValueError("Mídia indisponível")
            details = message[media_type]
            default_mime = {"imageMessage": "image/jpeg", "audioMessage": "audio/ogg", "documentMessage": "application/pdf"}[media_type]
            media = {"data": retrieved["base64"], "mimetype": retrieved.get("mimetype") or details.get("mimetype") or default_mime, "filename": retrieved.get("fileName") or details.get("fileName", "")}
            caption = details.get("caption", "")
            text = text or (caption if isinstance(caption, str) else "")
        state = {"phone_number": phone, "user_id": None, "message": text, "context": {"channel": "whatsapp", **({"media": media} if media else {})}, "error": None, "source_format": _source_format_from_payload(media_type, media)}
        result = orchestrator.invoke(state)
        if result.get("error"):
            raise ValueError("Processamento não concluído")
        replies = [{"type": "text", "number": phone, "text": result.get("response") or "Processamento concluído."}]
        report_path = result.get("report_path")
        if report_path and not os.path.isfile(report_path):
            raise ValueError("Relatório indisponível")
        if report_path and os.path.isfile(report_path):
            with open(report_path, "rb") as report:
                report_data = report.read(settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1)
            if len(report_data) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                raise ValueError("Relatório excede o limite")
            pdf = base64.b64encode(report_data).decode("ascii")
            replies.append({"type": "document", "number": phone, "data": pdf, "filename": os.path.basename(report_path), "mimetype": "application/pdf"})
        with sync_session_maker() as db:
            if not finish_event(db, event_id, owner, replies):
                raise RuntimeError("Evento não reservado")
            db.commit()
            reply_ids = list(db.scalars(select(EvolutionReply.id).where(EvolutionReply.event_id == event_id).order_by(EvolutionReply.position)))
        sent = False
        for reply_id, reply in zip(reply_ids, replies, strict=True):
            with sync_session_maker() as db:
                claimed = claim_reply(db, reply_id)
                db.commit()
            if not claimed:
                sent = False
                break
            sent = await (send_whatsapp_message(phone, reply["text"]) if reply["type"] == "text" else send_whatsapp_document(phone, reply))
            with sync_session_maker() as db:
                finish_reply(db, reply_id, delivered=sent)
                db.commit()
            if not sent:
                break
        return {"status": "completed" if sent else "delivery_uncertain"}
    except Exception:
        logger.error("Falha no processamento de evento Evolution")
        try:
            with sync_session_maker() as db:
                mark_event_uncertain(db, event_id, owner)
                db.commit()
        except Exception:
            logger.error("Falha ao registrar estado incerto")
        raise HTTPException(status_code=503, detail="Evento requer reconciliação") from None


@router.get("/health")
async def webhook_health():
    """Health check do webhook."""
    r = _get_redis()
    redis_status = "ok" if (r and r.ping()) else "unavailable"
    return {"status": "ok", "service": "webhook", "redis": redis_status}
