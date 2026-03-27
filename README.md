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
