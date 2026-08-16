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
    expect(pipeline.columns.fetched.length).toBeGreaterThan(0);
    expect(pipeline.columns.queued.length).toBeGreaterThan(0);
    expect(pipeline.columns.applied.length).toBeGreaterThan(0);
    expect(pipeline.columns.queued[0].application.session_steps.length).toBeGreaterThan(2);
  });

  it('returns resume versions for the profile page', () => {
    const data = resolveDemoData('/api/v1/users/me/resumes', 'get');
    expect(data).toHaveLength(3);
    expect(data[0].name).toBe('Guest_Explorer_Resume.pdf');
    expect(data[1].name).toBe('Guest_Explorer_Resume_v2.pdf');
    expect(data[0].is_default).toBe(true);
  });

  it('returns the listing URL on a single job fetch', () => {
    const data = resolveDemoData('/api/v1/jobs/demo-job-1', 'get');
    expect(data.title).toBe('Senior Frontend Engineer');
    expect(data.apply_url).toContain('linkedin.com/jobs/view/');
    expect(data.description).toMatch(/React/);
  });
});
