import { afterEach, describe, expect, it, vi } from 'vitest';
import { getRealtimeHttpEndpoint, queryKeysForEvent, shouldToastEvent } from '../src/lib/realtime';

describe('realtime helpers', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('uses VITE_WS_URL when set', () => {
    vi.stubEnv('VITE_WS_URL', 'wss://jobai.example/api/v1/ws');
    expect(getRealtimeHttpEndpoint()).toBe('https://jobai.example/api/v1/ws');
  });

  it('uses VITE_API_ORIGIN for relative API base', () => {
    vi.stubEnv('VITE_API_URL', '/api/v1');
    vi.stubEnv('VITE_API_ORIGIN', 'https://jobai.example');
    expect(getRealtimeHttpEndpoint()).toBe('https://jobai.example/api/v1/ws');
  });

  it('maps job events to jobs + analytics keys', () => {
    const keys = queryKeysForEvent('job.matched').map((k) => k[0]);
    expect(keys).toContain('jobs');
    expect(keys).toContain('analytics');
    expect(keys).toContain('pipeline');
  });

  it('maps approval events to approvals queue', () => {
    const keys = queryKeysForEvent('approval.needed').map((k) => k[0]);
    expect(keys).toContain('approvals');
    expect(keys).toContain('approval-blockers');
    expect(keys).toContain('weekly-story');
  });

  it('maps apply blockers to applications + blockers', () => {
    const keys = queryKeysForEvent('application.needs_otp').map((k) => k[0]);
    expect(keys).toContain('applications');
    expect(keys).toContain('approval-blockers');
  });

  it('maps email inbox events to email + pipeline keys', () => {
    const keys = queryKeysForEvent('email.applied').map((k) => k[0]);
    expect(keys).toContain('email-messages');
    expect(keys).toContain('pipeline');
    expect(keys).toContain('calendar');
  });

  it('maps portal sync lifecycle to portals + automation keys', () => {
    for (const event of ['portal.sync_started', 'portal.synced', 'portal.health']) {
      const keys = queryKeysForEvent(event).map((k) => k[0]);
      expect(keys).toContain('portals');
      expect(keys).toContain('automation-logs');
    }
    expect(shouldToastEvent('portal.sync_started')).toBe(true);
  });

  it('toasts worker-driven events but not mutation echoes', () => {
    expect(shouldToastEvent('approval.needed')).toBe(true);
    expect(shouldToastEvent('job.success')).toBe(true);
    expect(shouldToastEvent('approval.decided')).toBe(false);
    expect(shouldToastEvent('automation.triggered')).toBe(false);
  });
});
