# Hito 0 — Análisis y definición de hitos (Xinghuo, Doubao, Zhipu, MiniMax, Pangu, Grok)

Este documento fija el **Hito 0 (alineación)** para la nueva iniciativa de integración multi-proveedor LLM.

## 1) Objetivo de la iniciativa

Integrar en Texto2Sql los proveedores/modelos:

- Xinghuo
- Doubao
- Zhipu
- MiniMax
- Pangu
- Grok

bajo el mismo estándar técnico del proyecto (configuración runtime/startup, validaciones, wiring converter/API, smoke y documentación).

## 2) Supuestos de diseño (base Hito 0)

1. Se mantendrá la precedencia canónica de configuración:
   - `llm_*` por request → variables por proveedor (`<PROVIDER>_*`) → variables globales (`LLM_*`) → defaults.
2. Se reutilizará el patrón existente de proveedores:
   - OpenAI-compatible cuando sea viable.
   - Gateway nativo cuando el proveedor no sea totalmente compatible.
3. Cada proveedor debe cerrar paridad mínima de calidad:
   - validación de `api_key/model/base_url`,
   - pruebas unitarias + integración mock,
   - documentación operativa.

## 3) Fuera de alcance de Hito 0

- Implementación de código de cada proveedor.
- Ajustes de optimización de prompts por dominio de negocio.
- Políticas avanzadas de enrutamiento dinámico por costo/latencia.
- Hardening de producción específico por tenant (se tratará en hitos posteriores si aplica).

## 4) Riesgos iniciales y mitigaciones

- **Compatibilidad parcial de APIs entre proveedores**.
  - Mitigación: introducir/ajustar gateway nativo por proveedor cuando OpenAI-compatible no cubra contrato.
- **Deriva entre documentación y código**.
  - Mitigación: mantener generación/validación de docs y catálogo en CI.
- **Errores de configuración en despliegue**.
  - Mitigación: validación startup + errores runtime explícitos (`400`) + smoke dry-run.
- **Incremento de complejidad por 6 proveedores nuevos**.
  - Mitigación: integración incremental por hitos con criterios de salida estrictos.

## 5) Definición de hitos

### Hito 1 — Diseño técnico transversal (todos los proveedores)

**Entregables:**
- Matriz de decisión por proveedor: OpenAI-compatible vs gateway nativo.
- Definición de aliases, modelos por defecto y base URLs por defecto.
- Contrato de errores homogéneo por proveedor.

**Definition of Done:**
1. Documento técnico aprobado y sin ambigüedades.
2. Lista cerrada de variables por proveedor (`*_API_KEY`, `*_MODEL`, `*_BASE_URL`).
3. Criterios de prueba por capa definidos para los 6 proveedores.

### Hito 2 — Integración Xinghuo

**DoD mínimo:**
1. Runtime/startup config implementado.
2. Wiring en converter/API con pruebas.
3. Documentación y estado de backlog actualizados.

### Hito 3 — Integración Doubao

**DoD mínimo:**
1. Paridad técnica con Xinghuo.
2. Validaciones de configuración y errores de API cubiertos.
3. Smoke dry-run estable.

### Hito 4 — Integración Zhipu + MiniMax

**DoD mínimo:**
1. Ambos proveedores integrados con el mismo estándar de pruebas.
2. Cobertura de converter/API y validaciones startup/runtime.
3. Documentación operativa por proveedor completa.

### Hito 5 — Integración Pangu + Grok

**DoD mínimo:**
1. Ambos proveedores integrados y validados.
2. Evidencia de compatibilidad en smoke/tests.
3. Actualización de catálogo/docs/scripts de validación.

### Hito 6 — Cierre de iniciativa multi-proveedor

**DoD mínimo:**
1. Suite de pruebas relevante en verde.
2. Documentación consolidada (índices, catálogo, matriz).
3. Checklist de producción actualizado con riesgos y mitigaciones finales.

## 6) Orden de ejecución aprobado

1. Hito 1 (diseño transversal).
2. Hito 2 (Xinghuo).
3. Hito 3 (Doubao).
4. Hito 4 (Zhipu + MiniMax).
5. Hito 5 (Pangu + Grok).
6. Hito 6 (cierre y consolidación).

## 7) Criterio de cierre del Hito 0

Hito 0 se considera cerrado cuando:

1. El roadmap anterior queda documentado.
2. Existe DoD medible por hito.
3. Se identifican riesgos y mitigaciones.
4. Se acuerda explícitamente el inicio de Hito 1.
