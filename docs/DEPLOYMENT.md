# Production Deployment Guide

## Recommended topology

- Stateless FastAPI replicas (2+)
- Dedicated worker deployments per Kafka consumer group
- Managed MongoDB (Atlas) or self-hosted replica set
- Managed Kafka (MSK / Confluent) or self-hosted
- Redis for rate limits / locks
- Object storage for resumes/screenshots/reports (S3-compatible)
- Ingress / TLS termination
- Prometheus + Grafana

## Azure (production)

Public URL: **`https://jobpilot.azurewebsites.net`** (Azure App Service). API + Playwright Jobs run on Azure Container Apps. See **[docs/AZURE.md](AZURE.md)** for full steps.

## Docker Compose (single host)

```bash
cp .env.example .env
# set APP_ENV=production, strong SECRET_KEY, CORS origins
docker compose up -d --build
```

Harden:

- Do not expose MongoDB/Kafka/Redis publicly
- Put frontend behind HTTPS reverse proxy
- Rotate `SECRET_KEY` and portal credentials regularly
- Mount persistent volumes for `/tmp/jobpilot` or migrate to object storage

## Kubernetes

Manifests in `k8s/`:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
```

Scale workers independently:

```bash
kubectl -n jobpilot scale deploy jobpilot-backend --replicas=3
```

## Environment checklist

- [ ] `SECRET_KEY` from a secrets manager
- [ ] `APP_ENV=production`
- [ ] `DEBUG=false`
- [ ] MongoDB auth enabled
- [ ] Kafka ACLs / TLS
- [ ] CORS locked to production domains
- [ ] Rate limits tuned
- [ ] Playwright workers resource-limited
- [ ] Backups for MongoDB
- [ ] Alerting on `/health/ready` and worker lag

## Observability

- Health: `GET /health`, `GET /health/ready`
- Metrics: `GET /metrics` (Prometheus)
- Grafana datasource → Prometheus
- Logs: JSON structured with `request_id` / `correlation_id`

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs tests on pull requests and pushes:

1. Backend unit tests (Pytest)
2. Frontend unit tests + build
3. (Optional) Playwright E2E against compose stack

On every push to `main`, [`.github/workflows/azure-dev.yml`](../.github/workflows/azure-dev.yml) logs in to Azure (OIDC) and redeploys the public App Service plus frontend/API Container Apps via `./scripts/azure-redeploy.sh`. See **[docs/AZURE.md](AZURE.md)**.

## Vercel (optional, not production)

Production is Azure-only (`https://jobpilot.azurewebsites.net`). This monorepo can still run **two** Vercel projects for experiments (same GitHub repo):

| Project | Root Directory | Role |
|---------|----------------|------|
| Frontend (e.g. `jobgpt`) | `frontend` | Vite SPA — works in guest/demo mode without a backend |
| API (e.g. `jobai`) | `.` (repo root) | FastAPI via `backend.app.main:app` (`pyproject.toml` `[tool.vercel]`) |

### Frontend

1. New Project → Import `bihiya/jobgpt`
2. **Root Directory** = `frontend`
3. Framework preset: Vite (see `frontend/vercel.json` for SPA rewrites)
4. Optional env: `VITE_API_URL` = your API origin + `/api/v1` (omit for demo-only)

```bash
cd frontend && npx vercel --prod
```

### FastAPI (`jobai`)

Root `pyproject.toml` sets `entrypoint = "backend.app.main:app"`. Root `requirements.txt` is a slim API set (no Playwright).

Required env vars for a real API:

- `APP_ENV=production`
- `SECRET_KEY` (strong random)
- `MONGODB_URL` (Atlas SRV) + `MONGODB_DB`
- `REDIS_URL` (Upstash / Redis Cloud)
- `KAFKA_ENABLED=false` (workers do not run on Vercel)
- `CORS_ORIGINS` = your frontend `*.vercel.app` origin(s)

```bash
npx vercel --prod
```

**Limits:** Vercel serverless is not a substitute for Kafka consumers, Playwright automation, or APScheduler. Use Docker/K8s (above) for the full automation stack; keep Vercel for the UI + lightweight API.
