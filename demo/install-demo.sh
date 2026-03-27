#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="$(dirname "$0")/.env"

prompt_default() {
  local prompt="$1"
  local default="$2"
  local value
  read -rp "$prompt [$default]: " value
  echo "${value:-$default}"
}

echo "Configuración de demo Texto2SQL"

API_PROVIDER=$(prompt_default "Compañía/API provider (ej: openai, anthropic, azure-openai)" "openai")

read -rsp "API key (obligatoria): " API_KEY
echo
if [[ -z "${API_KEY}" ]]; then
  echo "ERROR: La API key no puede quedar vacía." >&2
  exit 1
fi

API_MODEL=$(prompt_default "Modelo (ej: gpt-4.1-mini)" "gpt-4.1-mini")
API_URL=$(prompt_default "URL API NL2SQL" "http://host.docker.internal:5000/nl2sql/query")
CHAT_TTL=$(prompt_default "TTL historial en minutos" "360")

if ! [[ "$CHAT_TTL" =~ ^[0-9]+$ ]] || [[ "$CHAT_TTL" -le 0 ]]; then
  echo "ERROR: CHAT_CACHE_TTL_MINUTES debe ser un entero positivo." >&2
  exit 1
fi

DB_HOST=$(prompt_default "Host DB para el payload enviado a la API" "127.0.0.1")
DB_PORT=$(prompt_default "Puerto DB para el payload enviado a la API" "3306")
DB_NAME=$(prompt_default "Nombre DB" "sakila")
DB_USER=$(prompt_default "Usuario DB" "demo")
read -rsp "Password DB [demo1234]: " DB_PASS
echo
DB_PASS=${DB_PASS:-demo1234}

cat > "$ENV_FILE" <<ENVVARS
NL2SQL_API_PROVIDER=${API_PROVIDER}
NL2SQL_API_KEY=${API_KEY}
NL2SQL_MODEL=${API_MODEL}
NL2SQL_API_URL=${API_URL}
CHAT_CACHE_TTL_MINUTES=${CHAT_TTL}
CHAT_MAX_MESSAGES=40
MYSQL_DEMO_USER=${DB_USER}
MYSQL_DEMO_PASSWORD=${DB_PASS}
MYSQL_DEMO_DB=${DB_NAME}
MYSQL_HOST=${DB_HOST}
MYSQL_PORT=${DB_PORT}
ENVVARS

echo "Archivo generado: $ENV_FILE"
echo "Siguiente paso: make demo-up"
