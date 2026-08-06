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
| Guest browse mode | All app pages viewable without login; actions open Sign-in gate + demo data |
| Portal reliability pack | Session cookie vault, selector versioning, verified apply, fail screenshot+DOM |
| Apply session recorder | Step timeline on applications / Approvals blockers |
| Question bank UX | Pause on unknown field → answer once → resume (`/questions`) |
| Captcha / 2FA path | 2captcha poll + TOTP vault; OTP blockers on Approvals |
| Smart batch apply | Approve ≥ threshold for a portal with daily caps + cooldown |
| Home Digest command center | Ranked match cards, live apply tray, blockers inbox, portal health, weekly story |
| Pipeline Kanban | Matched → Approved → Applied → Interview → Offer → Rejected |

## Default safer flow

1. Fetch → Match (heuristic + optional LLM)  
2. If score ≥ threshold → **Approval queue** (not blind apply)  
3. User approves (web/PWA) or **smart batch** (≥85% + portal + caps) → `job.apply`  
4. Session vault restores cookies; captcha/TOTP handled; question bank fills forms  
5. Unknown field or OTP → pause → user answers on Approvals/Questions → resume  
6. Success **verified** (not assumed); screenshot + DOM proof on fail; follow-up reminder  

## Automation reliability notes

- Cookies encrypted in `Portal.session_blob` via Fernet derived from `SECRET_KEY`
- Selector packs versioned under `backend/app/automation/selectors/`
- Apply steps stored on `Application.session_steps` + `AutomationLog`
- Rate limits: `max_applications_per_day`, `apply_cooldown_seconds`, `batch_min_score`  


## Enable LLM / S3 / Captcha / SMTP

See `.env.example` keys: `LLM_*`, `S3_*`, `CAPTCHA_*`, `SMTP_*`.
