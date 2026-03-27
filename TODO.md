# TODO – Correcciones pendientes para sesión Redis

Este documento resume el análisis de los ajustes que faltan tras el PR **"Add configurable Redis session backend with TTL and session deletion support"**.

> Nota: como en este contexto no se adjuntaron los comentarios inline exactos del diff, este plan consolida los puntos que normalmente se observan como bloqueantes en revisión para este cambio y que debemos confirmar uno a uno.

## 1) Compatibilidad y contrato público

- [ ] Verificar compatibilidad hacia atrás del símbolo `SessionManager`:
  - Si el código externo espera instanciar `SessionManager()`, definir alias/fábrica explícita o adaptar imports.
  - Documentar claramente cuál clase concreta usar en tests y runtime.
- [ ] Revisar tipado en `converter.py` / `api.py` para que dependa de la interfaz y no de una implementación concreta.

## 2) Robustez de `RedisSessionManager`

- [ ] Validar configuración al inicio:
  - [x] `SESSION_TTL_SECONDS` debe ser entero positivo.
  - [x] Backend desconocido en `SESSION_MANAGER_BACKEND` debe generar warning claro o fallback explícito documentado.
- [ ] Manejar payload JSON corrupto en Redis (`json.loads`) sin romper el flujo:
  - [x] Registrar warning.
  - [x] Retornar historial vacío y/o limpiar clave inválida según decisión.
- [ ] Confirmar política de expiración:
  - [x] Definir si el TTL es “absolute” (solo en `set`) o “sliding” (renovar también al `get`).
  - [x] Implementar comportamiento elegido de forma explícita y documentada.

## 3) Operación de borrado `/session/{id}`

- [ ] Confirmar borrado completo por `session_id` para ambos agentes (`refiner`, `sql_agent`).
- [ ] Revisar semántica de respuesta 404/200 cuando la sesión expiró por TTL justo antes del delete.
- [ ] Añadir/ajustar pruebas para condiciones de carrera básicas (borrado + escrituras concurrentes).

## 4) Pruebas automatizadas

- [ ] Asegurar ejecución de test suite en entorno con dependencias instaladas (`fastapi`, etc.).
- [ ] Agregar pruebas unitarias adicionales:
  - [x] agente inválido -> error esperado.
  - [x] TTL inválido en env -> fallback/error controlado.
  - [x] backend inválido -> comportamiento esperado.
  - [x] payload JSON inválido en Redis.
- [ ] Agregar prueba de integración mínima del endpoint `DELETE /session/{id}` con backend Redis simulado.

## 5) Documentación y operación

- [ ] Extender `README.md` con ejemplos completos de configuración:
  - modo memoria
  - modo Redis
  - TTL y prefijos recomendados por ambiente (dev/staging/prod)
- [ ] Documentar formato exacto de claves Redis y consideraciones de limpieza/observabilidad.

## 6) Criterios de aceptación para cerrar corrección

- [ ] Todas las pruebas (`pytest`) en verde en entorno estándar del proyecto.
- [ ] Sin regresiones en flujo actual de `nl2sql/query`.
- [ ] Confirmación explícita de que el borrado por `/session/{id}` funciona igual en memoria y Redis.
- [ ] Documentación actualizada y consistente con comportamiento real.
