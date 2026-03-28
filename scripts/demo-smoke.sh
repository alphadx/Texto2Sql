#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="demo/docker-compose.yml"
ENV_FILE="demo/.env"
BACKUP_ENV="demo/.env.bak.smoke"
MYSQL_USER="demo"
MYSQL_PASSWORD="demo1234"
MYSQL_HOST="127.0.0.1"
MOCK_PID=""

cleanup() {
  docker compose -f "$COMPOSE_FILE" down -v || true
  if [[ -n "$MOCK_PID" ]]; then
    kill "$MOCK_PID" >/dev/null 2>&1 || true
  fi
  if [[ -f "$BACKUP_ENV" ]]; then
    mv "$BACKUP_ENV" "$ENV_FILE"
  else
    rm -f "$ENV_FILE"
  fi
}
trap cleanup EXIT

mysql_exec() {
  local query="$1"
  docker compose -f "$COMPOSE_FILE" exec -T texto2sql-demo \
    env MYSQL_PWD="$MYSQL_PASSWORD" \
    mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -sN -e "$query"
}

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
    raise SystemExit(f"[demo-smoke] assertion failed: {message}")
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

if [[ -f "$ENV_FILE" ]]; then
  cp "$ENV_FILE" "$BACKUP_ENV"
fi

cp demo/.env.example "$ENV_FILE"

# Forzar API mock local para hacer smoke reproducible sin llaves LLM.
if grep -q '^NL2SQL_API_URL=' "$ENV_FILE"; then
  sed -i 's|^NL2SQL_API_URL=.*$|NL2SQL_API_URL=http://host.docker.internal:5000/nl2sql/query|' "$ENV_FILE"
else
  echo 'NL2SQL_API_URL=http://host.docker.internal:5000/nl2sql/query' >> "$ENV_FILE"
fi

echo "[demo-smoke] starting mock /nl2sql/query API on 0.0.0.0:5000..."
MOCK_API_HOST=0.0.0.0 MOCK_API_PORT=5000 python scripts/mock_nl2sql_api.py &
MOCK_PID=$!

sleep 1
if ! kill -0 "$MOCK_PID" >/dev/null 2>&1; then
  echo "[demo-smoke] mock api failed to start" >&2
  exit 1
fi

echo "[demo-smoke] building and starting demo container..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo "[demo-smoke] waiting for mysql to become ready..."
for _ in {1..240}; do
  CID=$(docker compose -f "$COMPOSE_FILE" ps -q texto2sql-demo)
  if [[ -z "$CID" ]]; then
    sleep 2
    continue
  fi

  STATUS=$(docker inspect -f "{{.State.Status}}" "$CID" 2>/dev/null || true)
  if [[ "$STATUS" == "exited" || "$STATUS" == "dead" ]]; then
    echo "[demo-smoke] container exited before mysql became ready" >&2
    docker compose -f "$COMPOSE_FILE" logs texto2sql-demo || true
    exit 1
  fi

  if mysql_exec "SELECT 1" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! mysql_exec "SELECT 1" >/dev/null 2>&1; then
  echo "[demo-smoke] mysql did not become ready in time" >&2
  docker compose -f "$COMPOSE_FILE" logs texto2sql-demo || true
  exit 1
fi

echo "[demo-smoke] verifying sakila dataset..."
FILM_COUNT=""
for _ in {1..120}; do
  FILM_COUNT=$(mysql_exec "SELECT COUNT(*) FROM sakila.film;" 2>/dev/null || true)
  if [[ "$FILM_COUNT" =~ ^[0-9]+$ ]]; then
    break
  fi
  sleep 2
done

if [[ ! "$FILM_COUNT" =~ ^[0-9]+$ || "$FILM_COUNT" -le 0 ]]; then
  echo "[demo-smoke] invalid sakila.film count: ${FILM_COUNT:-empty}" >&2
  docker compose -f "$COMPOSE_FILE" logs texto2sql-demo || true
  exit 1
fi

echo "[demo-smoke] OK: sakila.film rows = $FILM_COUNT"

echo "[demo-smoke] waiting for chat.php endpoint..."
if ! wait_http_ok "http://localhost:8080/chat.php?session_id=smoke-get"; then
  echo "[demo-smoke] chat.php GET endpoint not reachable" >&2
  docker compose -f "$COMPOSE_FILE" logs texto2sql-demo || true
  exit 1
fi

GET_JSON=$(curl -sS "http://localhost:8080/chat.php?session_id=smoke-get")
assert_json_expr "$GET_JSON" "payload.get('session_id') == 'smoke-get'" "session_id en GET"
assert_json_expr "$GET_JSON" "isinstance(payload.get('history'), list)" "history lista en GET"

echo "[demo-smoke] validating chat.php POST (mock API current contract)..."
POST_CURRENT=$(curl -sS -X POST "http://localhost:8080/chat.php" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"smoke-post-current","message":"consulta current","params":{"api_url":"http://host.docker.internal:5000/nl2sql/query","db_engine":"mysql"}}')

assert_json_expr "$POST_CURRENT" "payload.get('ok') is True" "ok=true en POST current"
assert_json_expr "$POST_CURRENT" "len(payload.get('history', [])) >= 2" "history contiene user+assistant"
assert_json_expr "$POST_CURRENT" "payload['history'][-1]['result'].get('error') in (None, '')" "POST current sin error"
assert_json_expr "$POST_CURRENT" "payload['history'][-1]['result'].get('filas')" "POST current con filas"

echo "[demo-smoke] validating chat.php POST (mock API legacy contract)..."
POST_LEGACY=$(curl -sS -X POST "http://localhost:8080/chat.php" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"smoke-post-legacy","message":"consulta legacy","params":{"api_url":"http://host.docker.internal:5000/nl2sql/query","db_engine":"mysql"}}')

assert_json_expr "$POST_LEGACY" "payload.get('ok') is True" "ok=true en POST legacy"
assert_json_expr "$POST_LEGACY" "payload['history'][-1]['result'].get('sql_generado') not in (None, '')" "POST legacy con sql_generado"
assert_json_expr "$POST_LEGACY" "payload['history'][-1]['result'].get('columnas')" "POST legacy con columnas"

echo "[demo-smoke] all checks passed"
