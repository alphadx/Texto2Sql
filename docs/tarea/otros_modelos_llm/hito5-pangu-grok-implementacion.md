# Hito 5 — Integración Pangu + Grok (implementación y evidencia)

## 1) Alcance implementado

Se integraron **Pangu** y **Grok** como proveedores OpenAI-compatible dentro del stack actual.

### Pangu
- Provider: `pangu`
- Aliases: `huawei`, `huaweicloud`
- Prefijo env: `PANGU`
- Modelo default: `pangu-pro`
- Base URL default: `https://modelarts.cn-north-4.myhuaweicloud.com/v1`

### Grok
- Provider: `grok`
- Alias: `xai`
- Prefijo env: `GROK`
- Modelo default: `grok-2-latest`
- Base URL default: `https://api.x.ai/v1`

## 2) Cambios técnicos realizados

1. Runtime (`app/llm/providers.py`):
   - aliases/normalización,
   - prefijos env,
   - defaults model/base_url por proveedor.
2. Startup (`app/llm/settings.py`):
   - proveedores soportados,
   - aliases equivalentes,
   - defaults model/base_url.
3. Pruebas:
   - runtime config y gateway fallback,
   - startup defaults,
   - wiring converter,
   - forwarding API e2e mock,
   - smoke dry-run.

## 3) Definition of Done (Hito 5)

- [x] Ambos proveedores integrados y validados.
- [x] Evidencia de compatibilidad en smoke/tests.
- [x] Actualización de catálogo/docs/scripts de validación (docs operativas + seguimiento de hitos).

## 4) Evidencia de validación

Comandos de validación ejecutados en este hito:

- `pytest -q tests/test_llm_providers.py tests/test_llm_settings.py tests/test_llm_converter.py tests/test_app.py tests/test_llm_smoke_script.py`
- `git diff --check`
