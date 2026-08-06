# JobPilot AI — Architecture

## Overview

JobPilot AI is a full-stack job automation platform. Users configure resumes, preferences, companies, and job portals once. The system continuously scans portals, scores matches, applies via browser automation, and surfaces analytics.

## Design Principles

- **Clean Architecture** — API → Service → Repository → Database
- **SOLID / DRY / KISS** — modular boundaries, single responsibility
- **Repository + Service Layer** — persistence isolated from business logic
- **Dependency Injection** — FastAPI `Depends` for auth, DB, services
- **Event-driven workers** — Kafka topics for fetch / match / apply / notify / report
- **Portal Adapter Pattern** — Playwright adapters per job portal

## High-Level Architecture

```mermaid
flowchart TB
    subgraph Client
        FE[React 19 + MUI Frontend]
    end

    subgraph API["API Layer (FastAPI)"]
        GW[API Gateway /v1]
        AUTH[Auth JWT + Refresh]
        RBAC[RBAC Middleware]
    end

    subgraph Domain["Domain Services"]
        US[User Service]
        JS[Job Service]
        MS[Match Service]
        AS[Application Service]
        CS[Company Service]
        PS[Portal Service]
        RS[Report Service]
        AUTOS[Automation Service]
    end

    subgraph Data
        REPO[Repositories]
        MONGO[(MongoDB)]
        REDIS[(Redis Cache)]
    end

    subgraph Async["Async Pipeline"]
        SCH[APScheduler]
        PROD[Kafka Producers]
        KAFKA[[Apache Kafka]]
        CONS[Consumers / Workers]
        PW[Playwright Automation]
    end

    subgraph Obs
        PROM[Prometheus]
        GRAF[Grafana]
        LOGS[Structured Logs]
    end

    FE --> GW
    GW --> AUTH --> RBAC
    RBAC --> US & JS & MS & AS & CS & PS & RS & AUTOS
    US & JS & MS & AS & CS & PS & RS & AUTOS --> REPO
    REPO --> MONGO
    AUTOS --> REDIS
    SCH --> PROD --> KAFKA --> CONS
    CONS --> PW
    CONS --> REPO
    GW --> PROM
    CONS --> LOGS
    PROM --> GRAF
```

## Clean Architecture Layers

```mermaid
flowchart LR
    subgraph Presentation
        R[REST Routers]
        SCHEMAS[Pydantic Schemas]
    end
    subgraph Application
        SVC[Services]
        DEP[Dependencies]
    end
    subgraph Domain
        MODELS[Beanie Models]
        EVENTS[Domain Events]
    end
    subgraph Infrastructure
        REPOS[Repositories]
        KAFKA_I[Kafka]
        PW_I[Playwright]
        SCHED[APScheduler]
        MONGO_I[Motor/MongoDB]
    end

    R --> SCHEMAS --> SVC --> REPOS
    SVC --> EVENTS
    REPOS --> MODELS --> MONGO_I
    SVC --> KAFKA_I
    SVC --> PW_I
    SCHED --> SVC
```

## Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as FastAPI
    participant DB as MongoDB

    U->>FE: Register / Login
    FE->>API: POST /api/v1/auth/login
    API->>DB: Verify credentials
    DB-->>API: User + roles
    API-->>FE: access_token + refresh_token
    FE->>FE: Store tokens (memory + httpOnly refresh)
    FE->>API: Request + Bearer access_token
    API->>API: Validate JWT + RBAC
    API-->>FE: Resource

    Note over FE,API: On 401
    FE->>API: POST /api/v1/auth/refresh
    API-->>FE: New access_token
```

## Job Automation Sequence

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant P as Producer
    participant K as Kafka
    participant F as Fetch Worker
    participant M as Match Worker
    participant A as Apply Worker
    participant PW as Playwright
    participant DB as MongoDB

    S->>P: Interval tick
    P->>K: job.fetch
    K->>F: Consume
    F->>PW: Login + Search + Extract
    PW-->>F: Job listings
    F->>DB: Upsert jobs
    F->>K: job.match
    K->>M: Consume
    M->>DB: Score vs resume/prefs
    M->>K: job.apply (if score >= threshold)
    K->>A: Consume
    A->>PW: Open + Fill + Upload + Submit
    alt Success
        A->>DB: application success + screenshot
        A->>K: job.success
    else Failure
        A->>DB: log failure + retry metadata
        A->>K: job.failed
    end
```

## Kafka Event Flow

```mermaid
flowchart LR
    SCH[Scheduler] -->|job.fetch| T1[(job.fetch)]
    T1 --> FW[Fetch Worker]
    FW -->|job.match| T2[(job.match)]
    T2 --> MW[Match Worker]
    MW -->|job.apply| T3[(job.apply)]
    T3 --> AW[Apply Worker]
    AW -->|job.success| T4[(job.success)]
    AW -->|job.failed| T5[(job.failed)]
    T4 & T5 --> NW[Notification Worker]
    NW -->|notifications| T6[(notifications)]
    T4 & T5 --> RW[Report Worker]
    RW -->|reports| T7[(reports)]
```

## Module Map

| Module | Responsibility |
|--------|----------------|
| `api/v1/*` | HTTP routers, OpenAPI contracts |
| `core/` | Config, security, logging, Kafka client, exceptions |
| `models/` | Beanie documents |
| `schemas/` | Pydantic request/response DTOs |
| `repository/` | Data access (MongoDB) |
| `services/` | Business logic |
| `workers/` | Background Kafka consumers |
| `automation/` | Playwright portal adapters |
| `scheduler/` | APScheduler jobs |
| `producers/` / `consumers/` | Kafka I/O |
| `frontend/src/store/` | Redux Toolkit (JS) global UI state |

## Scalability Notes

- Stateless API replicas behind a load balancer
- Horizontal worker scaling per Kafka consumer group
- MongoDB indexes on user_id, portal, status, fetched_at, match_score
- Redis for rate limits, session cache, and distributed locks
- Playwright workers isolated in containers with resource limits
