# Matriz de compatibilidad por proveedor y lenguaje

> Archivo generado automáticamente desde `docs/providers/catalog.json`.

| Proveedor | Modelo mini/equivalente sugerido | PHP 8.3 | Node.js (LTS) | Python (estable) | C++ (libcurl) | C# (.NET) | Java (JDK) |
|---|---|---|---|---|---|---|---|
| OpenAI | `gpt-4.1-mini` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DeepSeek | `deepseek-chat` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hugging Face | `Qwen/Qwen2.5-3B-Instruct` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Google | `gemini-2.0-flash-lite` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mistral | `mistral-small-latest` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Anthropic Claude | `claude-3-5-haiku-latest` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Alibaba Cloud | `qwen-plus` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Moonshot AI | `kimi-k2` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Meta | `meta-llama/Llama-3.1-8B-Instruct` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| GitHub | `gpt-4.1-mini` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| iFlytek | `generalv3.5` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ByteDance | `doubao-pro-32k` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Zhipu AI | `glm-4-flash` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| MiniMax | `MiniMax-Text-01` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Huawei | `pangu-pro` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| xAI | `grok-2-latest` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## Notas

- ✅ indica que existe snippet documentado en `docs/providers/<proveedor>.md`.
- En C++ se documenta vía `libcurl` para máxima portabilidad.
- En Node.js/Python/C#/Java se usa HTTP JSON para desacoplar de SDKs específicos.
