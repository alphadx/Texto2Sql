# Anthropic Claude

## Estado de implementación (Hito 0: alineación)

### Decisión inicial de integración
- Claude se integra mediante **gateway nativo Anthropic** (`/v1/messages`) ya existente en el backend.
- Se soporta override de `base_url` por request/env para entornos proxy o compliance empresarial.

### Alcance del primer release (no-GA)
- Flujo NL→SQL con `llm_provider=claude`/`anthropic`.
- Compatibilidad con flujo de 2 agentes (refine + sql) sobre contrato de mensajes Anthropic.
- Resolución de configuración por precedencia: request → env por proveedor → env global.

### Fuera de alcance en esta fase
- Tool use avanzado de Anthropic.
- Routing dinámico entre familias de modelos Claude.
- Estrategias multi-región activas con failover automático.

### Criterios de aceptación (Definition of Done)
1. Variables documentadas y validadas: `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_BASE_URL`.
2. Soporte explícito de alias (`claude` → `anthropic`) sin inconsistencias startup/runtime.
3. Ejemplo funcional en `POST /nl2sql/query` con `llm_provider=claude` y overrides `llm_*`.
4. Pruebas de wiring de gateway nativo + precedencia de configuración.
5. Smoke `--dry-run` con salida verificable y errores estructurados.

### Riesgos y mitigaciones iniciales
- **Diferencias de formato mensajes**: mantener adaptación `system`/`messages` en gateway Anthropic.
- **Límites/cuotas**: reutilizar retry/backoff/circuit breaker global.
- **Evolución de API**: encapsular cambios en gateway nativo para no romper contrato NL→SQL.

## Hito 1 — Diseño técnico detallado

### 1) Mapeo de configuración (entorno + request)

| Nivel | Campo/variable | Uso en Claude/Anthropic | Regla |
|---|---|---|---|
| Request (prioridad máxima) | `llm_provider` | selección de proveedor | acepta `claude` o `anthropic` |
| Request | `llm_model` | modelo runtime | pisa defaults/env |
| Request | `llm_api_key` | credencial runtime | prioritaria en multi-tenant |
| Request | `llm_base_url` | endpoint runtime | habilita proxy/gateway dedicado |
| Entorno por proveedor | `ANTHROPIC_MODEL` | default de modelo | aplica si no llega `llm_model` |
| Entorno por proveedor | `ANTHROPIC_API_KEY` | credencial default | aplica si no llega `llm_api_key` |
| Entorno por proveedor | `ANTHROPIC_BASE_URL` | endpoint default | aplica si no llega `llm_base_url` |
| Entorno global | `LLM_MODEL` / `LLM_API_KEY` / `LLM_BASE_URL` | fallback transversal | último fallback antes de defaults internos |

### 2) Precedencia propuesta (algoritmo canónico)

1. Resolver proveedor desde `llm_provider` o `LLM_PROVIDER`.
2. Normalizar alias `claude -> anthropic`.
3. Tomar `model/api_key/base_url` desde request `llm_*`.
4. Completar faltantes con `ANTHROPIC_*`.
5. Completar faltantes con `LLM_*`.
6. Si falta `api_key`, retornar error de configuración explícito.
7. Si falta `base_url`, usar default Anthropic (`https://api.anthropic.com`).

### 3) Contrato runtime para `POST /nl2sql/query`

Payload mínimo recomendado:

```json
{
  "question": "Top 5 clientes por facturación",
  "llm_provider": "claude",
  "llm_model": "claude-3-5-haiku-latest"
}
```

Payload con override completo:

```json
{
  "question": "Top 5 clientes por facturación",
  "llm_provider": "claude",
  "llm_model": "claude-3-5-haiku-latest",
  "llm_api_key": "***",
  "llm_base_url": "https://api.anthropic.com"
}
```

### 4) Errores esperados (diseño)

- `provider_not_supported`: proveedor inválido/no normalizable.
- `missing_api_key`: faltan `llm_api_key`, `ANTHROPIC_API_KEY` y `LLM_API_KEY`.
- `invalid_base_url`: URL inválida o esquema no permitido.
- `provider_http_error`: error HTTP no recuperable en `/v1/messages`.
- `rate_limited`: límites de cuota/rate limit (retryable según status).

> Requisito transversal: no exponer API keys ni secretos en logs o payloads de error.

### 5) Plan de pruebas por capas (hito 1)

- **Unitarias (resolución de config):** alias + precedencia request/env-provider/env-global.
- **Unitarias (gateway):** transformación `system` + mensajes en contrato Anthropic.
- **Integración liviana:** flujo refine/sql con provider `claude`.
- **Smoke dry-run:** validar wiring sin llamadas reales.

### 6) Criterio de salida del Hito 1

Hito 1 se cierra cuando precedencia, contrato runtime, errores y plan de pruebas queden documentados para implementación del Hito 2.

## Hito 2 — Avance de implementación (actual)

Estado actual ya cubierto en código:

- Gateway nativo Anthropic para `/v1/messages`.
- Soporte de alias `claude -> anthropic` en runtime/startup.
- Default de modelo por proveedor (`claude-3-5-haiku-latest`) alineado al catálogo.
- Validación de `base_url` y manejo consistente de errores de configuración en API/smoke.
- Evidencia de wiring en converter y endpoint API (`tests/test_llm_converter.py`, `tests/test_app.py`).

Pendiente para cierre completo de Hito 2:

- ✅ Prueba e2e de `POST /nl2sql/query` con `llm_provider=claude` y mocks de pipeline (`tests/test_app.py`).

## Modelo mini/equivalente recomendado
- `claude-3-5-haiku-latest`

## Endpoint de referencia
- `https://api.anthropic.com/v1/messages`

## Variables de entorno
- `LLM_PROVIDER=claude`
- `LLM_MODEL=claude-3-5-haiku-latest`
- `LLM_BASE_URL` (si aplica)
- `ANTHROPIC_API_KEY`

## Snippets cliente (PHP 8.3, Node.js, Python, C++, C#, Java)

> Archivo generado automáticamente desde `docs/providers/catalog.json`.

### PHP 8.3
```php
$payload = ['model' => getenv('LLM_MODEL'), 'messages' => [['role'=>'user','content'=>'hola']]];
$ch = curl_init(getenv('LLM_BASE_URL') ?: 'https://api.anthropic.com/v1/messages');
curl_setopt_array($ch, [CURLOPT_POST=>true, CURLOPT_RETURNTRANSFER=>true,
  CURLOPT_HTTPHEADER=>['Content-Type: application/json','Authorization: Bearer '.getenv('ANTHROPIC_API_KEY')],
  CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
```

### Node.js (LTS actual)
```js
const r = await fetch(process.env.LLM_BASE_URL ?? 'https://api.anthropic.com/v1/messages', {
  method: 'POST',
  headers: {'Content-Type':'application/json','Authorization':`Bearer ${process.env.ANTHROPIC_API_KEY}`},
  body: JSON.stringify({model: process.env.LLM_MODEL, messages:[{role:'user', content:'hola'}]})
});
console.log(await r.text());
```

### Python (estable actual)
```python
import os, requests
resp = requests.post(
    os.getenv('LLM_BASE_URL') or 'https://api.anthropic.com/v1/messages',
    headers={'Authorization': f"Bearer {os.getenv('ANTHROPIC_API_KEY')}", 'Content-Type': 'application/json'},
    json={'model': os.getenv('LLM_MODEL'), 'messages': [{'role': 'user', 'content': 'hola'}]}
)
print(resp.text)
```

### C++ (estándar actual + libcurl)
```cpp
// Compilar con libcurl. Enviar JSON con Authorization: Bearer <API_KEY>.
// Endpoint: https://api.anthropic.com/v1/messages
```

### C# (.NET actual)
```csharp
using var http = new HttpClient();
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY"));
var body = JsonSerializer.Serialize(new { model = Environment.GetEnvironmentVariable("LLM_MODEL"), messages = new[] { new { role = "user", content = "hola" } } });
var res = await http.PostAsync(Environment.GetEnvironmentVariable("LLM_BASE_URL") ?? "https://api.anthropic.com/v1/messages", new StringContent(body, Encoding.UTF8, "application/json"));
Console.WriteLine(await res.Content.ReadAsStringAsync());
```

### Java (JDK actual)
```java
var client = HttpClient.newHttpClient();
var json = "{\"model\":\"" + System.getenv("LLM_MODEL") + "\",\"messages\":[{\"role\":\"user\",\"content\":\"hola\"}]}";
var req = HttpRequest.newBuilder(URI.create(System.getenv().getOrDefault("LLM_BASE_URL", "https://api.anthropic.com/v1/messages")))
    .header("Content-Type", "application/json")
    .header("Authorization", "Bearer " + System.getenv("ANTHROPIC_API_KEY"))
    .POST(HttpRequest.BodyPublishers.ofString(json))
    .build();
var res = client.send(req, HttpResponse.BodyHandlers.ofString());
System.out.println(res.body());
```
