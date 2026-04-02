# Roadmap: Skill de onboarding + integración Qwen/Kimi

Este documento fija el **Hito 0 (alineación)** para la iniciativa:

1. Crear una skill reusable para alta de nuevos proveedores/modelos LLM.
2. Integrar **Qwen**.
3. Integrar **Kimi**.

## 1) Alcance acordado

### 1.1 Skill de onboarding (framework reusable)
- Definir un estándar único para incorporar proveedores nuevos al stack NL→SQL.
- Incluir pasos para: runtime config, startup config, validaciones, errores, smoke y docs.
- Incluir checklist de pruebas mínimas para evitar regresiones.

### 1.2 Qwen
- Integración v1 con la misma arquitectura multi-proveedor actual.
- Soporte de `llm_*` por request + env por proveedor + fallback global.
- Cobertura de wiring converter/API y smoke dry-run.

### 1.3 Kimi
- Integración v1 siguiendo el mismo estándar de Qwen y proveedores previos.
- Cobertura de configuración, validación y pruebas e2e mockeadas.

## 2) Fuera de alcance (Hito 0)

- Implementación de código de Qwen/Kimi.
- Ajustes avanzados de optimización de prompts por dominio.
- Estrategias de routing dinámico multi-proveedor con políticas de costo/latencia en tiempo real.

## 3) Criterios de aceptación del Hito 0

El Hito 0 se considera cerrado cuando:

1. Queda documentada la secuencia de hitos para skill + Qwen + Kimi.
2. Se fijan Definition of Done medibles por cada bloque.
3. Se listan riesgos iniciales y mitigaciones.
4. El plan es ejecutable paso a paso sin ambigüedad.

## 4) Definition of Done por bloque

### 4.1 Skill de onboarding (DoD)
1. Plantilla de integración de proveedor publicada (config + tests + docs + smoke).
2. Lista de chequeo obligatoria para PRs de nuevos proveedores.
3. Guía de uso con ejemplo completo de “alta de proveedor”.

### 4.2 Qwen (DoD)
1. Runtime/startup defaults + precedencia request/env-provider/env-global.
2. Validación de `api_key`, `model`, `base_url` y errores consistentes.
3. Pruebas de wiring (converter + API e2e mockeado).
4. Documentación y estado en `docs/README.md`.

### 4.3 Kimi (DoD)
1. Misma paridad técnica y de pruebas alcanzada en Qwen.
2. Smoke dry-run y evidencia de robustez de configuración.
3. Documentación operativa y checklist de salida v1.

## 5) Riesgos iniciales y mitigaciones

- **Drift entre documentación y código**  
  Mitigación: mantener validadores de docs/catálogo en CI.

- **Diferencias de compatibilidad entre endpoints**  
  Mitigación: encapsular diferencias por gateway + pruebas de wiring por proveedor.

- **Errores de configuración en producción**  
  Mitigación: validación temprana startup/runtime + errores API 400 + smoke dry-run.

- **Crecimiento desordenado de integraciones**  
  Mitigación: forzar uso de la skill/checklist como “puerta” de calidad.

## 6) Orden de ejecución aprobado (siguientes hitos)

1. **Hito 1**: diseño e implementación de la skill de onboarding.
2. **Hito 2**: Qwen (diseño + implementación + pruebas + docs).
3. **Hito 3**: Kimi (diseño + implementación + pruebas + docs).
