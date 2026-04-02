#!/usr/bin/env python3
"""Smoke checker for LLM providers.

Modes:
- dry-run: validates provider/config resolution + gateway selection without network calls
- live: sends one test message (requires API key + connectivity)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Evita fallar por validación de auth al importar el paquete `app` en ejecución standalone.
os.environ.setdefault("AUTH_REQUIRED", "false")
os.environ.setdefault("AUTH_JWT_SECRET", "smoke-script-placeholder-secret-32chars")

from app.llm.providers import get_gateway, resolve_runtime_config


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LLM provider smoke checker")
    parser.add_argument("--provider", required=True, help="Provider name (openai/deepseek/mistral/...) ")
    parser.add_argument("--model", default="", help="Model override")
    parser.add_argument("--base-url", default="", help="Base URL override")
    parser.add_argument("--api-key", default="", help="API key override")
    parser.add_argument("--dry-run", action="store_true", help="Only validate config and gateway wiring")
    parser.add_argument("--prompt", default="Devuelve OK", help="Prompt used in live mode")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    llm_options = {
        "provider": args.provider,
        "model": args.model or None,
        "base_url": args.base_url or None,
        "api_key": args.api_key or None,
    }

    try:
        config = resolve_runtime_config(llm_options)
        gateway = get_gateway(config.provider)
    except (ValueError, RuntimeError) as exc:
        payload = {
            "status": "error",
            "mode": "dry-run" if args.dry_run else "live",
            "provider": args.provider,
            "error": str(exc),
        }
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return 2

    if args.dry_run:
        payload = {
            "status": "ok",
            "mode": "dry-run",
            "provider": config.provider,
            "model": config.model,
            "base_url": config.base_url,
            "gateway": gateway.__class__.__name__,
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    if not config.api_key:
        print("error: missing API key (set --api-key or env vars)", file=sys.stderr)
        return 2

    messages = [{"role": "user", "content": args.prompt}]
    result = gateway.complete(config, messages)
    payload = {
        "status": "ok",
        "mode": "live",
        "provider": config.provider,
        "model": config.model,
        "gateway": result.gateway,
        "attempts": result.attempts,
        "text": result.text,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
