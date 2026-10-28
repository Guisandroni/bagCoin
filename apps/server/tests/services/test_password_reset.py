from __future__ import annotations

import pytest

from app.core.exceptions import RateLimitError
from app.services.password_reset import PasswordResetService


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.counters: dict[str, int] = {}

    async def ttl(self, key: str) -> int:
        return self.ttls.get(key, -2)

    async def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def expire(self, key: str, ttl: int) -> bool:
        self.ttls[key] = ttl
        return True

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self.values[key] = value
        if ttl is not None:
            self.ttls[key] = ttl


@pytest.mark.anyio
async def test_password_reset_rate_limit_sets_three_minute_cooldown(monkeypatch):
    from app.services import password_reset

    monkeypatch.setattr(password_reset.settings, "PASSWORD_RESET_REQUEST_COOLDOWN_SECONDS", 180)
    redis = FakeRedis()
    service = PasswordResetService(db=None, redis=redis)  # type: ignore[arg-type]

    await service._ensure_rate_limit("USER@Email.com", "127.0.0.1")

    assert redis.values["password-reset:cooldown:email:user@email.com"] == "1"
    assert redis.values["password-reset:cooldown:ip:127.0.0.1"] == "1"
    assert redis.ttls["password-reset:cooldown:email:user@email.com"] == 180
    assert redis.ttls["password-reset:cooldown:ip:127.0.0.1"] == 180


@pytest.mark.anyio
async def test_password_reset_rate_limit_blocks_during_cooldown():
    redis = FakeRedis()
    redis.ttls["password-reset:cooldown:email:user@email.com"] = 120
    service = PasswordResetService(db=None, redis=redis)  # type: ignore[arg-type]

    with pytest.raises(RateLimitError) as exc_info:
        await service._ensure_rate_limit("user@email.com", "127.0.0.1")

    assert exc_info.value.code == "PASSWORD_RESET_COOLDOWN"
    assert exc_info.value.message == "Aguarde 3 minutos antes de solicitar outro link."
    assert exc_info.value.details["retry_after_seconds"] == 120
