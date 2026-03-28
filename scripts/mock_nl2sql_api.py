#!/usr/bin/env python3
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/nl2sql/query":
            self._send(404, {"detail": {"error": "not found"}})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8") if raw else "{}")
        except json.JSONDecodeError:
            self._send(422, {"detail": {"error": "json inválido"}})
            return

        question = str(payload.get("consulta_nl", "")).lower()
        if "auth" in question:
            self._send(401, {"detail": {"error": "token inválido"}})
            return
        if "legacy" in question:
            self._send(
                200,
                {
                    "columnas": ["categoria", "total"],
                    "filas": [["Action", 42]],
                    "sql_generado": "SELECT categoria, total FROM demo_legacy",
                },
            )
            return

        self._send(
            200,
            {
                "columns": ["categoria", "total"],
                "rows": [["Comedy", 10]],
                "sql": "SELECT categoria, total FROM demo_current",
            },
        )

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    host = os.getenv("MOCK_API_HOST", "127.0.0.1")
    port = int(os.getenv("MOCK_API_PORT", "5000"))
    server = HTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
