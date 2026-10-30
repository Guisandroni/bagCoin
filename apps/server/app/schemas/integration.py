"""Schemas for web↔bot integration (pairing tokens)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import BaseSchema

IntegrationChannel = Literal["whatsapp"]


class LinkTokenRequest(BaseSchema):
    channel: IntegrationChannel = Field(description="Channel this token is intended for")


class LinkTokenResponse(BaseSchema):
    token: str
    expires_at: datetime
    deeplink_whatsapp: str | None = None
    manual_command_whatsapp: str


class IntegrationStatus(BaseSchema):
    whatsapp_linked: bool
    phone_number: str | None = None
