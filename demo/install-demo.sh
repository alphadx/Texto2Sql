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
echo "Nota: proveedor/modelo/api key LLM se configuran en la instalación principal o se envían por request."

API_URL=$(prompt_default "URL API NL2SQL" "http://host.docker.internal:5000/nl2sql/query")
API_BEARER=$(prompt_default "Bearer token para la API (si aplica)" "")
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
NL2SQL_API_URL=${API_URL}
NL2SQL_API_KEY=${API_BEARER}
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
