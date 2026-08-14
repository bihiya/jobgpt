import { afterEach, describe, expect, it, vi } from 'vitest';
import { DEMO_SYNC_BEATS, demoSyncStep, playDemoSync } from '../src/lib/demoSync';

describe('demoSync', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('keeps every beat on the same sync id', () => {
    const steps = DEMO_SYNC_BEATS.map((beat, index) =>
      demoSyncStep('linkedin', 'sync-abc', beat, index, 't0'),
    );
    expect(steps.map((s) => s.correlation_id)).toEqual(DEMO_SYNC_BEATS.map(() => 'sync-abc'));
    expect(steps[0].message).toMatch(/queued/i);
    expect(steps.at(-1)?.action).toBe('fetch.complete');
  });

  it('plays beats in order under one sync id', () => {
    vi.useFakeTimers();
    const seen = [];
    const cancel = playDemoSync('indeed', 'cid-1', (step, index, done) => {
      seen.push({ id: step.correlation_id, index, done, action: step.action });
    });
    vi.runAllTimers();
    cancel();
    expect(seen.map((s) => s.id)).toEqual(DEMO_SYNC_BEATS.map(() => 'cid-1'));
    expect(seen.at(-1)?.done).toBe(true);
    expect(seen.at(-1)?.action).toBe('fetch.complete');
  });
});
