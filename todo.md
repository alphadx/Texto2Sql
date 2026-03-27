# TODO técnico

- [ ] Endurecer el parser SQL para cubrir casos complejos (dollar-quoted strings de PostgreSQL, identificadores entrecomillados exóticos y comentarios anidados) sin depender solo de regex.
- [ ] Mejorar la inserción de límite para SQL Server cuando la consulta empieza con CTE (`WITH ...`) sin `TOP` explícito; hoy el path más robusto aún requiere una estrategia específica por forma de consulta.
- [ ] Añadir tests de integración por motor (Postgres/MySQL/SQL Server) para verificar que la configuración de timeout se aplica y se limpia correctamente al reutilizar conexiones de pool.

- [x] Instalación principal: definir proveedor/API key/modelo vía `make install-main-config`.
- [x] API principal: aceptar override de proveedor/modelo/api_key/base_url por request.
- [x] CI demo: agregar smoke test para build + validación de carga `sakila.film`.
