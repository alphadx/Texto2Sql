"""Provider abstraction for commercial LLM backends.

This module keeps provider-specific concerns behind a stable interface so the
NL→SQL pipeline can remain provider-agnostic.
"""

from __future__ import annotations

import os
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List
from urllib.parse import urlparse
from urllib import request
import json
from urllib.error import HTTPError, URLError
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

_PROVIDER_ALIASES = {
    "openai": "openai",
    "deepseek": "deepseek",
    "mistral": "mistral",
    "huggingface": "huggingface",
    "hf": "huggingface",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "gemini": "gemini",
    "google": "gemini",
    "llama": "llama",
    "copilot": "copilot",
}

_SUPPORTED_PROVIDERS = set(_PROVIDER_ALIASES.values())

_PROVIDER_ENV_PREFIX = {
    "openai": "OPENAI",
    "deepseek": "DEEPSEEK",
    "mistral": "MISTRAL",
    "huggingface": "HUGGINGFACE",
    "anthropic": "ANTHROPIC",
    "gemini": "GEMINI",
    "llama": "LLAMA",
    "copilot": "COPILOT",
}

_DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "mistral": "https://api.mistral.ai/v1",
    "huggingface": "https://router.huggingface.co/v1",
}

_DEFAULT_MODELS = {
    "openai": "gpt-4",
    "deepseek": "deepseek-chat",
    "mistral": "mistral-small-latest",
    "huggingface": "Qwen/Qwen2.5-3B-Instruct",
    "anthropic": "claude-3-5-sonnet-latest",
    "gemini": "gemini-2.0-flash-lite",
    "llama": "meta-llama/llama-3.1-8b-instruct",
    "copilot": "gpt-4.1-mini",
}


def normalize_provider(provider: str | None) -> str:
    value = (provider or "openai").strip().lower()
    return _PROVIDER_ALIASES.get(value, value)


@dataclass(frozen=True)
class LLMRuntimeConfig:
    provider: str
    api_key: str
    model: str
    base_url: str | None = None


@dataclass(frozen=True)
class LLMCompletionResult:
    text: str
    provider: str
    model: str
    gateway: str
    attempts: int
    latency_ms: float


@dataclass(frozen=True)
class LLMProviderError(RuntimeError):
    provider: str
    message: str
    retryable: bool = False
    status_code: int | None = None

    def __str__(self) -> str:
        details = [f"provider={self.provider}", self.message]
        if self.status_code is not None:
            details.append(f"status={self.status_code}")
        details.append(f"retryable={self.retryable}")
        return " | ".join(details)


_clients: dict[tuple[str, str, str | None], OpenAI] = {}
_circuit_lock = threading.Lock()
_circuit_state: dict[str, dict[str, float]] = {}


class BaseGateway(ABC):
    @abstractmethod
    def complete(self, config: LLMRuntimeConfig, messages: List[Dict[str, Any]]) -> LLMCompletionResult:
        """Generate completion text from chat messages."""


class OpenAICompatibleGateway(BaseGateway):
    """Universal gateway for providers exposing OpenAI-compatible chat APIs."""

    def complete(self, config: LLMRuntimeConfig, messages: List[Dict[str, Any]]) -> LLMCompletionResult:
        if _is_circuit_open(config.provider):
            raise LLMProviderError(
                provider=config.provider,
                message="Circuit breaker is open for provider",
                retryable=True,
                status_code=503,
            )
        start = time.perf_counter()
        for attempt in range(_max_retries() + 1):
            try:
                key = (config.provider, config.api_key, config.base_url)
                if key not in _clients:
                    kwargs: dict[str, Any] = {"api_key": config.api_key}
                    if config.base_url:
                        kwargs["base_url"] = config.base_url
                    _clients[key] = OpenAI(**kwargs)

                response = _clients[key].chat.completions.create(
                    model=config.model,
                    messages=messages,
                )
                content = response.choices[0].message.content or ""
                logger.info(
                    "llm_gateway_complete provider=%s gateway=openai-compatible elapsed_ms=%.3f attempt=%d",
                    config.provider,
                    (time.perf_counter() - start) * 1000,
                    attempt + 1,
                )
                _record_success(config.provider)
                return LLMCompletionResult(
                    text=content,
                    provider=config.provider,
                    model=config.model,
                    gateway="openai-compatible",
                    attempts=attempt + 1,
                    latency_ms=(time.perf_counter() - start) * 1000,
                )
            except Exception as exc:  # noqa: BLE001
                retryable = attempt < _max_retries()
                if retryable:
                    _sleep_backoff(attempt)
                    continue
                _record_failure(config.provider)
                raise LLMProviderError(
                    provider=config.provider,
                    message=f"OpenAI-compatible completion failed: {exc}",
                    retryable=False,
                ) from exc


class AnthropicGateway(BaseGateway):
    def complete(self, config: LLMRuntimeConfig, messages: List[Dict[str, Any]]) -> LLMCompletionResult:
        start = time.perf_counter()
        base_url = config.base_url or "https://api.anthropic.com"
        endpoint = f"{base_url.rstrip('/')}/v1/messages"
        payload = {
            "model": config.model,
            "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1024")),
            "messages": [
                {"role": m.get("role", "user"), "content": [{"type": "text", "text": m.get("content", "")}]}
                for m in messages
                if m.get("role") in {"user", "assistant"}
            ],
        }
        system_messages = [m.get("content", "") for m in messages if m.get("role") == "system"]
        if system_messages:
            payload["system"] = "\n\n".join(system_messages)

        body = _http_json_post(
            provider=config.provider,
            endpoint=endpoint,
            headers={
                "x-api-key": config.api_key,
                "anthropic-version": os.getenv("ANTHROPIC_VERSION", "2023-06-01"),
                "content-type": "application/json",
            },
            payload=payload,
        )
        content = body.get("content", [])
        texts = [block.get("text", "") for block in content if isinstance(block, dict)]
        logger.info(
            "llm_gateway_complete provider=%s gateway=anthropic elapsed_ms=%.3f",
            config.provider,
            (time.perf_counter() - start) * 1000,
        )
        return LLMCompletionResult(
            text="\n".join(t for t in texts if t).strip(),
            provider=config.provider,
            model=config.model,
            gateway="anthropic",
            attempts=1,
            latency_ms=(time.perf_counter() - start) * 1000,
        )


class GeminiGateway(BaseGateway):
    def complete(self, config: LLMRuntimeConfig, messages: List[Dict[str, Any]]) -> LLMCompletionResult:
        start = time.perf_counter()
        base_url = config.base_url or "https://generativelanguage.googleapis.com"
        endpoint = (
            f"{base_url.rstrip('/')}/v1beta/models/{config.model}:generateContent"
            f"?key={config.api_key}"
        )
        contents = []
        system_parts = []
        for message in messages:
            role = message.get("role")
            content = str(message.get("content", ""))
            if role == "system":
                system_parts.append(content)
            elif role in {"assistant", "user"}:
                contents.append({
                    "role": "model" if role == "assistant" else "user",
                    "parts": [{"text": content}],
                })

        payload: dict[str, Any] = {"contents": contents}
        if system_parts:
            payload["system_instruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

        body = _http_json_post(
            provider=config.provider,
            endpoint=endpoint,
            headers={"content-type": "application/json"},
            payload=payload,
        )

        candidates = body.get("candidates", [])
        if not candidates:
            return LLMCompletionResult(
                text="",
                provider=config.provider,
                model=config.model,
                gateway="gemini",
                attempts=1,
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        logger.info(
            "llm_gateway_complete provider=%s gateway=gemini elapsed_ms=%.3f",
            config.provider,
            (time.perf_counter() - start) * 1000,
        )
        return LLMCompletionResult(
            text="\n".join(t for t in texts if t).strip(),
            provider=config.provider,
            model=config.model,
            gateway="gemini",
            attempts=1,
            latency_ms=(time.perf_counter() - start) * 1000,
        )


def _max_retries() -> int:
    return max(0, int(os.getenv("LLM_MAX_RETRIES", "2")))


def _sleep_backoff(attempt: int) -> None:
    base = float(os.getenv("LLM_RETRY_BACKOFF_SECONDS", "0.5"))
    time.sleep(base * (2 ** attempt))


def _http_json_post(*, provider: str, endpoint: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    if _is_circuit_open(provider):
        raise LLMProviderError(
            provider=provider,
            message="Circuit breaker is open for provider",
            retryable=True,
            status_code=503,
        )
    last_error: Exception | None = None
    for attempt in range(_max_retries() + 1):
        try:
            req = request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with request.urlopen(req, timeout=int(os.getenv("LLM_HTTP_TIMEOUT_SECONDS", "60"))) as response:
                parsed = json.loads(response.read().decode("utf-8"))
                _record_success(provider)
                return parsed
        except HTTPError as exc:
            status = getattr(exc, "code", None)
            retryable = status is not None and status >= 500 and attempt < _max_retries()
            last_error = exc
            if retryable:
                _sleep_backoff(attempt)
                continue
            _record_failure(provider)
            raise LLMProviderError(
                provider=provider,
                message=f"HTTP error calling provider endpoint: {exc}",
                status_code=status,
                retryable=False,
            ) from exc
        except URLError as exc:
            last_error = exc
            if attempt < _max_retries():
                _sleep_backoff(attempt)
                continue
            _record_failure(provider)
            raise LLMProviderError(
                provider=provider,
                message=f"Network error calling provider endpoint: {exc}",
                retryable=False,
            ) from exc
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            _record_failure(provider)
            raise LLMProviderError(
                provider=provider,
                message=f"Unexpected error calling provider endpoint: {exc}",
                retryable=False,
            ) from exc

    raise LLMProviderError(
        provider=provider,
        message=f"Retries exhausted calling provider endpoint: {last_error}",
        retryable=False,
    )


def _circuit_failure_threshold() -> int:
    return max(1, int(os.getenv("LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD", "3")))


def _circuit_reset_seconds() -> int:
    return max(1, int(os.getenv("LLM_CIRCUIT_BREAKER_RESET_SECONDS", "30")))


def _is_circuit_open(provider: str) -> bool:
    now = time.time()
    with _circuit_lock:
        state = _circuit_state.get(provider)
        if not state:
            return False
        opened_until = state.get("opened_until", 0.0)
        if opened_until and now < opened_until:
            return True
        if opened_until and now >= opened_until:
            _circuit_state[provider] = {"failures": 0.0, "opened_until": 0.0}
    return False


def _record_success(provider: str) -> None:
    with _circuit_lock:
        _circuit_state[provider] = {"failures": 0.0, "opened_until": 0.0}


def _record_failure(provider: str) -> None:
    threshold = float(_circuit_failure_threshold())
    with _circuit_lock:
        state = _circuit_state.get(provider, {"failures": 0.0, "opened_until": 0.0})
        failures = float(state.get("failures", 0.0)) + 1
        opened_until = 0.0
        if failures >= threshold:
            opened_until = time.time() + _circuit_reset_seconds()
        _circuit_state[provider] = {"failures": failures, "opened_until": opened_until}


def _get_env(prefix: str, key: str) -> str | None:
    value = os.getenv(f"{prefix}_{key}")
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_base_url(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid LLM base URL: {cleaned!r}. Expected absolute http(s) URL.")
    return cleaned


def resolve_runtime_config(llm_options: dict[str, Any] | None = None) -> LLMRuntimeConfig:
    options = llm_options or {}
    provider = normalize_provider(str(options.get("provider") or os.getenv("LLM_PROVIDER") or "openai"))
    if provider not in _SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported LLM provider: {provider!r}. "
            f"Supported providers: {', '.join(sorted(_SUPPORTED_PROVIDERS))}."
        )

    env_prefix = _PROVIDER_ENV_PREFIX.get(provider, "OPENAI")

    api_key = str(
        options.get("api_key")
        or _get_env(env_prefix, "API_KEY")
        or os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()
    model = str(
        options.get("model")
        or _get_env(env_prefix, "MODEL")
        or os.getenv("LLM_MODEL")
        or os.getenv("OPENAI_MODEL")
        or _DEFAULT_MODELS.get(provider, "gpt-4")
    ).strip()

    base_url = _normalize_base_url(
        options.get("base_url")
        or _get_env(env_prefix, "BASE_URL")
        or os.getenv("LLM_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or _DEFAULT_BASE_URLS.get(provider)
    )

    if not api_key:
        raise RuntimeError(
            f"Missing LLM API key for provider '{provider}': "
            "set LLM_API_KEY/<PROVIDER>_API_KEY or send llm_api_key in request"
        )

    return LLMRuntimeConfig(provider=provider, api_key=api_key, model=model, base_url=base_url)


def get_gateway(_provider: str) -> BaseGateway:
    provider = normalize_provider(_provider)
    if provider == "anthropic":
        return AnthropicGateway()
    if provider == "gemini":
        return GeminiGateway()
    return OpenAICompatibleGateway()
