# JobPilot AI

Production-ready full-stack AI-powered Job Automation Platform.

Configure your resume, preferences, companies, and job portals once. JobPilot continuously scans portals, scores matches, applies with Playwright automation, and delivers analytics.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for Mermaid diagrams covering:

- Clean Architecture layers
- Authentication flow
- Kafka event pipeline
- Playwright automation sequence

Additional docs:

| Doc | Description |
|-----|-------------|
| [docs/DATABASE.md](docs/DATABASE.md) | MongoDB collections & indexes |
| [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md) | REST API contracts |
| [docs/REDUX_TOOLKIT.md](docs/REDUX_TOOLKIT.md) | Redux Toolkit (JS) setup |
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | Local setup |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production / K8s guide |

## Tech Stack

**Frontend:** React 19, TypeScript, Vite, MUI v7, React Router v7, TanStack Query, Redux Toolkit (JS), Axios, RHF + Zod, MUI DataGrid, Recharts, Dayjs

**Backend:** FastAPI, Python 3.13, Pydantic v2, Motor, Beanie, JWT + Refresh, APScheduler, Kafka, Playwright

**Infra:** Docker Compose, MongoDB, Redis, Kafka/Zookeeper, Prometheus, Grafana, GitHub Actions

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

## Project Structure

```
backend/app/
  api/v1/          # REST routers
  core/            # config, security, logging, kafka, middleware
  models/          # Beanie documents
  schemas/         # Pydantic DTOs
  repository/      # data access
  services/        # business logic
  workers/         # Kafka consumers
  automation/      # Playwright portal adapters
  scheduler/       # APScheduler
  producers/       # typed Kafka publishers

frontend/src/
  api/ hooks/ components/ layouts/ pages/
  features/ store/ routes/ theme/ types/
```

## Kafka Topics

`job.fetch` → `job.match` → `job.apply` → `job.success` / `job.failed` → `notifications` / `reports`

## Development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
npm test
```

### E2E

```bash
cd e2e
npm install
npx playwright install
npm test
```

## Security

- Bcrypt password hashing
- JWT access + refresh token rotation
- RBAC via role dependencies
- Rate limiting, CORS, security headers
- Structured request logging with correlation IDs
- Global exception handler + audit log collection

## License

Proprietary — all rights reserved.
