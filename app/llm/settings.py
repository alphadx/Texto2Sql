"""Startup-time LLM settings loading and validation."""

from __future__ import annotations

import os
from dataclasses import dataclass

_SUPPORTED_PROVIDERS = {
    "openai",
    "deepseek",
    "mistral",
    "huggingface",
    "anthropic",
    "gemini",
    "llama",
    "copilot",
    "claude",  # alias aceptado para compatibilidad de configuración
}


@dataclass(frozen=True)
class LLMStartupSettings:
    provider: str
    model: str
    api_key: str
    base_url: str
    max_retries: int
    retry_backoff_seconds: float
    http_timeout_seconds: int
    circuit_breaker_failure_threshold: int
    circuit_breaker_reset_seconds: int
    startup_validate: bool


def _read(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def load_llm_startup_settings_from_env() -> LLMStartupSettings:
    provider = _read("LLM_PROVIDER", "openai").lower()
    model = _read("LLM_MODEL", _read("OPENAI_MODEL", "gpt-4"))
    base_url = _read("LLM_BASE_URL", _read("OPENAI_BASE_URL", ""))

    provider_prefix = provider.upper().replace("-", "_")
    api_key = _read("LLM_API_KEY", _read(f"{provider_prefix}_API_KEY", _read("OPENAI_API_KEY", "")))

    startup_validate = _read("LLM_STARTUP_VALIDATE", "false").lower() in {"1", "true", "yes"}

    return LLMStartupSettings(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        max_retries=int(_read("LLM_MAX_RETRIES", "2")),
        retry_backoff_seconds=float(_read("LLM_RETRY_BACKOFF_SECONDS", "0.5")),
        http_timeout_seconds=int(_read("LLM_HTTP_TIMEOUT_SECONDS", "60")),
        circuit_breaker_failure_threshold=int(_read("LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD", "3")),
        circuit_breaker_reset_seconds=int(_read("LLM_CIRCUIT_BREAKER_RESET_SECONDS", "30")),
        startup_validate=startup_validate,
    )


def validate_llm_startup_settings(settings: LLMStartupSettings) -> None:
    provider = settings.provider
    if provider not in _SUPPORTED_PROVIDERS:
        supported = ", ".join(sorted(_SUPPORTED_PROVIDERS))
        raise RuntimeError(f"Unsupported LLM_PROVIDER={provider!r}. Supported: {supported}")

    if settings.max_retries < 0:
        raise RuntimeError("LLM_MAX_RETRIES must be >= 0")
    if settings.retry_backoff_seconds < 0:
        raise RuntimeError("LLM_RETRY_BACKOFF_SECONDS must be >= 0")
    if settings.http_timeout_seconds <= 0:
        raise RuntimeError("LLM_HTTP_TIMEOUT_SECONDS must be > 0")
    if settings.circuit_breaker_failure_threshold <= 0:
        raise RuntimeError("LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD must be > 0")
    if settings.circuit_breaker_reset_seconds <= 0:
        raise RuntimeError("LLM_CIRCUIT_BREAKER_RESET_SECONDS must be > 0")

    if settings.startup_validate and not settings.api_key:
        raise RuntimeError(
            "LLM_STARTUP_VALIDATE=true requires API key at startup "
            "(LLM_API_KEY or <PROVIDER>_API_KEY/OPENAI_API_KEY)."
        )
