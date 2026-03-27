#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="$(dirname "$0")/.env"

echo "Configuración de demo Texto2SQL"
read -rp "Compañía/API provider (ej: openai, anthropic, azure-openai): " API_PROVIDER
read -rp "API key: " API_KEY
read -rp "Modelo (ej: gpt-4.1-mini): " API_MODEL
read -rp "URL API NL2SQL [http://host.docker.internal:5000/nl2sql/query]: " API_URL
API_URL=${API_URL:-http://host.docker.internal:5000/nl2sql/query}
read -rp "TTL historial en minutos [360]: " CHAT_TTL
CHAT_TTL=${CHAT_TTL:-360}

cat > "$ENV_FILE" <<ENVVARS
NL2SQL_API_PROVIDER=${API_PROVIDER}
NL2SQL_API_KEY=${API_KEY}
NL2SQL_MODEL=${API_MODEL}
NL2SQL_API_URL=${API_URL}
CHAT_CACHE_TTL_MINUTES=${CHAT_TTL}
MYSQL_DEMO_USER=demo
MYSQL_DEMO_PASSWORD=demo1234
MYSQL_DEMO_DB=sakila
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
ENVVARS

echo "Archivo generado: $ENV_FILE"
