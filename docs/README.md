# Documentación de LLM comerciales y configuración de API keys

Este documento resume **qué modelos/proveedores LLM comerciales** soporta el proyecto hoy y **cómo se configuran las API keys** tanto por entorno como por request.

## 1) Resumen rápido

- El backend usa el SDK de `openai` y un cliente `OpenAI(...)` configurable con `base_url`, por lo que opera como **OpenAI-compatible API**.
- El proveedor por defecto es `openai`.
- El modelo por defecto en runtime es `gpt-4`.
- Se puede sobreescribir proveedor/modelo/key/base_url por cada request en `POST /nl2sql/query`.

## 2) Qué LLM comerciales están disponibles en el código

Actualmente, el código implementa integración directa con un cliente OpenAI-compatible:

- **Proveedor lógico**: `openai` (default).
- **Modelos**: cualquier modelo aceptado por el endpoint OpenAI-compatible configurado en `OPENAI_BASE_URL`.
  - Ejemplos visibles en el proyecto:
    - `gpt-4` (default en `resolve_llm_config`).
    - `gpt-4.1-mini` (ejemplo en el schema de request).

> Nota: El campo `llm_provider` existe y se transporta en request, pero el cliente concreto se construye con `OpenAI(...)`; por eso, para otros proveedores comerciales se espera un endpoint compatible o adaptación futura del código.

## 3) Configuración principal por variables de entorno

Las variables de entorno oficiales para el motor LLM son:

- `LLM_PROVIDER`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`

Flujo de resolución en backend (`app/llm/converter.py`):

1. Toma primero los overrides de `llm_options` (request).
2. Si no existen, usa variables de entorno.
3. Si falta API key, lanza error de runtime.

## 4) Overrides por request (runtime)

El endpoint `POST /nl2sql/query` permite enviar:

- `llm_provider`
- `llm_model`
- `llm_api_key`
- `llm_base_url`

Esto habilita escenarios multi-tenant o pruebas de proveedor/modelo sin tocar el `.env` global.

## 5) Variables usadas en demo/UI

El demo (`demo/app/public/chat.php`) consume parámetros runtime y/o env para reenviarlos al backend:

- `NL2SQL_API_PROVIDER` → `llm_provider`
- `NL2SQL_MODEL` → `llm_model`
- `LLM_API_KEY` → `llm_api_key`
- `LLM_BASE_URL` → `llm_base_url`

Además, puede incluir un bearer para la API principal con `NL2SQL_API_KEY`.

## 6) Archivos clave para mantener esta integración

- `app/llm/converter.py`: resolución de config LLM y cliente OpenAI-compatible.
- `app/api.py`: schema de request con campos `llm_*` y construcción de `llm_options`.
- `README.md`: guía de instalación principal y variables oficiales.
- `demo/app/public/chat.php`: mapeo de variables/env del demo hacia payload `llm_*`.

## 7) Recomendaciones de documentación futura

Si se agrega soporte nativo para otros proveedores comerciales (Anthropic, Gemini, etc.), documentar explícitamente:

1. SDK/cliente usado por proveedor.
2. Variables de entorno por proveedor.
3. Modelos validados/oficialmente soportados.
4. Reglas de precedencia entre `.env` y overrides por request.

## 8) TODO de implementación (pendiente)

Se deja explícito el backlog para ampliar proveedores/modelos más allá de OpenAI-compatible.

> Alcance actual: este backlog documenta trabajo pendiente de producto/arquitectura; no implica soporte GA hasta cerrar criterios mínimos por proveedor.

- [x] **DeepSeek**: integración inicial por compatibilidad OpenAI completada (pendiente evolución a cliente nativo solo si aparece brecha funcional).
- [x] **Hugging Face Inference**: integración v1 completada (serverless + dedicated endpoint en modo OpenAI-compatible; evolución futura a capacidades nativas según necesidad).
- [x] **Gemini (Google)**: integración v1 completada (gateway nativo `generateContent`, mapeo de prompts y soporte por request/env).
- [x] **Mistral**: integración v1 completada (OpenAI-compatible `chat/completions` con soporte por request/env y validación de configuración).
- [ ] **Claude (Anthropic)**: cliente dedicado, manejo de mensajes y compatibilidad con el flujo de 2 agentes. *(Hitos 0 y 1 documentados en `docs/providers/claude.md`; pendiente implementación.)*
- [ ] **Llama** (proveedores comerciales/hosted): definir variantes soportadas y endpoint objetivo.
- [ ] **Copilot** (escenario enterprise): evaluar alcance técnico real para uso como backend programático.

### Criterios mínimos para cerrar cada TODO

1. Variables nuevas documentadas en `.env.example` o guía equivalente.
2. Validación de configuración (`api_key`, `model`, `base_url`) en backend.
3. Ejemplo funcional en `POST /nl2sql/query` usando `llm_*` por request.
4. Pruebas mínimas (unit/integración) para resolución de configuración y llamada al proveedor.

## 9) Configuración operativa centralizada (resiliencia)

Para operación estable multi-proveedor, la capa LLM ahora contempla parámetros globales:

- `LLM_MAX_RETRIES`: reintentos por llamada cuando hay fallos transitorios.
- `LLM_RETRY_BACKOFF_SECONDS`: backoff base (exponencial) entre reintentos.
- `LLM_HTTP_TIMEOUT_SECONDS`: timeout HTTP para gateways nativos.
- `LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD`: fallos consecutivos para abrir circuito por proveedor.
- `LLM_CIRCUIT_BREAKER_RESET_SECONDS`: ventana antes de permitir intentos de recuperación.

Además de:

- `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` (defaults globales),
- y el fallback por proveedor con `<PROVIDER>_API_KEY`, `<PROVIDER>_MODEL`, `<PROVIDER>_BASE_URL`.

### Matriz rápida por proveedor (actual)

- **OpenAI / DeepSeek / Mistral / HuggingFace / Llama / Copilot**: ruta OpenAI-compatible.
- **Anthropic**: gateway nativo `messages`.
- **Gemini**: gateway nativo `generateContent`.

## 10) Hito de guías por compañía (multi-lenguaje)

Se creó un paquete de documentación por compañía con enfoque en modelo mini/equivalente y snippets compatibles con:

- PHP 8.3
- Node.js (LTS actual)
- Python (estable actual)
- C++ (estándar actual + libcurl)
- C# (.NET actual)
- Java (JDK actual)

Índice: `docs/providers/README.md`.

## 11) Hito de configuración central (`.env.example` + validación de arranque)

Se añadió `.env.example` con:

- variables base de auth,
- defaults LLM,
- API keys por proveedor,
- y parámetros de resiliencia.

También se incorporó validación de settings LLM al arranque de la API:

- `LLM_PROVIDER` debe ser soportado,
- parámetros de resiliencia deben tener rangos válidos,
- si `LLM_STARTUP_VALIDATE=true`, la API key debe existir al iniciar.

## 12) Hito de smoke-test por proveedor (CI + script)

Se añadió:

- script `scripts/llm_provider_smoke.py` (modo `--dry-run` y modo live),
- target `make llm-smoke-dry`,
- job de CI con matriz de proveedores para validar wiring de configuración/gateway sin llamadas reales.

## 13) Hito final: matriz de compatibilidad + checklist de producción

Se añadieron dos documentos operativos:

- `docs/providers/compatibility-matrix.md`: matriz por proveedor/lenguaje/modelo mini-equivalente.
- `docs/providers/production-checklist.md`: checklist de despliegue por compañía.

## 14) Hito extra: catálogo JSON para automatización

Se añadió `docs/providers/catalog.json` como fuente machine-readable con:

- proveedor,
- compañía,
- modelo mini/equivalente,
- variable de API key,
- endpoint base,
- y ruta del markdown asociado.

Además:

- script `scripts/validate_provider_catalog.py` para validar integridad del catálogo,
- test automatizado en `tests/test_provider_catalog_validator.py`,
- y job de CI `provider-catalog-validate`.

## 15) Hito extra: generación automática de artefactos de docs

Se añadió `scripts/generate_provider_artifacts.py` para generar desde `catalog.json`:

- `docs/providers/compatibility-matrix.md`
- `docs/providers/snippets-index.md`

Con validación de sincronía en CI (`provider-artifacts-sync`).

## 16) Hito extra: generación de markdowns por proveedor desde catálogo

Se añadieron:

- `scripts/generate_provider_markdowns.py` para regenerar `docs/providers/*.md` desde `catalog.json`.
- `scripts/validate_provider_docs.py` para validar consistencia catálogo ↔ markdown.
- job CI `provider-markdown-sync` para exigir sincronía.

## 17) Hito de cierre completo: snippets typed + validación CI

Se añadieron:

- `scripts/generate_typed_snippets.py` para generar snippets por proveedor/lenguaje en `docs/providers/sdk/`.
- `scripts/validate_typed_snippets.py` para validar estructura y contenido base.
- job CI `typed-snippets-sync` para generar, validar y comprobar sincronía (`git diff --exit-code`).

## 18) Gobernanza de cambios del Demo

Para cambios que impacten el demo (contrato API, UX o smokes), usar:

- Proceso de change management: `docs/demo-change-management.md`
- Plantilla PR con sección obligatoria **Impacto en DEMO**: `.github/pull_request_template.md`

Esto permite declarar releases como **Demo Compatible** con evidencia verificable.
