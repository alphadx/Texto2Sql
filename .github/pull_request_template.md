## Summary
- Describe what changed.
- Include affected modules/files.

## Motivation
- Why is this change needed?

## Testing
- [ ] `make test` (or explain why not)
- [ ] `make demo-smoke-nodocker`
- [ ] `make demo-smoke` (if Docker available)

## Impacto en DEMO (obligatorio)
- [ ] ¿Afecta contrato `/nl2sql/query` consumido por `demo/app/public/chat.php`?
- [ ] ¿Afecta UX o comportamiento de `demo/app/public/index.php`?
- [ ] ¿Afecta smoke tests del demo (`scripts/demo-smoke*.sh`)?
- [ ] Evidencia adjunta (logs/comandos/checklist).

## Release checklist (Demo Compatible)
- [ ] Contrato demo↔API verificado (legacy/current + fallback).
- [ ] Errores 2xx/4xx/5xx renderizan estado claro.
- [ ] Correlation/logging del demo validados.
- [ ] Documentación actualizada si cambió comportamiento.
