#!/usr/bin/env bash
# Rebuild and redeploy JobPilot frontend + API Azure Container Apps.
# Requires: az login (OIDC or service principal) and a subscription that
# already contains the JobPilot API Container App.
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

if ! az account show >/dev/null 2>&1; then
  echo "Not logged in to Azure. Run az login (or azure/login in GitHub Actions)." >&2
  exit 1
fi

if [ -n "${AZURE_SUBSCRIPTION_ID:-}" ]; then
  az account set --subscription "$AZURE_SUBSCRIPTION_ID"
fi

TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"
API_HINT="${AZURE_API_APP_NAME:-ca-jobpilot-api}"
WEB_HINT="${AZURE_FRONTEND_APP_NAME:-ca-jobpilot-web}"

echo "Looking up Container Apps in subscription $(az account show --query id -o tsv)..."

API_NAME="$(az containerapp list --query "[?name=='${API_HINT}' || contains(name, 'jobpilot-api')] | [0].name" -o tsv)"
if [ -z "$API_NAME" ]; then
  echo "Could not find the JobPilot API Container App (tried ${API_HINT} / *jobpilot-api*)." >&2
  echo "Set AZURE_API_APP_NAME or deploy infra first with ./scripts/azure-up.sh" >&2
  exit 1
fi

RG="${AZURE_RESOURCE_GROUP:-}"
if [ -z "$RG" ]; then
  RG="$(az containerapp list --query "[?name=='${API_NAME}'] | [0].resourceGroup" -o tsv)"
fi

API_IMAGE="$(az containerapp show -n "$API_NAME" -g "$RG" --query "properties.template.containers[0].image" -o tsv)"
ENV_ID="$(az containerapp show -n "$API_NAME" -g "$RG" --query "properties.environmentId" -o tsv)"
ENV_NAME="$(basename "$ENV_ID")"
API_FQDN="$(az containerapp show -n "$API_NAME" -g "$RG" --query "properties.configuration.ingress.fqdn" -o tsv)"
LOCATION="$(az containerapp show -n "$API_NAME" -g "$RG" --query location -o tsv)"

ACR_NAME="${AZURE_ACR_NAME:-}"
if [ -z "$ACR_NAME" ]; then
  case "$API_IMAGE" in
    *.azurecr.io/*) ACR_NAME="${API_IMAGE%%.*}" ;;
  esac
fi
if [ -z "$ACR_NAME" ]; then
  ACR_NAME="$(az acr list --query "[?resourceGroup=='${RG}'] | [0].name" -o tsv)"
fi
if [ -z "$ACR_NAME" ]; then
  echo "Could not determine Azure Container Registry. Set AZURE_ACR_NAME." >&2
  exit 1
fi

ACR_LOGIN="$(az acr show -n "$ACR_NAME" --query loginServer -o tsv)"
WEB_NAME="$(az containerapp list -g "$RG" --query "[?name=='${WEB_HINT}' || contains(name, 'jobpilot-web')] | [0].name" -o tsv)"
if [ -z "$WEB_NAME" ]; then
  WEB_NAME="$WEB_HINT"
fi

echo "Resource group: $RG"
echo "ACR:            $ACR_LOGIN"
echo "API app:        $API_NAME"
echo "Frontend app:   $WEB_NAME"
echo "Image tag:      $TAG"

echo "Building API image in ACR..."
az acr build \
  --registry "$ACR_NAME" \
  --image "jobpilot-api:${TAG}" \
  --file Dockerfile \
  "${ROOT}/backend"

echo "Updating API Container App..."
az containerapp update \
  --name "$API_NAME" \
  --resource-group "$RG" \
  --image "${ACR_LOGIN}/jobpilot-api:${TAG}" \
  --output none

echo "Building frontend image in ACR..."
az acr build \
  --registry "$ACR_NAME" \
  --image "jobpilot-web:${TAG}" \
  --file Dockerfile \
  --build-arg NGINX_CONF=nginx.azure.conf \
  --build-arg VITE_API_URL=/api/v1 \
  "${ROOT}/frontend"

if az containerapp show --name "$WEB_NAME" --resource-group "$RG" >/dev/null 2>&1; then
  echo "Updating frontend Container App..."
  az containerapp update \
    --name "$WEB_NAME" \
    --resource-group "$RG" \
    --image "${ACR_LOGIN}/jobpilot-web:${TAG}" \
    --output none
else
  echo "Creating frontend Container App ${WEB_NAME}..."
  az containerapp create \
    --name "$WEB_NAME" \
    --resource-group "$RG" \
    --environment "$ENV_NAME" \
    --image "${ACR_LOGIN}/jobpilot-web:${TAG}" \
    --target-port 80 \
    --ingress external \
    --cpu 0.25 \
    --memory 0.5Gi \
    --min-replicas 0 \
    --max-replicas 3 \
    --registry-server "$ACR_LOGIN" \
    --output none
fi

WEB_FQDN="$(az containerapp show -n "$WEB_NAME" -g "$RG" --query "properties.configuration.ingress.fqdn" -o tsv)"
API_URI="https://${API_FQDN}"
WEB_URI="https://${WEB_FQDN}"

echo "Waiting for apps to accept traffic..."
curl -fsS --retry 8 --retry-all-errors --retry-delay 8 "${API_URI}/health"
curl -fsS --retry 8 --retry-all-errors --retry-delay 8 -o /dev/null "${WEB_URI}/"

echo
echo "Redeploy complete."
echo "  API:      ${API_URI}"
echo "  Frontend: ${WEB_URI}"
echo "  Location: ${LOCATION}"
