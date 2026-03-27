"""Thread-safe in-memory store for LLM conversation histories, keyed by session ID."""

import threading
from typing import Any, Dict, List


class SessionManager:
    """Stores per-session message histories for each LLM agent."""

    _AGENTS = ("refiner", "sql_agent")

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, List[Any]]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create(self, session_id: str) -> Dict[str, List[Any]]:
        """Return the session dict, creating it if it does not exist.

        Must be called while ``self._lock`` is held.
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = {agent: [] for agent in self._AGENTS}
        return self._sessions[session_id]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_history(self, session_id: str, agent: str) -> List[Any]:
        """Return a copy of the message history for *agent* in *session_id*."""
        with self._lock:
            return list(self._get_or_create(session_id)[agent])

    def set_history(self, session_id: str, agent: str, history: List[Any]) -> None:
        """Replace the message history for *agent* in *session_id*."""
        with self._lock:
            self._get_or_create(session_id)[agent] = list(history)

    def session_exists(self, session_id: str) -> bool:
        """Return ``True`` if *session_id* has been created."""
        with self._lock:
            return session_id in self._sessions

    def clear_session(self, session_id: str) -> bool:
        """Delete *session_id*.  Returns ``True`` if it existed."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False
