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

## Contrato de integración del Demo

El adaptador de `demo/app/public/chat.php` consume el endpoint principal `/nl2sql/query` y **normaliza internamente** la respuesta a:

- `columnas: string[]`
- `filas: array[]`
- `sql_generado: string|null`
- `texto_formal: string|null`
- `error: string|null`
- `http_code: int|null`
- `error_type: one of [none, connectivity, auth, validation, execution, api_error]`
- `request_ts: unix timestamp`
- `latency_ms: int`

### Matriz de compatibilidad Demo ↔ API

| Escenario | Campo API (actual) | Campo API (legacy) | Campo canónico demo |
|---|---|---|---|
| Columnas | `columns` | `columnas` | `columnas` |
| Filas | `rows` | `filas` | `filas` |
| SQL generado | `sql` | `sql_generado` | `sql_generado` |
| Texto formal (refiner) | `texto_formal` | _(no disponible)_ | `texto_formal` |
| Error simple | `error` | `errores` (string) | `error` |
| Error FastAPI | `detail.error` | `detail` (string) | `error` |
| Error no JSON | _body no parseable_ | _body no parseable_ | `error` + `error_type` |

### Reglas de fallback

1. Si no hay `texto_formal`, la UI muestra: `Texto formal: No disponible en respuesta API`.
2. Si no hay `sql`/`sql_generado`, la UI muestra: `SQL: No disponible en respuesta API`.
3. Si la API retorna body no JSON, se informa `La API devolvió un body no JSON (HTTP NNN)`.
4. En errores HTTP se categoriza por tipo para feedback más útil:
   - `401/403`: `auth`
   - `400/404/422`: `validation`
   - `5xx`: `execution`
   - fallo cURL: `connectivity`

### Ejemplos JSON

Éxito (formato actual):

```json
{
  "columns": ["name", "total"],
  "rows": [["Action", 1320]],
  "sql": "SELECT ...",
  "texto_formal": "Mostrar el total por categoría."
}
```

Éxito (formato legacy):

```json
{
  "columnas": ["name", "total"],
  "filas": [["Action", 1320]],
  "sql_generado": "SELECT ..."
}
```

Error FastAPI:

```json
{
  "detail": {
    "error": "No se pudo generar SQL"
  }
}
```

### Checklist previa a merge (cambios de contrato API)

- [ ] ¿`columns/rows` o `columnas/filas` siguen siendo parseables por el demo?
- [ ] ¿Errores en `error`, `errores`, `detail.error` o `detail` string muestran mensaje útil?
- [ ] ¿El demo sigue mostrando estado claro en 2xx/4xx/5xx sin romper sesión?
- [ ] ¿`texto_formal` faltante cae en fallback legible?
- [ ] ¿`sql`/`sql_generado` faltante cae en fallback legible?
- [ ] ¿`http_code`, `request_ts` y `latency_ms` quedan guardados en historial para trazabilidad?


## Cómo cambiar proveedor/modelo sin perder contexto inesperadamente

La sesión del chat rota automáticamente cuando cambia la firma de contexto (`context_signature`).

Incluye estos campos: `api_url`, `db_engine`, `db_host`, `db_port`, `db_name`, `db_user`, `llm_provider`, `llm_model`, `llm_base_url`.

Recomendación operativa:

1. Si quieres **continuar el mismo hilo**, evita cambiar esos campos y modifica solo la pregunta NL.
2. Si necesitas comparar modelos/proveedores, asume que cada cambio crea un hilo nuevo (comportamiento intencional).
3. Usa las sugerencias visuales del formulario para provider/model/base URL y puertos DB para reducir errores de configuración.

## Testing E2E del demo (chat.php GET/POST)

### Smoke full con Docker (MySQL + Sakila + mock API)

```bash
make demo-smoke
```

Este smoke ahora valida:

- Salud de MySQL y carga de `sakila`.
- `GET /chat.php` devuelve `session_id` e historial válido.
- `POST /chat.php` contra API mock con contrato **actual** (`columns/rows/sql/texto_formal`).
- `POST /chat.php` contra API mock con contrato **legacy** (`columnas/filas/sql_generado`).

### Smoke sin Docker (checks mínimos de adaptador)

```bash
make demo-smoke-nodocker
```

Este modo levanta:

- API mock local (`scripts/mock_nl2sql_api.py`).
- Servidor PHP embebido para `demo/app/public`.
- Aserciones mínimas de `chat.php` (`GET` y `POST`) sin depender de contenedores ni llaves LLM.

### Estrategia CI sugerida

- **Job con Docker (full smoke):** `make demo-smoke`.
- **Job sin Docker (rápido):** `php -l demo/app/public/chat.php`, `php scripts/demo_chat_adapter_harness.php`, `make demo-smoke-nodocker`.

## Troubleshooting Demo

Guía rápida para diagnóstico operativo (top errores):

1. **`Falla de conectividad con la API`**
   - Verifica `NL2SQL_API_URL` y reachability desde el contenedor demo.
2. **`HTTP 401/403` (`error_type=auth`)**
   - Revisa Bearer/API key y permisos del proveedor.
3. **`HTTP 422` (`error_type=validation`)**
   - Revisa parámetros DB/LLM enviados (`db_engine`, `host`, `model`, etc.).
4. **Body no JSON en respuesta API**
   - Confirma que el endpoint devuelve JSON válido y no HTML/texto de error intermedio.
5. **Sin tabla en respuesta**
   - La API pudo devolver solo error o solo SQL/texto formal; revisa `history[].result.error`, `sql_generado` y `texto_formal`.
6. **Rotación inesperada de sesión**
   - Cambiar campos de `context_signature` crea sesión nueva (comportamiento esperado).
7. **`demo-smoke-nodocker` falla al iniciar PHP**
   - Asegura que el puerto `8081` esté libre.
8. **`demo-smoke` falla por Docker/MySQL no listo**
   - Revisa logs de `texto2sql-demo` y vuelve a correr el smoke.
9. **Sin datos de Sakila**
   - Ejecuta nuevamente `make demo-smoke` para recrear volumen y carga.
10. **Errores intermitentes en integración**
   - Usa `correlation_id` del historial para trazar request demo→API en logs.

### Logging estructurado (demo)

Cada POST del chat registra una línea JSON en `/var/log/texto2sql-demo/chat.log` con:

- `ts`
- `session_id`
- `correlation_id`
- `api_url`
- `http_code`
- `latency_ms`
- `error_type`

No se registran secretos (`api_bearer`, `db_password`, `llm_api_key`).

## Checklist de seguridad del demo

> Alcance: entorno de demostración/no productivo.

- [x] Secretos sensibles (`api_bearer`, `db_password`, `llm_api_key`) **no** se persisten en `localStorage`.
- [x] Logs estructurados sanitizan campos sensibles y no registran credenciales en texto plano.
- [x] Se emiten headers de seguridad básicos en `chat.php` (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`).
- [x] CORS configurable por `NL2SQL_DEMO_ALLOWED_ORIGIN` (recomendado fijar origen explícito en despliegues remotos).
- [x] Correlation ID por request para auditoría y troubleshooting.

### Límites de uso del demo

- Uso recomendado solo para validación funcional y pruebas internas.
- No exponer públicamente sin reverse proxy, TLS y política CORS estricta.
- No almacenar secretos reales persistentes en navegadores compartidos.
- No usar el demo como canal productivo de consulta SQL.

## Variables claves (`demo/.env`)

- `NL2SQL_API_URL` (endpoint del programa principal)
- `NL2SQL_API_KEY` (Bearer para la API principal, si aplica)
- `NL2SQL_DEMO_ALLOWED_ORIGIN` (opcional; habilita CORS para un origen explícito)
- `CHAT_CACHE_TTL_MINUTES` (default 360)
- `CHAT_MAX_MESSAGES` (default 40)
- `INSTALL_YII_ON_BOOT` (`false` default para acelerar startup; `true` si quieres crear skeleton Yii3 al boot)

## Flujo

1. El usuario escribe en el chat.
2. El contenedor llama al endpoint de API (`NL2SQL_API_URL`) con credenciales + consulta NL.
3. La API responde JSON con SQL/resultados.
4. La UI dibuja una tabla por respuesta del asistente y deja todo en caché por sesión.
