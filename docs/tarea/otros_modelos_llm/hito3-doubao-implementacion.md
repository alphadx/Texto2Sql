# Hito 3 — Integración Doubao (implementación y evidencia)

## 1) Alcance implementado

Se integró **Doubao** como proveedor OpenAI-compatible dentro del stack actual:

- Identificador de proveedor: `doubao`
- Alias soportado: `bytedance`
- Prefijo de entorno: `DOUBAO`
- Modelo default: `doubao-pro-32k`
- Base URL default: `https://ark.cn-beijing.volces.com/api/v3`

## 2) Cambios técnicos realizados

1. Runtime (`app/llm/providers.py`):
   - alias/normalización de proveedor,
   - mapping de prefijo env,
   - defaults de `model` y `base_url`.
2. Startup (`app/llm/settings.py`):
   - proveedor soportado,
   - alias equivalente,
   - defaults de `model` y `base_url`.
3. Pruebas:
   - runtime config y gateway fallback,
   - startup defaults,
   - wiring converter,
   - forwarding API e2e mock,
   - smoke dry-run.

## 3) Definition of Done (Hito 3)

- [x] Paridad técnica con Hito 2 (Xinghuo).
- [x] Validaciones de configuración y errores de API cubiertos.
- [x] Smoke dry-run estable.

## 4) Evidencia de validación

Comandos de validación ejecutados en este hito:

- `pytest -q tests/test_llm_providers.py tests/test_llm_settings.py tests/test_llm_converter.py tests/test_app.py tests/test_llm_smoke_script.py`
- `git diff --check`
