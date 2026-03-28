# TODO técnico

- [ ] Definir prioridad (`P0/P1/P2`), responsable y fecha objetivo para cada pendiente; hoy no hay orden operativo y dificulta el cierre.
- [ ] Endurecer el parser SQL para cubrir casos complejos (dollar-quoted strings de PostgreSQL, identificadores entrecomillados exóticos y comentarios anidados) sin depender solo de regex.
- [ ] Mejorar la inserción de límite para SQL Server cuando la consulta empieza con CTE (`WITH ...`) sin `TOP` explícito; hoy el path más robusto aún requiere una estrategia específica por forma de consulta.
- [ ] Añadir tests de integración por motor (Postgres/MySQL/SQL Server) para verificar que la configuración de timeout se aplica y se limpia correctamente al reutilizar conexiones de pool.
- [ ] Añadir pruebas negativas de seguridad (exfiltración por prompt injection, funciones SQL peligrosas y bypass de políticas `SELECT-only`) para cubrir lo definido en el plan.
- [ ] Registrar una tarea explícita de observabilidad (métricas p95/p99, error-rate por motor y coste/tokens LLM) con criterios de aceptación medibles.
- [ ] Registrar una tarea explícita de hardening de despliegue (headers de seguridad Nginx, límites de body, rotación de secretos y healthchecks en CI).
- [ ] Añadir revisión legal/privacidad periódica como tarea recurrente (alineada con Ley 21.719 y retención/borrado de logs).

- [x] Instalación principal: definir proveedor/API key/modelo vía `make install-main-config`.
- [x] API principal: aceptar override de proveedor/modelo/api_key/base_url por request.
- [x] CI demo: agregar smoke test para build + validación de carga `sakila.film`.
