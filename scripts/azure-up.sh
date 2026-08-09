#!/usr/bin/env bash
# Provision + deploy JobPilot to Azure Container Apps.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required tool: $1" >&2
    exit 1
  }
}

need az
need azd
need docker
need openssl

if ! az account show >/dev/null 2>&1; then
  echo "Not logged in. Run: az login && azd auth login"
  exit 1
fi

ENV_NAME="${AZURE_ENV_NAME:-prod}"
LOCATION="${AZURE_LOCATION:-eastus}"

if ! azd env list 2>/dev/null | grep -q "$ENV_NAME"; then
  azd env new "$ENV_NAME"
fi

azd env select "$ENV_NAME"
azd env set AZURE_LOCATION "$LOCATION"

require_env() {
  local key="$1"
  if ! azd env get-values 2>/dev/null | grep -q "^${key}="; then
    echo "Set ${key} first, e.g.: azd env set ${key} \"...\"" >&2
    exit 1
  fi
}

if ! azd env get-values 2>/dev/null | grep -q '^SECRET_KEY='; then
  azd env set SECRET_KEY "$(openssl rand -hex 32)"
  echo "Generated SECRET_KEY"
fi

require_env MONGODB_URL
require_env REDIS_URL
require_env CORS_ORIGINS

echo "Running azd up (environment=${ENV_NAME}, location=${LOCATION})..."
azd up --no-prompt

echo
echo "Done. Next:"
echo "  1) Copy SERVICE_API_URI from the output above"
echo "  2) Set Vercel VITE_API_URL=https://<SERVICE_API_URI>/api/v1"
echo "  3) See docs/AZURE.md for smoke tests and day-2 commands"
