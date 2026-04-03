# Timeouts y política SQL (operación)

Este documento consolida la política operativa vigente para ejecución de consultas NL→SQL:

1. **Una sola sentencia SQL por consulta**.
2. **Timeouts parametrizados** en APP y DEMO.
3. **Defaults de 15 minutos** en archivos `.env.example`.

## 1) Política SQL: una sola sentencia

- El backend valida que cada consulta SQL contenga **una única sentencia**.
- Si detecta múltiples sentencias, responde error de validación.
- Se ignoran `;` que estén dentro de literales/identificadores entre comillas.

Referencia de implementación:
- `app/db/sql_guard.py`
- Pruebas: `tests/test_app.py` (`TestSqlGuard`)

## 2) Inventario de timeouts (APP)

Variables recomendadas para operación (definidas en `.env.example`):

- `QUERY_TIMEOUT_MS` (ms) — timeout de ejecución SQL.
- `LLM_HTTP_TIMEOUT_SECONDS` (s) — timeout HTTP hacia proveedor LLM.
- `TIMEOUT` (s) — timeout de worker Gunicorn.
- `GRACEFUL_TIMEOUT` (s) — timeout de apagado elegante Gunicorn.
- `KEEPALIVE` (s) — keepalive de Gunicorn.
- `NGINX_CLIENT_BODY_TIMEOUT_SECONDS` (s)
- `NGINX_PROXY_READ_TIMEOUT_SECONDS` (s)
- `NGINX_PROXY_CONNECT_TIMEOUT_SECONDS` (s)
- `NGINX_PROXY_SEND_TIMEOUT_SECONDS` (s)
- `NGINX_SSL_SESSION_TIMEOUT_SECONDS` (s)

## 3) Inventario de timeouts (DEMO)

Variables recomendadas para operación (definidas en `demo/.env.example`):

- `DEMO_NL2SQL_HTTP_TIMEOUT_SECONDS` (s) — timeout HTTP cURL demo→API.
- `DEMO_MYSQL_WAIT_TIMEOUT_SECONDS` (s)
- `DEMO_MYSQL_INTERACTIVE_TIMEOUT_SECONDS` (s)
- `DEMO_MYSQL_MAX_EXECUTION_TIME_MS` (ms)
- `DEMO_HEALTHCHECK_TIMEOUT_SECONDS` (s)

## 4) Convención de defaults

- **15 minutos** equivalen a:
  - `900` segundos
  - `900000` milisegundos

Se usan estos valores por defecto en `.env.example` para estandarizar comportamiento entre ambientes.
