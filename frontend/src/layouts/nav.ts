export type PrefetchKey = 'dashboard' | 'jobs';

export type NavLink = {
  label: string;
  path: string;
  prefetch?: PrefetchKey;
  match?: 'exact' | 'prefix';
};

export type NavSection = {
  label: string;
  items: NavLink[];
};

/** Always-visible sidebar. Job All/Tracked/Applied/History live as tabs on Jobs. */
export const SIDEBAR_SECTIONS: NavSection[] = [
  {
    label: 'Work',
    items: [
      { label: 'Digest', path: '/dashboard', prefetch: 'dashboard' },
      { label: 'Jobs', path: '/jobs', prefetch: 'jobs', match: 'prefix' },
      { label: 'Pipeline', path: '/pipeline' },
      { label: 'Approvals', path: '/approvals' },
      { label: 'Automation', path: '/automation' },
      { label: 'Email', path: '/email' },
    ],
  },
  {
    label: 'Setup',
    items: [
      { label: 'Portals', path: '/job-portals' },
      { label: 'Companies', path: '/companies' },
      { label: 'Questions', path: '/questions' },
      { label: 'Onboarding', path: '/onboarding' },
    ],
  },
  {
    label: 'More',
    items: [
      { label: 'Calendar', path: '/calendar' },
      { label: 'Activity', path: '/activity' },
      { label: 'Reports', path: '/reports', prefetch: 'dashboard' },
      { label: 'Profile', path: '/profile' },
      { label: 'Settings', path: '/settings' },
    ],
  },
];

export const SIDEBAR_NAV: NavLink[] = SIDEBAR_SECTIONS.flatMap((section) => section.items);

export const JOB_TAB_PATHS: Record<'all' | 'tracked' | 'applied' | 'history', string> = {
  all: '/jobs',
  tracked: '/jobs/tracked',
  applied: '/jobs/applied',
  history: '/jobs/history',
};

export const JOB_TABS: { value: keyof typeof JOB_TAB_PATHS; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'tracked', label: 'Tracked' },
  { value: 'applied', label: 'Applied' },
  { value: 'history', label: 'History' },
];

export const TITLE_NAV: NavLink[] = [
  ...SIDEBAR_NAV,
  { label: 'Tracked jobs', path: '/jobs/tracked' },
  { label: 'Applied jobs', path: '/jobs/applied' },
  { label: 'Job history', path: '/jobs/history' },
];
