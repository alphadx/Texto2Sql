# Hito 2 — Integración Xinghuo (implementación y evidencia)

## 1) Alcance implementado

Se integró **Xinghuo** como proveedor OpenAI-compatible dentro del stack actual:

- Identificador de proveedor: `xinghuo`
- Aliases soportados: `spark`, `iflytek`
- Prefijo de entorno: `XINGHUO`
- Modelo default: `generalv3.5`
- Base URL default: `https://spark-api-open.xf-yun.com/v1`

## 2) Cambios técnicos realizados

1. Runtime (`app/llm/providers.py`):
   - alias/normalización de proveedor,
   - mapping de prefijo env,
   - defaults de `model` y `base_url`.
2. Startup (`app/llm/settings.py`):
   - proveedor soportado,
   - aliases equivalentes,
   - defaults de `model` y `base_url`.
3. Pruebas:
   - runtime config y gateway fallback,
   - startup defaults,
   - wiring converter,
   - forwarding API e2e mock,
   - smoke dry-run.

## 3) Definition of Done (Hito 2)

- [x] Runtime/startup config implementado.
- [x] Wiring converter/API con pruebas.
- [x] Documentación y estado de backlog actualizados.

## 4) Evidencia de validación

Comandos de validación ejecutados en este hito:

- `pytest -q tests/test_llm_providers.py tests/test_llm_settings.py tests/test_llm_converter.py tests/test_app.py tests/test_llm_smoke_script.py`
- `git diff --check`
