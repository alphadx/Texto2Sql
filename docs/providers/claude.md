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
