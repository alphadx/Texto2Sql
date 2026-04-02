"""Startup-time LLM settings loading and validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

_SUPPORTED_PROVIDERS = {
    "openai",
    "deepseek",
    "mistral",
    "huggingface",
    "anthropic",
    "gemini",
    "qwen",
    "kimi",
    "llama",
    "copilot",
    "xinghuo",
    "doubao",
    "zhipu",
    "minimax",
    "pangu",
    "grok",
    "claude",  # alias aceptado para compatibilidad de configuración
}

_PROVIDER_ALIASES = {
    "claude": "anthropic",
    "google": "gemini",
    "hf": "huggingface",
    "spark": "xinghuo",
    "iflytek": "xinghuo",
    "bytedance": "doubao",
    "glm": "zhipu",
    "mini-max": "minimax",
    "huawei": "pangu",
    "huaweicloud": "pangu",
    "xai": "grok",
}

_DEFAULT_MODELS = {
    "openai": "gpt-4",
    "deepseek": "deepseek-chat",
    "mistral": "mistral-small-latest",
    "huggingface": "Qwen/Qwen2.5-3B-Instruct",
    "anthropic": "claude-3-5-haiku-latest",
    "gemini": "gemini-2.0-flash-lite",
    "qwen": "qwen-plus",
    "kimi": "kimi-k2",
    "llama": "meta-llama/Llama-3.1-8B-Instruct",
    "copilot": "gpt-4.1-mini",
    "xinghuo": "generalv3.5",
    "doubao": "doubao-pro-32k",
    "zhipu": "glm-4-flash",
    "minimax": "MiniMax-Text-01",
    "pangu": "pangu-pro",
    "grok": "grok-2-latest",
}

_DEFAULT_BASE_URLS = {
    "llama": "https://router.huggingface.co/v1",
    "copilot": "https://models.inference.ai.azure.com",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "kimi": "https://api.moonshot.cn/v1",
    "xinghuo": "https://spark-api-open.xf-yun.com/v1",
    "doubao": "https://ark.cn-beijing.volces.com/api/v3",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "minimax": "https://api.minimax.chat/v1",
    "pangu": "https://modelarts.cn-north-4.myhuaweicloud.com/v1",
    "grok": "https://api.x.ai/v1",
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
    provider_raw = _read("LLM_PROVIDER", "openai").lower()
    provider = _PROVIDER_ALIASES.get(provider_raw, provider_raw)

    provider_prefix = provider.upper().replace("-", "_")
    model = _read(
        "LLM_MODEL",
        _read(f"{provider_prefix}_MODEL", _read("OPENAI_MODEL", _DEFAULT_MODELS.get(provider, "gpt-4"))),
    )
    base_url = _read(
        "LLM_BASE_URL",
        _read(f"{provider_prefix}_BASE_URL", _read("OPENAI_BASE_URL", _DEFAULT_BASE_URLS.get(provider, ""))),
    )
    api_key = _read(f"{provider_prefix}_API_KEY", _read("LLM_API_KEY", _read("OPENAI_API_KEY", "")))

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
    if settings.base_url:
        parsed = urlparse(settings.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError("LLM_BASE_URL/<PROVIDER>_BASE_URL must be an absolute http(s) URL")
