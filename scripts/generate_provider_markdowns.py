#!/usr/bin/env python3
"""Generate docs/providers/<provider>.md from catalog.json template."""

from __future__ import annotations

import json
from pathlib import Path


def _render(provider: dict) -> str:
    endpoint = provider["base_url"]
    api_key = provider["env_api_key"]
    provider_id = provider["id"]
    model = provider["mini_model"]
    title = provider["company"] if provider_id != "claude" else "Anthropic Claude"

    return f"""# {title}

## Modelo mini/equivalente recomendado
- `{model}`

## Endpoint de referencia
- `{endpoint}`

## Variables de entorno
- `LLM_PROVIDER={provider_id}`
- `LLM_MODEL={model}`
- `LLM_BASE_URL` (si aplica)
- `{api_key}`

## Snippets cliente (PHP 8.3, Node.js, Python, C++, C#, Java)

> Archivo generado automáticamente desde `docs/providers/catalog.json`.

### PHP 8.3
```php
$payload = ['model' => getenv('LLM_MODEL'), 'messages' => [['role'=>'user','content'=>'hola']]];
$ch = curl_init(getenv('LLM_BASE_URL') ?: '{endpoint}');
curl_setopt_array($ch, [CURLOPT_POST=>true, CURLOPT_RETURNTRANSFER=>true,
  CURLOPT_HTTPHEADER=>['Content-Type: application/json','Authorization: Bearer '.getenv('{api_key}')],
  CURLOPT_POSTFIELDS=>json_encode($payload)]);
echo curl_exec($ch);
```

### Node.js (LTS actual)
```js
const r = await fetch(process.env.LLM_BASE_URL ?? '{endpoint}', {{
  method: 'POST',
  headers: {{'Content-Type':'application/json','Authorization':`Bearer ${{process.env.{api_key}}}`}},
  body: JSON.stringify({{model: process.env.LLM_MODEL, messages:[{{role:'user', content:'hola'}}]}})
}});
console.log(await r.text());
```

### Python (estable actual)
```python
import os, requests
resp = requests.post(
    os.getenv('LLM_BASE_URL') or '{endpoint}',
    headers={{'Authorization': f"Bearer {{os.getenv('{api_key}')}}", 'Content-Type': 'application/json'}},
    json={{'model': os.getenv('LLM_MODEL'), 'messages': [{{'role': 'user', 'content': 'hola'}}]}}
)
print(resp.text)
```

### C++ (estándar actual + libcurl)
```cpp
// Compilar con libcurl. Enviar JSON con Authorization: Bearer <API_KEY>.
// Endpoint: {endpoint}
```

### C# (.NET actual)
```csharp
using var http = new HttpClient();
http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("{api_key}"));
var body = JsonSerializer.Serialize(new {{ model = Environment.GetEnvironmentVariable("LLM_MODEL"), messages = new[] {{ new {{ role = "user", content = "hola" }} }} }});
var res = await http.PostAsync(Environment.GetEnvironmentVariable("LLM_BASE_URL") ?? "{endpoint}", new StringContent(body, Encoding.UTF8, "application/json"));
Console.WriteLine(await res.Content.ReadAsStringAsync());
```

### Java (JDK actual)
```java
var client = HttpClient.newHttpClient();
var json = "{{\\\"model\\\":\\\"" + System.getenv(\"LLM_MODEL\") + \"\\\",\\\"messages\\\":[{{\\\"role\\\":\\\"user\\\",\\\"content\\\":\\\"hola\\\"}}]}}";
var req = HttpRequest.newBuilder(URI.create(System.getenv().getOrDefault("LLM_BASE_URL", "{endpoint}")))
    .header("Content-Type", "application/json")
    .header("Authorization", "Bearer " + System.getenv("{api_key}"))
    .POST(HttpRequest.BodyPublishers.ofString(json))
    .build();
var res = client.send(req, HttpResponse.BodyHandlers.ofString());
System.out.println(res.body());
```
"""


def run() -> int:
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads((root / "docs/providers/catalog.json").read_text())

    for provider in catalog.get("providers", []):
        out = root / provider["doc"]
        out.write_text(_render(provider))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
