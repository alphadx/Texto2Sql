# DeepSeek

## Estado de implementación (Hito 0: alineación)

### Decisión inicial de integración
- Se adopta **DeepSeek por vía OpenAI-compatible** como estrategia base (`/v1/chat/completions`), evitando introducir un gateway dedicado en esta fase.
- Se mantiene la puerta abierta a cliente nativo futuro solo si aparecen brechas funcionales medibles (features, latencia, costos o fiabilidad).

### Alcance del primer release (no-GA)
- Flujo NL→SQL con `llm_provider=deepseek` usando el contrato actual de `llm_*` en request.
- Resolución de configuración por precedencia: request → variables por proveedor → variables globales.
- Cobertura de modelos de chat compatibles con el payload estándar del proyecto.

### Fuera de alcance en esta fase
- Optimización específica por familia de modelos (prompts especializados por modelo).
- Soporte de capacidades no compatibles con Chat Completions estándar.
- Compromiso de alta disponibilidad multi-región de DeepSeek.

### Criterios de aceptación (Definition of Done)
1. Configuración documentada de `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `DEEPSEEK_BASE_URL` + fallback con `LLM_*`.
2. Validación de errores para API key/model/base URL inválidos o ausentes.
3. Ejemplo funcional en `POST /nl2sql/query` con `llm_provider=deepseek` y overrides `llm_*`.
4. Pruebas automatizadas de resolución de config + gateway y smoke `--dry-run`.
5. Registro de limitaciones conocidas y checklist de salida a producción.

### Riesgos y mitigaciones iniciales
- **Compatibilidad parcial de payload**: validar en smoke y fallback de parámetros opcionales.
- **Rate limits/errores transitorios**: usar política global de retries/backoff/circuit breaker.
- **Deriva documental**: mantener sincronía con `catalog.json` y validadores de docs/artefactos.

## Hito 1 — Diseño técnico detallado

### 1) Mapeo de configuración (entorno + request)

| Nivel | Campo/variable | Uso en DeepSeek | Regla |
|---|---|---|---|
| Request (prioridad máxima) | `llm_provider` | selección de proveedor | debe resolver a `deepseek` |
| Request | `llm_model` | modelo runtime | pisa cualquier default de entorno |
| Request | `llm_api_key` | credencial runtime | preferente para escenarios multi-tenant |
| Request | `llm_base_url` | endpoint runtime | permite gateway/proxy dedicado |
| Entorno por proveedor | `DEEPSEEK_MODEL` | default de modelo | se usa si no llega `llm_model` |
| Entorno por proveedor | `DEEPSEEK_API_KEY` | credencial default | se usa si no llega `llm_api_key` |
| Entorno por proveedor | `DEEPSEEK_BASE_URL` | endpoint default | se usa si no llega `llm_base_url` |
| Entorno global | `LLM_MODEL` / `LLM_API_KEY` / `LLM_BASE_URL` | fallback transversal | último fallback antes de default interno |

### 2) Precedencia propuesta (algoritmo canónico)

1. Resolver proveedor desde request (`llm_provider`) o `LLM_PROVIDER`; normalizar alias.
2. Si proveedor resuelto = `deepseek`, buscar `model/api_key/base_url` en request `llm_*`.
3. Si faltan valores, completar con `DEEPSEEK_*`.
4. Si aún faltan valores, completar con `LLM_*` globales.
5. Si falta `api_key`, retornar error de configuración explícito (no reintentar).
6. Si falta `base_url`, usar endpoint por defecto de catálogo (`https://api.deepseek.com/v1`).

### 3) Contrato runtime para `POST /nl2sql/query`

Payload mínimo recomendado para DeepSeek:

```json
{
  "question": "Top 5 clientes por facturación",
  "llm_provider": "deepseek",
  "llm_model": "deepseek-chat"
}
```

Payload con overrides completos por request:

```json
{
  "question": "Top 5 clientes por facturación",
  "llm_provider": "deepseek",
  "llm_model": "deepseek-chat",
  "llm_api_key": "***",
  "llm_base_url": "https://api.deepseek.com/v1"
}
```

### 4) Errores esperados (diseño)

- `provider_not_supported`: proveedor inválido/no normalizable.
- `missing_api_key`: no existe `llm_api_key`, `DEEPSEEK_API_KEY` ni `LLM_API_KEY`.
- `invalid_base_url`: URL malformada o esquema no permitido.
- `provider_http_error`: error HTTP no recuperable desde gateway.

> Requisito transversal: jamás exponer secretos en logs o mensajes de error.

### 5) Plan de pruebas por capas (hito 1)

- **Unitarias (resolución de config):** matriz request/env-provider/env-global y casos límite de precedencia.
- **Unitarias (validación):** proveedor inválido, API key ausente, base URL inválida.
- **Integración liviana (gateway mock):** request NL→SQL con `llm_provider=deepseek` y respuesta normalizada.
- **Smoke dry-run:** validación de wiring sin llamada real a DeepSeek.

### 6) Criterio de salida del Hito 1

Hito 1 se considera cerrado cuando la precedencia, el contrato runtime y el plan de pruebas queden documentados y trazables para implementación del Hito 2.

## Estado de cierre (DeepSeek v1)

DeepSeek queda **habilitado en v1** bajo estrategia OpenAI-compatible con:

- resolución de configuración por precedencia (request → provider env → global env),
- validación de `base_url` en runtime y startup,
- defaults de modelo por proveedor,
- y rutas de error consistentes en API/smoke para configuración inválida.

### Evidencia mínima de cierre

1. Runtime config + validación: `tests/test_llm_providers.py`.
2. Startup config + aliases: `tests/test_llm_settings.py`.
3. Mapeo de error API (`400` para config inválida): `tests/test_api_llm_errors.py`.
4. Smoke script con salida estructurada y códigos de error: `tests/test_llm_smoke_script.py`.

## Siguiente proveedor recomendado

Próximo pendiente sugerido: **Hugging Face Inference** (serverless/dedicated endpoint, autenticación y límites operativos).

## Modelo mini/equivalente recomendado
- `deepseek-chat`

## Endpoint de referencia
- `https://api.deepseek.com/v1/chat/completions`

## Variables de entorno
- `LLM_PROVIDER=deepseek`
- `LLM_MODEL=deepseek-chat`
- `LLM_BASE_URL` (si aplica)
- `DEEPSEEK_API_KEY`

## Snippets cliente (PHP 8.3, Node.js, Python, C++, C#, Java)

> Archivo generado automáticamente desde `docs/providers/catalog.json`.

### PHP 8.3
```php
$payload = ['model' => getenv('LLM_MODEL'), 'messages' => [['role'=>'user','content'=>'hola']]];
$ch = curl_init(getenv('LLM_BASE_URL') ?: 'https://api.deepseek.com/v1/chat/completions');
curl_setopt_array($ch, [CURLOPT_POST=>true, CURLOPT_RETURNTRANSFER=>true,
  CURLOPT_HTTPHEADER=>['Content-Type: application/json','Authorization: Bearer '.getenv('DEEPSEEK_API_KEY')],
  CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
```

### Node.js (LTS actual)
```js
const r = await fetch(process.env.LLM_BASE_URL ?? 'https://api.deepseek.com/v1/chat/completions', {
  method: 'POST',
  headers: {'Content-Type':'application/json','Authorization':`Bearer ${process.env.DEEPSEEK_API_KEY}`},
  body: JSON.stringify({model: process.env.LLM_MODEL, messages:[{role:'user', content:'hola'}]})
});
console.log(await r.text());
```

### Python (estable actual)
```python
import os, requests
resp = requests.post(
    os.getenv('LLM_BASE_URL') or 'https://api.deepseek.com/v1/chat/completions',
    headers={'Authorization': f"Bearer {os.getenv('DEEPSEEK_API_KEY')}", 'Content-Type': 'application/json'},
    json={'model': os.getenv('LLM_MODEL'), 'messages': [{'role': 'user', 'content': 'hola'}]}
)
print(resp.text)
```

### C++ (estándar actual + libcurl)
```cpp
// Compilar con libcurl. Enviar JSON con Authorization: Bearer <API_KEY>.
// Endpoint: https://api.deepseek.com/v1/chat/completions
```

### C# (.NET actual)
```csharp
using var http = new HttpClient();
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("DEEPSEEK_API_KEY"));
var body = JsonSerializer.Serialize(new { model = Environment.GetEnvironmentVariable("LLM_MODEL"), messages = new[] { new { role = "user", content = "hola" } } });
var res = await http.PostAsync(Environment.GetEnvironmentVariable("LLM_BASE_URL") ?? "https://api.deepseek.com/v1/chat/completions", new StringContent(body, Encoding.UTF8, "application/json"));
Console.WriteLine(await res.Content.ReadAsStringAsync());
```

### Java (JDK actual)
```java
var client = HttpClient.newHttpClient();
var json = "{\"model\":\"" + System.getenv("LLM_MODEL") + "\",\"messages\":[{\"role\":\"user\",\"content\":\"hola\"}]}";
var req = HttpRequest.newBuilder(URI.create(System.getenv().getOrDefault("LLM_BASE_URL", "https://api.deepseek.com/v1/chat/completions")))
    .header("Content-Type", "application/json")
    .header("Authorization", "Bearer " + System.getenv("DEEPSEEK_API_KEY"))
    .POST(HttpRequest.BodyPublishers.ofString(json))
    .build();
var res = client.send(req, HttpResponse.BodyHandlers.ofString());
System.out.println(res.body());
```
