"""LLM service for BagCoin agents.

Manages LLM provider selection with global caching.
Priority: DeepSeek -> OpenCodeGo (multi-model) -> Groq (fallback).

OpenCodeGo models ranked by latency:
  1. minimax-m2.7      — ~2.0s
  2. mimo-v2.5         — ~3.5s
  3. mimo-v2-omni      — ~4.0s
  4. mimo-v2-pro       — ~4.4s
  5. kimi-k2.6         — ~4.6s (reasoning)
  6. kimi-k2.5         — ~4.8s (reasoning)
  7. qwen3.6-plus      — ~5.6s
  8. deepseek-v4-flash — variable
  9. mimo-v2.5-pro     — ~8.0s
 10. qwen3.5-plus      — ~8.2s
 11. deepseek-v4-pro   — variable (reasoning)
 12. glm-5.1           — variable (reasoning)
 13. glm-5             — variable (reasoning)

Supports BAGCOIN_MODEL env var for model override without restart.
"""

import logging
import os
import time

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global LLM cache
_cached_llm: BaseChatModel | None = None
_cache_error: bool = False

# OpenCodeGo models in priority order (ranked by latency)
OPENCODE_MODELS = [
    "minimax-m2.7",       # 🥇 2.0s, 119 tok
    "mimo-v2.5",          # 🥈 3.5s, 104 tok
    "mimo-v2-omni",       # 🥉 4.0s, 103 tok
    "mimo-v2-pro",        # 4.4s, 104 tok
    "kimi-k2.6",          # 4.6s, 230 tok (reasoning)
    "kimi-k2.5",          # 4.8s, 258 tok (reasoning)
    "qwen3.6-plus",       # 5.6s, 307 tok
    "deepseek-v4-flash",  # 1.4-7s*, 181 tok (reasoning, varia)
    "mimo-v2.5-pro",      # 8.0s, 105 tok
    "qwen3.5-plus",       # 8.2s, 448 tok
    "deepseek-v4-pro",    # variable, 208 tok (reasoning)
    "glm-5.1",            # variable, 223 tok (reasoning)
    "glm-5",              # variable, 230 tok (reasoning)
]


def _get_model_override() -> str | None:
    """Check for model override from env var or shared file."""
    override = os.environ.get("BAGCOIN_MODEL")
    if override:
        return override
    try:
        fp = "/app/model_override.txt"
        if os.path.exists(fp):
            with open(fp) as f:
                return f.read().strip() or None
    except Exception:
        pass
    return None


def _create_deepseek_llm(
    temperature: float = 0.2,
    model: str | None = None,
    request_timeout: float | None = None,
) -> BaseChatModel | None:
    """Create a DeepSeek LLM instance (primary provider)."""
    if not settings.DEEPSEEK_API_KEY:
        return None
    model_name = model or settings.DEFAULT_LLM_MODEL
    try:
        return ChatOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            model=model_name,
            temperature=temperature,
            max_tokens=2048,
            timeout=request_timeout or 30,
            max_retries=1,
        )
    except Exception as e:
        logger.warning(f"Error creating DeepSeek LLM ({model_name}): {e}")
        return None


def _create_opencode_llm(
    temperature: float = 0.2,
    model: str | None = None,
    request_timeout: float | None = None,
) -> BaseChatModel | None:
    """Create an OpenCodeGo LLM instance."""
    if not settings.OPENCODE_API_KEY:
        return None
    model_name = model or _get_model_override() or OPENCODE_MODELS[0]
    try:
        extra = {}
        if any(m in model_name.lower() for m in ["deepseek", "kimi", "glm"]):
            extra = {"extra_body": {"thinking": {"type": "disabled"}}}
        return ChatOpenAI(
            api_key=settings.OPENCODE_API_KEY,
            base_url="https://opencode.ai/zen/go/v1",
            model=model_name,
            temperature=temperature,
            max_tokens=2048,
            timeout=request_timeout or 30,
            max_retries=1,
            model_kwargs=extra,
        )
    except Exception as e:
        logger.warning(f"Error creating OpenCodeGo LLM ({model_name}): {e}")
        return None


def _create_groq_llm(
    temperature: float = 0.2,
    model: str | None = None,
    request_timeout: float | None = None,
) -> BaseChatModel | None:
    """Create a Groq LLM instance (final fallback)."""
    if not settings.GROQ_API_KEY:
        return None
    model_name = model or settings.DEFAULT_LLM_MODEL
    try:
        return ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=model_name,
            temperature=temperature,
            max_tokens=2048,
            timeout=request_timeout or 15,
            max_retries=1,
        )
    except Exception as e:
        logger.warning(f"Error creating Groq LLM: {e}")
        return None


def _invalidate_cache() -> None:
    """Invalidate the LLM cache on error or model change."""
    global _cached_llm, _cache_error
    _cached_llm = None
    _cache_error = True
    logger.info("LLM cache invalidated.")


def _select_llm(
    temperature: float = 0.2,
    model: str | None = None,
    request_timeout: float | None = None,
) -> BaseChatModel | None:
    """Select the best available LLM.

    Priority: DeepSeek -> OpenCodeGo (model list) -> Groq (fallback).
    Cache is invalidated when BAGCOIN_MODEL changes.
    """
    global _cached_llm, _cache_error
    use_cache = request_timeout is None

    override = _get_model_override()
    if override:
        deepseek = _create_deepseek_llm(temperature, override, request_timeout)
        if deepseek:
            logger.info(f"LLM selected: DeepSeek/{override} (override)")
            if use_cache:
                _cached_llm = deepseek
                _cache_error = False
            return deepseek
        opencode = _create_opencode_llm(temperature, override, request_timeout)
        if opencode:
            logger.info(f"LLM selected: OpenCodeGo/{override} (override)")
            if use_cache:
                _cached_llm = opencode
                _cache_error = False
            return opencode

    if use_cache and _cached_llm and not _cache_error:
        return _cached_llm

    if use_cache and _cache_error:
        _cached_llm = None

    # 1. DeepSeek (primary)
    deepseek = _create_deepseek_llm(temperature, model, request_timeout)
    if deepseek:
        logger.info(f"LLM selected: DeepSeek ({model or settings.DEFAULT_LLM_MODEL})")
        if use_cache:
            _cached_llm = deepseek
            _cache_error = False
        return deepseek

    # 2. OpenCodeGo — try models in priority order
    models_to_try = [model] if model else OPENCODE_MODELS
    for model_name in models_to_try:
        opencode = _create_opencode_llm(temperature, model_name, request_timeout)
        if opencode:
            logger.info(f"LLM selected: OpenCodeGo ({model_name})")
            if use_cache:
                _cached_llm = opencode
                _cache_error = False
            return opencode

    # 3. Groq (fallback)
    groq = _create_groq_llm(temperature, model, request_timeout)
    if groq:
        logger.info(f"LLM fallback: Groq ({model or settings.DEFAULT_LLM_MODEL})")
        if use_cache:
            _cached_llm = groq
            _cache_error = False
        return groq

    logger.warning("No LLM available. Running in offline mode (fast-path only).")
    if use_cache:
        _cached_llm = None
    return None


def get_llm(
    temperature: float = 0.2,
    model: str | None = None,
    request_timeout: float | None = None,
) -> BaseChatModel | None:
    """Return a configured LLM instance (cached globally, no health check)."""
    return _select_llm(temperature, model, request_timeout)


def timed_invoke(llm: BaseChatModel, messages: list, operation: str = "llm_invoke") -> tuple:
    """Invoke an LLM with latency timing.

    Returns:
        (response, latency_ms)

    Invalidates cache on 429/timeout errors.
    """
    start = time.time()
    try:
        response = llm.invoke(messages)
        latency_ms = (time.time() - start) * 1000
        logger.info(f"[{operation}] Latency: {latency_ms:.0f}ms")
        return response, latency_ms
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        error_str = str(e).lower()
        logger.warning(f"[{operation}] Failed after {latency_ms:.0f}ms: {e}")
        if "429" in str(e) or "rate limit" in error_str or "timeout" in error_str:
            _invalidate_cache()
        raise
