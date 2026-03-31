# Hugging Face

## Estado de implementación (Hito 0: alineación)

### Decisión inicial de integración
- Se adopta **Hugging Face Inference por vía OpenAI-compatible** usando el router `chat/completions`.
- Para fase inicial se soportan dos escenarios:
  1. **Serverless Inference Router** (default operativo).
  2. **Dedicated Inference Endpoint** vía `HUGGINGFACE_BASE_URL`/`llm_base_url`.

### Alcance del primer release (no-GA)
- Flujo NL→SQL con `llm_provider=huggingface` dentro del contrato actual `llm_*`.
- Resolución de configuración por precedencia: request → env por proveedor → env global.
- Compatibilidad con modelos de instrucción tipo chat disponibles en el router/endpoint configurado.

### Fuera de alcance en esta fase
- Selección automática de modelo por coste/latencia.
- Política de fallback multi-modelo dentro de Hugging Face.
- Gestión avanzada de cuotas por tenant (más allá de límites globales existentes).

### Criterios de aceptación (Definition of Done)
1. Variables documentadas y validadas: `HUGGINGFACE_API_KEY`, `HUGGINGFACE_MODEL`, `HUGGINGFACE_BASE_URL`.
2. Soporte explícito de ambos modos (`serverless` y `dedicated endpoint`) mediante `base_url`.
3. Ejemplo funcional en `POST /nl2sql/query` con `llm_provider=huggingface` y overrides `llm_*`.
4. Pruebas mínimas para precedencia, validación de configuración y wiring del gateway.
5. Smoke `--dry-run` con salida verificable y errores estructurados.

### Riesgos y mitigaciones iniciales
- **Rate limits / créditos**: usar retry/backoff/circuit breaker ya centralizados.
- **Diferencias de disponibilidad de modelos**: validar modelo al arranque y en smoke por entorno.
- **Variación de latencia serverless**: permitir dedicated endpoint como estrategia de estabilidad.

## Hito 1 — Diseño técnico detallado

### 1) Mapeo de configuración (entorno + request)

| Nivel | Campo/variable | Uso en Hugging Face | Regla |
|---|---|---|---|
| Request (prioridad máxima) | `llm_provider` | selección de proveedor | debe resolver a `huggingface` |
| Request | `llm_model` | modelo runtime | pisa defaults/env |
| Request | `llm_api_key` | token runtime | preferente en multi-tenant |
| Request | `llm_base_url` | endpoint runtime | permite dedicated endpoint |
| Entorno por proveedor | `HUGGINGFACE_MODEL` | default de modelo | aplica si falta `llm_model` |
| Entorno por proveedor | `HUGGINGFACE_API_KEY` | token default | aplica si falta `llm_api_key` |
| Entorno por proveedor | `HUGGINGFACE_BASE_URL` | endpoint default | aplica si falta `llm_base_url` |
| Entorno global | `LLM_MODEL` / `LLM_API_KEY` / `LLM_BASE_URL` | fallback transversal | último fallback antes de defaults internos |

### 2) Precedencia propuesta (algoritmo canónico)

1. Resolver proveedor desde `llm_provider` o `LLM_PROVIDER`.
2. Si proveedor = `huggingface`, tomar `model/api_key/base_url` desde request `llm_*`.
3. Completar faltantes con `HUGGINGFACE_*`.
4. Completar faltantes con `LLM_*` globales.
5. Si falta `api_key`, retornar error de configuración explícito (sin reintento).
6. Si falta `base_url`, usar default router: `https://router.huggingface.co/v1`.

### 3) Contrato runtime para `POST /nl2sql/query`

Payload mínimo recomendado:

```json
{
  "question": "Top 5 clientes por facturación",
  "llm_provider": "huggingface",
  "llm_model": "Qwen/Qwen2.5-3B-Instruct"
}
```

Payload con dedicated endpoint:

```json
{
  "question": "Top 5 clientes por facturación",
  "llm_provider": "huggingface",
  "llm_model": "Qwen/Qwen2.5-3B-Instruct",
  "llm_api_key": "***",
  "llm_base_url": "https://<tu-endpoint-dedicado>/v1"
}
```

### 4) Errores esperados (diseño)

- `provider_not_supported`: proveedor inválido/no normalizable.
- `missing_api_key`: faltan `llm_api_key`, `HUGGINGFACE_API_KEY` y `LLM_API_KEY`.
- `invalid_base_url`: URL inválida o esquema no permitido.
- `provider_http_error`: error HTTP no recuperable en router/endpoint.
- `rate_limited`: límite de cuota/rate limit (tratar como retryable según status).

> Requisito transversal: no exponer secretos (`api_key`, headers auth) en logs o errores.

### 5) Plan de pruebas por capas (hito 1)

- **Unitarias (resolución de config):** matriz request/env-provider/env-global con caso Hugging Face.
- **Unitarias (validación):** `base_url` inválida, API key ausente, provider inválido.
- **Integración liviana (gateway mock):** `llm_provider=huggingface` con respuesta normalizada.
- **Smoke dry-run:** validar wiring `serverless` vs `dedicated endpoint` sin llamada real.

### 6) Criterio de salida del Hito 1

Hito 1 se cierra cuando precedencia, contrato runtime, errores esperados y plan de pruebas queden documentados y listos para implementación del Hito 2.

## Hito 2 — Avance de implementación (actual)

Estado actual ya cubierto en código:

- Default de modelo por proveedor para Hugging Face (`Qwen/Qwen2.5-3B-Instruct`).
- Resolución por precedencia request → `HUGGINGFACE_*` → `LLM_*`.
- Validación de `base_url` y manejo de errores de configuración en API/smoke.
- Evidencia de wiring con tests de converter para:
  - `serverless` (base URL default router),
  - `dedicated endpoint` por override `llm_base_url`.

Pendiente para cierre completo de Hito 2:

1. Prueba de integración end-to-end en `POST /nl2sql/query` validando contrato completo con mocks de pipeline.

## Modelo mini/equivalente recomendado
- `Qwen/Qwen2.5-3B-Instruct`

## Endpoint de referencia
- `https://router.huggingface.co/v1/chat/completions`

## Variables de entorno
- `LLM_PROVIDER=huggingface`
- `LLM_MODEL=Qwen/Qwen2.5-3B-Instruct`
- `LLM_BASE_URL` (si aplica)
- `HUGGINGFACE_API_KEY`

## Snippets cliente (PHP 8.3, Node.js, Python, C++, C#, Java)

> Archivo generado automáticamente desde `docs/providers/catalog.json`.

### PHP 8.3
```php
$payload = ['model' => getenv('LLM_MODEL'), 'messages' => [['role'=>'user','content'=>'hola']]];
$ch = curl_init(getenv('LLM_BASE_URL') ?: 'https://router.huggingface.co/v1/chat/completions');
curl_setopt_array($ch, [CURLOPT_POST=>true, CURLOPT_RETURNTRANSFER=>true,
  CURLOPT_HTTPHEADER=>['Content-Type: application/json','Authorization: Bearer '.getenv('HUGGINGFACE_API_KEY')],
  CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
```

### Node.js (LTS actual)
```js
const r = await fetch(process.env.LLM_BASE_URL ?? 'https://router.huggingface.co/v1/chat/completions', {
  method: 'POST',
  headers: {'Content-Type':'application/json','Authorization':`Bearer ${process.env.HUGGINGFACE_API_KEY}`},
  body: JSON.stringify({model: process.env.LLM_MODEL, messages:[{role:'user', content:'hola'}]})
});
console.log(await r.text());
```

### Python (estable actual)
```python
import os, requests
resp = requests.post(
    os.getenv('LLM_BASE_URL') or 'https://router.huggingface.co/v1/chat/completions',
    headers={'Authorization': f"Bearer {os.getenv('HUGGINGFACE_API_KEY')}", 'Content-Type': 'application/json'},
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
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("HUGGINGFACE_API_KEY"));
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
    .header("Authorization", "Bearer " + System.getenv("HUGGINGFACE_API_KEY"))
    .POST(HttpRequest.BodyPublishers.ofString(json))
    .build();
var res = client.send(req, HttpResponse.BodyHandlers.ofString());
System.out.println(res.body());
```
