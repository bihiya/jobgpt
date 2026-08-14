#!/usr/bin/env bash
# Create a GitHub Actions OIDC identity (app registration + federated
# credentials) that can redeploy JobPilot Container Apps. Prints the
# client/tenant/subscription IDs for GitHub Actions.
set -euo pipefail

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required tool: $1" >&2
    exit 1
  }
}

need az

if ! az account show >/dev/null 2>&1; then
  echo "Not logged in to Azure." >&2
  exit 1
fi

SUB_ID="$(az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"
REPO="${GITHUB_REPOSITORY:-bihiya/jobgpt}"
APP_NAME="${OIDC_APP_NAME:-jobgpt-github-actions}"

API_NAME="$(az containerapp list --query "[?name=='ca-jobpilot-api' || contains(name, 'jobpilot-api')] | [0].name" -o tsv)"
if [ -z "$API_NAME" ]; then
  echo "Could not find JobPilot API Container App in this subscription." >&2
  exit 1
fi
RG="$(az containerapp list --query "[?name=='${API_NAME}'] | [0].resourceGroup" -o tsv)"
SCOPE="$(az group show -n "$RG" --query id -o tsv)"

echo "Ensuring app registration ${APP_NAME}..."
APP_ID="$(az ad app list --display-name "$APP_NAME" --query "[0].appId" -o tsv)"
if [ -z "$APP_ID" ]; then
  APP_ID="$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)"
fi

SP_ID="$(az ad sp list --filter "appId eq '${APP_ID}'" --query "[0].id" -o tsv)"
if [ -z "$SP_ID" ]; then
  az ad sp create --id "$APP_ID" --output none
  SP_ID="$(az ad sp list --filter "appId eq '${APP_ID}'" --query "[0].id" -o tsv)"
fi

create_fed() {
  local name="$1"
  local subject="$2"
  if az ad app federated-credential list --id "$APP_ID" --query "[?name=='${name}'] | [0].name" -o tsv | grep -q .; then
    echo "Federated credential ${name} already exists"
    return
  fi
  local params
  params="$(mktemp)"
  cat >"$params" <<EOF
{
  "name": "${name}",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "${subject}",
  "audiences": ["api://AzureADTokenExchange"],
  "description": "GitHub Actions ${name}"
}
EOF
  az ad app federated-credential create --id "$APP_ID" --parameters @"$params" --output none
  rm -f "$params"
  echo "Created federated credential ${name}"
}

create_fed "github-main" "repo:${REPO}:ref:refs/heads/main"
create_fed "github-production-env" "repo:${REPO}:environment:Production"

echo "Assigning Contributor on ${RG}..."
az role assignment create \
  --assignee "$APP_ID" \
  --role Contributor \
  --scope "$SCOPE" \
  --output none 2>/dev/null || true

ACR_ID="$(az acr list --query "[?resourceGroup=='${RG}'] | [0].id" -o tsv)"
if [ -n "$ACR_ID" ]; then
  az role assignment create \
    --assignee "$APP_ID" \
    --role AcrPush \
    --scope "$ACR_ID" \
    --output none 2>/dev/null || true
fi

echo
echo "OIDC identity is ready. GitHub Actions needs:"
echo "  AZURE_CLIENT_ID=${APP_ID}"
echo "  AZURE_TENANT_ID=${TENANT_ID}"
echo "  AZURE_SUBSCRIPTION_ID=${SUB_ID}"
echo "  AZURE_RESOURCE_GROUP=${RG}"
