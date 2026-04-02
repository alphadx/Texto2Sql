# Hito 1 — Diseño técnico transversal (Xinghuo, Doubao, Zhipu, MiniMax, Pangu, Grok)

Este documento cierra el diseño técnico transversal para preparar la implementación de los seis proveedores solicitados.

## 1) Decisiones de arquitectura por proveedor

| Provider ID | Compañía | Estrategia inicial | Motivo técnico | Riesgo principal |
|---|---|---|---|---|
| `xinghuo` | iFlytek | OpenAI-compatible (si endpoint lo soporta) con fallback a gateway nativo | Minimiza tiempo de integración y reutiliza `OpenAICompatibleGateway` | Diferencias de payload/headers por versión |
| `doubao` | ByteDance | OpenAI-compatible con posibilidad de gateway nativo | Mantiene paridad con proveedores hosted ya integrados | Cambios de endpoint regional/tenant |
| `zhipu` | Zhipu AI | OpenAI-compatible primero | Patrón más cercano a integraciones actuales | Compatibilidad parcial en tool-calls/mensajes |
| `minimax` | MiniMax | OpenAI-compatible primero | Reutilización de validaciones y precedencia vigente | Divergencia en auth y límites por modelo |
| `pangu` | Huawei Cloud | Gateway nativo por defecto (evaluar compatibilidad) | Reduce acoplamiento a supuestos OpenAI si API difiere | Complejidad de mapeo de mensajes |
| `grok` | xAI | OpenAI-compatible primero | Probable ajuste mínimo sobre stack actual | Políticas/headers específicos del proveedor |

### Criterio de selección definitivo en implementación

1. Si el proveedor responde correctamente a contrato `chat.completions` del cliente OpenAI, se integra como OpenAI-compatible.
2. Si no hay paridad funcional mínima (mensajes/sistema/errores), se implementa gateway nativo dedicado.
3. La elección final se registrará en el PR de cada proveedor (Hitos 2–5) con evidencia de pruebas.

## 2) Contrato de configuración (canónico)

Se mantiene la precedencia transversal:

1. Overrides por request: `llm_provider`, `llm_model`, `llm_api_key`, `llm_base_url`.
2. Variables por proveedor: `<PROVIDER>_API_KEY`, `<PROVIDER>_MODEL`, `<PROVIDER>_BASE_URL`.
3. Variables globales: `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`.
4. Defaults del código por proveedor.

## 3) Especificación de IDs, aliases y variables por proveedor

| Provider ID | Aliases propuestos | Prefijo env |
|---|---|---|
| `xinghuo` | `spark`, `iflytek` | `XINGHUO` |
| `doubao` | `bytedance` | `DOUBAO` |
| `zhipu` | `glm` | `ZHIPU` |
| `minimax` | `mini-max` | `MINIMAX` |
| `pangu` | `huawei`, `huaweicloud` | `PANGU` |
| `grok` | `xai` | `GROK` |

Variables esperadas por proveedor:

- `<PREFIX>_API_KEY`
- `<PREFIX>_MODEL`
- `<PREFIX>_BASE_URL`

## 4) Defaults iniciales de modelo/base_url (propuestos)

> Estos valores son **placeholders técnicos** para guiar implementación. Se validarán y ajustarán con documentación oficial al ejecutar cada hito de proveedor.

| Provider ID | Modelo default inicial | Base URL default inicial |
|---|---|---|
| `xinghuo` | `generalv3.5` | `https://spark-api-open.xf-yun.com/v1` |
| `doubao` | `doubao-pro-32k` | `https://ark.cn-beijing.volces.com/api/v3` |
| `zhipu` | `glm-4-flash` | `https://open.bigmodel.cn/api/paas/v4` |
| `minimax` | `MiniMax-Text-01` | `https://api.minimax.chat/v1` |
| `pangu` | `pangu-pro` | `https://modelarts.cn-north-4.myhuaweicloud.com/v1` |
| `grok` | `grok-2-latest` | `https://api.x.ai/v1` |

## 5) Contrato transversal de errores (API/runtime)

Errores mínimos estandarizados por proveedor:

- `missing_api_key`: no existe API key efectiva tras resolver precedencia.
- `invalid_base_url`: URL no absoluta `http(s)`.
- `provider_http_error`: error HTTP no recuperable del proveedor.
- `rate_limited`: proveedor devuelve condición de límite de tasa.
- `provider_timeout`: timeout contra endpoint remoto.

Mapeo mínimo esperado en API:

- Errores de configuración: `400`.
- Errores remotos recuperables/transitorios: `502/503` según corresponda.
- Mensajes de error deben incluir `provider` para trazabilidad.

## 6) Plan de pruebas transversal (por cada proveedor)

1. `tests/test_llm_providers.py`
   - resolución de config runtime y validaciones.
2. `tests/test_llm_settings.py`
   - paridad startup (aliases/defaults/validación base_url).
3. `tests/test_llm_converter.py`
   - wiring provider→gateway.
4. `tests/test_app.py` + `tests/test_api_llm_errors.py`
   - forwarding `llm_*` y errores `400/5xx` esperados.
5. `tests/test_llm_smoke_script.py`
   - cobertura dry-run para proveedor añadido.

## 7) Entregables para cerrar Hito 1

- Documento de diseño transversal publicado (este documento).
- Variables/aliases/defaults propuestos para los 6 proveedores.
- Contrato de errores y plan de pruebas definido por capas.
- Dependencias para Hitos 2–5 explícitas y sin ambigüedad.

## 8) Dependencias habilitadas para los siguientes hitos

- **Hito 2 (Xinghuo):** puede iniciar inmediatamente con este contrato.
- **Hito 3 (Doubao):** reutiliza la misma plantilla de implementación.
- **Hito 4 (Zhipu + MiniMax):** ejecución en paralelo posible.
- **Hito 5 (Pangu + Grok):** requiere confirmar decisión final OpenAI-compatible vs nativo en PR técnico.
