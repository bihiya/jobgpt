import { describe, expect, it } from 'vitest';
import { lastPortalRun } from '../src/utils/loginStory';

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
