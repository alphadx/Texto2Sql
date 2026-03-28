#!/usr/bin/env python3
"""Generate typed SDK/code snippets from provider catalog."""

from __future__ import annotations

import json
from pathlib import Path

LANG_FILES = {
    "python": "snippet.py",
    "node": "snippet.mjs",
    "php": "snippet.php",
    "cpp": "snippet.cpp",
    "csharp": "snippet.cs",
    "java": "snippet.java",
}


def _python(provider: dict) -> str:
    return f'''from openai import OpenAI\n\nclient = OpenAI(api_key="${{{provider["env_api_key"]}}}", base_url="{provider["base_url"]}")\nresp = client.chat.completions.create(model="{provider["mini_model"]}", messages=[{{"role":"user","content":"hola"}}])\nprint(resp.choices[0].message.content)\n'''


def _node(provider: dict) -> str:
    return f'''import OpenAI from "openai";\n\nconst client = new OpenAI({{ apiKey: process.env.{provider["env_api_key"]}, baseURL: "{provider["base_url"]}" }});\nconst resp = await client.chat.completions.create({{ model: "{provider["mini_model"]}", messages: [{{ role: "user", content: "hola" }}] }});\nconsole.log(resp.choices[0].message.content);\n'''


def _php(provider: dict) -> str:
    return f'''<?php\n$payload = ["model"=>"{provider["mini_model"]}","messages"=>[["role"=>"user","content"=>"hola"]]];\n$ch = curl_init("{provider["base_url"]}");\ncurl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_RETURNTRANSFER=>true,CURLOPT_HTTPHEADER=>["Content-Type: application/json","Authorization: Bearer ".getenv("{provider["env_api_key"]}")],CURLOPT_POSTFIELDS=>json_encode($payload)]);\necho curl_exec($ch);\n'''


def _cpp(provider: dict) -> str:
    return f'''// Provider: {provider["id"]}\n// Model: {provider["mini_model"]}\n// Endpoint: {provider["base_url"]}\n// Use libcurl with Authorization: Bearer <{provider["env_api_key"]}>\n'''


def _csharp(provider: dict) -> str:
    return f'''using System.Net.Http.Headers;\nusing System.Text;\nusing System.Text.Json;\n\nusing var http = new HttpClient();\nhttp.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", Environment.GetEnvironmentVariable("{provider["env_api_key"]}"));\nvar body = JsonSerializer.Serialize(new {{ model = "{provider["mini_model"]}", messages = new[] {{ new {{ role = "user", content = "hola" }} }} }});\nvar res = await http.PostAsync("{provider["base_url"]}", new StringContent(body, Encoding.UTF8, "application/json"));\nConsole.WriteLine(await res.Content.ReadAsStringAsync());\n'''


def _java(provider: dict) -> str:
    return f'''var client = java.net.http.HttpClient.newHttpClient();\nvar json = "{{\\\"model\\\":\\\"{provider["mini_model"]}\\\",\\\"messages\\\":[{{\\\"role\\\":\\\"user\\\",\\\"content\\\":\\\"hola\\\"}}]}}";\nvar req = java.net.http.HttpRequest.newBuilder(java.net.URI.create("{provider["base_url"]}"))\n    .header("Content-Type","application/json")\n    .header("Authorization","Bearer " + System.getenv("{provider["env_api_key"]}"))\n    .POST(java.net.http.HttpRequest.BodyPublishers.ofString(json))\n    .build();\nvar resp = client.send(req, java.net.http.HttpResponse.BodyHandlers.ofString());\nSystem.out.println(resp.body());\n'''


def run() -> int:
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads((root / "docs/providers/catalog.json").read_text())
    sdk_root = root / "docs/providers/sdk"
    sdk_root.mkdir(parents=True, exist_ok=True)

    for p in catalog.get("providers", []):
        pdir = sdk_root / p["id"]
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / LANG_FILES["python"]).write_text(_python(p))
        (pdir / LANG_FILES["node"]).write_text(_node(p))
        (pdir / LANG_FILES["php"]).write_text(_php(p))
        (pdir / LANG_FILES["cpp"]).write_text(_cpp(p))
        (pdir / LANG_FILES["csharp"]).write_text(_csharp(p))
        (pdir / LANG_FILES["java"]).write_text(_java(p))

    index = ["# SDK typed snippets (generado)", "", "> Generado desde catalog.json", ""]
    for p in catalog.get("providers", []):
        index.append(f"- `{p['id']}` -> `docs/providers/sdk/{p['id']}/`")
    (sdk_root / "README.md").write_text("\n".join(index) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
