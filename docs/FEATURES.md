# JobPilot AI — Product Enhancements

## Feature map

| Feature | Location |
|---------|----------|
| LLM job ranking + match breakdown | `services/llm/ranking.py`, Job `match_breakdown`, Job detail drawer |
| Human-in-the-loop apply | `Approval` model, `/approvals`, match worker gate, Approvals PWA page |
| Smart question bank | `QuestionAnswer`, `/questions`, apply worker resolve |
| Duplicate / already-applied detection | `DedupeService` + Redis bloom approx + `content_hash` |
| Webhook / Slack / email alerts | `NotificationDispatcher`, `/notification-channels` |
| Onboarding wizard | `/onboarding`, `OnboardingPage` |
| Job detail drawer (“why this score”) | `JobDetailDrawer` |
| Calendar + follow-up reminders | `ReminderService`, `/calendar`, `CalendarPage` |
| Chrome extension | `chrome-extension/` → `POST /jobs/ingest` |
| Mobile PWA approve/reject | `manifest.webmanifest`, `sw.js`, `/approvals` |
| Captcha/2FA hooks | `automation/captcha.py` wired into `BasePortal` |
| Portal health + auto-pause | `PortalHealthService`, portal `health` field |
| Dead-letter queue | Kafka topic `job.dlq` in `workers/base.py` |
| Marketing SSR/ISR | `marketing/` Next.js site |
| S3 object storage | `StorageService` for resumes/screenshots |
| WebSocket realtime | `GET/WS /api/v1/ws`, Redis pub/sub bridge, live UI invalidation |
| User + job audit logs | `AuditLog`, `/activity`, `/users/me/activity`, `/jobs/{id}/activity`, Activity UI |

## Default safer flow

1. Fetch → Match (heuristic + optional LLM)  
2. If score ≥ threshold → **Approval queue** (not blind apply)  
3. User approves (web/PWA) → `job.apply`  
4. Question bank fills forms; screenshot stored in S3/local  
5. Follow-up reminder scheduled; Slack/email/webhook notified  

## Enable LLM / S3 / Captcha / SMTP

See `.env.example` keys: `LLM_*`, `S3_*`, `CAPTCHA_*`, `SMTP_*`.
