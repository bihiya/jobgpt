# JobPilot AI — Database Schema (MongoDB)

## Collections

### users
```json
{
  "_id": "ObjectId",
  "email": "string (unique)",
  "hashed_password": "string",
  "full_name": "string",
  "roles": ["user" | "admin"],
  "is_active": true,
  "profile": {
    "skills": ["string"],
    "experience_years": 0,
    "location": "string",
    "salary_expectation": { "min": 0, "max": 0, "currency": "USD" },
    "keywords": ["string"],
    "notice_period_days": 0,
    "linkedin_url": "string",
    "github_url": "string",
    "portfolio_url": "string"
  },
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### roles
```json
{
  "_id": "ObjectId",
  "name": "user|admin",
  "permissions": ["jobs:read", "jobs:write", "admin:all"],
  "created_at": "datetime"
}
```

### resumes
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "name": "string",
  "file_path": "string",
  "file_type": "pdf|docx",
  "is_default": true,
  "parsed_text": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### companies
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "name": "string",
  "career_url": "string",
  "platform": "greenhouse|lever|ashby|workday|custom",
  "priority": 1,
  "tags": ["string"],
  "status": "active|paused|disabled",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### portals
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "name": "linkedin|naukri|indeed|foundit|wellfound|greenhouse|lever|ashby|workday|smartrecruiters|oracle|sap_successfactors|taleo",
  "credentials": { "username": "encrypted", "password": "encrypted" },
  "cookies": {},
  "proxy": { "server": "string", "username": "string", "password": "string" },
  "status": "connected|disconnected|error",
  "last_sync_at": "datetime",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### jobs
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "external_id": "string",
  "title": "string",
  "company": "string",
  "location": "string",
  "salary": "string",
  "experience": "string",
  "description": "string",
  "skills": ["string"],
  "apply_url": "string",
  "portal": "string",
  "status": "new|tracked|matched|applying|applied|failed|ignored",
  "match_score": 0.0,
  "fetched_at": "datetime",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### applications
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "job_id": "ObjectId",
  "resume_id": "ObjectId",
  "status": "pending|in_progress|success|failed|retrying",
  "attempts": 0,
  "next_retry_at": "datetime",
  "screenshot_path": "string",
  "error_message": "string",
  "applied_at": "datetime",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### automation_logs
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "job_id": "ObjectId",
  "application_id": "ObjectId",
  "portal": "string",
  "action": "login|search|apply|submit|screenshot",
  "level": "info|warning|error",
  "message": "string",
  "metadata": {},
  "correlation_id": "string",
  "created_at": "datetime"
}
```

### reports
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "type": "daily|weekly|custom",
  "format": "csv|excel|pdf",
  "file_path": "string",
  "filters": {},
  "status": "pending|ready|failed",
  "created_at": "datetime"
}
```

### scheduler_jobs
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "name": "string",
  "job_type": "fetch|match|apply|report",
  "cron": "string",
  "interval_seconds": 3600,
  "is_enabled": true,
  "last_run_at": "datetime",
  "next_run_at": "datetime",
  "created_at": "datetime"
}
```

### notifications
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "title": "string",
  "body": "string",
  "type": "info|success|warning|error",
  "is_read": false,
  "created_at": "datetime"
}
```

### settings
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "match_threshold": 0.7,
  "auto_apply": true,
  "max_applications_per_day": 50,
  "headless": true,
  "timezone": "UTC",
  "notification_email": true,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### refresh_tokens
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "token_hash": "string",
  "expires_at": "datetime",
  "revoked": false,
  "created_at": "datetime"
}
```

### audit_logs
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "action": "string",
  "resource": "string",
  "ip": "string",
  "user_agent": "string",
  "metadata": {},
  "created_at": "datetime"
}
```

## Indexes

| Collection | Index |
|------------|-------|
| users | unique(email) |
| jobs | (user_id, portal, status), (user_id, match_score), (external_id, portal) |
| applications | (user_id, status), (job_id) |
| companies | (user_id, status), (user_id, name) |
| portals | (user_id, name) unique |
| automation_logs | (user_id, created_at), (correlation_id) |
| refresh_tokens | (token_hash), (user_id, expires_at) |
