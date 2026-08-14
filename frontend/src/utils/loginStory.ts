export type AutomationLogItem = {
  id: string;
  created_at: string;
  portal?: string;
  action: string;
  level?: string;
  message: string;
};

const RUN_START = /fetching jobs from/i;

/** Newest-first API logs → chronological steps for the latest sync of one portal. */
export function lastPortalRun(logs: AutomationLogItem[], portal: string): AutomationLogItem[] {
  const name = (portal || '').toLowerCase();
  const mine = logs.filter((l) => (l.portal || '').toLowerCase() === name);
  if (!mine.length) return [];
  const startIdx = mine.findIndex(
    (l) => l.action === 'fetch.portal' || RUN_START.test(l.message || ''),
  );
  const slice =
    startIdx >= 0
      ? mine.slice(0, startIdx + 1)
      : mine.filter((l) => l.action === 'fetch.login').slice(0, 16);
  return [...slice].reverse();
}

export function loginStepLabel(item: AutomationLogItem): string {
  return (item.message || item.action || '').trim();
}
