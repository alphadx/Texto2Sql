# Hito 4 — Integración Zhipu + MiniMax (implementación y evidencia)

## 1) Alcance implementado

Se integraron **Zhipu** y **MiniMax** como proveedores OpenAI-compatible dentro del stack actual.

### Zhipu
- Provider: `zhipu`
- Alias: `glm`
- Prefijo env: `ZHIPU`
- Modelo default: `glm-4-flash`
- Base URL default: `https://open.bigmodel.cn/api/paas/v4`

### MiniMax
- Provider: `minimax`
- Alias: `mini-max`
- Prefijo env: `MINIMAX`
- Modelo default: `MiniMax-Text-01`
- Base URL default: `https://api.minimax.chat/v1`

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

## 3) Definition of Done (Hito 4)

- [x] Ambos proveedores integrados con el mismo estándar de pruebas.
- [x] Cobertura de converter/API y validaciones startup/runtime.
- [x] Documentación operativa por proveedor completa.

## 4) Evidencia de validación

Comandos de validación ejecutados en este hito:

- `pytest -q tests/test_llm_providers.py tests/test_llm_settings.py tests/test_llm_converter.py tests/test_app.py tests/test_llm_smoke_script.py`
- `git diff --check`
