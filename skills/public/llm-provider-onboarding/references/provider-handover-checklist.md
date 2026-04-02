# Provider handover checklist

Usar esta lista para revisar una integración antes de marcarla `v1 completada`.

## Configuración

- [ ] `provider_id` y aliases definidos.
- [ ] Default `model` definido en runtime y startup.
- [ ] Default `base_url` definido (si aplica) en runtime y startup.
- [ ] Precedencia `request -> provider env -> global env -> defaults` validada.
- [ ] `base_url` inválida produce error de validación explícito.

## Wiring y errores

- [ ] Converter usa configuración resuelta correcta (provider/model/base_url).
- [ ] API `/nl2sql/query` reenvía `llm_*` a refine/sql sin pérdida.
- [ ] Errores de config regresan `400` (no `503`).
- [ ] Smoke script regresa códigos de salida consistentes para config inválida.

## Documentación

- [ ] `docs/providers/<provider>.md` actualizado (Hitos 0/1/2).
- [ ] `docs/README.md` actualizado en backlog.
- [ ] Modelo y endpoint en docs coinciden con defaults/catálogo.

## Validación mínima

- [ ] `pytest -q tests/test_llm_providers.py tests/test_llm_settings.py tests/test_llm_converter.py tests/test_app.py`
- [ ] `python scripts/validate_provider_docs.py`
- [ ] `git diff --check`
