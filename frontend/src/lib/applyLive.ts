import type { SessionStep } from '../components/automation/ApplySessionTimeline';
import { parseApiDate } from '../utils/datetime';

export const LIVE_APPLY_STATUSES = new Set([
  'pending',
  'in_progress',
  'retrying',
  'needs_input',
  'needs_otp',
  'needs_account',
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
  if (value === 'needs otp') return 'Needs a verification code';
  if (value === 'needs account') return 'Needs a candidate account';
  if (value === 'success') return 'Applied';
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function pipelineHasLiveApply(columns?: Record<string, Array<{ status?: string; application?: ApplySnapshot }>>): boolean {
  if (!columns) return false;
  return Object.values(columns).some((jobs) =>
    jobs.some((job) => isJobApplying(job.status, job.application?.status)),
  );
}

export type ApplyChannel = {
  kind: 'linkedin' | 'external' | 'indeed';
  label: string;
  ats?: string;
};

type StepLike = {
  key?: string;
  label?: string;
  detail?: string;
  metadata?: Record<string, unknown>;
};

function stepMeta(step: StepLike): Record<string, unknown> {
  return step.metadata && typeof step.metadata === 'object' ? step.metadata : {};
}

export function applyChannelFromSteps(
  steps?: StepLike[] | null,
  fallback?: { portal?: string; metadata?: Record<string, unknown> } | null,
): ApplyChannel | null {
  for (const step of steps || []) {
    if (step.key !== 'apply_channel' || !step.label) continue;
    const meta = stepMeta(step);
    const kindRaw = String(meta.kind || '');
    const label = String(step.label);
    const kind: ApplyChannel['kind'] =
      kindRaw === 'linkedin' || /easy apply/i.test(label)
        ? 'linkedin'
        : kindRaw === 'indeed' || /^indeed apply$/i.test(label)
          ? 'indeed'
          : 'external';
    return { kind, label, ats: String(meta.ats || '') || undefined };
  }
  for (const step of steps || []) {
    if (step.key !== 'clicked_apply') continue;
    const label = String(step.label || '');
    if (/external/i.test(label)) return { kind: 'external', label: 'External apply' };
    if (/easy apply/i.test(label)) return { kind: 'linkedin', label: 'LinkedIn Easy Apply' };
    if (/indeed/i.test(label)) return { kind: 'indeed', label: 'Indeed apply' };
  }
  const stored = fallback?.metadata?.apply_channel;
  if (typeof stored === 'string' && stored.trim()) {
    if (/easy apply/i.test(stored)) return { kind: 'linkedin', label: stored };
    if (/indeed apply/i.test(stored)) return { kind: 'indeed', label: stored };
    return {
      kind: 'external',
      label: stored,
      ats: typeof fallback?.metadata?.ats === 'string' ? fallback.metadata.ats : undefined,
    };
  }
  return null;
}

export function applyChannelChipColor(channel: ApplyChannel): 'info' | 'secondary' | 'default' {
  if (channel.kind === 'linkedin') return 'info';
  if (channel.kind === 'external') return 'secondary';
  return 'default';
}
