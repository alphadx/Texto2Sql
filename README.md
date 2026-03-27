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

Cada historial se serializa en JSON y se almacena con TTL para expiración automática. También se puede borrar explícitamente con `DELETE /session/{session_id}`.
