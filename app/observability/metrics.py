"""Minimal Prometheus-compatible metrics registry."""

from __future__ import annotations

from collections import Counter
from threading import Lock


class MetricsRegistry:
    """Collect and export basic request metrics."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._requests_total = 0
        self._latency_ms_count = 0
        self._latency_ms_sum = 0.0
        self._errors_by_type: Counter[str] = Counter()

    def observe_request(self, latency_ms: float, *, error_type: str | None = None) -> None:
        with self._lock:
            self._requests_total += 1
            self._latency_ms_count += 1
            self._latency_ms_sum += latency_ms
            if error_type:
                self._errors_by_type[error_type] += 1

    def to_prometheus_text(self) -> str:
        with self._lock:
            lines = [
                "# HELP nl2sql_requests_total Total NL2SQL requests processed.",
                "# TYPE nl2sql_requests_total counter",
                f"nl2sql_requests_total {self._requests_total}",
                "# HELP nl2sql_request_latency_ms Request latency summary in milliseconds.",
                "# TYPE nl2sql_request_latency_ms summary",
                f"nl2sql_request_latency_ms_count {self._latency_ms_count}",
                f"nl2sql_request_latency_ms_sum {self._latency_ms_sum}",
                "# HELP nl2sql_errors_total Total failed requests partitioned by error type.",
                "# TYPE nl2sql_errors_total counter",
            ]
            for error_type, count in sorted(self._errors_by_type.items()):
                escaped = error_type.replace('\\', r'\\').replace('"', r'\"')
                lines.append(f'nl2sql_errors_total{{error_type="{escaped}"}} {count}')

        return "\n".join(lines) + "\n"
