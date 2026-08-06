# JobPilot AI — API Contracts

Base URL: `/api/v1`  
Auth: `Authorization: Bearer <access_token>`  
Content-Type: `application/json`

## Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Obtain tokens |
| POST | `/auth/refresh` | Rotate access token |
| POST | `/auth/logout` | Revoke refresh token |
| GET | `/auth/me` | Current user |

### Register
```json
// Request
{ "email": "user@example.com", "password": "Str0ng!Pass", "full_name": "Ada Lovelace" }
// Response 201
{ "id": "...", "email": "user@example.com", "full_name": "Ada Lovelace", "roles": ["user"] }
```

### Login
```json
// Request
{ "email": "user@example.com", "password": "Str0ng!Pass" }
// Response 200
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 900
}
```

## Users / Profile

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users/me` | Profile |
| PATCH | `/users/me` | Update profile |
| POST | `/users/me/resumes` | Upload resume (multipart) |
| GET | `/users/me/resumes` | List resumes |
| DELETE | `/users/me/resumes/{id}` | Delete resume |

## Jobs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/jobs` | List (filters, pagination, sort) |
| GET | `/jobs/tracked` | Tracked jobs |
| GET | `/jobs/applied` | Applied jobs |
| GET | `/jobs/history` | History |
| GET | `/jobs/{id}` | Detail |
| PATCH | `/jobs/{id}` | Update status |
| POST | `/jobs/{id}/track` | Mark tracked |
| POST | `/jobs/{id}/ignore` | Ignore |

Query params: `q`, `portal`, `company`, `status`, `min_score`, `page`, `page_size`, `sort_by`, `sort_dir`

## Applications

| Method | Path | Description |
|--------|------|-------------|
| GET | `/applications` | List applications |
| GET | `/applications/{id}` | Detail + logs |
| POST | `/applications` | Queue apply |
| POST | `/applications/{id}/retry` | Retry failed |

## Companies

| Method | Path | Description |
|--------|------|-------------|
| GET | `/companies` | List |
| POST | `/companies` | Create |
| GET | `/companies/{id}` | Detail |
| PATCH | `/companies/{id}` | Update |
| DELETE | `/companies/{id}` | Delete |

```json
{
  "name": "Google",
  "career_url": "https://careers.google.com",
  "platform": "custom",
  "priority": 1,
  "tags": ["tech", "faang"],
  "status": "active"
}
```

## Job Portals

| Method | Path | Description |
|--------|------|-------------|
| GET | `/job-portals` | List connectors |
| POST | `/job-portals` | Connect portal |
| PATCH | `/job-portals/{id}` | Update credentials/proxy |
| POST | `/job-portals/{id}/sync` | Trigger sync |
| DELETE | `/job-portals/{id}` | Disconnect |

Supported portals: `linkedin`, `naukri`, `indeed`, `foundit`, `wellfound`, `greenhouse`, `lever`, `ashby`, `workday`, `smartrecruiters`, `oracle`, `sap_successfactors`, `taleo`

## Automation

| Method | Path | Description |
|--------|------|-------------|
| GET | `/automation/status` | Worker status |
| GET | `/automation/logs` | Automation logs |
| POST | `/automation/run` | Manual trigger |

## Reports

| Method | Path | Description |
|--------|------|-------------|
| GET | `/reports` | List reports |
| POST | `/reports` | Generate report |
| GET | `/reports/{id}/download` | Download CSV/Excel/PDF |
| GET | `/reports/analytics` | Dashboard analytics |

## Settings / Scheduler

| Method | Path | Description |
|--------|------|-------------|
| GET | `/settings` | User settings |
| PATCH | `/settings` | Update settings |
| GET | `/scheduler/jobs` | Scheduled jobs |
| PATCH | `/scheduler/jobs/{id}` | Enable/disable/interval |

## Health / Metrics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/health/ready` | Readiness |
| GET | `/metrics` | Prometheus metrics |

## Error Envelope

```json
{
  "detail": "Human readable message",
  "code": "AUTH_INVALID_CREDENTIALS",
  "request_id": "uuid",
  "errors": []
}
```
