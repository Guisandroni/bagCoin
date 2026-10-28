"""Shared types for multimodal processing."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class MultimodalResult:
    """Unified contract for all media processors."""

    text: str
    structured: dict | None = None
    confidence: Literal["normal", "low"] = "normal"
    reason: str | None = None
    provider: str = ""
    failure: bool = False

    @property
    def is_failure(self) -> bool:
        return self.failure or not self.text
