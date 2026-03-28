#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=".env"

prompt_default() {
  local prompt="$1"
  local default="$2"
  local value
  read -rp "$prompt [$default]: " value
  echo "${value:-$default}"
}

echo "Configuración principal de Texto2SQL"

LLM_PROVIDER=$(prompt_default "Compañía/proveedor LLM oficial" "openai")
read -rsp "API key oficial del proveedor LLM: " LLM_API_KEY
echo
if [[ -z "${LLM_API_KEY}" ]]; then
  echo "ERROR: la API key LLM es obligatoria." >&2
  exit 1
fi

LLM_MODEL=$(prompt_default "Modelo LLM oficial" "gpt-4.1-mini")
LLM_BASE_URL=$(prompt_default "Base URL del proveedor (vacío = default SDK)" "")

if [[ -f "$ENV_FILE" ]]; then
  cp "$ENV_FILE" "${ENV_FILE}.bak"
fi

cat > "$ENV_FILE" <<ENVVARS
LLM_PROVIDER=${LLM_PROVIDER}
OPENAI_API_KEY=${LLM_API_KEY}
OPENAI_MODEL=${LLM_MODEL}
OPENAI_BASE_URL=${LLM_BASE_URL}
ENVVARS

echo "Configuración principal guardada en $ENV_FILE"
echo "También puedes sobreescribir por request en POST /nl2sql/query usando llm_provider, llm_model, llm_api_key y llm_base_url."
