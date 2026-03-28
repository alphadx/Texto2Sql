#!/usr/bin/env python3
"""Validate docs/providers/catalog.json integrity."""

from __future__ import annotations

import json
from pathlib import Path
import sys

REQUIRED_FIELDS = {"id", "company", "mini_model", "env_api_key", "base_url", "doc"}


def run() -> int:
    root = Path(__file__).resolve().parents[1]
    catalog_path = root / "docs/providers/catalog.json"
    if not catalog_path.exists():
        print(f"missing: {catalog_path}", file=sys.stderr)
        return 2

    data = json.loads(catalog_path.read_text())
    providers = data.get("providers", [])
    if not isinstance(providers, list) or not providers:
        print("catalog.providers must be a non-empty list", file=sys.stderr)
        return 3

    ids: set[str] = set()
    for provider in providers:
        missing = REQUIRED_FIELDS.difference(provider.keys())
        if missing:
            print(f"provider missing fields: {sorted(missing)} -> {provider}", file=sys.stderr)
            return 4

        pid = str(provider["id"])
        if pid in ids:
            print(f"duplicate provider id: {pid}", file=sys.stderr)
            return 5
        ids.add(pid)

        doc_file = root / str(provider["doc"])
        if not doc_file.exists():
            print(f"missing provider doc file: {doc_file}", file=sys.stderr)
            return 6

    print(json.dumps({"status": "ok", "providers": sorted(ids)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
