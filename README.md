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

## Variables de despliegue

### Aplicación

- `OPENAI_API_KEY`: clave obligatoria para llamar al modelo.
- `OPENAI_MODEL` (default `gpt-4` en `docker-compose.yml`).
- `SESSION_MANAGER_BACKEND` (`memory` o `redis`).
- `REDIS_URL`, `SESSION_TTL_SECONDS`, `SESSION_KEY_PREFIX` (si se usa Redis).

### Gunicorn / Uvicorn (ASGI)

- `GUNICORN_BIND` (default `0.0.0.0:5000`).
- `WEB_CONCURRENCY` (default `max(2, CPU)`): número de workers de proceso.
- `WORKER_CONNECTIONS` (default `1000`): concurrencia de sockets por worker async.
- `TIMEOUT` (default `180`): timeout duro por request en segundos.
- `GRACEFUL_TIMEOUT` (default `30`): ventana de apagado elegante.
- `KEEPALIVE` (default `5`): keep-alive HTTP.
- `MAX_REQUESTS` (default `2000`) y `MAX_REQUESTS_JITTER` (default `200`): reciclado preventivo de workers.
- `LOG_LEVEL` (default `info`).
- `FORWARDED_ALLOW_IPS` (default `*`) para headers de proxy.

### Nginx (reverse proxy)

- Rate limiting por IP: `10 req/s` con burst `20`.
- Límite de conexiones por IP: `20`.
- `client_max_body_size`: `2m`.
- Timeouts de proxy: `connect=15s`, `read/send=180s`.
- Certificados TLS esperados en:
  - `/etc/nginx/certs/fullchain.pem`
  - `/etc/nginx/certs/privkey.pem`

## Perfiles de ejecución

### Perfil local (desarrollo)

- HTTP en `localhost` sin redirect a HTTPS.
- Puede ejecutarse solo con `docker compose up --build`.
- Recomendado usar `SESSION_MANAGER_BACKEND=memory` para pruebas rápidas.

### Perfil producción

- HTTP (`:80`) redirige a HTTPS (`:443`) para hosts distintos de `localhost`.
- Montar certificados reales en `/etc/nginx/certs/`.
- Exponer puerto 443 en el servicio `nginx` y mantener 80 para redirect.
- Recomendado:
  - `SESSION_MANAGER_BACKEND=redis`
  - ajustar `WEB_CONCURRENCY` según CPU y carga esperada
  - mantener límites de body/rate limiting activos

## Ejemplo de variables para producción

```env
OPENAI_API_KEY=***
OPENAI_MODEL=gpt-4
SESSION_MANAGER_BACKEND=redis
REDIS_URL=redis://redis:6379/0
SESSION_TTL_SECONDS=3600
SESSION_KEY_PREFIX=nl2sql:session

WEB_CONCURRENCY=4
WORKER_CONNECTIONS=1000
TIMEOUT=180
GRACEFUL_TIMEOUT=30
KEEPALIVE=5
MAX_REQUESTS=2000
MAX_REQUESTS_JITTER=200
LOG_LEVEL=info
FORWARDED_ALLOW_IPS=*
```
