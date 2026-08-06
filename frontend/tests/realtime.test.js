import { describe, expect, it } from 'vitest';
import { queryKeysForEvent, shouldToastEvent } from '../src/lib/realtime';

describe('realtime helpers', () => {
  it('maps job events to jobs + analytics keys', () => {
    const keys = queryKeysForEvent('job.matched').map((k) => k[0]);
    expect(keys).toContain('jobs');
    expect(keys).toContain('analytics');
  });

  it('maps approval events to approvals queue', () => {
    const keys = queryKeysForEvent('approval.needed').map((k) => k[0]);
    expect(keys).toContain('approvals');
  });

  it('toasts worker-driven events but not mutation echoes', () => {
    expect(shouldToastEvent('approval.needed')).toBe(true);
    expect(shouldToastEvent('job.success')).toBe(true);
    expect(shouldToastEvent('approval.decided')).toBe(false);
    expect(shouldToastEvent('automation.triggered')).toBe(false);
  });
});
