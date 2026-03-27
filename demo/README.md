# Demo one-container (PHP 8.3 + Yii3 + MySQL + Sakila)

Este demo levanta **un solo contenedor Docker** con:

- PHP 8.3
- Instalador/skeleton de Yii3 (best-effort)
- MySQL server con base `sakila` cargada automáticamente
- UI de chat (única página) para enviar consultas en lenguaje natural
- Historial en caché con TTL configurable (default: 360 minutos)

## Uso rápido

```bash
make demo-install   # crea demo/.env (solicita provider + key + modelo + DB + TTL)
make demo-up
```

La app queda en: <http://localhost:8080>

## Parámetros y comportamiento dinámico

- La vista incluye sección **Parámetros del test** para cambiar en runtime:
  - host, puerto, DB, usuario, password y engine
  - TTL del historial
- Estos valores se guardan en `localStorage`.
- En cada mensaje, el backend reenvía esas credenciales a la API NL2SQL y guarda la respuesta (incluyendo tabla) en el historial de sesión.

## Variables claves (`demo/.env`)

- `NL2SQL_API_PROVIDER`
- `NL2SQL_API_KEY`
- `NL2SQL_MODEL`
- `NL2SQL_API_URL`
- `CHAT_CACHE_TTL_MINUTES` (default 360)
- `CHAT_MAX_MESSAGES` (default 40)

## Flujo

1. El usuario escribe en el chat.
2. El contenedor llama al endpoint de API (`NL2SQL_API_URL`) con credenciales + consulta NL.
3. La API responde JSON con SQL/resultados.
4. La UI dibuja una tabla por respuesta del asistente y deja todo en caché por sesión.
