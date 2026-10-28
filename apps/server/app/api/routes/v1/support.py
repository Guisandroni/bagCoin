"""Support contact endpoints."""

from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.schemas.support import SupportContactRequest, SupportContactResponse
from app.services.email_delivery import send_plain_email

router = APIRouter(prefix="/support", tags=["support"])


@router.post("/contact", response_model=SupportContactResponse)
async def contact_support(
    body: SupportContactRequest,
    current_user: CurrentUser,
) -> Any:
    """Send a support message from an authenticated user."""
    if not settings.SUPPORT_EMAIL:
        raise BadRequestError(
            message="Email de suporte não configurado",
            code="SUPPORT_EMAIL_NOT_CONFIGURED",
        )
    await send_plain_email(
        to_email=settings.SUPPORT_EMAIL,
        subject=f"BagCoin suporte - {body.subject}",
        body="\n".join(
            [
                "Nova mensagem de suporte do BagCoin.",
                "",
                f"Usuário: {current_user.full_name or 'Sem nome'}",
                f"Email: {current_user.email}",
                "",
                f"Assunto: {body.subject}",
                "",
                body.message,
            ]
        ),
        reply_to=current_user.email,
    )
    return SupportContactResponse()
