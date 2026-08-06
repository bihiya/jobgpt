/** Resolve WebSocket URL for the JobPilot realtime channel. */
export function getRealtimeUrl(accessToken: string): string {
  const apiBase = import.meta.env.VITE_API_URL || '/api/v1';
  let httpUrl: string;
  if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) {
    httpUrl = `${apiBase.replace(/\/$/, '')}/ws`;
  } else {
    const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5173';
    httpUrl = `${origin}${apiBase.replace(/\/$/, '')}/ws`;
  }
  const wsUrl = httpUrl.replace(/^http/, 'ws');
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
    case 'portal.synced':
    case 'portal.health':
      return [['portals'], ['jobs'], ['jobs-infinite'], ['analytics'], ['approval-blockers'], ['weekly-story']];
    case 'reminder.due':
    case 'reminder.scheduled':
    case 'reminder.completed':
      return [['reminders-due'], ['calendar']];
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
    'portal.synced',
    'portal.health',
    'reminder.due',
    'reminder.completed',
  ].includes(event);
}
