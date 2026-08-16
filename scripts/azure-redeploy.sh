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
LOCATION="$(echo "$LOCATION" | tr '[:upper:]' '[:lower:]' | tr -d ' ')"

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
echo "Public app:     ${AZURE_PUBLIC_WEBAPP_NAME:-jobpilot}.azurewebsites.net"
echo "Image tag:      $TAG"

docker_cmd() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  elif sudo docker info >/dev/null 2>&1; then
    sudo docker "$@"
  else
    echo "Docker is required to build images (ACR Tasks are not available on this registry)." >&2
    exit 1
  fi
}

echo "Logging in to ACR..."
TOKEN="$(az acr login --name "$ACR_NAME" --expose-token --query accessToken -o tsv)"
echo "$TOKEN" | docker_cmd login "$ACR_LOGIN" -u 00000000-0000-0000-0000-000000000000 --password-stdin >/dev/null

echo "Building API image..."
docker_cmd build --platform linux/amd64 -t "${ACR_LOGIN}/jobpilot-api:${TAG}" "${ROOT}/backend"
docker_cmd push "${ACR_LOGIN}/jobpilot-api:${TAG}"

echo "Updating API Container App..."
az containerapp update \
  --name "$API_NAME" \
  --resource-group "$RG" \
  --image "${ACR_LOGIN}/jobpilot-api:${TAG}" \
  --output none

API_IMAGE="${ACR_LOGIN}/jobpilot-api:${TAG}"
for JOB_HINT in job-jobpilot-fetch job-jobpilot-match job-jobpilot-apply; do
  JOB_NAME="$(az containerapp job list -g "$RG" --query "[?name=='${JOB_HINT}' || contains(name, '${JOB_HINT}')] | [0].name" -o tsv)"
  if [ -z "$JOB_NAME" ]; then
    continue
  fi
  echo "Updating job ${JOB_NAME}..."
  az containerapp job update \
    --name "$JOB_NAME" \
    --resource-group "$RG" \
    --image "$API_IMAGE" \
    --output none
done

echo "Building frontend image..."
docker_cmd build --platform linux/amd64 \
  --build-arg NGINX_CONF=nginx.azure.conf \
  --build-arg VITE_API_URL=/api/v1 \
  -t "${ACR_LOGIN}/jobpilot-web:${TAG}" \
  "${ROOT}/frontend"
docker_cmd push "${ACR_LOGIN}/jobpilot-web:${TAG}"

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
PUBLIC_APP="${AZURE_PUBLIC_WEBAPP_NAME:-jobpilot}"
PUBLIC_URI=""

sync_public_webapp() {
  local image="${ACR_LOGIN}/jobpilot-web:${TAG}"
  if ! az webapp show --name "$PUBLIC_APP" --resource-group "$RG" >/dev/null 2>&1; then
    echo "Creating public App Service ${PUBLIC_APP} (https://${PUBLIC_APP}.azurewebsites.net)..."
    az deployment group create \
      --resource-group "$RG" \
      --name jobpilot-public-hostname \
      --template-file "${ROOT}/infra/app-service-public.bicep" \
      --parameters \
        location="$LOCATION" \
        webAppName="$PUBLIC_APP" \
        acrName="$ACR_NAME" \
        containerImage="$image" \
        assignAcrPull=false \
      --output none
  fi

  echo "Updating public App Service image..."
  ACR_USER="$(az acr credential show --name "$ACR_NAME" --query username -o tsv)"
  ACR_PASS="$(az acr credential show --name "$ACR_NAME" --query passwords[0].value -o tsv)"
  az webapp config container set \
    --name "$PUBLIC_APP" \
    --resource-group "$RG" \
    --container-image-name "$image" \
    --container-registry-url "https://${ACR_LOGIN}" \
    --container-registry-user "$ACR_USER" \
    --container-registry-password "$ACR_PASS" \
    --enable-app-service-storage false \
    --output none
  az webapp config appsettings set \
    --name "$PUBLIC_APP" \
    --resource-group "$RG" \
    --settings WEBSITES_PORT=80 WEBSITES_ENABLE_APP_SERVICE_STORAGE=false \
    --output none
  PUBLIC_URI="https://$(az webapp show --name "$PUBLIC_APP" --resource-group "$RG" --query defaultHostName -o tsv)"
}

if az webapp show --name "$PUBLIC_APP" --resource-group "$RG" >/dev/null 2>&1 \
  || [ -f "${ROOT}/infra/app-service-public.bicep" ]; then
  sync_public_webapp
fi

if [ -n "$PUBLIC_URI" ]; then
  CORS_ORIGINS="${PUBLIC_URI},${WEB_URI}"
  echo "Setting API CORS to Azure origins only: ${CORS_ORIGINS}"
  az containerapp update \
    --name "$API_NAME" \
    --resource-group "$RG" \
    --set-env-vars "CORS_ORIGINS=${CORS_ORIGINS}" \
    --output none
fi

echo "Waiting for apps to accept traffic..."
curl -fsS --retry 8 --retry-all-errors --retry-delay 8 "${API_URI}/health"
curl -fsS --retry 8 --retry-all-errors --retry-delay 8 -o /dev/null "${WEB_URI}/"
if [ -n "$PUBLIC_URI" ]; then
  curl -fsS --retry 12 --retry-all-errors --retry-delay 10 -o /dev/null "${PUBLIC_URI}/"
fi

echo
echo "Redeploy complete."
echo "  App:      ${PUBLIC_URI:-$WEB_URI}"
echo "  API:      ${API_URI}"
echo "  ACA web:  ${WEB_URI}"
echo "  Location: ${LOCATION}"

