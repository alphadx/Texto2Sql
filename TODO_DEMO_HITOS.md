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
- [ ] Documentar contrato mínimo esperado de `/nl2sql/query` consumido por el demo.
- [ ] Crear matriz de compatibilidad (campos legacy vs actuales) para respuestas exitosas y de error.
- [ ] Registrar decisiones de fallback (ej. texto cuando no hay SQL en respuesta).

### Entregables
- [ ] Sección nueva en `demo/README.md`: “Contrato de integración del Demo”.
- [ ] Tabla de mapeo de campos (legacy/current) y ejemplos JSON.

### Criterio de aceptación
- [ ] Cualquier cambio de contrato en API puede validarse contra una checklist concreta antes de merge.

---

## Hito 1 — Robustez funcional del adaptador PHP (Semana 1–2)

### Objetivo
Asegurar parsing resiliente y comportamiento predecible en éxito/error.

### Tareas
- [ ] Estandarizar internamente una sola estructura canónica (`columnas`, `filas`, `error`, `sql_generado`).
- [ ] Homologar extracción de errores incluyendo:
  - [ ] `error`
  - [ ] `errores`
  - [ ] `detail.error`
  - [ ] errores no JSON / body inválido
- [ ] Diferenciar mensajes por tipo de falla (conectividad, auth, validación, ejecución SQL).
- [ ] Mejorar trazabilidad en historial de chat (guardar HTTP status y timestamp de request externo).

### Entregables
- [ ] Refactor incremental en `demo/app/public/chat.php` con funciones pequeñas y testeables.
- [ ] Casos de prueba de parsing en script/fixture (si no hay framework PHP tests, al menos harness reproducible).

### Criterio de aceptación
- [ ] En respuestas 2xx/4xx/5xx el demo siempre renderiza un estado claro (tabla o error explicativo) sin romper la sesión.

---

## Hito 2 — UX de proveedores/modelos y motores (Semana 2)

### Objetivo
Alinear la UI del demo con capacidades reales del backend para reducir errores de operador.

### Tareas
- [ ] Cambiar `llm_provider` a componente guiado (datalist/select) + ayuda contextual.
- [ ] Añadir placeholders sugeridos por proveedor para `llm_model` y `llm_base_url`.
- [ ] Validaciones de cliente para motores BD soportados y puertos sugeridos.
- [ ] Indicador visual cuando cambiar parámetros rota sesión por `context_signature`.

### Entregables
- [ ] Ajustes en `demo/app/public/index.php` (inputs, hints, validaciones ligeras).
- [ ] Documentación de “cómo cambiar de proveedor/modelo sin perder contexto inesperadamente”.

### Criterio de aceptación
- [ ] Un usuario nuevo puede ejecutar una consulta end-to-end con configuración correcta en < 3 minutos.

---

## Hito 3 — Testing E2E del demo (Semana 2–3)

### Objetivo
Tener pruebas reproducibles del flujo real del demo, no solo del backend Python.

### Tareas
- [ ] Extender `scripts/demo-smoke.sh` para validar también endpoint del chat PHP (`GET` y `POST`).
- [ ] Agregar escenario con API mock/stub para testear UI adapter sin depender de llaves LLM reales.
- [ ] Definir estrategia de ejecución en CI:
  - [ ] job con Docker (full smoke)
  - [ ] job sin Docker (checks mínimos + linters)

### Entregables
- [ ] Smoke ampliado con aserciones HTTP y JSON schema básico.
- [ ] Instrucciones claras para ejecutar localmente y en CI.

### Criterio de aceptación
- [ ] El PR falla automáticamente si el demo deja de renderizar filas/errores esperados.

---

## Hito 4 — Observabilidad y soporte operativo (Semana 3)

### Objetivo
Reducir tiempo de diagnóstico cuando el demo “falla” por causas externas.

### Tareas
- [ ] Añadir correlation id por mensaje demo → API.
- [ ] Registrar en logs del demo: endpoint llamado, status, latencia y tipo de error (sin exponer secretos).
- [ ] Definir troubleshooting guide (top 10 errores frecuentes y resolución).

### Entregables
- [ ] Logging estructurado mínimo en PHP.
- [ ] Sección “Troubleshooting Demo” en `demo/README.md`.

### Criterio de aceptación
- [ ] Soporte puede clasificar la mayoría de incidentes en < 10 minutos usando logs.

---

## Hito 5 — Hardening de seguridad del demo (Semana 3–4)

### Objetivo
Evitar exposición accidental de secretos y reducir superficie de ataque del entorno demo.

### Tareas
- [ ] Revisar manejo de secretos en UI (no persistir API keys en localStorage).
- [ ] Revisar política CORS/headers/cookies según modo de despliegue.
- [ ] Enmascarar y sanitizar campos sensibles en errores y logs.
- [ ] Documentar límites de uso del demo (no productivo / fines de validación).

### Entregables
- [ ] Checklist de seguridad del demo.
- [ ] Ajustes mínimos de hardening en contenedor y app PHP.

### Criterio de aceptación
- [ ] Ningún secreto queda persistido o logueado en texto plano por defecto.

---

## Hito 6 — Gobernanza de cambios y definición de terminado (Semana 4)

### Objetivo
Cerrar ciclo con proceso claro para futuros cambios de modelo/proveedor/API.

### Tareas
- [ ] Plantilla de PR con sección obligatoria “Impacto en DEMO”.
- [ ] Checklist de release para cambios en contrato API o providers.
- [ ] Owner técnico del demo y cadencia de revisión.

### Entregables
- [ ] `docs/` con proceso liviano de change management.
- [ ] Definición de Done para “Demo Compatible”.

### Criterio de aceptación
- [ ] Cada release puede declararse compatible/incompatible con evidencia de tests + checklist.

---

## Backlog priorizado (rápido)

### Prioridad P0
- [ ] Matriz de contrato Demo↔API y documentación mínima.
- [ ] Smoke E2E que valide `chat.php` (GET/POST) además de MySQL sakila.

### Prioridad P1
- [ ] UX guiada por proveedor/modelo y mensajes de error por categoría.
- [ ] Logging mínimo con latencia/status sin secretos.

### Prioridad P2
- [ ] Hardening adicional y gobernanza de cambios.

---

## Métricas de avance sugeridas
- **Compatibilidad**: % de escenarios de contrato cubiertos por smoke.
- **Calidad**: tasa de regresiones demo por release.
- **Operación**: MTTR de incidentes del demo.
- **UX**: tiempo medio a “primera consulta exitosa”.

---

## Nota de trabajo colaborativo
Iremos marcando checkboxes por hito y registrando fecha + PR asociado en cada cierre parcial.
