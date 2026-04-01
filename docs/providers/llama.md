# Meta

## Estado de implementación (Hito 0: alineación)

### Decisión inicial de integración
- Llama se integra en fase inicial por vía **OpenAI-compatible** usando proveedor hosted/comercial.
- Se prioriza endpoint configurable (`base_url`) para soportar distintos vendors (HF Router, Together, Groq, etc.).

### Alcance del primer release (no-GA)
- Flujo NL→SQL con `llm_provider=llama`.
- Resolución de configuración por precedencia: request → env por proveedor → env global.
- Soporte de variantes instruct compatibles con contrato `chat/completions`.

### Fuera de alcance en esta fase
- Selección automática de proveedor hosted por coste/latencia.
- Orquestación multi-vendor con fallback activo.
- Ajustes finos por familia/modelo más allá del baseline de prompts.

### Criterios de aceptación (Definition of Done)
1. Variables documentadas y validadas: `LLAMA_API_KEY`, `LLAMA_MODEL`, `LLAMA_BASE_URL`.
2. Ejemplo funcional en `POST /nl2sql/query` con `llm_provider=llama` y `llm_*` por request.
3. Validación de configuración (`api_key`, `model`, `base_url`) y errores claros.
4. Pruebas de wiring y precedencia con gateway OpenAI-compatible.
5. Smoke `--dry-run` verificable.

### Riesgos y mitigaciones iniciales
- **Diferencias entre vendors hosted**: estandarizar contrato OpenAI-compatible y validar con smoke por entorno.
- **Rate limits variables**: reutilizar retry/backoff/circuit breaker global.
- **Deriva de modelo recomendado**: mantener catálogo/versionado en docs.

## Hito 1 — Diseño técnico detallado

### 1) Mapeo de configuración (entorno + request)

| Nivel | Campo/variable | Uso en Llama hosted | Regla |
|---|---|---|---|
| Request (prioridad máxima) | `llm_provider` | selección de proveedor | debe resolver a `llama` |
| Request | `llm_model` | modelo runtime | pisa defaults/env |
| Request | `llm_api_key` | credencial runtime | prioritaria en multi-tenant |
| Request | `llm_base_url` | endpoint runtime | define vendor hosted objetivo |
| Entorno por proveedor | `LLAMA_MODEL` | default de modelo | aplica si no llega `llm_model` |
| Entorno por proveedor | `LLAMA_API_KEY` | credencial default | aplica si no llega `llm_api_key` |
| Entorno por proveedor | `LLAMA_BASE_URL` | endpoint default | aplica si no llega `llm_base_url` |
| Entorno global | `LLM_MODEL` / `LLM_API_KEY` / `LLM_BASE_URL` | fallback transversal | último fallback antes de defaults internos |

### 2) Precedencia propuesta (algoritmo canónico)

1. Resolver proveedor desde `llm_provider` o `LLM_PROVIDER`.
2. Si proveedor = `llama`, tomar `model/api_key/base_url` desde request `llm_*`.
3. Completar faltantes con `LLAMA_*`.
4. Completar faltantes con `LLM_*`.
5. Si falta `api_key`, retornar error explícito de configuración.
6. Si falta `base_url`, usar default del catálogo (`https://router.huggingface.co/v1`).

### 3) Contrato runtime para `POST /nl2sql/query`

Payload mínimo recomendado:

```json
{
  "question": "Top 5 clientes por facturación",
  "llm_provider": "llama",
  "llm_model": "meta-llama/Llama-3.1-8B-Instruct"
}
```

Payload con override completo:

```json
{
  "question": "Top 5 clientes por facturación",
  "llm_provider": "llama",
  "llm_model": "meta-llama/Llama-3.1-8B-Instruct",
  "llm_api_key": "***",
  "llm_base_url": "https://router.huggingface.co/v1"
}
```

### 4) Errores esperados (diseño)

- `provider_not_supported`: proveedor inválido/no normalizable.
- `missing_api_key`: faltan `llm_api_key`, `LLAMA_API_KEY` y `LLM_API_KEY`.
- `invalid_base_url`: URL inválida o esquema no permitido.
- `provider_http_error`: error HTTP no recuperable del endpoint hosted.
- `rate_limited`: límites de cuota/rate limit (retryable según status).

### 5) Plan de pruebas por capas (hito 1)

- **Unitarias:** precedencia request/env-provider/env-global y validación de base URL.
- **Integración liviana:** wiring OpenAI-compatible para `llama`.
- **Smoke dry-run:** validar endpoint/modelo configurado sin llamada real.

### 6) Criterio de salida del Hito 1

Hito 1 se cierra cuando precedencia, contrato runtime, errores y plan de pruebas queden documentados para implementación del Hito 2.

## Modelo mini/equivalente recomendado
- `meta-llama/Llama-3.1-8B-Instruct`

## Endpoint de referencia
- `https://router.huggingface.co/v1/chat/completions`

## Variables de entorno
- `LLM_PROVIDER=llama`
- `LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct`
- `LLM_BASE_URL` (si aplica)
- `LLAMA_API_KEY`

## Snippets cliente (PHP 8.3, Node.js, Python, C++, C#, Java)

> Archivo generado automáticamente desde `docs/providers/catalog.json`.

### PHP 8.3
```php
$payload = ['model' => getenv('LLM_MODEL'), 'messages' => [['role'=>'user','content'=>'hola']]];
$ch = curl_init(getenv('LLM_BASE_URL') ?: 'https://router.huggingface.co/v1/chat/completions');
curl_setopt_array($ch, [CURLOPT_POST=>true, CURLOPT_RETURNTRANSFER=>true,
  CURLOPT_HTTPHEADER=>['Content-Type: application/json','Authorization: Bearer '.getenv('LLAMA_API_KEY')],
  CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
```

### Node.js (LTS actual)
```js
const r = await fetch(process.env.LLM_BASE_URL ?? 'https://router.huggingface.co/v1/chat/completions', {
  method: 'POST',
  headers: {'Content-Type':'application/json','Authorization':`Bearer ${process.env.LLAMA_API_KEY}`},
  body: JSON.stringify({model: process.env.LLM_MODEL, messages:[{role:'user', content:'hola'}]})
});
console.log(await r.text());
```

### Python (estable actual)
```python
import os, requests
resp = requests.post(
    os.getenv('LLM_BASE_URL') or 'https://router.huggingface.co/v1/chat/completions',
    headers={'Authorization': f"Bearer {os.getenv('LLAMA_API_KEY')}", 'Content-Type': 'application/json'},
    json={'model': os.getenv('LLM_MODEL'), 'messages': [{'role': 'user', 'content': 'hola'}]}
)
print(resp.text)
```

### C++ (estándar actual + libcurl)
```cpp
// Compilar con libcurl. Enviar JSON con Authorization: Bearer <API_KEY>.
// Endpoint: https://router.huggingface.co/v1/chat/completions
```

### C# (.NET actual)
```csharp
using var http = new HttpClient();
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("LLAMA_API_KEY"));
var body = JsonSerializer.Serialize(new { model = Environment.GetEnvironmentVariable("LLM_MODEL"), messages = new[] { new { role = "user", content = "hola" } } });
var res = await http.PostAsync(Environment.GetEnvironmentVariable("LLM_BASE_URL") ?? "https://router.huggingface.co/v1/chat/completions", new StringContent(body, Encoding.UTF8, "application/json"));
Console.WriteLine(await res.Content.ReadAsStringAsync());
```

### Java (JDK actual)
```java
var client = HttpClient.newHttpClient();
var json = "{\"model\":\"" + System.getenv("LLM_MODEL") + "\",\"messages\":[{\"role\":\"user\",\"content\":\"hola\"}]}";
var req = HttpRequest.newBuilder(URI.create(System.getenv().getOrDefault("LLM_BASE_URL", "https://router.huggingface.co/v1/chat/completions")))
    .header("Content-Type", "application/json")
    .header("Authorization", "Bearer " + System.getenv("LLAMA_API_KEY"))
    .POST(HttpRequest.BodyPublishers.ofString(json))
    .build();
var res = client.send(req, HttpResponse.BodyHandlers.ofString());
System.out.println(res.body());
```
