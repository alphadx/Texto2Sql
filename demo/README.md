# Demo one-container (PHP 8.3 + Yii3 + MySQL + Sakila)

Este demo levanta **un solo contenedor Docker** con:

- PHP 8.3
- Instalador/skeleton de Yii3 (best-effort)
- MySQL server con base `sakila` cargada automáticamente
- UI de chat (única página) para enviar consultas en lenguaje natural
- Historial en caché con TTL configurable (default: 360 minutos)

## Uso rápido

```bash
make demo-install
make demo-up
```

La app queda en: <http://localhost:8080>

## Variables claves

Se guardan en `demo/.env` usando el asistente `make demo-install`:

- `NL2SQL_API_PROVIDER`
- `NL2SQL_API_KEY`
- `NL2SQL_MODEL`
- `NL2SQL_API_URL`
- `CHAT_CACHE_TTL_MINUTES` (default 360)

## Flujo

1. El usuario escribe en el chat.
2. El contenedor llama al endpoint de API (`NL2SQL_API_URL`) con credenciales + consulta NL.
3. La API responde JSON con SQL/resultados.
4. La UI dibuja la tabla y guarda historial en caché de archivo por sesión.
