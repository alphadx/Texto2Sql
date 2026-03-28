# TODO DEMO – Plan por hitos (análisis profundo)

> Objetivo: estabilizar y evolucionar el DEMO de Texto2SQL para que siga funcionando ante cambios de contrato API, nuevos proveedores/modelos LLM y variaciones de motores de BD.

## Resumen ejecutivo del análisis

### Hallazgos clave
- El demo web (`demo/app/public/*`) es un adaptador entre la UI y la API principal. Es el punto más sensible a cambios de contrato (nombres de campos, estructura de errores y metadatos).
- El backend FastAPI hoy responde oficialmente con `columns`/`rows` y maneja errores en `detail.error`, mientras que históricamente el demo trabajó con `columnas`/`filas`/`errores`.
- La configuración LLM creció (más proveedores y aliases), por lo que la UX del demo debe guiar mejor para evitar entradas inválidas y errores silenciosos.
- El smoke test del demo depende de Docker; en entornos sin Docker no hay validación E2E real de la capa visual + PHP + MySQL.

### Riesgos actuales
1. **Regresiones de contrato** si la API evoluciona y el demo no se actualiza en paralelo.
2. **Experiencia inconsistente** cuando la API no devuelve SQL explícito.
3. **Cobertura de prueba incompleta** para escenarios reales del demo (HTTP codes, errores auth, timeouts, proveedores).
4. **Deuda operativa**: falta una matriz de compatibilidad “Demo ↔ API” como referencia viva.

---

## Hito 0 — Línea base y contrato estable (Semana 1)

### Objetivo
Definir explícitamente qué contrato soporta el demo y cómo se valida.

### Tareas
- [x] Documentar contrato mínimo esperado de `/nl2sql/query` consumido por el demo. _(2026-03-28)_
- [x] Crear matriz de compatibilidad (campos legacy vs actuales) para respuestas exitosas y de error. _(2026-03-28)_
- [x] Registrar decisiones de fallback (ej. texto cuando no hay SQL en respuesta). _(2026-03-28)_

### Entregables
- [x] Sección nueva en `demo/README.md`: “Contrato de integración del Demo”. _(2026-03-28)_
- [x] Tabla de mapeo de campos (legacy/current) y ejemplos JSON. _(2026-03-28)_

### Criterio de aceptación
- [x] Cualquier cambio de contrato en API puede validarse contra una checklist concreta antes de merge. _(2026-03-28)_

---

## Hito 1 — Robustez funcional del adaptador PHP (Semana 1–2)

### Objetivo
Asegurar parsing resiliente y comportamiento predecible en éxito/error.

### Tareas
- [x] Estandarizar internamente una sola estructura canónica (`columnas`, `filas`, `error`, `sql_generado`). _(2026-03-28)_
- [x] Homologar extracción de errores incluyendo: _(2026-03-28)_
  - [x] `error`
  - [x] `errores`
  - [x] `detail.error`
  - [x] errores no JSON / body inválido
- [x] Diferenciar mensajes por tipo de falla (conectividad, auth, validación, ejecución SQL). _(2026-03-28)_
- [x] Mejorar trazabilidad en historial de chat (guardar HTTP status y timestamp de request externo). _(2026-03-28)_

### Entregables
- [x] Refactor incremental en `demo/app/public/chat.php` con funciones pequeñas y testeables. _(2026-03-28)_
- [x] Casos de prueba de parsing en script/fixture (si no hay framework PHP tests, al menos harness reproducible). _(2026-03-28)_

### Criterio de aceptación
- [x] En respuestas 2xx/4xx/5xx el demo siempre renderiza un estado claro (tabla o error explicativo) sin romper la sesión. _(2026-03-28, validado por harness y contrato canónico)_

---

## Hito 2 — UX de proveedores/modelos y motores (Semana 2)

### Objetivo
Alinear la UI del demo con capacidades reales del backend para reducir errores de operador.

### Tareas
- [x] Cambiar `llm_provider` a componente guiado (datalist/select) + ayuda contextual. _(2026-03-28)_
- [x] Añadir placeholders sugeridos por proveedor para `llm_model` y `llm_base_url`. _(2026-03-28)_
- [x] Validaciones de cliente para motores BD soportados y puertos sugeridos. _(2026-03-28)_
- [x] Indicador visual cuando cambiar parámetros rota sesión por `context_signature`. _(2026-03-28)_

### Entregables
- [x] Ajustes en `demo/app/public/index.php` (inputs, hints, validaciones ligeras). _(2026-03-28)_
- [x] Documentación de “cómo cambiar de proveedor/modelo sin perder contexto inesperadamente”. _(2026-03-28)_

### Criterio de aceptación
- [ ] Un usuario nuevo puede ejecutar una consulta end-to-end con configuración correcta en < 3 minutos.

---

## Hito 3 — Testing E2E del demo (Semana 2–3)

### Objetivo
Tener pruebas reproducibles del flujo real del demo, no solo del backend Python.

### Tareas
- [x] Extender `scripts/demo-smoke.sh` para validar también endpoint del chat PHP (`GET` y `POST`). _(2026-03-28)_
- [x] Agregar escenario con API mock/stub para testear UI adapter sin depender de llaves LLM reales. _(2026-03-28)_
- [x] Definir estrategia de ejecución en CI: _(2026-03-28)_
  - [x] job con Docker (full smoke)
  - [x] job sin Docker (checks mínimos + linters)

### Entregables
- [x] Smoke ampliado con aserciones HTTP y JSON schema básico. _(2026-03-28)_
- [x] Instrucciones claras para ejecutar localmente y en CI. _(2026-03-28)_

### Criterio de aceptación
- [ ] El PR falla automáticamente si el demo deja de renderizar filas/errores esperados.

---

## Hito 4 — Observabilidad y soporte operativo (Semana 3)

### Objetivo
Reducir tiempo de diagnóstico cuando el demo “falla” por causas externas.

### Tareas
- [x] Añadir correlation id por mensaje demo → API. _(2026-03-28)_
- [x] Registrar en logs del demo: endpoint llamado, status, latencia y tipo de error (sin exponer secretos). _(2026-03-28)_
- [x] Definir troubleshooting guide (top 10 errores frecuentes y resolución). _(2026-03-28)_

### Entregables
- [x] Logging estructurado mínimo en PHP. _(2026-03-28)_
- [x] Sección “Troubleshooting Demo” en `demo/README.md`. _(2026-03-28)_

### Criterio de aceptación
- [ ] Soporte puede clasificar la mayoría de incidentes en < 10 minutos usando logs.

---

## Hito 5 — Hardening de seguridad del demo (Semana 3–4)

### Objetivo
Evitar exposición accidental de secretos y reducir superficie de ataque del entorno demo.

### Tareas
- [x] Revisar manejo de secretos en UI (no persistir API keys en localStorage). _(2026-03-28)_
- [x] Revisar política CORS/headers/cookies según modo de despliegue. _(2026-03-28)_
- [x] Enmascarar y sanitizar campos sensibles en errores y logs. _(2026-03-28)_
- [x] Documentar límites de uso del demo (no productivo / fines de validación). _(2026-03-28)_

### Entregables
- [x] Checklist de seguridad del demo. _(2026-03-28)_
- [x] Ajustes mínimos de hardening en contenedor y app PHP. _(2026-03-28, headers + CORS configurable en app PHP)_

### Criterio de aceptación
- [ ] Ningún secreto queda persistido o logueado en texto plano por defecto.

---

## Hito 6 — Gobernanza de cambios y definición de terminado (Semana 4)

### Objetivo
Cerrar ciclo con proceso claro para futuros cambios de modelo/proveedor/API.

### Tareas
- [x] Plantilla de PR con sección obligatoria “Impacto en DEMO”. _(2026-03-28)_
- [x] Checklist de release para cambios en contrato API o providers. _(2026-03-28)_
- [x] Owner técnico del demo y cadencia de revisión. _(2026-03-28)_

### Entregables
- [x] `docs/` con proceso liviano de change management. _(2026-03-28)_
- [x] Definición de Done para “Demo Compatible”. _(2026-03-28)_

### Criterio de aceptación
- [x] Cada release puede declararse compatible/incompatible con evidencia de tests + checklist. _(2026-03-28, vía template PR + workflow de smoke)_

---

## Backlog priorizado (rápido)

### Prioridad P0
- [x] Matriz de contrato Demo↔API y documentación mínima. _(cerrado 2026-03-28)_
- [x] Smoke E2E que valide `chat.php` (GET/POST) además de MySQL sakila. _(cerrado 2026-03-28)_

### Prioridad P1
- [x] UX guiada por proveedor/modelo y mensajes de error por categoría. _(cerrado 2026-03-28)_
- [x] Logging mínimo con latencia/status sin secretos. _(cerrado 2026-03-28)_

### Prioridad P2
- [x] Hardening adicional y gobernanza de cambios. _(cerrado 2026-03-28)_

---

## Métricas de avance sugeridas
- **Compatibilidad**: % de escenarios de contrato cubiertos por smoke.
- **Calidad**: tasa de regresiones demo por release.
- **Operación**: MTTR de incidentes del demo.
- **UX**: tiempo medio a “primera consulta exitosa”.

---

## Nota de trabajo colaborativo
Iremos marcando checkboxes por hito y registrando fecha + PR asociado en cada cierre parcial.

### Estado global (2026-03-28)
- Hitos 0, 1, 2, 3, 4, 5 y 6 implementados.
- Smokes Docker y no-Docker disponibles para validación continua.
- Gobernanza de cambios activa con template PR + checklist de compatibilidad.
- Criterios de aceptación operativos (tiempo de onboarding, MTTR y validación sostenida en releases) quedan en seguimiento.
