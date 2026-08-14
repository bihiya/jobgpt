import { describe, expect, it } from 'vitest';
import { groupPortalRuns, lastPortalRun, withLiveRun } from '../src/utils/loginStory';

describe('lastPortalRun', () => {
  it('returns chronological steps for the latest LinkedIn sync', () => {
    const logs = [
      { id: '9', created_at: 't9', portal: 'linkedin', action: 'fetch.done', message: 'Fetch finished' },
      { id: '8', created_at: 't8', portal: 'linkedin', action: 'fetch.failed', message: 'linkedin sync failed: checkpoint' },
      { id: '7', created_at: 't7', portal: 'linkedin', action: 'fetch.login', message: 'Login blocked: [CHECKPOINT]' },
      { id: '6', created_at: 't6', portal: 'linkedin', action: 'fetch.login', message: 'After submit — checkpoint URL' },
      { id: '5', created_at: 't5', portal: 'linkedin', action: 'fetch.login', message: 'Clicked Sign in / submit' },
      { id: '4', created_at: 't4', portal: 'linkedin', action: 'fetch.login', message: 'Filled password' },
      { id: '3', created_at: 't3', portal: 'linkedin', action: 'fetch.login', message: 'Filled email / username' },
      { id: '2', created_at: 't2', portal: 'linkedin', action: 'fetch.login', message: 'Login page opened' },
      { id: '1', created_at: 't1', portal: 'linkedin', action: 'fetch.portal', message: 'Fetching jobs from linkedin…' },
      { id: '0', created_at: 't0', portal: 'linkedin', action: 'fetch.login', message: 'older run' },
    ];
    const steps = lastPortalRun(logs, 'linkedin');
    expect(steps.map((s) => s.message)).toEqual([
      'Fetching jobs from linkedin…',
      'Login page opened',
      'Filled email / username',
      'Filled password',
      'Clicked Sign in / submit',
      'After submit — checkpoint URL',
      'Login blocked: [CHECKPOINT]',
      'linkedin sync failed: checkpoint',
      'Fetch finished',
    ]);
  });
});

describe('groupPortalRuns', () => {
  it('groups two syncs by correlation_id, newest first', () => {
    const logs = [
      { id: 'b2', created_at: 't4', portal: 'linkedin', action: 'fetch.failed', message: 'checkpoint', correlation_id: 'run-b', level: 'error' },
      { id: 'b1', created_at: 't3', portal: 'linkedin', action: 'fetch.portal', message: 'Fetching jobs from linkedin…', correlation_id: 'run-b' },
      { id: 'a2', created_at: 't2', portal: 'linkedin', action: 'fetch.complete', message: 'added 3', correlation_id: 'run-a', level: 'success' },
      { id: 'a1', created_at: 't1', portal: 'linkedin', action: 'fetch.portal', message: 'Fetching jobs from linkedin…', correlation_id: 'run-a' },
    ];
    const runs = groupPortalRuns(logs, 'linkedin');
    expect(runs.map((r) => r.id)).toEqual(['run-b', 'run-a']);
    expect(runs[0].outcome).toBe('error');
    expect(runs[0].steps.map((s) => s.id)).toEqual(['b1', 'b2']);
    expect(runs[1].outcome).toBe('success');
    expect(runs[1].stepCount).toBe(2);
  });
});

describe('withLiveRun', () => {
  it('pins a pending sync id on top before worker logs arrive', () => {
    const live = withLiveRun([], { id: 'abc123def', portal: 'linkedin' });
    expect(live[0].id).toBe('abc123def');
    expect(live[0].steps[0].message).toMatch(/queued/i);
    expect(live[0].steps[0].correlation_id).toBe('abc123def');
  });

  it('adopts server logs onto the live sync id via aliases', () => {
    const logs = [
      { id: '1', created_at: 't1', portal: 'linkedin', action: 'fetch.login', message: 'Login page opened', correlation_id: 'server-cid' },
    ];
    const runs = withLiveRun(groupPortalRuns(logs, 'linkedin'), {
      id: 'server-cid',
      portal: 'linkedin',
      aliasIds: ['local-cid'],
    });
    expect(runs[0].id).toBe('server-cid');
    expect(runs[0].steps.map((s) => s.message)).toEqual(['Login page opened']);
  });
});
