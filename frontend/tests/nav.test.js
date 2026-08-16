import { describe, expect, it } from 'vitest';
import { JOB_TAB_PATHS, JOB_TABS, SIDEBAR_NAV, SIDEBAR_SECTIONS } from '../src/layouts/nav';

describe('sidebar nav', () => {
  it('keeps every unique page visible (no collapsed groups, no buried extras)', () => {
    const paths = SIDEBAR_NAV.map((item) => item.path);
    expect(paths).toEqual([
      '/dashboard',
      '/jobs',
      '/pipeline',
      '/approvals',
      '/automation',
      '/email',
      '/job-portals',
      '/companies',
      '/questions',
      '/onboarding',
      '/calendar',
      '/activity',
      '/reports',
      '/profile',
      '/settings',
    ]);
    expect(SIDEBAR_SECTIONS.every((section) => section.items.length > 0)).toBe(true);
  });

  it('does not list job sub-routes in the sidebar', () => {
    const paths = SIDEBAR_NAV.map((item) => item.path);
    expect(paths).not.toContain('/jobs/tracked');
    expect(paths).not.toContain('/jobs/applied');
    expect(paths).not.toContain('/jobs/history');
  });
});

describe('jobs tabs', () => {
  it('maps All / Tracked / Applied / History onto the job list routes', () => {
    expect(JOB_TABS.map((tab) => tab.value)).toEqual(['all', 'tracked', 'applied', 'history']);
    expect(JOB_TAB_PATHS).toEqual({
      all: '/jobs',
      tracked: '/jobs/tracked',
      applied: '/jobs/applied',
      history: '/jobs/history',
    });
  });
});
