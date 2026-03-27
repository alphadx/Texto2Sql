# Demo one-container (PHP 8.3 + Yii3 + MySQL + Sakila)

Este demo levanta **un solo contenedor Docker** con:

- PHP 8.3
- Instalador/skeleton de Yii3 (best-effort)
- MySQL server con base `sakila` cargada automáticamente
- UI de chat (única página) para enviar consultas en lenguaje natural
- Historial en caché con TTL configurable (default: 360 minutos)

## Uso rápido

```bash
make install-main-config  # define proveedor/modelo/api key en el programa principal
make demo-install         # crea demo/.env para runtime del contenedor demo
make demo-up
make demo-smoke          # valida que sakila se haya cargado correctamente
```

La app queda en: <http://localhost:8080>

## Parámetros en vista (editables en runtime)

La vista de demo ahora expone **todos los parámetros relevantes** para ejecutar la API:

- URL de API y Bearer token
- Credenciales y conexión DB (`host`, `port`, `name`, `user`, `password`, `engine`)
- Parámetros LLM (`provider`, `model`, `base_url`, `api_key`)
- `ttl_minutes`

Comportamiento:

- Si el usuario deja campos vacíos, el backend usa los valores por defecto (env del demo o defaults internos).
- Si el usuario ingresa valores, se envían en el request y tienen prioridad.
- Si cambia el contexto (endpoint + DB + proveedor/modelo/base_url LLM), la vista rota automáticamente `session_id` y empieza un nuevo hilo.

## Ambigüedad resuelta en esta iteración

Se definió explícitamente qué cambio de parámetros rompe el hilo conversacional:

- `api_url`, `db_engine`, `db_host`, `db_port`, `db_name`, `db_user`, `llm_provider`, `llm_model`, `llm_base_url`

Cuando cambia cualquiera, se crea una nueva sesión. Así evitamos mezclar contexto viejo con nueva configuración.

## Variables claves (`demo/.env`)

- `NL2SQL_API_URL` (endpoint del programa principal)
- `NL2SQL_API_KEY` (Bearer para la API principal, si aplica)
- `CHAT_CACHE_TTL_MINUTES` (default 360)
- `CHAT_MAX_MESSAGES` (default 40)
- `INSTALL_YII_ON_BOOT` (`false` default para acelerar startup; `true` si quieres crear skeleton Yii3 al boot)

## Flujo

1. El usuario escribe en el chat.
2. El contenedor llama al endpoint de API (`NL2SQL_API_URL`) con credenciales + consulta NL.
3. La API responde JSON con SQL/resultados.
4. La UI dibuja una tabla por respuesta del asistente y deja todo en caché por sesión.
