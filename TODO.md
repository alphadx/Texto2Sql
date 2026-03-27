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

- [x] Confirmar borrado completo por `session_id` para ambos agentes (`refiner`, `sql_agent`).
- [x] Revisar semántica de respuesta 404/200 cuando la sesión expiró por TTL justo antes del delete.
- [x] Añadir/ajustar pruebas para condiciones de carrera básicas (borrado + escrituras concurrentes).

## 4) Pruebas automatizadas

- [x] Asegurar ejecución de test suite en entorno con dependencias instaladas (`fastapi`, etc.).
- [x] Agregar pruebas unitarias adicionales:
  - [x] agente inválido -> error esperado.
  - [x] TTL inválido en env -> fallback/error controlado.
  - [x] backend inválido -> comportamiento esperado.
  - [x] payload JSON inválido en Redis.
- [x] Agregar prueba de integración mínima del endpoint `DELETE /session/{id}` con backend Redis simulado.

## 5) Documentación y operación

- [x] Extender `README.md` con ejemplos completos de configuración:
  - [x] modo memoria
  - [x] modo Redis
  - [x] TTL y prefijos recomendados por ambiente (dev/staging/prod)
- [x] Documentar formato exacto de claves Redis y consideraciones de limpieza/observabilidad.

## 6) Criterios de aceptación para cerrar corrección

- [x] Todas las pruebas (`pytest`) en verde en entorno estándar del proyecto.
- [x] Sin regresiones en flujo actual de `nl2sql/query`.
- [x] Confirmación explícita de que el borrado por `/session/{id}` funciona igual en memoria y Redis.
- [x] Documentación actualizada y consistente con comportamiento real.

## TODO demo Docker NL2SQL

- [ ] Definir la compañía/proveedor API oficial para testing del demo.
- [ ] Definir API key definitiva para ambiente de prueba.
- [ ] Definir modelo LLM oficial para el test.
- [x] El script de instalación del demo (`demo/install-demo.sh`) solicita esos datos al usuario.
