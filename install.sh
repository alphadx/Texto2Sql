#!/usr/bin/env bash
if [ "${CODESPACES:-}" = "true" ]; then echo "Running inside GitHub Codespaces"; fi
set -euo pipefail

INSTALL_DEMO=false
for arg in "$@"; do
  case "$arg" in
    --install-demo) INSTALL_DEMO=true ;;
    -h|--help)
      echo "Uso: ./install.sh [--install-demo]"
      exit 0
      ;;
    *)
      echo "Parámetro no soportado: $arg"
      exit 1
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "docker no está instalado."
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "No se encontró docker compose."
  exit 1
fi

ENV_EXAMPLE=".env.example"
ENV_FILE=".env"

if [[ ! -f "$ENV_EXAMPLE" ]]; then
  echo "No existe $ENV_EXAMPLE en el directorio actual."
  exit 1
fi

cp -f "$ENV_EXAMPLE" "$ENV_FILE"

rand() {
  tr -dc 'A-Za-z0-9' </dev/urandom | head -c "${1:-32}"
}

upsert_env() {
  local key="$1"
  local value="$2"
  local tmp
  tmp="$(mktemp)"
  awk -F= -v k="$key" -v v="$value" '
    BEGIN { updated=0 }
    $1==k { print k "=" v; updated=1; next }
    { print }
    END { if (!updated) print k "=" v }
  ' "$ENV_FILE" > "$tmp"
  mv "$tmp" "$ENV_FILE"
}

read -r -p "Proveedor LLM [openai]: " LLM_PROVIDER
LLM_PROVIDER="${LLM_PROVIDER:-openai}"

read -r -p "Modelo LLM [gpt-4o-mini]: " LLM_MODEL
LLM_MODEL="${LLM_MODEL:-gpt-4o-mini}"

read -r -s -p "API key LLM: " LLM_API_KEY
echo
if [[ -z "$LLM_API_KEY" ]]; then
  echo "La API key es obligatoria."
  exit 1
fi

upsert_env "LLM_PROVIDER" "$LLM_PROVIDER"
upsert_env "LLM_MODEL" "$LLM_MODEL"
upsert_env "LLM_API_KEY" "$LLM_API_KEY"

# Defaults autogenerados / estándar
upsert_env "APP_ENV" "production"
upsert_env "APP_PORT" "8000"
upsert_env "APP_SECRET" "$(rand 48)"
upsert_env "JWT_SECRET" "$(rand 48)"
upsert_env "ENCRYPTION_KEY" "$(rand 32)"
upsert_env "DB_HOST" "postgres"
upsert_env "DB_PORT" "5432"
upsert_env "DB_NAME" "texto2sql"
upsert_env "DB_USER" "texto2sql"
upsert_env "DB_PASSWORD" "$(rand 24)"
upsert_env "REDIS_HOST" "redis"
upsert_env "REDIS_PORT" "6379"
upsert_env "REDIS_PASSWORD" "$(rand 24)"

PROFILE_ARGS=()
if [[ "$INSTALL_DEMO" == "true" ]]; then
  upsert_env "DEMO_ENABLED" "true"
  PROFILE_ARGS+=(--profile demo)
else
  upsert_env "DEMO_ENABLED" "false"
fi

echo "Iniciando docker..."
"${COMPOSE[@]}" pull
"${COMPOSE[@]}" "${PROFILE_ARGS[@]}" up -d --build

echo "Listo. Entorno generado en $ENV_FILE y servicios levantados."
