# Plan de hitos — Exponer texto formal de `_REFINER_SYSTEM` en app y demo

## Objetivo funcional
Además de la salida SQL, la API y el demo deben mostrar también la salida formal generada por el agente **refiner** (prompt `_REFINER_SYSTEM`).

## Alcance
- **Backend app (`app/`)**: incluir el texto formal en el contrato de respuesta del endpoint `/nl2sql/query`.
- **Demo (`demo/`)**: consumir y desplegar el texto formal junto al SQL en la conversación y estructura de historial.
- **Pruebas**: ajustar/agregar validaciones de contrato y compatibilidad.
- **Documentación**: actualizar referencia de campos de respuesta (si aplica).

## Hitos de avance

### Hito 1 — Descubrimiento y diseño del cambio (**completado**)
**Entregables cerrados:**
1. Punto backend identificado: en `app/api.py`, el endpoint ya obtiene `refined = refine_query(...)` antes de `generate_sql(...)`.
2. Contrato propuesto: agregar campo `texto_formal: str | None` en la respuesta (sin romper `sql`).
3. Impacto demo identificado:
   - `demo/app/public/chat_adapter.php`: normalizar campo `texto_formal`.
   - `demo/app/public/chat.php`: imprimir texto formal + SQL y persistir en `history[].result`.
4. Compatibilidad: si `texto_formal` no viene, mantener fallback actual (solo SQL / mensaje de no disponible).

**Criterio de aceptación:**
- ✅ Decisión de contrato cerrada y trazable antes de tocar código.

---

### Hito 2 — Implementación en backend API (**completado**)
**Entregables:**
1. Extender `NL2SQLQueryResponse` para incluir el texto formal.
2. Persistir el valor refinado y retornarlo en `result` del endpoint.
3. (Opcional recomendado) incluirlo en auditoría si aporta trazabilidad.

**Criterio de aceptación:**
- ✅ `POST /nl2sql/query` devuelve SQL + texto formal en un mismo response exitoso.

---

### Hito 3 — Implementación en demo (**completado**)
**Entregables:**
1. Normalizar el nuevo campo en `chat_adapter.php`.
2. Mostrarlo en el texto de respuesta del asistente (`chat.php`) junto al SQL.
3. Guardarlo en `history[].result` para trazabilidad de sesión.

**Criterio de aceptación:**
- ✅ El demo imprime ambos bloques: texto formal y SQL, sin romper fallback de errores.

---

### Hito 4 — Pruebas, verificación y documentación (**completado**)
**Entregables:**
1. Ejecutar tests automáticos relevantes.
2. Ajustar tests de contrato donde aplique.
3. Actualizar README/docs del demo y/o API con el nuevo campo.

**Criterio de aceptación:**
- ✅ Pruebas relevantes en verde y documentación alineada al comportamiento real.

---

### Hito 5 — Cierre técnico (**completado**)
**Entregables:**
1. Revisión final de diff.
2. Commit atómico con mensaje claro.
3. PR con resumen de cambios, riesgos y validación.

**Criterio de aceptación:**
- ✅ Cambios listos para revisión e integración.

## Protocolo de avance
Tal como pediste, avanzaremos **hito por hito** y antes de ejecutar cada uno te pediré confirmación explícita con la palabra:

**`avanza`**

Estado actual: **Plan ejecutado completo (Hitos 1–5).**

## Revisión final de cumplimiento

Fecha de revisión: **2026-03-28**

- ✅ **Hito 1 (Descubrimiento/diseño):** contrato y puntos de integración definidos.
- ✅ **Hito 2 (Backend):** API retorna `texto_formal` junto con `sql`.
- ✅ **Hito 3 (Demo):** adapter y chat muestran/persisten `texto_formal`.
- ✅ **Hito 4 (Pruebas/docs):** tests en verde y documentación actualizada.
- ✅ **Hito 5 (Cierre técnico):** commits, validaciones y cierre realizados.

Resultado: **sin brechas detectadas** contra los criterios de aceptación del plan, por lo que **no se agregan pendientes a `todo.md`**.
