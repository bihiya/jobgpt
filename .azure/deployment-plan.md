# Azure Deployment Plan

> **Status:** Ready for Validation

Generated: 2026-08-09

---

## 1. Project Overview

**Goal:** Deploy JobPilot AI API + Playwright workers to Azure with elastic pay-per-use billing (Container Apps Consumption + manual Jobs). Public UI is `https://jobpilot.azurewebsites.net` (Azure App Service).

**Path:** Modernize Existing

**User approval:** Explicit “yes” to add Azure Container Apps + Jobs deploy config and steps (2026-08-09).

---

## 2. Requirements

| Attribute | Value |
|-----------|-------|
| Classification | Cost-optimized production starter |
| Scale | Small |
| Budget | Cost-Optimized (scale-to-zero / pay when used) |
| **Subscription** | Selected by user at deploy (`azd auth login` / `az account set`) |
| **Location** | `eastus` default (`AZURE_LOCATION` override) |

---

## 3. Components Detected

| Component | Type | Technology | Path |
|-----------|------|------------|------|
| API | API | FastAPI / Python | `backend/` |
| Fetch/Match/Apply | Worker Jobs | One-shot `run_job` | `backend/` |
| Frontend | SPA | React/Vite | `frontend/` (Azure App Service public URL) |

---

## 4. Recipe Selection

**Selected:** AZD (Bicep)

---

## 5. Architecture

Container Apps Consumption API (min 0) + 3 manual Jobs; Atlas + Upstash; Kafka disabled; API starts Jobs via managed identity.

---

## 6. Provisioning Limit Checklist

| Resource Type | Number to Deploy | Total After Deployment | Limit/Quota | Notes |
|---------------|------------------|------------------------|-------------|-------|
| Microsoft.App/managedEnvironments | 1 | 1 + existing | 15 / region (typical) | Official docs |
| Microsoft.App/containerApps | 1 | 1 + existing | High | Official docs |
| Microsoft.App/jobs | 3 | 3 + existing | High | Official docs |
| Microsoft.ContainerRegistry/registries | 1 | 1 + existing | 100 / sub | Official docs |
| Microsoft.OperationalInsights/workspaces | 1 | 1 + existing | 5000 / sub | Official docs |
| Microsoft.Insights/components | 1 | 1 + existing | High | Official docs |
| Microsoft.KeyVault/vaults | 1 | 1 + existing | 1000 / sub | Official docs |
| Microsoft.Storage/storageAccounts | 1 | 1 + existing | 250 / region | Official docs (azd may create) |

**Status:** ✅ Within default limits for a typical subscription (CLI unavailable in agent; user should run `az quota` before first deploy).

---

## 7. Execution Checklist

### Phase 1: Planning
- [x] Analyze / requirements / architecture
- [x] User approved

### Phase 2: Execution
- [x] Generate `azure.yaml` + `infra/**`
- [x] One-shot `run_job` + `azure_jobs` trigger wiring
- [x] `docs/AZURE.md` + `scripts/azure-up.sh`
- [x] Unit tests for azure job client
- [x] **Status → Ready for Validation**

### Phase 3: Validation
- [ ] User/local: `azd provision` dry-run or `azd up` in their subscription
- [ ] Agent environment has no `az`/`azd` — full azure-validate/deploy deferred to user machine

---

## 8. Files Generated

| File | Status |
|------|--------|
| `azure.yaml` | ✅ |
| `infra/main.bicep` + modules | ✅ |
| `backend/app/workers/run_job.py` | ✅ |
| `backend/app/services/azure_jobs.py` | ✅ |
| `docs/AZURE.md` | ✅ |
| `scripts/azure-up.sh` | ✅ |

---

## 9. Next Steps

1. User follows **docs/AZURE.md**
2. `azd auth login` → set secrets → `azd up`
3. Open `SERVICE_PUBLIC_WEB_URI` (`https://jobpilot.azurewebsites.net`)
