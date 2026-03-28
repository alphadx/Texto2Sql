#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="demo/docker-compose.yml"
ENV_FILE="demo/.env"
BACKUP_ENV="demo/.env.bak.smoke"

cleanup() {
  docker compose -f "$COMPOSE_FILE" down -v || true
  if [[ -f "$BACKUP_ENV" ]]; then
    mv "$BACKUP_ENV" "$ENV_FILE"
  else
    rm -f "$ENV_FILE"
  fi
}
trap cleanup EXIT

if [[ -f "$ENV_FILE" ]]; then
  cp "$ENV_FILE" "$BACKUP_ENV"
fi

cp demo/.env.example "$ENV_FILE"

# Asegura valor explícito para endpoint aunque no se use en este smoke.
if ! grep -q '^NL2SQL_API_URL=' "$ENV_FILE"; then
  echo 'NL2SQL_API_URL=http://host.docker.internal:5000/nl2sql/query' >> "$ENV_FILE"
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

  if docker compose -f "$COMPOSE_FILE" exec -T texto2sql-demo mysql -udemo -pdemo1234 -Nse "SELECT 1" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! docker compose -f "$COMPOSE_FILE" exec -T texto2sql-demo mysql -udemo -pdemo1234 -Nse "SELECT 1" >/dev/null 2>&1; then
  echo "[demo-smoke] mysql did not become ready in time" >&2
  docker compose -f "$COMPOSE_FILE" logs texto2sql-demo || true
  exit 1
fi

echo "[demo-smoke] verifying sakila dataset..."
FILM_COUNT=$(docker compose -f "$COMPOSE_FILE" exec -T texto2sql-demo mysql -udemo -pdemo1234 -Nse "SELECT COUNT(*) FROM sakila.film;")
if [[ -z "$FILM_COUNT" || "$FILM_COUNT" -le 0 ]]; then
  echo "[demo-smoke] invalid sakila.film count: ${FILM_COUNT:-empty}" >&2
  exit 1
fi

echo "[demo-smoke] OK: sakila.film rows = $FILM_COUNT"
