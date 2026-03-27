"""Structured audit logging with configurable persistence backends."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Literal


AuditBackend = Literal["stream", "file", "sqlite"]


@dataclass(frozen=True)
class AuditConfig:
    backend: AuditBackend = "stream"
    file_path: str = "logs/audit.log"
    db_path: str = "logs/audit.sqlite3"
    db_table: str = "audit_events"


class AuditLogger:
    """Persist JSON-formatted audit events to stream, file, or SQLite."""

    def __init__(self, config: AuditConfig):
        self._config = config
        self._lock = Lock()

        if config.backend == "file":
            Path(config.file_path).parent.mkdir(parents=True, exist_ok=True)
        elif config.backend == "sqlite":
            Path(config.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._initialize_sqlite()

    def persist(self, event: dict[str, Any]) -> None:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            **event,
        }

        if self._config.backend == "stream":
            print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            return

        if self._config.backend == "file":
            with self._lock:
                with open(self._config.file_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
            return

        if self._config.backend == "sqlite":
            self._persist_sqlite(payload)
            return

        raise ValueError(f"Unsupported backend: {self._config.backend!r}")

    def _initialize_sqlite(self) -> None:
        with sqlite3.connect(self._config.db_path) as conn:
            conn.execute(
                (
                    f"CREATE TABLE IF NOT EXISTS {self._config.db_table} "
                    "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "timestamp TEXT NOT NULL, "
                    "session_id TEXT, "
                    "engine TEXT, "
                    "status_code INTEGER, "
                    "error_type TEXT, "
                    "payload_json TEXT NOT NULL)"
                )
            )
            conn.commit()

    def _persist_sqlite(self, payload: dict[str, Any]) -> None:
        with self._lock:
            with sqlite3.connect(self._config.db_path) as conn:
                conn.execute(
                    (
                        f"INSERT INTO {self._config.db_table} "
                        "(timestamp, session_id, engine, status_code, error_type, payload_json) "
                        "VALUES (?, ?, ?, ?, ?, ?)"
                    ),
                    (
                        payload.get("timestamp"),
                        payload.get("session_id"),
                        payload.get("engine"),
                        payload.get("status_code"),
                        payload.get("error_type"),
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
                conn.commit()


def build_audit_logger_from_env() -> AuditLogger:
    backend_raw = os.getenv("AUDIT_LOG_BACKEND", "stream").strip().lower()
    backend: AuditBackend = "stream"
    if backend_raw in {"stream", "file", "sqlite"}:
        backend = backend_raw

    config = AuditConfig(
        backend=backend,
        file_path=os.getenv("AUDIT_LOG_FILE_PATH", "logs/audit.log"),
        db_path=os.getenv("AUDIT_LOG_DB_PATH", "logs/audit.sqlite3"),
        db_table=os.getenv("AUDIT_LOG_DB_TABLE", "audit_events"),
    )
    return AuditLogger(config)
