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
