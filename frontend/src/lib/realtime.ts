/** Resolve WebSocket URL for the JobPilot realtime channel. */

/**
 * Build the HTTP form of the realtime endpoint (converted to ws/wss by the caller).
 *
 * Vercel SPA rewrites proxy HTTP `/api/*` fine, but they do not upgrade WebSockets
 * (browser gets HTTP 404 on `wss://<frontend>/api/v1/ws`). Prefer an absolute API
 * origin for WS when the HTTP API base is relative.
 */
export function getRealtimeHttpEndpoint(): string {
  const explicit = import.meta.env.VITE_WS_URL?.trim();
  if (explicit) {
    // Accept wss://… or https://…
    return explicit.replace(/^ws/i, 'http').replace(/\/$/, '');
  }

  const apiBase = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '');
  const apiOrigin = import.meta.env.VITE_API_ORIGIN?.replace(/\/$/, '');

  if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) {
    return `${apiBase}/ws`;
  }

  if (apiOrigin) {
    const path = apiBase.startsWith('/') ? apiBase : `/${apiBase}`;
    return `${apiOrigin}${path}/ws`;
  }

  // Production frontend on Vercel: speak directly to the Azure API (WS not proxied by Vercel).
  if (typeof window !== 'undefined' && window.location.hostname.endsWith('.vercel.app')) {
    return 'https://ca-jobpilot-api.bravebeach-7fcbe2c3.centralindia.azurecontainerapps.io/api/v1/ws';
  }

  // Local Vite proxy (and Docker nginx) can upgrade same-origin /api WebSockets.
  const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5173';
  const path = apiBase.startsWith('/') ? apiBase : `/${apiBase}`;
  return `${origin}${path}/ws`;
}

export function getRealtimeUrl(accessToken: string): string {
  const httpUrl = getRealtimeHttpEndpoint();
  const wsUrl = httpUrl.replace(/^http/i, 'ws');
  const url = new URL(wsUrl);
  url.searchParams.set('token', accessToken);
  return url.toString();
}

export type RealtimeEvent = {
  event: string;
  user_id?: string;
  ts?: string;
  title?: string | null;
  body?: string | null;
  severity?: 'success' | 'error' | 'info' | 'warning';
  data?: Record<string, unknown>;
};

/** Map realtime events → React Query keys to invalidate. */
export function queryKeysForEvent(event: string): string[][] {
  switch (event) {
    case 'job.created':
    case 'job.matched':
      return [['jobs'], ['jobs-infinite'], ['analytics']];
    case 'approval.needed':
    case 'approval.decided':
    case 'approval.batch':
      return [['approvals'], ['approval-blockers'], ['jobs'], ['jobs-infinite'], ['analytics'], ['weekly-story'], ['pipeline']];
    case 'application.queued':
    case 'application.started':
    case 'application.session':
    case 'application.succeeded':
    case 'application.failed':
    case 'application.cancelled':
    case 'application.needs_input':
    case 'application.needs_otp':
    case 'application.rate_limited':
    case 'job.success':
    case 'job.failed':
      return [
        ['jobs'],
        ['jobs-infinite'],
        ['applications'],
        ['approval-blockers'],
        ['approvals'],
        ['automation-logs'],
        ['automation-status'],
        ['analytics'],
        ['weekly-story'],
        ['pipeline'],
        ['calendar'],
      ];
    case 'automation.log':
    case 'automation.triggered':
      return [['automation-logs'], ['automation-status']];
    case 'report.ready':
    case 'report.failed':
      return [['reports']];
    case 'portal.sync_started':
    case 'portal.synced':
    case 'portal.health':
      return [
        ['portals'],
        ['jobs'],
        ['jobs-infinite'],
        ['analytics'],
        ['approval-blockers'],
        ['weekly-story'],
        ['automation-logs'],
        ['automation-status'],
      ];
    case 'reminder.due':
    case 'reminder.scheduled':
    case 'reminder.completed':
      return [['reminders-due'], ['calendar']];
    case 'email.synced':
    case 'email.ingested':
    case 'email.applied':
      return [
        ['email-messages'],
        ['email-accounts'],
        ['pipeline'],
        ['jobs'],
        ['jobs-infinite'],
        ['calendar'],
        ['reminders-due'],
        ['weekly-story'],
      ];
    case 'audit.created':
      return [['user-activity'], ['job-activity']];
    default:
      return [];
  }
}

/** Events that should surface a user-visible toast (when title/body present). */
export function shouldToastEvent(event: string): boolean {
  // Skip events already toasted by mutation meta (approval.decided, automation.triggered).
  return [
    'approval.needed',
    'job.success',
    'job.failed',
    'application.started',
    'application.needs_input',
    'application.needs_otp',
    'application.cancelled',
    'report.ready',
    'report.failed',
    'portal.sync_started',
    'portal.synced',
    'portal.health',
    'reminder.due',
    'reminder.completed',
    'email.synced',
    'email.ingested',
    'email.applied',
  ].includes(event);
}
