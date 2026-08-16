import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  automationLogFromEvent,
  getRealtimeHttpEndpoint,
  patchApplicationSession,
  patchPipelineSession,
  prependAutomationLog,
  queryKeysForEvent,
  shouldToastEvent,
} from '../src/lib/realtime';

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

  it('maps portal sync lifecycle to portals without refetching logs every event', () => {
    expect(queryKeysForEvent('portal.sync_started').map((k) => k[0])).toEqual(['portals']);
    const synced = queryKeysForEvent('portal.synced').map((k) => k[0]);
    expect(synced).toContain('portals');
    expect(synced).not.toContain('automation-logs');
    expect(queryKeysForEvent('automation.log')).toEqual([]);
    expect(shouldToastEvent('portal.sync_started')).toBe(false);
    expect(shouldToastEvent('portal.synced')).toBe(true);
  });

  it('toasts worker-driven events but not mutation echoes', () => {
    expect(shouldToastEvent('approval.needed')).toBe(true);
    expect(shouldToastEvent('job.success')).toBe(true);
    expect(shouldToastEvent('approval.decided')).toBe(false);
    expect(shouldToastEvent('automation.triggered')).toBe(false);
  });

  it('maps automation.log socket frames onto the logs list without duplicates', () => {
    const item = automationLogFromEvent({
      event: 'automation.log',
      ts: '2026-08-14T17:40:00Z',
      body: 'Filled password',
      data: {
        id: 'log-1',
        action: 'fetch.login',
        level: 'info',
        message: 'Filled password',
        portal: 'linkedin',
        correlation_id: 'sync-abc',
      },
    });
    expect(item).toMatchObject({
      id: 'log-1',
      action: 'fetch.login',
      portal: 'linkedin',
      correlation_id: 'sync-abc',
      created_at: '2026-08-14T17:40:00Z',
    });
    const once = prependAutomationLog({ items: [], total: 0 }, item);
    const twice = prependAutomationLog(once, item);
    expect(once.items).toHaveLength(1);
    expect(twice.items).toHaveLength(1);
    expect(twice.total).toBe(1);
  });

  it('does not HTTP-refetch on every apply session step', () => {
    expect(queryKeysForEvent('application.session')).toEqual([]);
  });

  it('patches live apply steps onto applications and pipeline caches', () => {
    const data = {
      application_id: 'app-1',
      job_id: 'job-1',
      status: 'in_progress',
      steps: [{ key: 'opened_jd', label: 'Opened job description' }],
      updated_at: '2026-08-16T11:05:00Z',
    };
    const apps = patchApplicationSession(
      { items: [{ id: 'app-1', job_id: 'job-1', status: 'pending', session_steps: [] }], total: 1 },
      data,
    );
    expect(apps.items[0].status).toBe('in_progress');
    expect(apps.items[0].session_steps).toHaveLength(1);
    const pipeline = patchPipelineSession(
      {
        columns: {
          queued: [{ id: 'job-1', title: 'Eng', application: { id: 'app-1', status: 'pending', session_steps: [] } }],
        },
      },
      data,
    );
    expect(pipeline.columns.queued[0].application.session_steps[0].key).toBe('opened_jd');
  });
});
