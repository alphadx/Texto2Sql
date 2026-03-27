# Texto2Sql

Conversor intermedio (requiere LLM) para traducir preguntas en lenguaje natural a SQL y devolver resultados en JSON.

## Seguridad (JWT, scopes y roles)

La API usa autenticación por **Bearer JWT** para proteger `POST /nl2sql/query` y endpoints administrativos (ejemplo: `DELETE /session/{session_id}`).

### Variables de entorno de seguridad

- `AUTH_REQUIRED` (default `true`): activa/desactiva verificación JWT.
- `AUTH_JWT_SECRET` (**requerida** cuando `AUTH_REQUIRED=true`): secreto HMAC para validar JWT.
- `AUTH_JWT_ALGORITHM` (default `HS256`).
- `AUTH_JWT_AUDIENCE` (opcional).
- `AUTH_JWT_ISSUER` (opcional).

### Validaciones de arranque

Si `AUTH_REQUIRED=true`, la aplicación falla al arrancar cuando:

- Falta `AUTH_JWT_SECRET`.
- `AUTH_JWT_SECRET` tiene valores inseguros (`changeme`, `default`, `secret`, etc.).
- `AUTH_JWT_SECRET` tiene menos de 32 caracteres.

### Control de acceso

- `POST /nl2sql/query` requiere scope `query:execute`.
- Operaciones administrativas/auditoría requieren:
  - scope `audit:admin`, **o**
  - role `admin`.

### Claims esperados en JWT

- `sub`: identificador del sujeto (requerido).
- `scopes` (lista) o `scope` (string separado por espacios).
- `roles` (lista) o `role` (string).

## Gestión de sesión

El servicio soporta dos backends de sesión configurables por variables de entorno:

- `SESSION_MANAGER_BACKEND=memory` (default): historial en memoria del proceso.
- `SESSION_MANAGER_BACKEND=redis`: historial persistido en Redis por `session_id` y agente (`refiner` / `sql_agent`).

Variables para Redis:

- `REDIS_URL` (default `redis://localhost:6379/0`)
- `SESSION_TTL_SECONDS` (default `3600`)
- `SESSION_KEY_PREFIX` (default `nl2sql:session`)
- `SESSION_TTL_POLICY` (default `absolute`):
  - `absolute`: el TTL solo se aplica en escrituras (`set_history`).
  - `sliding`: el TTL se renueva en cada lectura válida (`get_history`).

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

## Ejecución de pruebas

Para asegurar ejecución en un entorno con dependencias instaladas:

```bash
make test
```

El target `test` instala `requirements.txt` + `requirements-dev.txt` y luego ejecuta `pytest tests/test_app.py`.
