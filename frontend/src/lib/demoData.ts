/** Demo payloads served to guests so they can browse features without an account. */

const now = new Date().toISOString();

export const demoAnalytics = {
  jobs_found: 128,
  applied: 24,
  pending: 7,
  success_rate: 68,
  daily_applications: [
    { date: 'Mon', count: 3 },
    { date: 'Tue', count: 5 },
    { date: 'Wed', count: 2 },
    { date: 'Thu', count: 6 },
    { date: 'Fri', count: 4 },
    { date: 'Sat', count: 1 },
    { date: 'Sun', count: 3 },
  ],
  portal_stats: [
    { portal: 'linkedin', count: 42 },
    { portal: 'indeed', count: 31 },
    { portal: 'greenhouse', count: 18 },
    { portal: 'lever', count: 12 },
  ],
};

export const demoJobs = {
  items: [
    {
      id: 'demo-job-1',
      title: 'Senior Frontend Engineer',
      company: 'Northwind Labs',
      location: 'Remote',
      portal: 'linkedin',
      status: 'matched',
      match_score: 0.92,
      match_breakdown: {
        total: 0.92,
        skills: 0.95,
        keywords: 0.9,
        location: 1,
        experience: 0.85,
        reasons: ['Strong React match', 'Remote-friendly', 'TypeScript required'],
        missing_skills: ['GraphQL'],
      },
    },
    {
      id: 'demo-job-2',
      title: 'Full-Stack Engineer',
      company: 'Harbor AI',
      location: 'Austin, TX',
      portal: 'greenhouse',
      status: 'tracked',
      match_score: 0.81,
    },
    {
      id: 'demo-job-3',
      title: 'Platform Engineer',
      company: 'Cedar Systems',
      location: 'New York, NY',
      portal: 'lever',
      status: 'awaiting_approval',
      match_score: 0.76,
    },
  ],
  total: 3,
  page: 1,
  page_size: 50,
  pages: 1,
};

export const demoApprovals = {
  items: [
    {
      id: 'demo-approval-1',
      job_id: 'demo-job-3',
      summary: 'Platform Engineer at Cedar Systems',
      match_score: 0.76,
      status: 'pending',
      created_at: now,
    },
  ],
  total: 1,
  page: 1,
  page_size: 50,
  pages: 1,
};

export const demoActivity = {
  items: [
    {
      id: 'demo-act-1',
      action: 'job.matched',
      message: 'Matched Senior Frontend Engineer (92%)',
      resource_type: 'job',
      job_id: 'demo-job-1',
      severity: 'success',
      source: 'worker',
      created_at: now,
    },
    {
      id: 'demo-act-2',
      action: 'approval.needed',
      message: 'Approval needed for Platform Engineer',
      resource_type: 'approval',
      job_id: 'demo-job-3',
      severity: 'warning',
      source: 'worker',
      created_at: now,
    },
    {
      id: 'demo-act-3',
      action: 'portal.synced',
      message: 'LinkedIn sync complete',
      resource_type: 'portal',
      severity: 'info',
      source: 'worker',
      created_at: now,
    },
  ],
  total: 3,
  page: 1,
  page_size: 50,
  pages: 1,
};

export const demoPortals = [
  { id: 'demo-portal-1', name: 'linkedin', status: 'connected', last_sync_at: now },
  { id: 'demo-portal-2', name: 'indeed', status: 'connected', last_sync_at: now },
];

export const demoCompanies = {
  items: [
    {
      id: 'demo-co-1',
      name: 'Northwind Labs',
      platform: 'greenhouse',
      priority: 1,
      status: 'active',
      career_url: 'https://example.com/careers',
    },
  ],
  total: 1,
  page: 1,
  page_size: 25,
  pages: 1,
};

export const demoSettings = {
  match_threshold: 0.7,
  auto_apply: false,
  require_approval: true,
  use_llm_ranking: true,
  max_applications_per_day: 15,
  apply_cooldown_seconds: 45,
  batch_min_score: 0.85,
  headless: true,
  timezone: 'UTC',
  notification_email: true,
  follow_up_days: 7,
};

export const demoQuestions = [
  {
    id: 'demo-q-1',
    question: 'How many years of experience do you have?',
    answer: '5',
    tags: ['default'],
    portals: [],
    use_count: 12,
  },
  {
    id: 'demo-q-2',
    question: 'Do you require sponsorship?',
    answer: 'No',
    tags: ['default'],
    portals: [],
    use_count: 8,
  },
];

export const demoBlockers = [
  {
    application_id: 'demo-app-1',
    job_id: 'demo-job-1',
    status: 'needs_input',
    blocker_type: 'unknown_question',
    unknown_questions: ['Are you willing to relocate?'],
    error_message: 'Paused — answer unknown form questions to resume',
    session_steps: [
      { key: 'opened_jd', label: 'Opened job description', status: 'ok' },
      { key: 'clicked_apply', label: 'Clicked Easy Apply / Apply', status: 'ok' },
      { key: 'needs_input', label: 'Paused for unknown questions', status: 'pending' },
    ],
    portal: 'linkedin',
    title: 'Senior Frontend Engineer',
    company: 'Northwind Labs',
    updated_at: now,
  },
];

export const demoProfile = {
  id: 'demo-user',
  email: 'guest@jobpilot.ai',
  full_name: 'Guest Explorer',
  roles: ['user'],
  is_active: true,
  profile: {
    skills: ['React', 'TypeScript', 'Python', 'FastAPI'],
    keywords: ['remote', 'frontend', 'platform'],
    location: 'Remote',
    experience_years: 5,
    notice_period_days: 30,
    linkedin_url: '',
    github_url: '',
    portfolio_url: '',
  },
};

export const demoAutomationStatus = {
  user_id: 'demo-user',
  total_logs: 12,
  workers: { fetch: 'idle', match: 'idle', apply: 'idle', notification: 'idle', report: 'idle' },
  recent: [],
};

export const demoAutomationLogs = {
  items: [
    {
      id: 'demo-log-1',
      created_at: now,
      portal: 'linkedin',
      action: 'fetch',
      level: 'info',
      message: 'Synced 18 new roles',
    },
  ],
  total: 1,
  page: 1,
  page_size: 50,
  pages: 1,
};

export const demoReports = {
  items: [
    { id: 'demo-report-1', type: 'custom', format: 'csv', status: 'ready', created_at: now },
  ],
  total: 1,
  page: 1,
  page_size: 25,
  pages: 1,
};

export const demoOnboarding = {
  completed: false,
  step: 'profile',
  steps: ['profile', 'resume', 'portals', 'sync', 'done'],
  checklist: { profile: false, resume: false, portals: false },
};

export const demoCalendar: unknown[] = [];
export const demoReminders: unknown[] = [];

/** Map API paths (without query) to demo payloads. */
export function resolveDemoData(url = '', method = 'get'): unknown | undefined {
  if (method.toLowerCase() !== 'get') return undefined;
  const path = url.split('?')[0].replace(/\/$/, '');

  if (path.endsWith('/reports/analytics') || path.includes('/reports/analytics')) return demoAnalytics;
  if (path.match(/\/jobs\/[^/]+\/activity$/)) return demoActivity;
  if (path.includes('/jobs/tracked') || path.includes('/jobs/applied') || path.includes('/jobs/history')) {
    return demoJobs;
  }
  if (path.match(/\/jobs\/[^/]+$/) && !path.endsWith('/jobs')) {
    return demoJobs.items[0];
  }
  if (path.endsWith('/jobs') || path.includes('/jobs?')) return demoJobs;
  if (path.includes('/approvals/blockers')) return demoBlockers;
  if (path.includes('/approvals')) return demoApprovals;
  if (path.includes('/activity') || path.includes('/users/me/activity')) return demoActivity;
  if (path.includes('/job-portals')) return demoPortals;
  if (path.includes('/companies')) return demoCompanies;
  if (path.includes('/settings')) return demoSettings;
  if (path.endsWith('/users/me') || path.includes('/users/me?')) return demoProfile;
  if (path.includes('/users/me/resumes')) return [];
  if (path.includes('/automation/status')) return demoAutomationStatus;
  if (path.includes('/automation/logs')) return demoAutomationLogs;
  if (path.includes('/reports') && !path.includes('analytics') && !path.includes('download')) {
    return demoReports;
  }
  if (path.includes('/onboarding')) return demoOnboarding;
  if (path.includes('/calendar')) return demoCalendar;
  if (path.includes('/reminders')) return demoReminders;
  if (path.includes('/questions')) return demoQuestions;
  if (path.includes('/notification-channels')) return [];
  if (path.includes('/applications')) return { items: [], total: 0, page: 1, page_size: 20, pages: 0 };

  return { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
}
