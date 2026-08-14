export type AutomationLogItem = {
  id: string;
  created_at: string;
  portal?: string;
  action: string;
  level?: string;
  message: string;
  correlation_id?: string;
};

export type SyncRun = {
  id: string;
  portal: string;
  startedAt: string;
  endedAt: string;
  outcome: 'success' | 'error' | 'warning' | 'info';
  summary: string;
  stepCount: number;
  steps: AutomationLogItem[];
};

const RUN_START = /fetching jobs from/i;

function isRunStart(item: AutomationLogItem): boolean {
  return item.action === 'fetch.portal' || RUN_START.test(item.message || '');
}

function outcomeOf(steps: AutomationLogItem[]): SyncRun['outcome'] {
  if (steps.some((s) => s.level === 'error' || s.action === 'fetch.failed' || s.action === 'portal.sync_failed')) {
    return 'error';
  }
  if (steps.some((s) => s.action === 'fetch.complete' && s.level === 'success')) return 'success';
  if (steps.some((s) => s.level === 'success')) return 'success';
  if (steps.some((s) => s.level === 'warning' || s.action === 'fetch.skipped')) return 'warning';
  return 'info';
}

function summaryOf(steps: AutomationLogItem[], portal: string): string {
  const tail = [...steps].reverse().find(
    (s) =>
      s.action === 'fetch.complete' ||
      s.action === 'fetch.failed' ||
      s.action === 'fetch.skipped' ||
      s.action === 'fetch.done' ||
      s.level === 'error',
  );
  if (tail?.message) return tail.message;
  return `${portal} sync · ${steps.length} step${steps.length === 1 ? '' : 's'}`;
}

function toRun(id: string, portal: string, newestFirst: AutomationLogItem[]): SyncRun {
  const steps = [...newestFirst].reverse();
  return {
    id,
    portal,
    startedAt: steps[0]?.created_at || '',
    endedAt: steps[steps.length - 1]?.created_at || '',
    outcome: outcomeOf(steps),
    summary: summaryOf(steps, portal),
    stepCount: steps.length,
    steps,
  };
}

/** Group newest-first logs into chronological sync runs (newest run first). */
export function groupPortalRuns(logs: AutomationLogItem[], portal?: string): SyncRun[] {
  const name = (portal || '').toLowerCase();
  const scoped = name
    ? logs.filter((l) => (l.portal || '').toLowerCase() === name)
    : logs.filter((l) => l.portal || l.action?.startsWith('fetch.'));
  if (!scoped.length) return [];

  const cids = new Set(
    scoped.map((l) => (l.correlation_id || '').trim()).filter(Boolean),
  );
  const related = name
    ? logs.filter((l) => {
        const cid = (l.correlation_id || '').trim();
        if ((l.portal || '').toLowerCase() === name) return true;
        return Boolean(cid && cids.has(cid));
      })
    : scoped;

  const hasCid = related.some((l) => (l.correlation_id || '').trim());
  if (hasCid) {
    const buckets = new Map<string, AutomationLogItem[]>();
    const order: string[] = [];
    for (const item of related) {
      const key = (item.correlation_id || '').trim() || `row-${item.id}`;
      if (!buckets.has(key)) {
        buckets.set(key, []);
        order.push(key);
      }
      buckets.get(key)!.push(item);
    }
    return order.map((key) => {
      const items = buckets.get(key)!;
      const portalName =
        items.find((i) => i.portal)?.portal || portal || 'portal';
      return toRun(key, portalName, items);
    });
  }

  const runs: AutomationLogItem[][] = [];
  let current: AutomationLogItem[] = [];
  for (const item of related) {
    current.push(item);
    if (isRunStart(item)) {
      runs.push(current);
      current = [];
    }
  }
  if (current.length) runs.push(current);
  return runs.map((items, idx) =>
    toRun(`anon-${idx}`, items.find((i) => i.portal)?.portal || portal || 'portal', items),
  );
}

/** Newest-first API logs → chronological steps for the latest sync of one portal. */
export function lastPortalRun(logs: AutomationLogItem[], portal: string): AutomationLogItem[] {
  return groupPortalRuns(logs, portal)[0]?.steps || [];
}
