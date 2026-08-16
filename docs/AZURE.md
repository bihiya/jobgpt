# Deploy JobPilot to Azure (pay-per-use)

Elastic setup using **Azure Container Apps Consumption** + **manual Jobs**.

The public site uses a short Azure hostname: **`https://jobpilot.azurewebsites.net`**. API, workers, and the original Container App remain Azure-only (no Vercel).

You pay for API CPU/memory only while it handles traffic (can scale to **0**), and for worker Jobs only while fetch/match/apply are running. The public App Service is a Basic (B1) Linux plan so the hostname stays `*.azurewebsites.net`.

| Piece | Where |
|--------|--------|
| Public UI | App Service `jobpilot.azurewebsites.net` (Linux container, B1) |
| Frontend fallback | Azure Container Apps (Consumption, min 0) |
| API | Azure Container Apps (Consumption, min 0) |
| Fetch / Match / Apply | Azure Container Apps **Jobs** (start → run → stop) |
| MongoDB | [MongoDB Atlas](https://www.mongodb.com/atlas) Flex/Serverless |
| Redis | [Upstash](https://upstash.com/) Redis |
| Kafka | **Off** (`KAFKA_ENABLED=false`) — Jobs replace always-on consumers |

---

## Prerequisites

1. Azure subscription  
2. Tools on your machine:
   ```bash
   # Azure CLI
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   # Azure Developer CLI
   curl -fsSL https://aka.ms/install-azd.sh | bash
   # Docker (for local image builds during azd deploy)
   ```
3. MongoDB Atlas connection string  
4. Upstash Redis URL

---

## Deploy steps

### 1. Login

```bash
az login
az account set --subscription "<YOUR_SUBSCRIPTION_ID>"
azd auth login
```

### 2. Clone and enter the repo

```bash
git clone https://github.com/bihiya/jobgpt.git
cd jobgpt
```

### 3. Create an azd environment

```bash
azd env new prod
azd env set AZURE_LOCATION centralindia
```

### 4. Set secrets / config

```bash
# Strong random secret
azd env set SECRET_KEY "$(openssl rand -hex 32)"

# Atlas + Upstash
azd env set MONGODB_URL "mongodb+srv://USER:PASS@cluster.mongodb.net/?retryWrites=true&w=majority"
azd env set REDIS_URL "rediss://default:TOKEN@REGION.upstash.io:6379"
```

Leave `CORS_ORIGINS` empty. Provision always adds the Azure App Service origin (`https://jobpilot.azurewebsites.net`) and the Container App web origin.

### 5. Provision + deploy

```bash
# One command: infra + build image + deploy API + Jobs + public web
azd up
```

When finished, azd prints **SERVICE_PUBLIC_WEB_URI** (`https://jobpilot.azurewebsites.net`) and **SERVICE_API_URI**. Then run `./scripts/azure-redeploy.sh` so the App Service hostname exists and CORS is Azure-only.

Or use the helper:

```bash
./scripts/azure-up.sh
```

### 6. Public URL

Use **`https://jobpilot.azurewebsites.net`**. Nginx on that app proxies `/api/` and `/health` to the Azure API Container App (same-origin, no extra CORS for the SPA).

The longer Container Apps hostname still works as a fallback.

### 7. Smoke test

```bash
curl https://jobpilot.azurewebsites.net/health
curl https://<SERVICE_API_URI>/health
# open https://jobpilot.azurewebsites.net
```

In the app: connect a portal → **Run fetch**.  
Automation logs should show `automation.azure_job` (not `playwright` missing).

---

## What `azd up` creates

- Resource group `rg-jobpilot-<env>`
- Container Apps Environment (Consumption)
- API Container App (scale 0–5)
- Frontend Container App (scale 0–3)
- Public App Service `jobpilot` → `https://jobpilot.azurewebsites.net` (created/updated by `./scripts/azure-redeploy.sh` using `infra/app-service-public.bicep`)
- Jobs: `fetch`, `match`, `apply` (manual trigger)
- Azure Container Registry (Basic)
- Key Vault (secrets)
- Log Analytics + Application Insights
- **Azure Blob Storage** (`stjobpilot…`, private `uploads` container) for resumes, reports, screenshots, and apply proofs. Apps get `AZURE_STORAGE_ACCOUNT`, `AZURE_STORAGE_CONTAINER`, and `AZURE_STORAGE_CONNECTION_STRING`. Bicep also assigns **Storage Blob Data Contributor** to API + Job identities when the deploying principal can write role assignments.

Workers run:

```text
python -m app.workers.run_job
```

with `JOB_TYPE` / `JOB_USER_ID` set per execution.

---

## CI/CD (deploy on every push to `main`)

GitHub Actions workflow [`.github/workflows/azure-dev.yml`](../.github/workflows/azure-dev.yml) logs in to Azure with OIDC, finds the existing JobPilot apps, rebuilds both images in ACR, and updates **App Service + Container Apps**.

Required GitHub Actions values are already in `.github/workflows/azure-dev.yml` (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, resource names).

GitHub OIDC subjects for this repo include owner/repo numeric IDs. Create them from a **user** `az login` (Cloud Shell):

```bash
az ad app federated-credential create \
  --id b0ad929b-1053-4a68-95cf-6982b70460b9 \
  --parameters '{"name":"github-production-env-ids","issuer":"https://token.actions.githubusercontent.com","subject":"repo:bihiya@55905431/jobgpt@1324611519:environment:Production","audiences":["api://AzureADTokenExchange"]}'

az ad app federated-credential create \
  --id b0ad929b-1053-4a68-95cf-6982b70460b9 \
  --parameters '{"name":"github-main-ids","issuer":"https://token.actions.githubusercontent.com","subject":"repo:bihiya@55905431/jobgpt@1324611519:ref:refs/heads/main","audiences":["api://AzureADTokenExchange"]}'
```

Then re-run **Actions → Azure Deploy**.

---

## Day-2 commands

```bash
# Redeploy API + frontend images after code changes (also refreshes jobpilot.azurewebsites.net)
./scripts/azure-redeploy.sh

# Change extra CORS origins then re-provision (Azure web origins are always included)
azd env set CORS_ORIGINS ""
azd provision

# Manually start a fetch job (debug)
az containerapp job start \
  --name "$(azd env get-values | sed -n 's/AZURE_JOB_FETCH_NAME=//p' | tr -d '\"')" \
  --resource-group "$(azd env get-values | sed -n 's/AZURE_RESOURCE_GROUP=//p' | tr -d '\"')" \
  --env-vars JOB_USER_ID=<user-id> JOB_TYPE=fetch

# Tail API logs
az containerapp logs show \
  --name "$(azd env get-values | sed -n 's/SERVICE_API_NAME=//p' | tr -d '\"')" \
  --resource-group "$(azd env get-values | sed -n 's/AZURE_RESOURCE_GROUP=//p' | tr -d '\"')" \
  --follow

# Tear down everything in this environment
azd down --force --purge
```

---

## Cost tips

- API `minReplicas: 0` → idle ≈ $0 compute (cold start on first request).
- Jobs bill only while running (Playwright fetch/apply use ~1–2 Gi for a few minutes).
- Public App Service B1 is a small always-on cost so the hostname can be `jobpilot.azurewebsites.net`.
- Prefer Atlas + Upstash free/flex tiers for light traffic.
- Avoid Event Hubs/Kafka until you need continuous high volume.
- ACR Basic has a small fixed monthly cost; delete unused envs with `azd down`.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `PLAYWRIGHT_UNAVAILABLE` | Point the UI at the Azure API (the public App Service already proxies `/api/`) |
| Job start 403 | Wait ~1–2 min after first deploy for RBAC; re-run `azd provision` |
| Job start 400 | Check Container Apps Job logs in Azure Portal |
| Mongo/Redis errors | Confirm Atlas IP access (allow Azure / `0.0.0.0/0` for ACA) and Upstash URL |
| CORS errors | `CORS_ORIGINS` must include `https://jobpilot.azurewebsites.net` (redeploy sets this) |

---

## Architecture (short)

```text
App Service (jobpilot.azurewebsites.net)
    └── /api ──►  Container App API  ──starts──►  Job (fetch/match/apply)
                       │
                       ├── MongoDB / Cosmos
                       ├── Upstash Redis
                       └── Azure Blob (resumes, reports, screenshots)
Container App (UI fallback, long *.azurecontainerapps.io hostname)
```
