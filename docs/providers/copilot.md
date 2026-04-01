# GitHub

## Estado de implementación (Hito 0: alineación)

### Decisión inicial de integración
- Copilot se considera en fase de **evaluación enterprise** con enfoque OpenAI-compatible donde aplique.
- La integración v1 se limita a backend programático explícitamente soportado por credenciales/tenant corporativo.

### Alcance del primer release (no-GA)
- Validar viabilidad técnica real de uso como backend NL→SQL.
- Definir configuración mínima por entorno (`api_key`, `model`, `base_url`) y contrato por request.
- Confirmar restricciones de seguridad/compliance para uso server-to-server.

### Fuera de alcance en esta fase
- Integración acoplada a UX de IDE/cliente Copilot.
- Supuestos de disponibilidad universal sin validación de tenant/licencia.
- Soporte contractual multi-org sin validación previa de permisos.

### Criterios de aceptación (Definition of Done)
1. Alcance técnico enterprise claramente delimitado (qué sí/qué no soporta backend).
2. Variables documentadas y validadas: `COPILOT_API_KEY`, `COPILOT_MODEL`, `COPILOT_BASE_URL`.
3. Ejemplo funcional en `POST /nl2sql/query` con `llm_provider=copilot`.
4. Pruebas de wiring/configuración y manejo de errores de autenticación/autorización.
5. Smoke `--dry-run` y checklist de precondiciones enterprise.

### Riesgos y mitigaciones iniciales
- **Ambigüedad de soporte programático**: validar fuentes oficiales + pruebas controladas por tenant.
- **Restricciones de seguridad/licenciamiento**: documentar prerequisitos antes de habilitar producción.
- **Dependencia de endpoint/credencial específica**: aislar configuración por entorno.

## Hito 1 — Diseño técnico detallado

### 1) Mapeo de configuración (entorno + request)

| Nivel | Campo/variable | Uso en Copilot enterprise | Regla |
|---|---|---|---|
| Request (prioridad máxima) | `llm_provider` | selección de proveedor | debe resolver a `copilot` |
| Request | `llm_model` | modelo runtime | pisa defaults/env |
| Request | `llm_api_key` | credencial runtime | prioritaria en multi-tenant/tenant-aware |
| Request | `llm_base_url` | endpoint runtime | define endpoint enterprise habilitado |
| Entorno por proveedor | `COPILOT_MODEL` | default de modelo | aplica si no llega `llm_model` |
| Entorno por proveedor | `COPILOT_API_KEY` | credencial default | aplica si no llega `llm_api_key` |
| Entorno por proveedor | `COPILOT_BASE_URL` | endpoint default | aplica si no llega `llm_base_url` |
| Entorno global | `LLM_MODEL` / `LLM_API_KEY` / `LLM_BASE_URL` | fallback transversal | último fallback antes de defaults internos |

### 2) Precedencia propuesta (algoritmo canónico)

1. Resolver proveedor desde `llm_provider` o `LLM_PROVIDER`.
2. Si proveedor = `copilot`, tomar `model/api_key/base_url` desde request `llm_*`.
3. Completar faltantes con `COPILOT_*`.
4. Completar faltantes con `LLM_*`.
5. Si falta `api_key`, retornar error explícito de configuración.
6. Si falta `base_url`, usar default enterprise configurado en catálogo (`https://models.inference.ai.azure.com`).

### 3) Contrato runtime para `POST /nl2sql/query`

Payload mínimo recomendado:

```json
{
  "question": "Top 5 clientes por facturación",
  "llm_provider": "copilot",
  "llm_model": "gpt-4.1-mini"
}
```

Payload con override completo:

```json
{
  "question": "Top 5 clientes por facturación",
  "llm_provider": "copilot",
  "llm_model": "gpt-4.1-mini",
  "llm_api_key": "***",
  "llm_base_url": "https://models.inference.ai.azure.com"
}
```

### 4) Errores esperados (diseño)

- `provider_not_supported`: proveedor inválido/no normalizable.
- `missing_api_key`: faltan `llm_api_key`, `COPILOT_API_KEY` y `LLM_API_KEY`.
- `invalid_base_url`: URL inválida o endpoint no permitido por política enterprise.
- `provider_http_error`: error HTTP no recuperable del endpoint configurado.
- `authz_error`: credencial válida pero sin permisos/tenant habilitado.

### 5) Plan de pruebas por capas (hito 1)

- **Unitarias:** precedencia request/env-provider/env-global y validación de base URL.
- **Integración liviana:** wiring OpenAI-compatible para `copilot`.
- **Smoke dry-run:** validación de configuración sin llamada real (incluyendo check de precondiciones enterprise).

### 6) Criterio de salida del Hito 1

Hito 1 se cierra cuando precedencia, contrato runtime, errores y plan de pruebas queden documentados para implementación del Hito 2.

## Modelo mini/equivalente recomendado
- `gpt-4.1-mini`

## Endpoint de referencia
- `https://models.inference.ai.azure.com/chat/completions`

## Variables de entorno
- `LLM_PROVIDER=copilot`
- `LLM_MODEL=gpt-4.1-mini`
- `LLM_BASE_URL` (si aplica)
- `COPILOT_API_KEY`

## Snippets cliente (PHP 8.3, Node.js, Python, C++, C#, Java)

> Archivo generado automáticamente desde `docs/providers/catalog.json`.

### PHP 8.3
```php
$payload = ['model' => getenv('LLM_MODEL'), 'messages' => [['role'=>'user','content'=>'hola']]];
$ch = curl_init(getenv('LLM_BASE_URL') ?: 'https://models.inference.ai.azure.com/chat/completions');
curl_setopt_array($ch, [CURLOPT_POST=>true, CURLOPT_RETURNTRANSFER=>true,
  CURLOPT_HTTPHEADER=>['Content-Type: application/json','Authorization: Bearer '.getenv('COPILOT_API_KEY')],
  CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
```

### Node.js (LTS actual)
```js
const r = await fetch(process.env.LLM_BASE_URL ?? 'https://models.inference.ai.azure.com/chat/completions', {
  method: 'POST',
  headers: {'Content-Type':'application/json','Authorization':`Bearer ${process.env.COPILOT_API_KEY}`},
  body: JSON.stringify({model: process.env.LLM_MODEL, messages:[{role:'user', content:'hola'}]})
});
console.log(await r.text());
```

### Python (estable actual)
```python
import os, requests
resp = requests.post(
    os.getenv('LLM_BASE_URL') or 'https://models.inference.ai.azure.com/chat/completions',
    headers={'Authorization': f"Bearer {os.getenv('COPILOT_API_KEY')}", 'Content-Type': 'application/json'},
    json={'model': os.getenv('LLM_MODEL'), 'messages': [{'role': 'user', 'content': 'hola'}]}
)
print(resp.text)
```

### C++ (estándar actual + libcurl)
```cpp
// Compilar con libcurl. Enviar JSON con Authorization: Bearer <API_KEY>.
// Endpoint: https://models.inference.ai.azure.com/chat/completions
```

### C# (.NET actual)
```csharp
using var http = new HttpClient();
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("COPILOT_API_KEY"));
var body = JsonSerializer.Serialize(new { model = Environment.GetEnvironmentVariable("LLM_MODEL"), messages = new[] { new { role = "user", content = "hola" } } });
var res = await http.PostAsync(Environment.GetEnvironmentVariable("LLM_BASE_URL") ?? "https://models.inference.ai.azure.com/chat/completions", new StringContent(body, Encoding.UTF8, "application/json"));
Console.WriteLine(await res.Content.ReadAsStringAsync());
```

### Java (JDK actual)
```java
var client = HttpClient.newHttpClient();
var json = "{\"model\":\"" + System.getenv("LLM_MODEL") + "\",\"messages\":[{\"role\":\"user\",\"content\":\"hola\"}]}";
var req = HttpRequest.newBuilder(URI.create(System.getenv().getOrDefault("LLM_BASE_URL", "https://models.inference.ai.azure.com/chat/completions")))
    .header("Content-Type", "application/json")
    .header("Authorization", "Bearer " + System.getenv("COPILOT_API_KEY"))
    .POST(HttpRequest.BodyPublishers.ofString(json))
    .build();
var res = client.send(req, HttpResponse.BodyHandlers.ofString());
System.out.println(res.body());
```
