"""Webhook routes for BagCoin WhatsApp message processing.

Receives messages from WhatsApp Bridge, validates, deduplicates,
and processes via the LangGraph orchestrator.
"""

import base64
import logging
import os
import re
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse

from app.agents.orchestrator import orchestrator
from app.agents.persistence import get_or_create_user_sync
from app.agents.tenant_context import tenant_phone_error
from app.api.deps import verify_api_key as verify_telegram_api_key
from app.core.config import settings
from app.schemas.common import (
    TelegramResponse,
    TelegramWebhookPayload,
    WebhookPayload,
    WhatsAppResponse,
)
from app.services.integration_service import redact_message_for_log

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


def normalize_whatsapp_id(chat_id: str) -> str:
    """Remove @c.us, @lid, @g.us e outros sufixos, mantendo só dígitos."""
    if not chat_id:
        return chat_id
    number = chat_id.split("@")[0]
    return re.sub(r"\D", "", number)


def is_duplicate_message(message_id: str) -> bool:
    """Retorna True se a mensagem já foi processada nos últimos 60 segundos.

    Uses atomic SET NX to prevent race conditions with multiple workers.
    """
    r = _get_redis()
    if not message_id or not r:
        return False
    key = f"msg:processed:{message_id}"
    # SET NX is atomic: returns True only if the key was set (first caller wins)
    was_set = r.set(key, "1", nx=True, ex=60)
    return not was_set  # If was_set is False/None, key already existed → duplicate


def _source_format_from_payload(message_type: str | None, media: dict | None = None) -> str:
    """Normalize WhatsApp/bridge message types into BagCoin source formats."""
    media_type = str((media or {}).get("mimetype") or "").lower()
    raw_type = str(message_type or "").lower()

    if media_type.startswith("audio/") or raw_type in {"ptt", "audio", "voice"}:
        return "audio"
    if media_type.startswith("image/") or raw_type in {"image", "sticker"}:
        return "image"
    if media_type or raw_type in {"document", "file"}:
        return "document"
    return "text"


async def verify_api_key(x_api_key: str = Header(...)):
    """Verifica a API key do WhatsApp Bridge."""
    if x_api_key != settings.WHATSAPP_API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")
    return x_api_key


async def verify_any_bridge_api_key(x_api_key: str = Header(...)):
    """Accept either WHATSAPP_API_KEY or the general API_KEY (used by bridges)."""
    valid_keys = [
        settings.WHATSAPP_API_KEY,
        settings.API_KEY,
    ]
    if not any(
        k and secrets.compare_digest(x_api_key, k) for k in valid_keys if isinstance(k, str)
    ):
        raise HTTPException(status_code=401, detail="API Key inválida")
    return x_api_key


@router.post("/whatsapp", response_model=WhatsAppResponse, tags=["csrf-exempt"])
async def receive_whatsapp_message(
    payload: WebhookPayload,
    api_key: str = Depends(verify_api_key),
):
    """Recebe mensagens do WhatsApp Bridge e processa via orquestrador."""

    # 1. Sanitiza phone_number
    raw_phone = payload.phone_number
    phone_number = normalize_whatsapp_id(raw_phone)

    terr = tenant_phone_error(phone_number)
    if terr:
        logger.warning(f"Webhook rejeitado — telefone inválido após normalização: {raw_phone!r}")
        return WhatsAppResponse(reply=f"⚠️ {terr}", actions=[])

    logger.info(
        "Webhook recebido de %s → %s: %s",
        raw_phone,
        phone_number,
        redact_message_for_log(payload.message or "", 50),
    )

    # 2. Deduplicação por message_id (se disponível) ou conteúdo
    msg_id = payload.raw_data.get("id") if payload.raw_data else None
    if not msg_id:
        msg_id = f"{phone_number}:{payload.message}:{payload.timestamp}"

    if is_duplicate_message(msg_id):
        logger.info(f"Mensagem {msg_id} já processada. Ignorando.")
        return WhatsAppResponse(reply="", actions=[])

    try:
        # 3. Determina formato da fonte
        source_format = _source_format_from_payload(payload.type, payload.media)

        # 4. Prepara estado inicial
        context = {"channel": "whatsapp"}
        if payload.media:
            context["media"] = payload.media

        initial_state = {
            "phone_number": phone_number,
            "user_id": None,
            "message": payload.message or "",
            "intent": None,
            "extracted_data": None,
            "query_result": None,
            "report_id": None,
            "report_path": None,
            "report_summary": None,
            "response": None,
            "context": context,
            "error": None,
            "source_format": source_format,
        }

        # 5. Executa o grafo de orquestração
        result = orchestrator.invoke(initial_state)

        response_text = result.get("response") or "Processamento concluído. Se precisar de algo, é só falar! 😊"

        logger.info(f"Resposta gerada para {phone_number}: {response_text[:100]}...")

        # 6. Se um relatório PDF foi gerado, lê e inclui na resposta
        document = None
        media = None
        report_path = result.get("report_path")
        report_id = result.get("report_id")

        if report_path and os.path.exists(report_path):
            try:
                with open(report_path, "rb") as f:
                    pdf_data = base64.b64encode(f.read()).decode("utf-8")
                filename = os.path.basename(report_path)
                document = {
                    "mimetype": "application/pdf",
                    "data": pdf_data,
                    "filename": filename,
                }
                logger.info(f"PDF anexado à resposta: {filename}")
            except Exception as e:
                logger.error(f"Erro ao ler PDF para envio: {e}")

        # HTTP-based download link (preferred for Telegram bridge)
        if report_id:
            filename = (
                os.path.basename(report_path)
                if report_path
                else f"relatorio_{report_id}.pdf"
            )
            base_url = getattr(settings, "INTERNAL_API_BASE_URL", None) or "http://app:8000"
            media = {
                "type": "document",
                "url": f"{base_url}/api/v1/webhook/reports/{report_id}/download",
                "filename": filename,
                "mimetype": "application/pdf",
            }

        return WhatsAppResponse(
            reply=response_text,
            document=document,
            media=media,
            actions=[],
        )

    except Exception as e:
        logger.error(f"Erro no processamento do webhook: {e}", exc_info=True)
        return WhatsAppResponse(
            reply="Ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.",
            actions=[],
        )


@router.post("/telegram", response_model=TelegramResponse, tags=["csrf-exempt"])
async def receive_telegram_message(
    payload: TelegramWebhookPayload,
    api_key: str = Depends(verify_telegram_api_key),
):
    """Recebe mensagens do Telegram bridge e processa via orquestrador."""

    # 1. Cria phone_number sintético
    phone_number = f"telegram:{payload.chat_id}"

    terr = tenant_phone_error(phone_number)
    if terr:
        logger.warning(f"Telegram webhook rejeitado — telefone inválido: {phone_number!r}")
        return TelegramResponse(reply=f"⚠️ {terr}", actions=[])

    # 2. Busca ou cria usuário unificado para garantir que existe
    try:
        get_or_create_user_sync(phone_number)
    except Exception as e:
        logger.error(f"Erro ao buscar/criar usuário para {phone_number}: {e}")
        return TelegramResponse(
            reply="Erro ao identificar usuário. Tente novamente.",
            actions=[],
        )

    logger.info(
        "Telegram webhook recebido de %s (username=%s): %s",
        payload.chat_id,
        payload.username,
        redact_message_for_log(payload.message or "", 50),
    )

    # 3. Deduplicação simples (baseada em chat_id + message)
    msg_id = f"telegram:{payload.chat_id}:{payload.message}"
    if is_duplicate_message(msg_id):
        logger.info(f"Mensagem {msg_id} já processada. Ignorando.")
        return TelegramResponse(reply="", actions=[])

    try:
        # 4. Determina formato da fonte
        source_format = payload.source_format or "text"

        # 5. Prepara estado inicial
        context = {"channel": "telegram"}
        if payload.media:
            context["media"] = payload.media

        initial_state = {
            "phone_number": phone_number,
            "user_id": None,
            "message": payload.message or "",
            "intent": None,
            "extracted_data": None,
            "query_result": None,
            "report_id": None,
            "report_path": None,
            "report_summary": None,
            "response": None,
            "context": context,
            "error": None,
            "source_format": source_format,
        }

        # 6. Executa o grafo de orquestração
        result = orchestrator.invoke(initial_state)

        response_text = result.get("response") or "Processamento concluído. Se precisar de algo, é só falar! 😊"

        logger.info(f"Resposta gerada para {phone_number}: {response_text[:100]}...")

        # Attach media URL if a report was generated (Bug 8.2 fix)
        media = None
        report_id = result.get("report_id")
        report_path = result.get("report_path")
        if report_id:
            filename = (
                os.path.basename(report_path)
                if report_path
                else f"relatorio_{report_id}.pdf"
            )
            base_url = getattr(settings, "INTERNAL_API_BASE_URL", None) or "http://app:8000"
            media = {
                "type": "document",
                "url": f"{base_url}/api/v1/webhook/reports/{report_id}/download",
                "filename": filename,
                "mimetype": "application/pdf",
            }

        return TelegramResponse(
            reply=response_text,
            media=media,
            actions=[],
        )

    except Exception as e:
        logger.error(f"Erro no processamento do webhook Telegram: {e}", exc_info=True)
        return TelegramResponse(
            reply="Ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.",
            actions=[],
        )


@router.get("/health")
async def webhook_health():
    """Health check do webhook."""
    r = _get_redis()
    redis_status = "ok" if (r and r.ping()) else "unavailable"
    return {"status": "ok", "service": "webhook", "redis": redis_status}


@router.get("/reports/{report_id}/download")
async def download_internal_report(
    report_id: int,
    _: str = Depends(verify_any_bridge_api_key),
):
    """Download endpoint for bridges (Bug 8.2 fix).

    Accepts either WHATSAPP_API_KEY or API_KEY — each bridge uses its own.
    Streams the PDF file. No per-user auth here because the URL only comes
    from orchestrator responses where ownership was already enforced.
    """
    from app.db.session import sync_session_maker
    from app.services.report_sync import get_report_sync

    db = sync_session_maker()
    try:
        report = get_report_sync(db, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        if not report.file_url or not os.path.exists(report.file_url):
            raise HTTPException(status_code=404, detail="Report file missing on disk")
        filename = os.path.basename(report.file_url)
        return FileResponse(
            path=report.file_url,
            media_type="application/pdf",
            filename=filename,
        )
    finally:
        db.close()
