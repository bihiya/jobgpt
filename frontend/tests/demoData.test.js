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
});
