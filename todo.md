# TODOs pendientes tras la migración a FastAPI

- [ ] Evaluar y decidir compatibilidad retroactiva para `POST /query` (alias de `POST /nl2sql/query`) para evitar ruptura de clientes existentes.
- [ ] Normalizar formato de errores (`{"error": ...}`) en FastAPI para evitar depender de `detail` en clientes actuales.
- [ ] Exigir/validar `host` cuando `motor_bd` no sea `sqlite` y documentar claramente la excepción de SQLite.
- [ ] Actualizar `README.md` con ejemplos de request/response para `/nl2sql/query`, `/health` y `/session/{session_id}`.
- [ ] Añadir pruebas de contrato OpenAPI (schema de request/response y códigos HTTP esperados).
- [ ] Revisar warnings de tests (`httpx` deprecación por uso de `data=`) y migrar a `content=`.
- [ ] Agregar comando de arranque ASGI recomendado en documentación (`gunicorn -k uvicorn.workers.UvicornWorker` / `uvicorn`).
