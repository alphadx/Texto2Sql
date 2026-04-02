---
name: llm-provider-onboarding
description: Implementar o actualizar un proveedor/modelo LLM en Texto2Sql de extremo a extremo. Usar cuando el usuario pida integrar una nueva compañía o modelo (por ejemplo Qwen/Kimi), ajustar precedencia/validaciones de configuración, agregar wiring en converter/API, actualizar smoke tests y mantener documentación de estado por hitos en docs/providers y docs/README.md.
---

# LLM Provider Onboarding

## Overview

Seguir este workflow para integrar proveedores nuevos de forma consistente (runtime, startup, tests, docs y smoke) sin romper integraciones existentes.

## Workflow

1. Definir alcance del proveedor (Hito 0/Hito 1).
2. Implementar configuración runtime/startup (Hito 2).
3. Agregar pruebas de wiring converter/API e2e mockeado.
4. Actualizar documentación y backlog.
5. Ejecutar validaciones y cerrar evidencia.

## Paso 1: Definir proveedor y contrato

- Registrar `provider_id`, aliases, default `model` y default `base_url`.
- Definir variables por proveedor: `<PROVIDER>_API_KEY`, `<PROVIDER>_MODEL`, `<PROVIDER>_BASE_URL`.
- Confirmar precedencia canónica: `request llm_* -> <PROVIDER>_* -> LLM_* -> defaults`.
- Documentar errores esperados: `missing_api_key`, `invalid_base_url`, `provider_http_error`, `rate_limited`.

Si necesitas formato detallado de diseño, lee `references/provider-handover-checklist.md`.

## Paso 2: Implementar configuración en código

Actualizar, como mínimo:

- `app/llm/providers.py`
  - `_DEFAULT_MODELS`
  - `_DEFAULT_BASE_URLS` (si aplica)
  - `resolve_runtime_config` (precedencia y validaciones)
- `app/llm/settings.py`
  - defaults/aliases/paridad startup
  - validación de `base_url`

Mantener coherencia entre defaults de runtime y startup.

## Paso 3: Implementar wiring y pruebas

Agregar pruebas por capa:

- Runtime config: `tests/test_llm_providers.py`
- Startup config: `tests/test_llm_settings.py`
- Converter wiring: `tests/test_llm_converter.py`
- API e2e forwarding (`llm_*`): `tests/test_app.py`
- Errores API de config: `tests/test_api_llm_errors.py`
- Smoke behavior: `tests/test_llm_smoke_script.py`

Criterio mínimo: evidencia de provider/model/base_url correctos y errores de configuración con `400`/exit code esperados.

## Paso 4: Documentar estado por hitos

Actualizar:

- `docs/providers/<provider>.md`
  - Hito 0: alineación
  - Hito 1: diseño técnico
  - Hito 2: implementación + evidencia
- `docs/README.md` con estado del backlog (`[ ]` o `[x]`).

Mantener nombres de modelos/endpoints alineados con catálogo.

## Paso 5: Validar y cerrar

Ejecutar como baseline:

- `pytest -q tests/test_llm_providers.py tests/test_llm_settings.py tests/test_llm_converter.py tests/test_app.py`
- `python scripts/validate_provider_docs.py`
- `git diff --check`

Si cambia smoke/error handling, ejecutar también:

- `pytest -q tests/test_llm_smoke_script.py tests/test_api_llm_errors.py`

## Output esperado al cerrar una integración

- Código de configuración y validación listo.
- Wiring probado en converter y API e2e.
- Docs de proveedor y backlog actualizados.
- Evidencia de tests/verificaciones en verde.
