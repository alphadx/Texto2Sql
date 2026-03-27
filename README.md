# Texto2Sql

Conversor intermedio (requiere LLM) para traducir preguntas en lenguaje natural a SQL y devolver resultados en JSON.

## Seguridad (JWT, scopes y roles)

La API usa autenticación por **Bearer JWT** para proteger `POST /nl2sql/query` y endpoints administrativos (ejemplo: `DELETE /session/{session_id}`).

### Variables de entorno de seguridad

- `AUTH_REQUIRED` (default `true`): activa/desactiva verificación JWT.
- `AUTH_JWT_SECRET` (**requerida** cuando `AUTH_REQUIRED=true`): secreto HMAC para validar JWT.
- `AUTH_JWT_ALGORITHM` (default `HS256`).
- `AUTH_JWT_AUDIENCE` (opcional).
- `AUTH_JWT_ISSUER` (opcional).

### Validaciones de arranque

Si `AUTH_REQUIRED=true`, la aplicación falla al arrancar cuando:

- Falta `AUTH_JWT_SECRET`.
- `AUTH_JWT_SECRET` tiene valores inseguros (`changeme`, `default`, `secret`, etc.).
- `AUTH_JWT_SECRET` tiene menos de 32 caracteres.

### Control de acceso

- `POST /nl2sql/query` requiere scope `query:execute`.
- Operaciones administrativas/auditoría requieren:
  - scope `audit:admin`, **o**
  - role `admin`.

### Claims esperados en JWT

- `sub`: identificador del sujeto (requerido).
- `scopes` (lista) o `scope` (string separado por espacios).
- `roles` (lista) o `role` (string).

## Gestión de sesión

El servicio soporta dos backends de sesión configurables por variables de entorno:

- `SESSION_MANAGER_BACKEND=memory` (default): historial en memoria del proceso.
- `SESSION_MANAGER_BACKEND=redis`: historial persistido en Redis por `session_id` y agente (`refiner` / `sql_agent`).

Variables para Redis:

- `REDIS_URL` (default `redis://localhost:6379/0`)
- `SESSION_TTL_SECONDS` (default `3600`)
- `SESSION_KEY_PREFIX` (default `nl2sql:session`)
- `SESSION_TTL_POLICY` (default `absolute`):
  - `absolute`: el TTL solo se aplica en escrituras (`set_history`).
  - `sliding`: el TTL se renueva en cada lectura válida (`get_history`).

Cada historial se serializa en JSON y se almacena con TTL para expiración automática. También se puede borrar explícitamente con `DELETE /session/{session_id}`.

### Ejemplos completos de configuración

#### 1) Modo memoria (local/dev)

```bash
export SESSION_MANAGER_BACKEND=memory
```

#### 2) Modo Redis (staging/prod)

```bash
export SESSION_MANAGER_BACKEND=redis
export REDIS_URL=redis://redis.internal:6379/0
export SESSION_TTL_SECONDS=3600
export SESSION_TTL_POLICY=absolute
export SESSION_KEY_PREFIX=nl2sql:session:staging
```

#### 3) Recomendaciones por ambiente

- **dev**:
  - `SESSION_MANAGER_BACKEND=memory` (simple y sin dependencias externas)
  - o Redis con `SESSION_KEY_PREFIX=nl2sql:session:dev` y `SESSION_TTL_SECONDS=900`
- **staging**:
  - `SESSION_MANAGER_BACKEND=redis`
  - `SESSION_KEY_PREFIX=nl2sql:session:staging`
  - `SESSION_TTL_SECONDS=1800` o `3600`
- **prod**:
  - `SESSION_MANAGER_BACKEND=redis`
  - `SESSION_KEY_PREFIX=nl2sql:session:prod`
  - `SESSION_TTL_SECONDS=3600` o mayor según retención requerida
  - `SESSION_TTL_POLICY=absolute` para comportamiento más predecible, o `sliding` si se busca mantener vivas sesiones activas

### Formato de claves Redis y operación

Formato de clave:

```text
{SESSION_KEY_PREFIX}:{session_id}:{agent}
```

Donde:
- `session_id`: identificador de conversación.
- `agent`: `refiner` o `sql_agent`.

Ejemplos:
- `nl2sql:session:prod:abc123:refiner`
- `nl2sql:session:prod:abc123:sql_agent`

Consideraciones operativas:
- Usar prefijos por ambiente (`dev/staging/prod`) evita colisiones.
- Con `SESSION_TTL_POLICY=sliding`, las lecturas renuevan expiración.
- `DELETE /session/{session_id}` elimina las claves de ambos agentes.
- Monitorear expiraciones y uso de claves desde Redis (métricas/keyspace notifications) ayuda a detectar sesiones huérfanas o TTL mal calibrado.

## Ejemplos de consumo de la API

> Todos los ejemplos usan `POST /nl2sql/query` con Bearer JWT (`query:execute`).

### Node.js (fetch)

```js
const payload = {
  host: "localhost",
  usuario: "user",
  contraseña: "secret",
  puerto: 5432,
  nombre_bd: "testdb",
  motor_bd: "postgres",
  consulta_nl: "Muestra los 10 usuarios más recientes",
  session_id: "demo-session-1"
};

const resp = await fetch("http://localhost:8000/nl2sql/query", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": "Bearer TU_JWT"
  },
  body: JSON.stringify(payload)
});

console.log(await resp.json());
```

### Python (requests)

```python
import requests

payload = {
    "host": "localhost",
    "usuario": "user",
    "contraseña": "secret",
    "puerto": 5432,
    "nombre_bd": "testdb",
    "motor_bd": "postgres",
    "consulta_nl": "Muestra los 10 usuarios más recientes",
    "session_id": "demo-session-1",
}

resp = requests.post(
    "http://localhost:8000/nl2sql/query",
    json=payload,
    headers={"Authorization": "Bearer TU_JWT"},
    timeout=30,
)
print(resp.status_code, resp.json())
```

### PHP (cURL)

```php
<?php
$payload = [
  "host" => "localhost",
  "usuario" => "user",
  "contraseña" => "secret",
  "puerto" => 5432,
  "nombre_bd" => "testdb",
  "motor_bd" => "postgres",
  "consulta_nl" => "Muestra los 10 usuarios más recientes",
  "session_id" => "demo-session-1"
];

$ch = curl_init("http://localhost:8000/nl2sql/query");
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
  "Content-Type: application/json",
  "Authorization: Bearer TU_JWT"
]);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$result = curl_exec($ch);
echo $result;
curl_close($ch);
```

### Java (HttpClient)

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

String json = """
{
  "host":"localhost",
  "usuario":"user",
  "contraseña":"secret",
  "puerto":5432,
  "nombre_bd":"testdb",
  "motor_bd":"postgres",
  "consulta_nl":"Muestra los 10 usuarios más recientes",
  "session_id":"demo-session-1"
}
""";

HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("http://localhost:8000/nl2sql/query"))
    .header("Content-Type", "application/json")
    .header("Authorization", "Bearer TU_JWT")
    .POST(HttpRequest.BodyPublishers.ofString(json))
    .build();

HttpResponse<String> response = HttpClient.newHttpClient()
    .send(request, HttpResponse.BodyHandlers.ofString());

System.out.println(response.statusCode());
System.out.println(response.body());
```

### C# (.NET HttpClient)

```csharp
using System.Net.Http.Headers;
using System.Text;

var payload = """
{
  "host":"localhost",
  "usuario":"user",
  "contraseña":"secret",
  "puerto":5432,
  "nombre_bd":"testdb",
  "motor_bd":"postgres",
  "consulta_nl":"Muestra los 10 usuarios más recientes",
  "session_id":"demo-session-1"
}
""";

using var client = new HttpClient();
var request = new HttpRequestMessage(HttpMethod.Post, "http://localhost:8000/nl2sql/query");
request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", "TU_JWT");
request.Content = new StringContent(payload, Encoding.UTF8, "application/json");

var response = await client.SendAsync(request);
Console.WriteLine((int)response.StatusCode);
Console.WriteLine(await response.Content.ReadAsStringAsync());
```

### C++ (libcurl)

```cpp
#include <curl/curl.h>
#include <string>

int main() {
  CURL* curl = curl_easy_init();
  if (!curl) return 1;

  std::string body = R"({
    "host":"localhost",
    "usuario":"user",
    "contraseña":"secret",
    "puerto":5432,
    "nombre_bd":"testdb",
    "motor_bd":"postgres",
    "consulta_nl":"Muestra los 10 usuarios más recientes",
    "session_id":"demo-session-1"
  })";

  struct curl_slist* headers = nullptr;
  headers = curl_slist_append(headers, "Content-Type: application/json");
  headers = curl_slist_append(headers, "Authorization: Bearer TU_JWT");

  curl_easy_setopt(curl, CURLOPT_URL, "http://localhost:8000/nl2sql/query");
  curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
  curl_easy_setopt(curl, CURLOPT_POST, 1L);
  curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body.c_str());

  curl_easy_perform(curl);

  curl_slist_free_all(headers);
  curl_easy_cleanup(curl);
  return 0;
}
```

## Auditoría y métricas

La API registra cada request de `POST /nl2sql/query` en formato JSON estructurado con:

- `session_id`
- `engine` (`motor_bd`)
- `status_code`
- `durations_ms` por etapa (`schema`, `llm`, `sql`) y total
- `error_type` / `error_message` (si aplica)

Backends de auditoría configurables:

- `AUDIT_LOG_BACKEND=stream` (default): emite JSON por stdout.
- `AUDIT_LOG_BACKEND=file`: persiste a `AUDIT_LOG_FILE_PATH` (default `logs/audit.log`).
- `AUDIT_LOG_BACKEND=sqlite`: persiste a `AUDIT_LOG_DB_PATH` y tabla `AUDIT_LOG_DB_TABLE`.

Métricas base compatibles con Prometheus disponibles en `GET /metrics`:

- `nl2sql_requests_total`
- `nl2sql_request_latency_ms_count` / `nl2sql_request_latency_ms_sum`
- `nl2sql_errors_total{error_type="..."}`

## Ejecución de pruebas

Para asegurar ejecución en un entorno con dependencias instaladas:

```bash
make test
```

El target `test` instala `requirements.txt` + `requirements-dev.txt` y luego ejecuta `pytest tests/test_app.py`.
