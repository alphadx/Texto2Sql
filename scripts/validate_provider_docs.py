#!/usr/bin/env python3
"""Validate consistency between provider catalog and markdown docs."""

from __future__ import annotations

import json
from pathlib import Path
import sys


def run() -> int:
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads((root / "docs/providers/catalog.json").read_text())

    for provider in catalog.get("providers", []):
        doc = root / provider["doc"]
        if not doc.exists():
            print(f"missing doc: {doc}", file=sys.stderr)
            return 2

        content = doc.read_text()
        required_tokens = [
            provider["mini_model"],
            provider["env_api_key"],
            provider["base_url"],
            f"LLM_PROVIDER={provider['id']}",
        ]
        for token in required_tokens:
            if token not in content:
                print(f"doc mismatch for {provider['id']}: missing token {token!r}", file=sys.stderr)
                return 3

    print('{"status":"ok"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
