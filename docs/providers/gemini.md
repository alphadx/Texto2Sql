# Google

## Estado de implementación (Hito 0: alineación)

### Decisión inicial de integración
- Gemini se integra mediante **gateway nativo** (`generateContent`) ya existente en el backend.
- Se mantiene compatibilidad con override de `base_url` para entornos proxy/private gateway.

### Alcance del primer release (no-GA)
- Flujo NL→SQL con `llm_provider=gemini`.
- Resolución de configuración por precedencia: request → env por proveedor → env global.
- Mapeo de mensajes al formato Gemini (`system_instruction` + `contents`).

### Fuera de alcance en esta fase
- Tool calling nativo de Gemini.
- Selección dinámica de modelo por coste/latencia.
- Estrategias de caching específicas por modelo Gemini.

### Criterios de aceptación (Definition of Done)
1. Variables documentadas y validadas: `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_BASE_URL`.
2. Contrato de prompts equivalente al flujo de 2 agentes (refine + sql) sin romper formato de salida.
3. Error handling consistente (rate limits, base URL inválida, API key ausente).
4. Pruebas mínimas de wiring gateway + precedencia de config.
5. Smoke `--dry-run` con salida verificable.

### Riesgos y mitigaciones iniciales
- **Cambios de API de Google**: aislar diferencias en gateway Gemini.
- **Límites/cuotas**: aplicar retry/backoff/circuit breaker global.
- **Deriva de prompts**: validar paridad funcional con baseline OpenAI-compatible en tests.

## Hito 1 — Diseño técnico detallado

### 1) Mapeo de configuración (entorno + request)

| Nivel | Campo/variable | Uso en Gemini | Regla |
|---|---|---|---|
| Request (prioridad máxima) | `llm_provider` | selección de proveedor | debe resolver a `gemini` |
| Request | `llm_model` | modelo runtime | pisa defaults/env |
| Request | `llm_api_key` | credencial runtime | prioritaria en multi-tenant |
| Request | `llm_base_url` | endpoint runtime | útil para proxy/gateway dedicado |
| Entorno por proveedor | `GEMINI_MODEL` | default de modelo | aplica si no llega `llm_model` |
| Entorno por proveedor | `GEMINI_API_KEY` | credencial default | aplica si no llega `llm_api_key` |
| Entorno por proveedor | `GEMINI_BASE_URL` | endpoint default | aplica si no llega `llm_base_url` |
| Entorno global | `LLM_MODEL` / `LLM_API_KEY` / `LLM_BASE_URL` | fallback transversal | último fallback antes de defaults internos |

### 2) Precedencia propuesta (algoritmo canónico)

1. Resolver proveedor desde `llm_provider` o `LLM_PROVIDER`.
2. Si proveedor = `gemini`, tomar `model/api_key/base_url` desde request `llm_*`.
3. Completar faltantes con `GEMINI_*`.
4. Completar faltantes con `LLM_*` globales.
5. Si falta `api_key`, retornar error explícito de configuración.
6. Si falta `base_url`, usar default Gemini (`https://generativelanguage.googleapis.com`).

### 3) Contrato runtime para `POST /nl2sql/query`

Payload mínimo recomendado:

```json
{
  "question": "Top 5 clientes por facturación",
  "llm_provider": "gemini",
  "llm_model": "gemini-2.0-flash-lite"
}
```

Payload con override completo:

```json
{
  "question": "Top 5 clientes por facturación",
  "llm_provider": "gemini",
  "llm_model": "gemini-2.0-flash-lite",
  "llm_api_key": "***",
  "llm_base_url": "https://generativelanguage.googleapis.com"
}
```

### 4) Errores esperados (diseño)

- `provider_not_supported`: proveedor inválido/no normalizable.
- `missing_api_key`: faltan `llm_api_key`, `GEMINI_API_KEY` y `LLM_API_KEY`.
- `invalid_base_url`: URL inválida o esquema no permitido.
- `provider_http_error`: error HTTP no recuperable del endpoint Gemini.
- `rate_limited`: límites de cuota/rate limit (tratar como retryable según status).

> Requisito transversal: no exponer API keys ni parámetros sensibles en logs/errores.

### 5) Plan de pruebas por capas (hito 1)

- **Unitarias (resolución de config):** matriz request/env-provider/env-global para Gemini.
- **Unitarias (validación):** API key ausente, base URL inválida, proveedor inválido.
- **Integración liviana (gateway mock):** transformación de mensajes a `system_instruction`/`contents`.
- **Smoke dry-run:** validar wiring y selección de gateway nativo sin llamadas reales.

### 6) Criterio de salida del Hito 1

Hito 1 se cierra cuando precedencia, contrato runtime, errores y plan de pruebas queden documentados para implementación del Hito 2.

## Modelo mini/equivalente recomendado
- `gemini-2.0-flash-lite`

## Endpoint de referencia
- `https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}`

## Variables de entorno
- `LLM_PROVIDER=gemini`
- `LLM_MODEL=gemini-2.0-flash-lite`
- `LLM_BASE_URL` (si aplica)
- `GEMINI_API_KEY`

## Snippets cliente (PHP 8.3, Node.js, Python, C++, C#, Java)

> Archivo generado automáticamente desde `docs/providers/catalog.json`.

### PHP 8.3
```php
$payload = ['model' => getenv('LLM_MODEL'), 'messages' => [['role'=>'user','content'=>'hola']]];
$ch = curl_init(getenv('LLM_BASE_URL') ?: 'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}');
curl_setopt_array($ch, [CURLOPT_POST=>true, CURLOPT_RETURNTRANSFER=>true,
  CURLOPT_HTTPHEADER=>['Content-Type: application/json','Authorization: Bearer '.getenv('GEMINI_API_KEY')],
  CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
```

### Node.js (LTS actual)
```js
const r = await fetch(process.env.LLM_BASE_URL ?? 'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}', {
  method: 'POST',
  headers: {'Content-Type':'application/json','Authorization':`Bearer ${process.env.GEMINI_API_KEY}`},
  body: JSON.stringify({model: process.env.LLM_MODEL, messages:[{role:'user', content:'hola'}]})
});
console.log(await r.text());
```

### Python (estable actual)
```python
import os, requests
resp = requests.post(
    os.getenv('LLM_BASE_URL') or 'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}',
    headers={'Authorization': f"Bearer {os.getenv('GEMINI_API_KEY')}", 'Content-Type': 'application/json'},
    json={'model': os.getenv('LLM_MODEL'), 'messages': [{'role': 'user', 'content': 'hola'}]}
)
print(resp.text)
```

### C++ (estándar actual + libcurl)
```cpp
// Compilar con libcurl. Enviar JSON con Authorization: Bearer <API_KEY>.
// Endpoint: https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}
```

### C# (.NET actual)
```csharp
using var http = new HttpClient();
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("GEMINI_API_KEY"));
var body = JsonSerializer.Serialize(new { model = Environment.GetEnvironmentVariable("LLM_MODEL"), messages = new[] { new { role = "user", content = "hola" } } });
var res = await http.PostAsync(Environment.GetEnvironmentVariable("LLM_BASE_URL") ?? "https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}", new StringContent(body, Encoding.UTF8, "application/json"));
Console.WriteLine(await res.Content.ReadAsStringAsync());
```

### Java (JDK actual)
```java
var client = HttpClient.newHttpClient();
var json = "{\"model\":\"" + System.getenv("LLM_MODEL") + "\",\"messages\":[{\"role\":\"user\",\"content\":\"hola\"}]}";
var req = HttpRequest.newBuilder(URI.create(System.getenv().getOrDefault("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}")))
    .header("Content-Type", "application/json")
    .header("Authorization", "Bearer " + System.getenv("GEMINI_API_KEY"))
    .POST(HttpRequest.BodyPublishers.ofString(json))
    .build();
var res = client.send(req, HttpResponse.BodyHandlers.ofString());
System.out.println(res.body());
```
