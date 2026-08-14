import type { AutomationLogItem } from '../utils/loginStory';

export type DemoSyncBeat = {
  ms: number;
  action: string;
  level: 'info' | 'success' | 'warning' | 'error';
  message: (portal: string) => string;
};

/** Timed beats used to animate a guest/demo sync under one correlation id. */
export const DEMO_SYNC_BEATS: DemoSyncBeat[] = [
  {
    ms: 0,
    action: 'fetch.portal',
    level: 'info',
    message: (portal) => `Sync queued for ${portal}…`,
  },
  {
    ms: 650,
    action: 'fetch.login',
    level: 'info',
    message: () => 'Login page opened',
  },
  {
    ms: 700,
    action: 'fetch.login',
    level: 'info',
    message: () => 'Filled email / username',
  },
  {
    ms: 650,
    action: 'fetch.login',
    level: 'info',
    message: () => 'Filled password',
  },
  {
    ms: 700,
    action: 'fetch.login',
    level: 'info',
    message: () => 'Clicked Sign in',
  },
  {
    ms: 900,
    action: 'fetch.extract',
    level: 'info',
    message: () => 'Found 18 job listing(s)',
  },
  {
    ms: 800,
    action: 'fetch.complete',
    level: 'success',
    message: (portal) => `${portal}: found 18, added 12 new job(s)`,
  },
];

export function demoSyncStep(
  portal: string,
  syncId: string,
  beat: DemoSyncBeat,
  index: number,
  at = new Date().toISOString(),
): AutomationLogItem {
  return {
    id: `${syncId}-step-${index}`,
    created_at: at,
    portal,
    action: beat.action,
    level: beat.level,
    message: beat.message(portal),
    correlation_id: syncId,
  };
}

/** Play demo beats; returns a cancel function. Newest-first callback order. */
export function playDemoSync(
  portal: string,
  syncId: string,
  onStep: (step: AutomationLogItem, index: number, done: boolean) => void,
): () => void {
  const timers: number[] = [];
  let elapsed = 0;
  DEMO_SYNC_BEATS.forEach((beat, index) => {
    elapsed += beat.ms;
    const handle = window.setTimeout(() => {
      onStep(demoSyncStep(portal, syncId, beat, index), index, index === DEMO_SYNC_BEATS.length - 1);
    }, elapsed);
    timers.push(handle);
  });
  return () => {
    timers.forEach((handle) => window.clearTimeout(handle));
  };
}
