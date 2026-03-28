#!/usr/bin/env bash
set -euo pipefail

MOCK_PID=""
PHP_PID=""

cleanup() {
  if [[ -n "$PHP_PID" ]]; then
    kill "$PHP_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "$MOCK_PID" ]]; then
    kill "$MOCK_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

assert_json_expr() {
  local json_input="$1"
  local expr="$2"
  local message="$3"
  python - <<'PY' "$json_input" "$expr" "$message"
import json
import sys

payload = json.loads(sys.argv[1])
expr = sys.argv[2]
message = sys.argv[3]

safe = {"payload": payload, "isinstance": isinstance, "list": list, "dict": dict, "len": len}
if not eval(expr, {"__builtins__": {}}, safe):
    raise SystemExit(f"[demo-smoke-nodocker] assertion failed: {message}")
PY
}

wait_http_ok() {
  local url="$1"
  for _ in {1..120}; do
    if curl -s -o /dev/null "$url"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

echo "[demo-smoke-nodocker] starting mock API..."
python scripts/mock_nl2sql_api.py &
MOCK_PID=$!

echo "[demo-smoke-nodocker] starting php built-in server..."
php -S 127.0.0.1:8081 -t demo/app/public >/tmp/demo-smoke-php.log 2>&1 &
PHP_PID=$!

if ! wait_http_ok "http://127.0.0.1:8081/chat.php?session_id=nodocker-get"; then
  echo "[demo-smoke-nodocker] php chat endpoint not reachable" >&2
  cat /tmp/demo-smoke-php.log >&2 || true
  exit 1
fi

GET_JSON=$(curl -sS "http://127.0.0.1:8081/chat.php?session_id=nodocker-get")
assert_json_expr "$GET_JSON" "payload.get('session_id') == 'nodocker-get'" "session_id correcto"
assert_json_expr "$GET_JSON" "isinstance(payload.get('history'), list)" "history lista"

POST_JSON=$(curl -sS -X POST "http://127.0.0.1:8081/chat.php" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"nodocker-post","message":"consulta legacy","params":{"api_url":"http://127.0.0.1:5000/nl2sql/query","db_engine":"mysql"}}')

assert_json_expr "$POST_JSON" "payload.get('ok') is True" "ok=true"
assert_json_expr "$POST_JSON" "payload['history'][-1]['result'].get('columnas')" "hay columnas"
assert_json_expr "$POST_JSON" "payload['history'][-1]['result'].get('filas')" "hay filas"

echo "[demo-smoke-nodocker] all checks passed"
