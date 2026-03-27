"""Session management backends for LLM conversation histories."""

from __future__ import annotations

import json
import logging
import os
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Sequence

from redis import Redis

logger = logging.getLogger(__name__)

AGENTS: tuple[str, str] = ("refiner", "sql_agent")


class SessionManager(ABC):
    """Common interface for conversation-history session stores."""

    @abstractmethod
    def get_history(self, session_id: str, agent: str) -> List[Any]:
        """Return a copy of the message history for *agent* in *session_id*."""

    @abstractmethod
    def set_history(self, session_id: str, agent: str, history: Sequence[Any]) -> None:
        """Replace the message history for *agent* in *session_id*."""

    @abstractmethod
    def session_exists(self, session_id: str) -> bool:
        """Return ``True`` if any agent history exists for *session_id*."""

    @abstractmethod
    def clear_session(self, session_id: str) -> bool:
        """Delete all agent histories for *session_id* and return whether any existed."""


class InMemorySessionManager(SessionManager):
    """Thread-safe in-memory store for LLM conversation histories."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, List[Any]]] = {}
        self._lock = threading.Lock()

    def _get_or_create(self, session_id: str) -> Dict[str, List[Any]]:
        if session_id not in self._sessions:
            self._sessions[session_id] = {agent: [] for agent in AGENTS}
        return self._sessions[session_id]

    def get_history(self, session_id: str, agent: str) -> List[Any]:
        with self._lock:
            return list(self._get_or_create(session_id)[agent])

    def set_history(self, session_id: str, agent: str, history: Sequence[Any]) -> None:
        with self._lock:
            self._get_or_create(session_id)[agent] = list(history)

    def session_exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    def clear_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False


class RedisSessionManager(SessionManager):
    """Redis-backed conversation history store with per-agent JSON payloads."""

    def __init__(
        self,
        redis_client: Redis,
        ttl_seconds: int = 3600,
        key_prefix: str = "nl2sql:session",
    ) -> None:
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds
        self._key_prefix = key_prefix

    def _key(self, session_id: str, agent: str) -> str:
        return f"{self._key_prefix}:{session_id}:{agent}"

    def _validate_agent(self, agent: str) -> None:
        if agent not in AGENTS:
            raise ValueError(f"Unknown agent {agent!r}. Expected one of: {', '.join(AGENTS)}")

    def get_history(self, session_id: str, agent: str) -> List[Any]:
        self._validate_agent(agent)
        value = self._redis.get(self._key(session_id, agent))
        if value is None:
            return []
        loaded = json.loads(value)
        return loaded if isinstance(loaded, list) else []

    def set_history(self, session_id: str, agent: str, history: Sequence[Any]) -> None:
        self._validate_agent(agent)
        payload = json.dumps(list(history), ensure_ascii=False)
        self._redis.set(self._key(session_id, agent), payload, ex=self._ttl_seconds)

    def session_exists(self, session_id: str) -> bool:
        keys = [self._key(session_id, agent) for agent in AGENTS]
        return any(self._redis.exists(key) for key in keys)

    def clear_session(self, session_id: str) -> bool:
        keys = [self._key(session_id, agent) for agent in AGENTS]
        deleted = self._redis.delete(*keys)
        return bool(deleted)


def build_session_manager_from_env() -> SessionManager:
    """Build the configured session manager backend from environment vars."""
    backend = os.getenv("SESSION_MANAGER_BACKEND", "memory").strip().lower()

    if backend == "redis":
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        ttl_seconds = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
        key_prefix = os.getenv("SESSION_KEY_PREFIX", "nl2sql:session")
        redis_client = Redis.from_url(redis_url, decode_responses=True)
        logger.info(
            "Using Redis session manager (url=%s, ttl=%s, key_prefix=%s)",
            redis_url,
            ttl_seconds,
            key_prefix,
        )
        return RedisSessionManager(
            redis_client=redis_client,
            ttl_seconds=ttl_seconds,
            key_prefix=key_prefix,
        )

    logger.info("Using in-memory session manager")
    return InMemorySessionManager()
