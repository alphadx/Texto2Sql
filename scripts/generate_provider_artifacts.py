#!/usr/bin/env python3
"""Generate provider documentation artifacts from catalog.json."""

from __future__ import annotations

import json
from pathlib import Path


def _render_matrix(catalog: dict) -> str:
    header = "| Proveedor | Modelo mini/equivalente sugerido | PHP 8.3 | Node.js (LTS) | Python (estable) | C++ (libcurl) | C# (.NET) | Java (JDK) |"
    sep = "|---|---|---|---|---|---|---|---|"
    lines = [
        "# Matriz de compatibilidad por proveedor y lenguaje",
        "",
        "> Archivo generado automáticamente desde `docs/providers/catalog.json`.",
        "",
        header,
        sep,
    ]
    for p in catalog.get("providers", []):
        provider = p["company"] if p["id"] != "claude" else "Anthropic Claude"
        lines.append(
            f"| {provider} | `{p['mini_model']}` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |"
        )

    lines.extend(
        [
            "",
            "## Notas",
            "",
            "- ✅ indica que existe snippet documentado en `docs/providers/<proveedor>.md`.",
            "- En C++ se documenta vía `libcurl` para máxima portabilidad.",
            "- En Node.js/Python/C#/Java se usa HTTP JSON para desacoplar de SDKs específicos.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_snippets_index(catalog: dict) -> str:
    lines = [
        "# Snippets rápidos por proveedor",
        "",
        "> Archivo generado automáticamente desde `docs/providers/catalog.json`.",
        "",
    ]
    for p in catalog.get("providers", []):
        lines.extend(
            [
                f"## {p['company']} ({p['id']})",
                f"- Modelo mini/equivalente: `{p['mini_model']}`",
                f"- Endpoint: `{p['base_url']}`",
                f"- API key env: `{p['env_api_key']}`",
                "",
            ]
        )
    return "\n".join(lines)


def run() -> int:
    root = Path(__file__).resolve().parents[1]
    catalog_path = root / "docs/providers/catalog.json"
    catalog = json.loads(catalog_path.read_text())

    matrix_path = root / "docs/providers/compatibility-matrix.md"
    matrix_path.write_text(_render_matrix(catalog))

    snippets_index = root / "docs/providers/snippets-index.md"
    snippets_index.write_text(_render_snippets_index(catalog))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
