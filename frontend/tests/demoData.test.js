import { describe, expect, it } from 'vitest';
import { resolveDemoData } from '../src/lib/demoData';

describe('guest demo data', () => {
  it('returns analytics for reports analytics path', () => {
    const data = resolveDemoData('http://localhost:8000/api/v1/reports/analytics', 'get');
    expect(data.jobs_found).toBeGreaterThan(0);
  });

  it('returns jobs list for /jobs', () => {
    const data = resolveDemoData('/api/v1/jobs', 'get');
    expect(data.items.length).toBeGreaterThan(0);
  });

  it('does not resolve write methods', () => {
    expect(resolveDemoData('/api/v1/jobs', 'post')).toBeUndefined();
  });

  it('returns question bank demo data', () => {
    const data = resolveDemoData('/api/v1/questions', 'get');
    expect(Array.isArray(data)).toBe(true);
    expect(data.length).toBeGreaterThan(0);
  });

  it('returns approval blockers demo data', () => {
    const data = resolveDemoData('/api/v1/approvals/blockers', 'get');
    expect(Array.isArray(data)).toBe(true);
    expect(data[0].blocker_type).toBe('unknown_question');
  });

  it('returns weekly story and pipeline for digest', () => {
    const story = resolveDemoData('/api/v1/reports/weekly-story', 'get');
    expect(story.applied).toBeGreaterThan(0);
    const pipeline = resolveDemoData('/api/v1/jobs/pipeline', 'get');
    expect(pipeline.columns.matched.length).toBeGreaterThan(0);
  });

  it('returns email inbox demo data', () => {
    const accounts = resolveDemoData('/api/v1/email/accounts', 'get');
    expect(accounts.length).toBeGreaterThan(0);
    const messages = resolveDemoData('/api/v1/email/messages', 'get');
    expect(messages.items[0].event_type).toBe('interview_schedule');
  });
});
