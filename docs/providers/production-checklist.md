# Checklist de producción por compañía

## Checklist base (aplica a todos)

- [ ] Definir `LLM_PROVIDER`, `LLM_MODEL` y API key correspondiente.
- [ ] Configurar `LLM_MAX_RETRIES`, `LLM_HTTP_TIMEOUT_SECONDS` y circuit breaker.
- [ ] Ejecutar `make llm-smoke-dry` y revisar salida JSON.
- [ ] Confirmar política de costos/cuotas del proveedor.
- [ ] Confirmar política de retención de datos y cumplimiento.
- [ ] Configurar monitoreo de errores `llm_provider_error_*` y `llm_circuit_open_*`.

## DeepSeek
- [ ] `DEEPSEEK_API_KEY` cargada.
- [ ] Endpoint/base URL validado para región.
- [ ] Modelo `deepseek-chat` aprobado por negocio.

## Hugging Face
- [ ] `HUGGINGFACE_API_KEY` cargada.
- [ ] Modelo small elegido según latencia/costo.
- [ ] SLA del endpoint (serverless/dedicated) validado.

## Gemini
- [ ] `GEMINI_API_KEY` cargada.
- [ ] Modelo `gemini-2.0-flash-lite` validado.
- [ ] Límites por proyecto y cuotas configurados.

## Mistral
- [ ] `MISTRAL_API_KEY` cargada.
- [ ] `mistral-small-latest` validado en QA.
- [ ] Política de rate limits revisada.

## Claude (Anthropic)
- [ ] `ANTHROPIC_API_KEY` cargada.
- [ ] `claude-3-5-haiku-latest` validado en QA.
- [ ] Estrategia de fallback definida ante degradación.

## Llama (hosted)
- [ ] `LLAMA_API_KEY` cargada.
- [ ] Endpoint hosted validado (HF u otro gateway compatible).
- [ ] Control de versión de modelo documentado.

## Copilot / Models
- [ ] `COPILOT_API_KEY` cargada.
- [ ] Endpoint enterprise validado.
- [ ] Modelo mini de referencia aprobado por seguridad.
