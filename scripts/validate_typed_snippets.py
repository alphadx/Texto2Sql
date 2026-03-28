#!/usr/bin/env python3
"""Validate generated SDK snippet files for every provider."""

from __future__ import annotations

import json
from pathlib import Path
import sys

EXPECTED = ["snippet.py", "snippet.mjs", "snippet.php", "snippet.cpp", "snippet.cs", "snippet.java"]


def run() -> int:
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads((root / "docs/providers/catalog.json").read_text())

    for p in catalog.get("providers", []):
        pdir = root / "docs/providers/sdk" / p["id"]
        if not pdir.exists():
            print(f"missing snippet dir: {pdir}", file=sys.stderr)
            return 2

        for fname in EXPECTED:
            file = pdir / fname
            if not file.exists() or file.stat().st_size == 0:
                print(f"missing/empty snippet file: {file}", file=sys.stderr)
                return 3
            content = file.read_text()
            if p["mini_model"] not in content and p["id"] not in content:
                print(f"snippet mismatch for {p['id']} in {file.name}", file=sys.stderr)
                return 4

    print('{"status":"ok"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
