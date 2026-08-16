import type { SessionStep } from '../components/automation/ApplySessionTimeline';
import { parseApiDate } from '../utils/datetime';

export const LIVE_APPLY_STATUSES = new Set([
  'pending',
  'in_progress',
  'retrying',
  'needs_input',
  'needs_otp',
]);

/** No worker update for this long → treat the apply as stuck. */
export const STALE_APPLY_MS = 3 * 60 * 1000;

export type ApplySnapshot = {
  id: string;
  job_id?: string;
  status: string;
  session_steps?: SessionStep[];
  error_message?: string;
  updated_at?: string;
  created_at?: string;
  attempts?: number;
  blocker_type?: string;
  title?: string;
  company?: string;
  portal?: string;
};

export function isLiveApplyStatus(status?: string | null): boolean {
  return LIVE_APPLY_STATUSES.has(String(status || ''));
}

export function isJobApplying(jobStatus?: string | null, appStatus?: string | null): boolean {
  return jobStatus === 'applying' || isLiveApplyStatus(appStatus);
}

export function isStaleApply(
  updatedAt?: string | null,
  now = Date.now(),
  staleMs = STALE_APPLY_MS,
): boolean {
  const parsed = parseApiDate(updatedAt);
  if (!parsed) return false;
  return now - parsed.valueOf() > staleMs;
}

export function latestSessionStep(steps?: SessionStep[] | null): SessionStep | null {
  if (!steps?.length) return null;
  return steps[steps.length - 1] || null;
}

export function mergeApplySnapshots(
  a?: ApplySnapshot | null,
  b?: ApplySnapshot | null,
): ApplySnapshot | undefined {
  if (!a) return b || undefined;
  if (!b) return a;
  const aAt = parseApiDate(a.updated_at)?.valueOf() || 0;
  const bAt = parseApiDate(b.updated_at)?.valueOf() || 0;
  const newer = aAt >= bAt ? a : b;
  const older = aAt >= bAt ? b : a;
  const newerLen = newer.session_steps?.length || 0;
  const olderLen = older.session_steps?.length || 0;
  if (olderLen > newerLen) {
    return { ...newer, session_steps: older.session_steps };
  }
  return newer;
}

export function applyStatusLabel(status?: string | null): string {
  const value = String(status || '').replace(/_/g, ' ');
  if (!value) return 'Applying';
  if (value === 'in progress') return 'Applying now';
  if (value === 'pending') return 'Queued';
  if (value === 'retrying') return 'Retrying';
  if (value === 'needs input') return 'Needs an answer';
  if (value === 'needs otp') return 'Needs OTP';
  if (value === 'success') return 'Applied';
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function pipelineHasLiveApply(columns?: Record<string, Array<{ status?: string; application?: ApplySnapshot }>>): boolean {
  if (!columns) return false;
  return Object.values(columns).some((jobs) =>
    jobs.some((job) => isJobApplying(job.status, job.application?.status)),
  );
}
