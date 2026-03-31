# Mistral

## Estado de implementación (Hito 0: alineación)

### Decisión inicial de integración
- Se adopta integración **OpenAI-compatible** para Mistral (`/v1/chat/completions`) en la fase inicial.
- Se habilita override de `base_url` por request/env para soportar proxys o gateways dedicados por entorno.

### Alcance del primer release (no-GA)
- Flujo NL→SQL con `llm_provider=mistral`.
- Resolución de configuración por precedencia: request → env por proveedor → env global.
- Soporte del modelo mini/equivalente documentado para despliegues iniciales.

### Fuera de alcance en esta fase
- Routing dinámico multi-modelo Mistral por coste/latencia.
- Features específicas no cubiertas por Chat Completions OpenAI-compatible.
- Políticas avanzadas de fallback multi-región.

### Criterios de aceptación (Definition of Done)
1. Variables documentadas y validadas: `MISTRAL_API_KEY`, `MISTRAL_MODEL`, `MISTRAL_BASE_URL`.
2. Ejemplo funcional en `POST /nl2sql/query` con overrides `llm_*`.
3. Validación de errores de configuración (`api_key`, `model`, `base_url`).
4. Pruebas de wiring de gateway y precedencia de configuración.
5. Smoke `--dry-run` con salida verificable y errores estructurados.

### Riesgos y mitigaciones iniciales
- **Rate limits / cuotas**: usar retry/backoff/circuit breaker existentes.
- **Diferencias de compatibilidad de payload**: validar en tests de converter y smoke.
- **Deriva entre docs y código**: mantener validación de sincronía en scripts de docs.

## Modelo mini/equivalente recomendado
- `mistral-small-latest`

## Endpoint de referencia
- `https://api.mistral.ai/v1/chat/completions`

## Variables de entorno
- `LLM_PROVIDER=mistral`
- `LLM_MODEL=mistral-small-latest`
- `LLM_BASE_URL` (si aplica)
- `MISTRAL_API_KEY`

## Snippets cliente (PHP 8.3, Node.js, Python, C++, C#, Java)

> Archivo generado automáticamente desde `docs/providers/catalog.json`.

### PHP 8.3
```php
$payload = ['model' => getenv('LLM_MODEL'), 'messages' => [['role'=>'user','content'=>'hola']]];
$ch = curl_init(getenv('LLM_BASE_URL') ?: 'https://api.mistral.ai/v1/chat/completions');
curl_setopt_array($ch, [CURLOPT_POST=>true, CURLOPT_RETURNTRANSFER=>true,
  CURLOPT_HTTPHEADER=>['Content-Type: application/json','Authorization: Bearer '.getenv('MISTRAL_API_KEY')],
  CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
```

### Node.js (LTS actual)
```js
const r = await fetch(process.env.LLM_BASE_URL ?? 'https://api.mistral.ai/v1/chat/completions', {
  method: 'POST',
  headers: {'Content-Type':'application/json','Authorization':`Bearer ${process.env.MISTRAL_API_KEY}`},
  body: JSON.stringify({model: process.env.LLM_MODEL, messages:[{role:'user', content:'hola'}]})
});
console.log(await r.text());
```

### Python (estable actual)
```python
import os, requests
resp = requests.post(
    os.getenv('LLM_BASE_URL') or 'https://api.mistral.ai/v1/chat/completions',
    headers={'Authorization': f"Bearer {os.getenv('MISTRAL_API_KEY')}", 'Content-Type': 'application/json'},
    json={'model': os.getenv('LLM_MODEL'), 'messages': [{'role': 'user', 'content': 'hola'}]}
)
print(resp.text)
```

### C++ (estándar actual + libcurl)
```cpp
// Compilar con libcurl. Enviar JSON con Authorization: Bearer <API_KEY>.
// Endpoint: https://api.mistral.ai/v1/chat/completions
```

### C# (.NET actual)
```csharp
using var http = new HttpClient();
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("MISTRAL_API_KEY"));
var body = JsonSerializer.Serialize(new { model = Environment.GetEnvironmentVariable("LLM_MODEL"), messages = new[] { new { role = "user", content = "hola" } } });
var res = await http.PostAsync(Environment.GetEnvironmentVariable("LLM_BASE_URL") ?? "https://api.mistral.ai/v1/chat/completions", new StringContent(body, Encoding.UTF8, "application/json"));
Console.WriteLine(await res.Content.ReadAsStringAsync());
```

### Java (JDK actual)
```java
var client = HttpClient.newHttpClient();
var json = "{\"model\":\"" + System.getenv("LLM_MODEL") + "\",\"messages\":[{\"role\":\"user\",\"content\":\"hola\"}]}";
var req = HttpRequest.newBuilder(URI.create(System.getenv().getOrDefault("LLM_BASE_URL", "https://api.mistral.ai/v1/chat/completions")))
    .header("Content-Type", "application/json")
    .header("Authorization", "Bearer " + System.getenv("MISTRAL_API_KEY"))
    .POST(HttpRequest.BodyPublishers.ofString(json))
    .build();
var res = client.send(req, HttpResponse.BodyHandlers.ofString());
System.out.println(res.body());
```
