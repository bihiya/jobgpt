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
      return [['jobs'], ['jobs-infinite'], ['analytics'], ['pipeline']];
    case 'approval.needed':
    case 'approval.decided':
    case 'approval.batch':
      return [['approvals'], ['approval-blockers'], ['jobs'], ['jobs-infinite'], ['analytics'], ['weekly-story'], ['pipeline']];
    case 'application.queued':
    case 'application.started':
    case 'application.succeeded':
    case 'application.failed':
    case 'application.cancelled':
    case 'application.needs_input':
    case 'application.needs_otp':
    case 'application.needs_account':
    case 'application.rate_limited':
    case 'job.success':
    case 'job.failed':
      return [
        ['jobs'],
        ['jobs-infinite'],
        ['applications'],
        ['job-application'],
        ['approval-blockers'],
        ['approvals'],
        ['automation-logs'],
        ['automation-status'],
        ['analytics'],
        ['weekly-story'],
        ['pipeline'],
        ['calendar'],
      ];
    case 'application.session':
    case 'automation.log':
      // Applied in-place on the live caches — do not HTTP-refetch every step.
      return [];
    case 'automation.triggered':
      return [['automation-status']];
    case 'report.ready':
    case 'report.failed':
      return [['reports']];
    case 'portal.sync_started':
      return [['portals']];
    case 'portal.synced':
    case 'portal.health':
      return [
        ['portals'],
        ['jobs'],
        ['jobs-infinite'],
        ['analytics'],
        ['approval-blockers'],
        ['weekly-story'],
        ['pipeline'],
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
    'application.needs_account',
    'application.cancelled',
    'report.ready',
    'report.failed',
    'portal.synced',
    'portal.health',
    'reminder.due',
    'reminder.completed',
    'email.synced',
    'email.ingested',
    'email.applied',
  ].includes(event);
}

export type AutomationLogEventItem = {
  id: string;
  created_at: string;
  portal?: string;
  action: string;
  level?: string;
  message: string;
  correlation_id?: string;
};

/** Turn an `automation.log` socket frame into the same shape as GET /automation/logs. */
export function automationLogFromEvent(payload: RealtimeEvent): AutomationLogEventItem | null {
  if (payload.event !== 'automation.log') return null;
  const data = payload.data || {};
  const id = String(data.id || '').trim();
  if (!id) return null;
  return {
    id,
    created_at: String(payload.ts || new Date().toISOString()),
    portal: String(data.portal || ''),
    action: String(data.action || ''),
    level: String(data.level || 'info'),
    message: String(data.message || payload.body || ''),
    correlation_id: String(data.correlation_id || ''),
  };
}

type LogsPage = {
  items?: AutomationLogEventItem[];
  total?: number;
  [key: string]: unknown;
};

/** Prepend a live log without refetching. Drops duplicates by id. */
export function prependAutomationLog(
  page: LogsPage | undefined,
  item: AutomationLogEventItem,
): LogsPage {
  const items = Array.isArray(page?.items) ? page.items : [];
  if (items.some((row) => row.id === item.id)) return page || { items };
  return {
    ...page,
    items: [item, ...items].slice(0, 200),
    total: typeof page?.total === 'number' ? page.total + 1 : items.length + 1,
  };
}

type ApplicationPage = {
  items?: Array<Record<string, unknown>>;
  total?: number;
  [key: string]: unknown;
};

function sessionStepsFromData(data: Record<string, unknown>): unknown[] | null {
  if (Array.isArray(data.steps)) return data.steps;
  if (Array.isArray(data.session_steps)) return data.session_steps;
  return null;
}

/** Patch live apply steps onto an applications list page without refetching. */
export function patchApplicationSession(
  page: ApplicationPage | undefined,
  data: Record<string, unknown>,
  ts?: string,
): ApplicationPage | undefined {
  if (!page || !Array.isArray(page.items)) return page;
  const appId = String(data.application_id || data.id || '').trim();
  const jobId = String(data.job_id || '').trim();
  const steps = sessionStepsFromData(data);
  if (!appId && !jobId) return page;
  let found = false;
  const items = page.items.map((row) => {
    const match =
      (appId && String(row.id) === appId) || (jobId && String(row.job_id) === jobId);
    if (!match) return row;
    found = true;
    return {
      ...row,
      ...(appId ? { id: appId } : {}),
      ...(jobId ? { job_id: jobId } : {}),
      status: data.status || row.status,
      session_steps: steps ?? row.session_steps,
      error_message: data.error_message ?? row.error_message,
      updated_at: data.updated_at || ts || row.updated_at,
      attempts: data.attempts ?? row.attempts,
      blocker_type: data.blocker_type ?? row.blocker_type,
    };
  });
  if (found) return { ...page, items };
  if (appId && jobId) {
    return {
      ...page,
      items: [
        {
          id: appId,
          job_id: jobId,
          status: data.status || 'in_progress',
          session_steps: steps || [],
          error_message: data.error_message || '',
          updated_at: data.updated_at || ts,
          attempts: data.attempts || 1,
          blocker_type: data.blocker_type || '',
        },
        ...items,
      ],
      total: typeof page.total === 'number' ? page.total + 1 : items.length + 1,
    };
  }
  return page;
}

type PipelineCache = {
  columns?: Record<string, Array<Record<string, unknown>>>;
  [key: string]: unknown;
};

/** Patch live apply steps onto pipeline kanban cards without refetching. */
export function patchPipelineSession(
  pipeline: PipelineCache | undefined,
  data: Record<string, unknown>,
  ts?: string,
): PipelineCache | undefined {
  if (!pipeline?.columns) return pipeline;
  const jobId = String(data.job_id || '').trim();
  if (!jobId) return pipeline;
  const steps = sessionStepsFromData(data);
  const columns: Record<string, Array<Record<string, unknown>>> = {};
  for (const [key, jobs] of Object.entries(pipeline.columns)) {
    columns[key] = jobs.map((job) => {
      if (String(job.id) !== jobId) return job;
      const prev = (job.application as Record<string, unknown> | undefined) || {};
      return {
        ...job,
        application: {
          ...prev,
          id: data.application_id || prev.id,
          job_id: jobId,
          status: data.status || prev.status || 'in_progress',
          session_steps: steps ?? prev.session_steps,
          error_message: data.error_message ?? prev.error_message,
          updated_at: data.updated_at || ts || prev.updated_at,
          attempts: data.attempts ?? prev.attempts,
          blocker_type: data.blocker_type ?? prev.blocker_type,
        },
      };
    });
  }
  return { ...pipeline, columns };
}
