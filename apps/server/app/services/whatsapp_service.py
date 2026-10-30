"""Send WhatsApp messages through the configured Evolution instance."""

import base64
import binascii
import json
import logging
from pathlib import PurePath
from urllib.parse import quote

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)
_MESSAGE_LIMIT = 4000


def _endpoint(path: str) -> str:
    return (
        f"{settings.EVOLUTION_API_URL.rstrip('/')}/{path}/"
        f"{quote(settings.EVOLUTION_INSTANCE_NAME, safe='')}"
    )


def _configured() -> bool:
    return bool(
        settings.EVOLUTION_API_URL
        and settings.EVOLUTION_API_KEY
        and settings.EVOLUTION_INSTANCE_NAME
    )


def _valid_media(data: str) -> bool:
    limit = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(data) > ((limit + 2) // 3) * 4:
        return False
    try:
        decoded = base64.b64decode(data, validate=True)
    except (ValueError, binascii.Error):
        return False
    return bool(decoded) and len(decoded) <= limit


async def send_whatsapp_message(phone_number: str, message: str) -> bool:
    """Envia texto sem repetir automaticamente chamadas com resultado incerto."""
    if not _configured() or not phone_number or not message:
        logger.error("Evolution API não configurada")
        return False
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for offset in range(0, len(message), _MESSAGE_LIMIT):
                response = await client.post(
                    _endpoint("message/sendText"),
                    json={"number": phone_number, "text": message[offset:offset + _MESSAGE_LIMIT]},
                    headers={"apikey": settings.EVOLUTION_API_KEY},
                )
                response.raise_for_status()
            return True
    except httpx.HTTPError:
        logger.error("Falha ao enviar mensagem pela Evolution API")
        return False


async def send_whatsapp_document(phone_number: str, document: dict) -> bool:
    """Envia o PDF produzido pelo agente sem repetir automaticamente o envio."""
    data = document.get("data")
    filename = document.get("filename")
    if (
        not _configured()
        or not phone_number
        or not isinstance(data, str)
        or not isinstance(filename, str)
        or not filename
        or document.get("mimetype") != "application/pdf"
        or not _valid_media(data)
    ):
        logger.error("Documento WhatsApp inválido ou Evolution não configurada")
        return False
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _endpoint("message/sendMedia"),
                json={
                    "number": phone_number,
                    "mediatype": "document",
                    "mimetype": "application/pdf",
                    "fileName": PurePath(filename).name,
                    "media": data,
                },
                headers={"apikey": settings.EVOLUTION_API_KEY},
            )
            response.raise_for_status()
        return True
    except httpx.HTTPError:
        logger.error("Falha ao enviar documento pela Evolution API")
        return False


async def get_whatsapp_media(message: dict) -> dict | None:
    """Obtém a mídia pelo objeto de mensagem retornado no webhook."""
    if not _configured() or not isinstance(message, dict):
        return None
    try:
        async with (
            httpx.AsyncClient(timeout=30.0) as client,
            client.stream(
                "POST",
                _endpoint("chat/getBase64FromMediaMessage"),
                json={"message": message, "convertToMp4": False},
                headers={"apikey": settings.EVOLUTION_API_KEY},
            ) as response,
        ):
            response.raise_for_status()
            limit = ((settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 2) // 3) * 4 + 65536
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > limit:
                    logger.error("Mídia WhatsApp excede o tamanho permitido")
                    return None
        media = json.loads(body)
        if not isinstance(media, dict) or not isinstance(media.get("base64"), str):
            return None
        if not _valid_media(media["base64"]):
            return None
        return media
    except (httpx.HTTPError, ValueError):
        logger.error("Falha ao obter mídia pela Evolution API")
        return None
