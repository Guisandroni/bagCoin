"""
Telegram Bridge Service
Polls Telegram API for updates and forwards them to the backend.
"""

import base64
import json
import logging
import os
import time

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("telegram-bridge")

# ── Configuration ────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://app:8000")
API_KEY = os.environ.get("API_KEY", "")
LAST_UPDATE_FILE = "/app/last_update.txt"

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else None


# ── Persisted offset ─────────────────────────────────────────────────────────

def load_offset() -> int:
    try:
        with open(LAST_UPDATE_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_offset(update_id: int) -> None:
    with open(LAST_UPDATE_FILE, "w") as f:
        f.write(str(update_id))


# ── Telegram API helpers ─────────────────────────────────────────────────────

def get_updates(offset: int, timeout: int = 30) -> list | None:
    if not API_BASE:
        logger.warning("TELEGRAM_BOT_TOKEN not set – cannot poll")
        return None

    url = f"{API_BASE}/getUpdates"
    params = {"offset": offset, "timeout": timeout}
    try:
        with httpx.Client(timeout=timeout + 10) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data.get("ok"):
                return data.get("result", [])
            logger.error("Telegram API error: %s", data)
            return None
    except httpx.TimeoutException:
        return []
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error polling Telegram: %s", exc)
        return None
    except httpx.RequestError as exc:
        logger.error("Request error polling Telegram: %s", exc)
        return None


def send_message(chat_id: int, text: str) -> bool:
    if not API_BASE:
        return False
    url = f"{API_BASE}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            ok = data.get("ok", False)
            if not ok:
                logger.error("Telegram sendMessage returned ok=false: %s", data)
            return ok
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500] if exc.response is not None else ""
        logger.error("Telegram sendMessage HTTP error: %s body=%s", exc, body)
        return False
    except httpx.RequestError as exc:
        logger.error("Failed to send message: %s", exc)
        return False


def send_document_from_url(
    chat_id: int,
    url: str,
    filename: str,
    caption: str = "",
) -> bool:
    """Download a document from the backend and forward it to Telegram.

    Uses API_KEY on the GET to the backend, then POSTs multipart to Telegram.
    """
    if not API_BASE:
        return False
    try:
        with httpx.Client(timeout=60) as backend:
            resp = backend.get(url, headers={"X-API-Key": API_KEY})
            resp.raise_for_status()
            content = resp.content

        with httpx.Client(timeout=60) as tg:
            files = {"document": (filename, content, "application/pdf")}
            data = {"chat_id": str(chat_id)}
            if caption:
                data["caption"] = caption
            send_url = f"{API_BASE}/sendDocument"
            tg_resp = tg.post(send_url, data=data, files=files)
            tg_resp.raise_for_status()
            return tg_resp.json().get("ok", False)
    except Exception as exc:
        logger.error("Failed to send document from %s: %s", url, exc)
        return False


def download_file(file_id: str) -> bytes | None:
    """Download a file from Telegram servers by file_id."""
    if not API_BASE:
        return None
    try:
        # 1. Get file path
        with httpx.Client(timeout=15) as client:
            resp = client.get(f"{API_BASE}/getFile", params={"file_id": file_id})
            resp.raise_for_status()
            file_info = resp.json()
            if not file_info.get("ok"):
                return None
            file_path = file_info["result"]["file_path"]

        # 2. Download file
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        with httpx.Client(timeout=30) as client:
            resp = client.get(download_url)
            resp.raise_for_status()
            return resp.content
    except Exception as exc:
        logger.error("Failed to download file %s: %s", file_id, exc)
        return None


# ── Backend forwarding ───────────────────────────────────────────────────────

def forward_text(chat_id: int, text: str, username: str | None) -> dict | None:
    """Forward a text message to the backend."""
    url = f"{BACKEND_URL}/api/v1/webhook/telegram"
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    payload = {
        "chat_id": str(chat_id),
        "message": text,
        "username": username or None,
        "source_format": "text",
    }
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except httpx.RequestError as exc:
        logger.error("Failed to forward to backend: %s", exc)
        return None


def forward_media(
    chat_id: int,
    mediatype: str,        # "audio", "image", "document"
    mimetype: str,
    data_b64: str,
    username: str | None,
    filename: str = "",
    text: str = "",
) -> dict | None:
    """Forward media (audio/image/document) to the backend."""
    url = f"{BACKEND_URL}/api/v1/webhook/telegram"
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    payload = {
        "chat_id": str(chat_id),
        "message": text,
        "username": username or None,
        "source_format": mediatype,
    }
    # Embed media as base64 in the payload (matching webhook.py expectations)
    payload["media"] = {
        "mimetype": mimetype,
        "data": data_b64,
    }
    if filename:
        payload["media"]["filename"] = filename

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except httpx.RequestError as exc:
        logger.error("Failed to forward media to backend: %s", exc)
        return None


# ── Message processing ───────────────────────────────────────────────────────

def _extract_media(message: dict) -> tuple[str | None, str | None, str | None]:
    """Extract media info from a Telegram message.

    Returns (mediatype, mimetype, file_id) or (None, None, None).
    """
    if "voice" in message:
        return ("audio", "audio/ogg", message["voice"]["file_id"])
    if "audio" in message:
        mime = message["audio"].get("mime_type", "audio/mpeg")
        return ("audio", mime, message["audio"]["file_id"])
    if "photo" in message:
        # photo is an array — use the largest size (last item)
        photos = message["photo"]
        return ("image", "image/jpeg", photos[-1]["file_id"])
    if "document" in message:
        doc = message["document"]
        mime = doc.get("mime_type", "application/octet-stream")
        return ("document", mime, doc["file_id"])
    if "video_note" in message:
        return ("video", "video/mp4", message["video_note"]["file_id"])
    return None, None, None


def process_update(update: dict) -> None:
    """Process a single Telegram update."""
    update_id = update.get("update_id")
    if not update_id:
        return

    message = update.get("message")
    if not message:
        save_offset(update_id)
        return

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    from_user = message.get("from", {})
    username = from_user.get("username")
    text = message.get("text", "") or message.get("caption", "")

    if not chat_id:
        save_offset(update_id)
        return

    mediatype, mimetype, file_id = _extract_media(message)
    if mediatype and file_id:
        logger.info("Received %s from %s (chat %s)", mediatype, username or "unknown", chat_id)

        file_data = download_file(file_id)
        if not file_data:
            logger.warning("Failed to download %s from chat %s", mediatype, chat_id)
            send_message(chat_id, "Desculpe, não consegui baixar o arquivo. Tente novamente.")
            save_offset(update_id)
            return

        data_b64 = base64.b64encode(file_data).decode()
        filename = ""
        if mediatype == "document" and "document" in message:
            filename = message["document"].get("file_name", "")

        logger.info("📎 %s: %s (%d bytes)", mediatype, mimetype, len(file_data))

        response = forward_media(chat_id, mediatype, mimetype, data_b64, username, filename, text)
        if response and isinstance(response, dict):
            reply_text = response.get("reply", "")
            if reply_text:
                if send_message(chat_id, reply_text):
                    logger.info("Replied to chat %s", chat_id)
                else:
                    logger.warning("Failed to reply to chat %s", chat_id)
            media = response.get("media")
            if isinstance(media, dict) and media.get("url"):
                report_filename = media.get("filename", "relatorio.pdf")
                if send_document_from_url(
                    chat_id, media["url"], report_filename, caption="Seu relatório 📊"
                ):
                    logger.info("Document sent to chat %s: %s", chat_id, report_filename)
                else:
                    logger.warning("Failed to send document %s to chat %s", report_filename, chat_id)
        else:
            send_message(chat_id, "Desculpe, não consegui processar o arquivo. Tente novamente como texto.")
        save_offset(update_id)
        return

    # ── Text message ──
    if text:
        logger.info("Received message from %s (chat %s): %s", username or "unknown", chat_id, text[:80])
        response = forward_text(chat_id, text, username)
        if response and isinstance(response, dict):
            reply_text = response.get("reply", "")
            if reply_text:
                if send_message(chat_id, reply_text):
                    logger.info("Replied to chat %s", chat_id)
                else:
                    logger.warning("Failed to reply to chat %s", chat_id)
            media = response.get("media")
            if isinstance(media, dict) and media.get("url"):
                filename = media.get("filename", "relatorio.pdf")
                if send_document_from_url(
                    chat_id, media["url"], filename, caption="Seu relatório 📊"
                ):
                    logger.info("Document sent to chat %s: %s", chat_id, filename)
                else:
                    logger.warning("Failed to send document %s to chat %s", filename, chat_id)
        else:
            send_message(chat_id, "Sorry, I couldn't process your message right now.")
        save_offset(update_id)
        return

    # Unknown message type — ignore

    save_offset(update_id)


# ── Main loop ────────────────────────────────────────────────────────────────

def main_loop() -> None:
    logger.info("Telegram Bridge Service starting")
    logger.info("Backend URL: %s", BACKEND_URL)
    logger.info("API Key configured: %s", "yes" if API_KEY else "no")
    logger.info("Bot token configured: %s", "yes" if TELEGRAM_BOT_TOKEN else "no")

    if not TELEGRAM_BOT_TOKEN:
        logger.warning("No TELEGRAM_BOT_TOKEN set – service will retry every 30s")

    offset = load_offset()
    logger.info("Starting with offset %s", offset)

    while True:
        updates = get_updates(offset + 1)
        if updates is None:
            time.sleep(30)
            continue
        if not updates:
            continue
        for update in updates:
            try:
                process_update(update)
                new_id = update.get("update_id", 0)
                if new_id > offset:
                    offset = new_id
            except Exception:
                logger.exception("Error processing update %s", update.get("update_id"))
                continue


if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("Shutting down Telegram Bridge Service")
    except Exception:
        logger.exception("Fatal error – service terminated")
