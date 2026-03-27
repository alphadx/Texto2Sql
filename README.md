# Texto2Sql

Conversor intermedio (requiere LLM) para traducir preguntas en lenguaje natural a SQL y devolver resultados en JSON.

## Gestión de sesión

El servicio soporta dos backends de sesión configurables por variables de entorno:

- `SESSION_MANAGER_BACKEND=memory` (default): historial en memoria del proceso.
- `SESSION_MANAGER_BACKEND=redis`: historial persistido en Redis por `session_id` y agente (`refiner` / `sql_agent`).

Variables para Redis:

- `REDIS_URL` (default `redis://localhost:6379/0`)
- `SESSION_TTL_SECONDS` (default `3600`)
- `SESSION_KEY_PREFIX` (default `nl2sql:session`)

Cada historial se serializa en JSON y se almacena con TTL para expiración automática. También se puede borrar explícitamente con `DELETE /session/{session_id}`.

## Auditoría y métricas

La API registra cada request de `POST /nl2sql/query` en formato JSON estructurado con:

- `session_id`
- `engine` (`motor_bd`)
- `status_code`
- `durations_ms` por etapa (`schema`, `llm`, `sql`) y total
- `error_type` / `error_message` (si aplica)

Backends de auditoría configurables:

- `AUDIT_LOG_BACKEND=stream` (default): emite JSON por stdout.
- `AUDIT_LOG_BACKEND=file`: persiste a `AUDIT_LOG_FILE_PATH` (default `logs/audit.log`).
- `AUDIT_LOG_BACKEND=sqlite`: persiste a `AUDIT_LOG_DB_PATH` y tabla `AUDIT_LOG_DB_TABLE`.

Métricas base compatibles con Prometheus disponibles en `GET /metrics`:

- `nl2sql_requests_total`
- `nl2sql_request_latency_ms_count` / `nl2sql_request_latency_ms_sum`
- `nl2sql_errors_total{error_type="..."}`
