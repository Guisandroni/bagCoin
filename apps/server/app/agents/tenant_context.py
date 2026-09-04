"""Tenant context validation for BagCoin agents.

All financial data access must originate from a valid user identifier.
"""

from __future__ import annotations

MIN_PHONE_DIGITS = 5


def tenant_phone_error(phone_number: str | None) -> str | None:
    """Return error message in pt-BR if phone is invalid; None otherwise."""
    if phone_number is None:
        return "Não foi possível identificar o contato. Tente novamente."
    digits = "".join(c for c in str(phone_number) if c.isdigit())
    if len(digits) < MIN_PHONE_DIGITS:
        return "Identificador de contato inválido ou incompleto. Verifique o número e tente novamente."
    return None


def assert_valid_tenant_phone(phone_number: str | None) -> None:
    """Raise ValueError if the tenant identifier is invalid."""
    err = tenant_phone_error(phone_number)
    if err:
        raise ValueError(err)


def tenant_user_id_error(user_id: int | None) -> str | None:
    """Return error message if user_id is invalid; None otherwise."""
    if user_id is None or user_id <= 0:
        return "Não foi possível identificar o usuário. Tente novamente."
    return None


def assert_valid_tenant_user(user_id: int | None) -> None:
    """Raise ValueError if the user_id is invalid."""
    err = tenant_user_id_error(user_id)
    if err:
        raise ValueError(err)
