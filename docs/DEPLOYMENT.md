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

GitHub Actions (`.github/workflows/ci.yml`) runs:

1. Backend unit tests (Pytest)
2. Frontend unit tests + build
3. (Optional) Playwright E2E against compose stack

Promote images after CI green; deploy via GitOps or `kubectl set image`.
