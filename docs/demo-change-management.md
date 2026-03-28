# Demo Change Management

## Objetivo
Definir un proceso liviano para declarar si un release es **Demo Compatible**.

## Owner y cadencia
- **Owner técnico del demo:** equipo Backend/API (rotación semanal del responsable de guardia).
- **Cadencia de revisión:**
  - En cada PR que toque `demo/*` o contrato `/nl2sql/query`.
  - Revisión semanal de salud del demo (smokes + issues abiertas).

## Checklist de release (cambios API/providers)

1. Contrato demo↔API revisado:
   - `columns/rows/sql/texto_formal` (actual)
   - `columnas/filas/sql_generado` (legacy)
   - fallback sin texto formal y/o sin SQL
2. Errores 2xx/4xx/5xx muestran estado usable en chat.
3. `correlation_id` y logging estructurado siguen presentes.
4. `make demo-smoke-nodocker` pasa en CI.
5. `make demo-smoke` pasa en CI (job con Docker).
6. README del demo actualizado si cambió UX o configuración.

## Definición de Done: "Demo Compatible"

Un cambio puede declararse **Demo Compatible** cuando:

- ✅ No rompe el contrato esperado por `demo/app/public/chat.php`.
- ✅ Mantiene render estable de tabla o error legible.
- ✅ Pasa smoke no-docker + smoke docker (o deja evidencia de limitación de entorno).
- ✅ Incluye sección “Impacto en DEMO” en el PR.
- ✅ Incluye evidencia de comandos ejecutados y resultados.

## Evidencia mínima en PR

- Link al workflow `demo-smoke`.
- Salida de:
  - `make demo-smoke-nodocker`
  - `make demo-smoke` (si aplica)
- Checklist “Impacto en DEMO” completada.
