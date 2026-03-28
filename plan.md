# Plan Técnico Detallado para un Servicio Web Python de Conversión de Lenguaje Natural a SQL con LLM, Gunicorn y Nginx

---

## Introducción

La demanda de interfaces que permitan a usuarios no técnicos consultar bases de datos mediante lenguaje natural ha crecido exponencialmente en los últimos años. Los grandes modelos de lenguaje (LLM) han revolucionado la capacidad de traducir instrucciones en lenguaje natural a consultas SQL precisas, democratizando el acceso a la información y potenciando la inteligencia de negocio. Sin embargo, implementar un servicio web robusto, seguro y eficiente que realice esta conversión y ejecute las consultas en múltiples motores de base de datos implica desafíos técnicos significativos.

Este plan técnico detalla, paso a paso, cómo diseñar, desarrollar, desplegar y asegurar un servicio web en Python que reciba consultas en lenguaje natural, las traduzca a SQL usando un LLM, ejecute la consulta en el motor de base de datos especificado y devuelva los resultados en formato JSON estructurado. Se abordan todos los aspectos críticos: arquitectura, diseño de API, seguridad, manejo de sesiones, integración con LLM, ejecución segura de SQL, conectividad multi-motor, despliegue en producción y cumplimiento normativo en Chile.

---

## 1. Arquitectura General del Sistema

### 1.1. Diagrama de Flujo de Datos

El flujo principal del sistema es el siguiente:

1. **Recepción de la solicitud**: El usuario envía una consulta en lenguaje natural junto con los parámetros de conexión y configuración.
2. **Extracción del esquema**: El sistema se conecta al motor de base de datos y extrae únicamente los metadatos del esquema (tablas, columnas, tipos).
3. **Generación de SQL**: El LLM recibe la consulta en lenguaje natural y el esquema, y genera la consulta SQL.
4. **Validación y análisis de SQL**: Se valida la sintaxis, seguridad y compatibilidad del SQL generado.
5. **Ejecución segura**: Se ejecuta la consulta en modo solo lectura, con límites de tiempo y recursos.
6. **Serialización de resultados**: Los resultados se devuelven en JSON, incluyendo nombres de columnas, tipos y filas.
7. **Auditoría y logging**: Se registra la consulta original, el SQL generado y los metadatos de ejecución para trazabilidad.

### 1.2. Componentes Principales

| Componente                | Descripción                                                                                  |
|---------------------------|---------------------------------------------------------------------------------------------|
| API RESTful (FastAPI)     | Punto de entrada para solicitudes HTTP, validación y documentación automática.              |
| Gunicorn                  | Servidor WSGI/ASGI para manejo eficiente de procesos y concurrencia.                        |
| Nginx                     | Reverse proxy, terminación TLS, balanceo de carga y rate limiting.                         |
| Módulo de integración LLM | Encapsula la interacción con el modelo de lenguaje (OpenAI, Azure, Ollama, local, etc.).   |
| Módulo de extracción de esquema | Obtiene metadatos de la base de datos sin acceder a datos reales.                 |
| Módulo de ejecución SQL   | Ejecuta consultas de forma segura, parametrizada y controlada.                             |
| Módulo de seguridad       | Autenticación, autorización, gestión de secretos, cifrado y RBAC.                          |
| Módulo de sesiones        | Maneja session_id, almacenamiento y expiración de sesiones.                                |
| Auditoría y logging       | Registro estructurado de eventos, consultas y errores.                                     |
| Observabilidad            | Métricas, monitoreo y alertas (Prometheus, Grafana, logs estructurados).                   |

**Análisis:** Esta arquitectura desacopla claramente las responsabilidades, permitiendo escalabilidad, mantenibilidad y seguridad. El uso de FastAPI facilita la validación de datos y la documentación OpenAPI, mientras que Gunicorn y Nginx aseguran robustez y rendimiento en producción.

---

## 2. Selección de Framework y Stack Python

### 2.1. FastAPI vs Flask

| Característica                  | FastAPI                                   | Flask                                   |
|----------------------------------|-------------------------------------------|-----------------------------------------|
| Soporte ASGI/WSGI                | ASGI nativo (Uvicorn, Hypercorn)          | WSGI (Gunicorn), ASGI vía extensiones   |
| Validación de datos              | Automática (Pydantic)                     | Manual                                  |
| Documentación automática         | Sí (Swagger, ReDoc)                       | No (requiere extensiones)               |
| Soporte async                    | Nativo                                    | Limitado                                |
| Rendimiento                      | Alto (~2-3x más rápido en APIs JSON)      | Bueno                                   |
| Curva de aprendizaje             | Moderada                                  | Baja                                    |
| Ecosistema                       | Creciendo                                 | Maduro                                  |

**Recomendación:** Para este proyecto, **FastAPI** es la opción preferida por su rendimiento, validación automática, soporte asíncrono y generación de documentación OpenAPI. Esto es especialmente relevante para servicios que requieren alta concurrencia y facilidad de integración con herramientas modernas.

### 2.2. Stack Tecnológico

- **Python 3.10+**
- **FastAPI** como framework principal
- **Gunicorn** como servidor de aplicaciones (con worker tipo `uvicorn.workers.UvicornWorker` para ASGI)
- **Nginx** como reverse proxy y terminador TLS
- **Docker** para contenerización y despliegue
- **SQLAlchemy** para abstracción de conectores de base de datos
- **Redis** para almacenamiento de sesiones y caching (opcional)
- **Prometheus/Grafana** para métricas y monitoreo

---

## 3. Diseño de la API RESTful y Especificación OpenAPI

### 3.1. Especificación de Endpoints

#### Endpoint principal: `/nl2sql/query`

- **Método:** POST
- **Descripción:** Convierte una consulta en lenguaje natural a SQL, la ejecuta y devuelve los resultados.
- **Cuerpo de la solicitud (JSON):**
  - `host`: string (opcional si es SQLite)
  - `usuario`: string
  - `contraseña`: string
  - `puerto`: int (opcional)
  - `nombre_bd`: string
  - `motor_bd`: enum [mysql, sqlsrv, mariadb, sybase, postgres, sqlite]
  - `consulta_nl`: string
  - `session_id`: string (opcional)
- **Respuesta (JSON):**
  - `columnas`: lista de objetos `{nombre: string, tipo: string}`
  - `filas`: lista de listas (valores)
  - `tipos`: lista de strings
  - `sql_generado`: string
  - `metadatos`: `{tiempo_ejecucion, session_id, ...}`
  - `errores`: string (si aplica)

#### Endpoint de autenticación: `/auth/login` (si se requiere autenticación propia)

- **Método:** POST
- **Cuerpo:** `{usuario, contraseña}`
- **Respuesta:** `{access_token, refresh_token, expires_in}`

#### Endpoint de auditoría: `/audit/logs` (acceso restringido)

- **Método:** GET
- **Parámetros:** filtros por usuario, fecha, session_id, etc.

### 3.2. Ejemplo de Esquema OpenAPI (YAML simplificado)

```yaml
paths:
  /nl2sql/query:
    post:
      summary: Ejecuta una consulta NL→SQL
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/NL2SQLRequest'
      responses:
        '200':
          description: Respuesta exitosa
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/NL2SQLResponse'
components:
  schemas:
    NL2SQLRequest:
      type: object
      properties:
        host: {type: string}
        usuario: {type: string}
        contraseña: {type: string}
        puerto: {type: integer}
        nombre_bd: {type: string}
        motor_bd: {type: string, enum: [mysql, sqlsrv, mariadb, sybase, postgres, sqlite]}
        consulta_nl: {type: string}
        session_id: {type: string}
      required: [usuario, contraseña, nombre_bd, motor_bd, consulta_nl]
    NL2SQLResponse:
      type: object
      properties:
        columnas: {type: array, items: {type: object, properties: {nombre: string, tipo: string}}}
        filas: {type: array, items: {type: array, items: {type: string}}}
        tipos: {type: array, items: {type: string}}
        sql_generado: {type: string}
        metadatos: {type: object}
        errores: {type: string}
```

**Análisis:** La definición OpenAPI permite la generación automática de documentación interactiva y clientes SDK, facilitando la integración y el mantenimiento.

---

## 4. Integración con LLM y Prompt Engineering

### 4.1. Selección de Proveedor y Modelo LLM

| Proveedor/Modelo      | Ventajas                                             | Desventajas                                  |
|-----------------------|------------------------------------------------------|----------------------------------------------|
| OpenAI (GPT-4, GPT-3.5)| Precisión, soporte multilenguaje, API robusta       | Coste, datos fuera de jurisdicción           |
| Azure OpenAI          | Integración empresarial, cumplimiento, latencia baja | Coste, dependencia de Azure                  |
| Ollama (local, Llama 3, Mistral, CodeLlama) | Privacidad, sin salida de datos, coste bajo | Requiere infraestructura, tuning necesario   |
| HuggingFace (Llama, Mistral, CodeLlama, etc.) | Flexibilidad, modelos open source           | Requiere tuning, recursos de hardware        |
| somosnlp/LLM_SQL_BaseDatosEspanol_Mistral | Fine-tuning en español, open source         | Comunidad pequeña, tuning adicional          |

**Recomendación:** Para entornos empresariales y cumplimiento estricto, se recomienda un modelo local (Ollama, HuggingFace) o Azure OpenAI. Para prototipado rápido, OpenAI es adecuado. Modelos como CodeLlama y Mistral han demostrado alta precisión en generación de SQL, especialmente tras fine-tuning.

### 4.2. Prompt Engineering

- **Incluir el esquema de la base de datos**: El prompt debe contener la estructura de tablas y columnas, sin datos reales.
- **Ejemplo de prompt**:
  ```
  ### Tarea
  Genera una consulta SQL para responder la siguiente pregunta:
  "{consulta_nl}"
  ### Esquema de la base de datos
  {esquema_formateado}
  ### SQL
  ```
- **Técnicas avanzadas**:
  - Few-shot prompting: incluir ejemplos de NL→SQL.
  - Chain-of-thought: pedir al modelo que explique los pasos antes de generar el SQL.
  - RAG (Retrieval Augmented Generation): recuperar ejemplos similares y contexto relevante.

**Análisis:** Un prompt bien diseñado, que incluya el esquema y ejemplos, mejora significativamente la precisión y seguridad de la consulta generada. Es fundamental evitar que el LLM tenga acceso a datos reales, limitando su contexto solo al esquema.

### 4.3. Integración Técnica

- **Librerías recomendadas**: `langchain`, `llama-index`, `openai`, `transformers`, `ollama`.
- **Gestión de claves API**: Usar variables de entorno o gestores de secretos (Vault, AWS Secrets Manager).
- **Timeouts y control de coste**: Limitar el tiempo y tokens de respuesta del LLM, implementar caching de respuestas con Redis para reducir latencia y coste.

---

## 5. Extracción y Manejo del Esquema de la Base de Datos

### 5.1. Obtención de Metadatos

- **Solo metadatos**: El sistema debe conectarse a la base de datos y extraer únicamente la estructura (tablas, columnas, tipos, relaciones), nunca datos reales.
- **Consultas estándar**:
  - **PostgreSQL**: `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';` y `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'mi_tabla';`.
  - **MySQL/MariaDB**: `SHOW TABLES;` y `DESCRIBE mi_tabla;`
  - **SQL Server**: `SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES;` y `SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'mi_tabla';`
  - **SQLite**: `PRAGMA table_info('mi_tabla');`
  - **Sybase**: Consultas similares a SQL Server.

### 5.2. Formateo del Esquema para el LLM

- **Estandarizar el formato**: Presentar el esquema en formato legible y consistente para el LLM.
- **Ejemplo**:
  ```
  CREATE TABLE empleados (
    id INT PRIMARY KEY,
    nombre VARCHAR(100),
    salario DECIMAL(10,2),
    departamento_id INT
  );
  ```

### 5.3. Seguridad y Privacidad

- **No exponer nombres sensibles**: Considerar aliasing de tablas/columnas si el esquema contiene información confidencial.
- **Acceso de solo lectura**: El usuario que conecta debe tener permisos mínimos necesarios para extraer metadatos.

---

## 6. Generación y Validación Segura de SQL

### 6.1. Validación Sintáctica y Semántica

- **Uso de parsers SQL**: Utilizar librerías como `sqlglot` para analizar el AST de la consulta generada, detectar errores y asegurar compatibilidad entre dialectos.
- **Whitelist/Blacklist**: Permitir solo sentencias `SELECT` y prohibir `INSERT`, `UPDATE`, `DELETE`, `DROP`, etc.
- **Límites de recursos**: Limitar el número de filas (`LIMIT`), tiempo de ejecución y profundidad de joins/subconsultas.

### 6.2. Ejecución Segura

- **Modo solo lectura**: Configurar la transacción como `READ ONLY` en motores que lo soporten (`SET TRANSACTION READ ONLY` en PostgreSQL, `ALTER DATABASE ... SET READ_ONLY` en SQL Server).
- **Prepared statements**: Ejecutar consultas parametrizadas para evitar inyección SQL, aunque el LLM genere el SQL completo.
- **Sandboxing**: Ejecutar las consultas en un entorno controlado, con usuarios de base de datos de privilegios mínimos.

### 6.3. Compatibilidad Multi-motor

- **Transpilación de dialectos**: Usar `sqlglot` para convertir el SQL generado al dialecto específico del motor de base de datos si es necesario.
- **Drivers soportados**:
  - PostgreSQL: `psycopg2` (sincrónico), `asyncpg` (asíncrono).
  - MySQL/MariaDB: `mysql-connector-python`, `PyMySQL`.
  - SQL Server: `pyodbc`.
  - Sybase: `pyodbc` o drivers específicos.
  - SQLite: `sqlite3` (incluido en Python).

---

## 7. Manejo de Parámetros y Prevención de Inyección SQL

### 7.1. Parámetros de Conexión

- **Validación estricta**: Validar y sanear todos los parámetros recibidos (host, usuario, nombre de base de datos, etc.).
- **Gestión de secretos**: Nunca almacenar contraseñas en texto plano; usar gestores de secretos y variables de entorno.

### 7.2. Parámetros en Consultas

- **Prepared statements**: Siempre que sea posible, ejecutar consultas con parámetros en vez de interpolar valores directamente.
- **Restricción de nombres de tablas/columnas**: No permitir que el usuario especifique nombres arbitrarios; validar contra el esquema extraído.

---

## 8. Mapeo de Tipos y Serialización de Resultados a JSON

### 8.1. Estructura de la Respuesta

- **Nombres de columnas**: Extraídos del cursor `.description` (DB API 2.0).
- **Tipos de datos**: Mapear los tipos de la base de datos a tipos JSON estándar (`string`, `number`, `boolean`, `null`).
- **Filas**: Lista de listas o lista de diccionarios.

### 8.2. Ejemplo de Respuesta

```json
{
  "columnas": [
    {"nombre": "id", "tipo": "integer"},
    {"nombre": "nombre", "tipo": "string"},
    {"nombre": "salario", "tipo": "float"}
  ],
  "filas": [
    [1, "Ana", 1200.5],
    [2, "Luis", 1500.0]
  ],
  "tipos": ["integer", "string", "float"],
  "sql_generado": "SELECT id, nombre, salario FROM empleados WHERE salario > 1000",
  "metadatos": {"tiempo_ejecucion": 0.12, "session_id": "abc123"},
  "errores": null
}
```

**Análisis:** Esta estructura facilita el consumo por aplicaciones front-end y BI, y permite la integración con herramientas de análisis y visualización.

---

## 9. Seguridad: Autenticación, Autorización, RBAC y Scopes

### 9.1. Autenticación

- **JWT (JSON Web Tokens)**: Para APIs públicas, implementar autenticación basada en JWT, con expiración corta y refresh tokens.
- **OAuth2**: Integración con proveedores externos si se requiere SSO.
- **API Keys**: Para integraciones máquina a máquina.

### 9.2. Autorización y RBAC

- **Roles**: Definir roles (admin, usuario, solo lectura, etc.) y asociar permisos a endpoints y operaciones.
- **Scopes**: Control granular sobre qué recursos y acciones puede ejecutar cada token.
- **Decoradores y dependencias**: Usar dependencias de FastAPI para verificar permisos en cada endpoint.

### 9.3. Gestión de secretos y cifrado

- **Vault, AWS Secrets Manager**: Almacenar credenciales y secretos fuera del código fuente, con rotación automática y acceso auditado.
- **Cifrado en tránsito**: Forzar HTTPS/TLS en todas las comunicaciones (Nginx termina TLS).
- **Cifrado en reposo**: Si se almacenan logs o auditoría con datos sensibles, cifrarlos en disco.

### 9.4. Protección contra ataques

- **Rate limiting**: Implementar límites de peticiones por IP/usuario en Nginx y en la aplicación para prevenir abuso y ataques de fuerza bruta.
- **Protección CSRF/XSS**: Si se expone una interfaz web, proteger contra ataques comunes.
- **Auditoría y logging estructurado**: Registrar todos los accesos, errores y eventos de seguridad para trazabilidad y cumplimiento.

---

## 10. Manejo de Sesiones y Estado

### 10.1. session_id Opcional

- **Identificador único**: Permite correlacionar múltiples consultas de un mismo usuario/sesión.
- **Almacenamiento**: Redis es recomendado para almacenar sesiones de forma eficiente y escalable.
- **Expiración**: Definir TTL (time-to-live) para sesiones inactivas.
- **Datos asociados**: Permitir almacenar contexto adicional (preferencias, historial, etc.) si es necesario.

### 10.2. Seguridad de sesiones

- **Regeneración de session_id**: Tras autenticación o cambios de privilegios.
- **Protección contra fijación de sesión**: Invalidar sesiones antiguas tras login.
- **Almacenamiento seguro**: No almacenar datos sensibles en la sesión; solo identificadores y contexto mínimo.

---

## 11. Auditoría, Logging y Trazabilidad

### 11.1. Registro de eventos

- **Consultas en lenguaje natural**: Registrar la consulta original, usuario, timestamp.
- **SQL generado**: Registrar el SQL producido por el LLM.
- **Metadatos de ejecución**: Tiempo de ejecución, número de filas, errores, session_id.
- **Accesos y errores**: Registrar intentos de acceso fallidos, errores de autenticación, excepciones.

### 11.2. Almacenamiento y consulta de logs

- **Logs estructurados**: JSON Lines, ELK Stack, o integración con sistemas de SIEM.
- **Retención y cumplimiento**: Definir políticas de retención según normativas locales (Ley 21.719 en Chile).
- **Alertas**: Configurar alertas ante patrones sospechosos o errores críticos.

---

## 12. Prevención de Fugas de Datos y Privacidad

### 12.1. Acceso solo a esquema

- **Nunca exponer datos reales**: El LLM solo recibe el esquema, no datos.
- **Anonimización y seudonimización**: Si se requiere exponer ejemplos, usar datos ficticios o anonimizados.

### 12.2. Protección de PII

- **Detección de PII**: Implementar validaciones para evitar que consultas accedan a columnas sensibles sin autorización.
- **Data masking**: Enmascarar datos sensibles en los resultados si es necesario.

### 12.3. Cumplimiento normativo en Chile

- **Ley 21.719**: Regular el tratamiento y protección de datos personales, incluyendo principios de licitud, finalidad, proporcionalidad, calidad, seguridad, confidencialidad y transparencia.
- **Auditoría y reporte de incidentes**: Obligación de reportar vulneraciones de seguridad y mantener registros de incidentes.

---

## 13. Limitación de Recursos, Rate Limiting y Protección contra Abuso

### 13.1. Rate Limiting en Nginx

- **Configuración de zonas**: Definir zonas de rate limiting por IP, usuario o endpoint.
- **Ejemplo**:
  ```
  limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
  server {
    location /nl2sql/ {
      limit_req zone=api_limit burst=20 nodelay;
      proxy_pass http://127.0.0.1:8000;
    }
  }
  ```
- **Respuesta 429**: Cuando se excede el límite, devolver HTTP 429 Too Many Requests.

### 13.2. Rate Limiting en la aplicación

- **Middleware**: Implementar middleware en FastAPI para limitar peticiones por usuario/session_id.
- **Redis**: Usar Redis para contar peticiones y aplicar límites dinámicos.

---

## 14. Herramientas de Parsing y Reescritura de SQL

### 14.1. sqlglot

- **Parsing**: Analiza y valida la sintaxis SQL, detecta errores y permite inspeccionar el AST.
- **Transpilación**: Convierte SQL entre diferentes dialectos (MySQL, PostgreSQL, SQL Server, etc.).
- **Optimización**: Permite reescribir consultas para compatibilidad y eficiencia.
- **Testing**: Incluye herramientas para pruebas unitarias y de integración de consultas SQL.

### 14.2. Otras herramientas

- **sqlparse**: Parsing y formateo básico de SQL.
- **pytest + bases de datos mock**: Para pruebas de integración y regresión.

---

## 15. Testing y QA

### 15.1. Pruebas unitarias y de integración

- **Cobertura**: Probar todos los endpoints, validaciones, integración con LLM y ejecución SQL.
- **Bases de datos mock**: Usar bases de datos temporales o en memoria para pruebas.
- **Pruebas de seguridad**: Fuzzing, inyección SQL, autenticación, autorización.

### 15.2. Pruebas de rendimiento

- **Carga**: Simular múltiples usuarios concurrentes.
- **Latencia**: Medir tiempos de respuesta del LLM, ejecución SQL y serialización.

### 15.3. Pruebas de compatibilidad

- **Multi-motor**: Validar funcionamiento con todos los motores soportados.
- **Dialectos SQL**: Probar transpilación y ejecución de SQL en cada motor.

---

## 16. Observabilidad y Monitoreo

### 16.1. Métricas de Gunicorn y FastAPI

- **Prometheus**: Exponer métricas de uso, latencia, errores, throughput.
- **Grafana**: Dashboards para monitoreo en tiempo real.
- **Gunicorn statsD**: Integración para monitoreo de workers y recursos.

### 16.2. Monitoreo de LLM

- **Latencia de inferencia**: Medir tiempos de respuesta del modelo.
- **Uso de tokens/coste**: Registrar consumo de tokens y coste asociado.

### 16.3. Monitoreo de base de datos

- **Conexiones activas**: Limitar y monitorear conexiones concurrentes.
- **Errores y timeouts**: Alertar ante fallos de conexión o ejecución.

---

## 17. Despliegue en Producción

### 17.1. Gunicorn y systemd

- **Archivo de servicio**: Crear un archivo `gunicorn.service` en `/etc/systemd/system/` para gestión automática.
- **Ejemplo**:
  ```
  [Unit]
  Description=Gunicorn instance to serve nl2sql
  After=network.target

  [Service]
  User=nl2sql
  Group=nl2sql
  WorkingDirectory=/srv/nl2sql
  Environment="PATH=/srv/nl2sql/venv/bin"
  ExecStart=/srv/nl2sql/venv/bin/gunicorn -k uvicorn.workers.UvicornWorker --workers 4 --bind unix:/run/gunicorn.sock app.main:app
  Restart=always

  [Install]
  WantedBy=multi-user.target
  ```
- **Comandos**:
  - `sudo systemctl daemon-reload`
  - `sudo systemctl start gunicorn`
  - `sudo systemctl enable gunicorn`
  - `sudo systemctl status gunicorn`

### 17.2. Nginx como reverse proxy

- **Configuración**:
  ```
  server {
    listen 443 ssl;
    server_name api.midominio.cl;

    ssl_certificate /etc/letsencrypt/live/api.midominio.cl/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.midominio.cl/privkey.pem;

    location / {
      proxy_pass http://unix:/run/gunicorn.sock;
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_read_timeout 300;
    }
  }
  ```
- **TLS**: Usar Let's Encrypt o certificados empresariales para cifrado.

### 17.3. Docker y CI/CD

- **Dockerfile**: Construir imagen reproducible con dependencias y configuración.
- **CI/CD**: Automatizar build, test y despliegue con GitHub Actions, Jenkins o similar.
- **Variables de entorno**: Gestionar configuración sensible fuera del código.

---

## 18. Optimización de Latencia y Coste de LLM

### 18.1. Caching de respuestas

- **Redis**: Implementar caching de respuestas LLM (exact match y semantic caching) para reducir llamadas redundantes y coste.
- **TTL**: Definir expiración de caché según frecuencia de cambios en el esquema.

### 18.2. Batching y modelos pequeños

- **Batching**: Agrupar consultas similares para reducir latencia.
- **Modelos compactos**: Usar versiones quantizadas o de menor tamaño para consultas simples.

---

## 19. Cumplimiento Legal y Normativo en Chile

### 19.1. Ley 21.719 y protección de datos

- **Principios**: Licitud, finalidad, proporcionalidad, calidad, responsabilidad, seguridad, transparencia y confidencialidad.
- **Consentimiento**: Obtener consentimiento explícito para tratamiento de datos personales sensibles.
- **Anonimización y seudonimización**: Aplicar técnicas para evitar identificación de titulares en logs y resultados.
- **Reporte de incidentes**: Notificar vulneraciones de seguridad a la Agencia de Protección de Datos Personales.

### 19.2. Auditoría y trazabilidad

- **Registro de accesos**: Mantener logs detallados de todas las operaciones sobre datos personales.
- **Derechos de titulares**: Implementar mecanismos para ejercer derechos de acceso, rectificación, supresión y oposición.

---

## 20. Resumen de Flujos y Componentes

| Flujo Principal                | Componentes Involucrados            | Seguridad y Control                              |
|-------------------------------|-------------------------------------|--------------------------------------------------|
| Recepción de consulta         | FastAPI, Nginx                      | Autenticación, rate limiting                     |
| Extracción de esquema         | SQLAlchemy, drivers DB              | Usuario de solo lectura, sin acceso a datos      |
| Generación de SQL             | LLM (OpenAI, Ollama, etc.), prompt  | Prompt seguro, sin datos reales                  |
| Validación de SQL             | sqlglot, validadores internos       | Whitelist, AST, solo SELECT                      |
| Ejecución de consulta         | SQLAlchemy, drivers DB              | Transacción read-only, prepared statements       |
| Serialización de resultados   | Pydantic, JSON                      | Data masking, tipos seguros                      |
| Auditoría y logging           | Logging estructurado, SIEM          | Logs cifrados, acceso restringido                |
| Observabilidad                | Prometheus, Grafana, logs           | Métricas protegidas, sin datos sensibles         |
| Despliegue y operación        | Gunicorn, Nginx, Docker, systemd    | TLS, gestión de secretos, CI/CD seguro           |

---

## 21. Consideraciones Finales y Recomendaciones

- **Modularidad**: Diseñar el sistema de forma modular para facilitar el mantenimiento y la evolución.
- **Escalabilidad**: Preparar la arquitectura para escalar horizontalmente (workers Gunicorn, réplicas Docker).
- **Seguridad por defecto**: Aplicar el principio de mínimo privilegio en todos los componentes.
- **Cumplimiento normativo**: Revisar periódicamente la legislación aplicable y adaptar el sistema a cambios regulatorios.
- **Documentación y formación**: Mantener documentación actualizada y capacitar a los usuarios y operadores en buenas prácticas de seguridad y privacidad.

---

## 22. Referencias Clave

- **LLM a SQL**: Q2BSTUDIO, Oracle, AWS, somosnlp, LinkedIn, arXiv
- **FastAPI vs Flask**: Apidog, Kanaries, DataCamp
- **Seguridad y RBAC**: SimeonOnSecurity, Apuntes.de, FastAPI docs
- **SQL seguro y multi-motor**: sqlglot, Parzibyte, PEP 249, asyncpg/psycopg2
- **Despliegue y producción**: Nginx, Gunicorn, systemd, Docker, CI/CD
- **Cumplimiento legal Chile**: Ley 21.719, Actualidad Jurídica

---

Este plan proporciona una hoja de ruta exhaustiva y detallada para implementar un servicio web de conversión NL→SQL seguro, eficiente y conforme a las mejores prácticas y normativas vigentes. Cada sección puede ser profundizada con ejemplos de código, scripts de despliegue y configuraciones específicas según el contexto y los requerimientos de la organización.
