# Installation Guide

## Prerequisites

- Docker & Docker Compose
- Node.js 22+ (local frontend)
- **Python 3.11+** (local backend; 3.12/3.13 recommended — Apple CLT Python 3.9 is not supported)
- Git

## 1. Clone and configure

```bash
git clone <repo-url> jobpilot-ai
cd jobpilot-ai
cp .env.example .env
```

Edit `.env` and set a strong `SECRET_KEY`:

```bash
openssl rand -hex 32
```

## 2. Start the stack

```bash
docker compose up --build
```

Services:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| OpenAPI | http://localhost:8000/docs |
| MongoDB | localhost:27017 |
| Kafka | localhost:9092 |
| Redis | localhost:6379 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |

## 3. Create an account

1. Open http://localhost:3000/register
2. Register with email/password
3. Configure Profile → upload resume
4. Connect Job Portals
5. Add Companies
6. Enable Auto Apply in Settings

## 4. Local development (optional)

### Backend

JobPilot uses Pydantic v2 typing (`str | None`, etc.). That requires **Python 3.11+**.  
Do not use macOS Command Line Tools Python 3.9.

#### Install a modern Python (macOS)

```bash
# Homebrew
brew install python@3.12

# Confirm
$(brew --prefix python@3.12)/bin/python3.12 --version
```

Or with [pyenv](https://github.com/pyenv/pyenv):

```bash
pyenv install 3.12.8
pyenv local 3.12.8
```

#### Create a fresh venv (important after upgrading)

```bash
cd backend
rm -rf .venv
python3.12 -m venv .venv          # or: python3.11 / python3.13
source .venv/bin/activate
python --version                  # must show 3.11+
pip install -U pip
pip install -r requirements.txt
playwright install --with-deps chromium
export MONGODB_URL=mongodb://localhost:27017
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://localhost:8000`.

## 5. Run workers locally

```bash
cd backend
source .venv/bin/activate
python -m app.workers.fetch_worker
python -m app.workers.match_worker
python -m app.workers.apply_worker
python -m app.workers.notification_worker
python -m app.workers.report_worker
```

## 6. Tests

```bash
# Backend
cd backend && pytest tests/unit -q

# Frontend
cd frontend && npm test

# E2E (stack must be running)
cd e2e && npm install && npx playwright install && npm test
```
