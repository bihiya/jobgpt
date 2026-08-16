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
      salary: '$160K – $190K / yr',
      experience: '5+ years',
      description:
        'About the job\nSenior Frontend Engineer\nNorthwind Labs\nRemote\n\nWe are hiring a Senior Frontend Engineer to own the product surface candidates see every day.\n\nResponsibilities\n• Build listing pages, match explanations, and apply workflows in React and TypeScript\n• Partner with design on a system that stays readable in light and dark themes\n• Ship accessible, high-contrast job details that feel like a LinkedIn posting\n\nRequirements\n• 5+ years building web apps with React\n• Strong TypeScript and design-system experience\n• Comfort working with REST APIs and real-time updates\n\nBenefits\n• Remote-first team\n• $160K – $190K / yr',
      skills: ['React', 'TypeScript', 'MUI'],
      apply_url: 'https://www.linkedin.com/jobs/view/4123456789/',
      listing_url: 'https://www.linkedin.com/jobs/view/4123456789/',
      portal: 'linkedin',
      status: 'matched',
      match_score: 0.92,
      source: 'portal',
      external_id: 'linkedin-4123456789',
      fetched_at: now,
      created_at: now,
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
      status: 'applying',
      match_score: 0.81,
      description: 'Ship product features across React and Python APIs.',
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
      job_id: 'demo-job-1',
      summary: 'Senior Frontend Engineer at Northwind Labs',
      title: 'Senior Frontend Engineer',
      company: 'Northwind Labs',
      portal: 'linkedin',
      match_score: 0.92,
      status: 'pending',
      created_at: now,
    },
    {
      id: 'demo-approval-2',
      job_id: 'demo-job-3',
      summary: 'Platform Engineer at Cedar Systems',
      title: 'Platform Engineer',
      company: 'Cedar Systems',
      portal: 'lever',
      match_score: 0.76,
      status: 'pending',
      created_at: now,
    },
  ],
  total: 2,
  page: 1,
  page_size: 50,
  pages: 1,
};

export const demoWeeklyStory = {
  headline: '24 applied · 6 replies · 2 interviews',
  narrative:
    'This week you applied to 24 roles. 6 engagement signals showed up and 2 moved to interview. Clear 2 pending approvals to keep the pipeline moving.',
  applied: 24,
  replies: 6,
  interviews: 2,
  offers: 0,
  approvals_pending: 2,
  blockers: 1,
  top_portal: 'linkedin',
  period_label: 'This week',
  highlights: [
    'You pushed 24 applications this week.',
    '6 reply signals (follow-ups / interviews).',
    '2 interview stage moves.',
    'Most activity came from linkedin.',
  ],
};

export const demoPipeline = {
  columns: {
    fetched: [
      {
        id: 'demo-job-1',
        title: 'Senior Frontend Engineer',
        company: 'Northwind Labs',
        portal: 'linkedin',
        status: 'matched',
        match_score: 0.92,
        location: 'Remote',
      },
      {
        id: 'demo-job-4',
        title: 'Staff Product Engineer',
        company: 'Lumen Forge',
        portal: 'indeed',
        status: 'new',
        match_score: 0.84,
        location: 'Remote',
      },
    ],
    queued: [
      {
        id: 'demo-job-2',
        title: 'Full-Stack Engineer',
        company: 'Harbor AI',
        portal: 'greenhouse',
        status: 'applying',
        match_score: 0.81,
        location: 'Austin, TX',
        updated_at: now,
        application: {
          id: 'demo-app-live',
          job_id: 'demo-job-2',
          status: 'in_progress',
          attempts: 1,
          error_message: '',
          updated_at: now,
          created_at: now,
          session_steps: [
            { key: 'queued', label: 'Queued for auto-apply', status: 'ok', detail: 'Waiting for worker to start', at: now },
            { key: 'started', label: 'Worker started applying', status: 'ok', detail: 'greenhouse', at: now },
            { key: 'opened_jd', label: 'Opened job description', status: 'ok', at: now },
            { key: 'clicked_apply', label: 'Clicked LinkedIn Easy Apply', status: 'ok', at: now },
            { key: 'filled_fields', label: 'Filled 4 fields', status: 'ok', at: now },
          ],
          blocker_type: '',
        },
      },
    ],
    applied: [
      {
        id: 'demo-job-3',
        title: 'Platform Engineer',
        company: 'Cedar Systems',
        portal: 'lever',
        status: 'applied',
        match_score: 0.76,
        location: 'New York, NY',
      },
    ],
    interview: [
      {
        id: 'demo-job-5',
        title: 'Frontend Engineer',
        company: 'Atlas Cloud',
        portal: 'ashby',
        status: 'interview',
        match_score: 0.88,
        location: 'Remote',
      },
    ],
    shortlisted: [],
  },
  counts: { fetched: 2, queued: 1, applied: 1, interview: 1, shortlisted: 0 },
};

export const demoApplications = {
  items: [
    {
      id: 'demo-app-live',
      job_id: 'demo-job-2',
      status: 'in_progress',
      attempts: 1,
      screenshot_path: '',
      error_message: '',
      applied_at: null,
      created_at: now,
      session_steps: [
        { key: 'queued', label: 'Queued for auto-apply', status: 'ok', detail: 'Waiting for worker to start', at: now },
        { key: 'started', label: 'Worker started applying', status: 'ok', detail: 'greenhouse', at: now },
        { key: 'opened_jd', label: 'Opened job description', status: 'ok', at: now },
        { key: 'clicked_apply', label: 'Clicked LinkedIn Easy Apply', status: 'ok', at: now },
        { key: 'filled_fields', label: 'Filled 4 fields', status: 'ok', at: now },
      ],
      unknown_questions: [],
      blocker_type: '',
      updated_at: now,
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
      action: 'settings.updated',
      message: 'changed auto_apply, match_threshold, require_approval',
      summary: 'Alex Rivera updated settings — changed auto_apply, match_threshold · Passed',
      outcome: 'Passed',
      next_step: 'New settings apply on the next fetch, match, or apply run.',
      actor_name: 'Alex Rivera',
      resource_type: 'settings',
      resource_id: 'demo-user',
      severity: 'success',
      source: 'user',
      created_at: now,
      metadata: {
        fields: ['auto_apply', 'match_threshold', 'require_approval'],
        changes: [
          { field: 'auto_apply', from: false, to: true },
          { field: 'match_threshold', from: 0.7, to: 0.85 },
          { field: 'require_approval', from: true, to: false },
        ],
      },
    },
    {
      id: 'demo-act-2',
      action: 'approval.approved',
      message: 'Approved “Senior Frontend Engineer” — apply will start next',
      summary: 'Alex Rivera approved an application — Approved “Senior Frontend Engineer” · Passed',
      outcome: 'Passed',
      next_step: 'Watch Automation for apply progress.',
      actor_name: 'Alex Rivera',
      resource_type: 'approval',
      job_id: 'demo-job-1',
      severity: 'success',
      source: 'user',
      created_at: now,
      metadata: {},
    },
    {
      id: 'demo-act-3',
      action: 'application.failed',
      message: 'LinkedIn apply failed — Easy Apply button not found',
      summary: 'JobPilot failed an application — LinkedIn apply failed · Failed',
      outcome: 'Failed',
      next_step: 'Check Automation logs, then retry from Applications.',
      actor_name: 'JobPilot',
      resource_type: 'application',
      job_id: 'demo-job-2',
      severity: 'error',
      source: 'worker',
      created_at: now,
      metadata: { portal: 'linkedin' },
    },
    {
      id: 'demo-act-4',
      action: 'job.matched',
      message: 'Matched Senior Frontend Engineer (92%)',
      summary: 'JobPilot matched a job — Matched Senior Frontend Engineer (92%) · Passed',
      outcome: 'Passed',
      next_step: 'Review the score in Approvals or Pipeline.',
      actor_name: 'JobPilot',
      resource_type: 'job',
      job_id: 'demo-job-1',
      severity: 'success',
      source: 'worker',
      created_at: now,
      metadata: { match_score: 0.92 },
    },
    {
      id: 'demo-act-5',
      action: 'approval.needed',
      message: 'Approval needed for Platform Engineer',
      summary: 'JobPilot flagged a job for approval — Approval needed for Platform Engineer · Needs attention',
      outcome: 'Needs attention',
      next_step: 'Open Approvals — approve to apply, or reject to skip.',
      actor_name: 'JobPilot',
      resource_type: 'approval',
      job_id: 'demo-job-3',
      severity: 'warning',
      source: 'worker',
      created_at: now,
      metadata: { note: 'Score below auto-apply threshold' },
    },
    {
      id: 'demo-act-6',
      action: 'portal.synced',
      message: 'LinkedIn sync complete — added 12 new jobs',
      summary: 'JobPilot synced a job portal — LinkedIn sync complete · Happened',
      outcome: 'Happened',
      next_step: 'New jobs are ready — run Match, or wait for automatic matching.',
      actor_name: 'JobPilot',
      resource_type: 'portal',
      severity: 'info',
      source: 'worker',
      created_at: now,
      metadata: { portal: 'linkedin', inserted: 12 },
    },
  ],
  total: 6,
  page: 1,
  page_size: 50,
  pages: 1,
};

export const demoPortals = [
  {
    id: 'demo-portal-1',
    name: 'linkedin',
    status: 'connected',
    last_sync_at: now,
    last_attempt_at: now,
    sync_started_at: null,
    has_credentials: true,
    has_password: true,
    username: 'you@linkedin.example',
    has_session: true,
    session_updated_at: now,
    session_identity: {
      display_name: 'Ada Lovelace',
      headline: 'Software Engineer',
      location: 'Bengaluru, Karnataka, India',
      profile_url: 'https://www.linkedin.com/in/ada-lovelace/',
      public_id: 'ada-lovelace',
      captured_at: now,
    },
    health: { score: 92, auto_paused: false, last_error: '', consecutive_failures: 0 },
  },
  {
    id: 'demo-portal-2',
    name: 'indeed',
    status: 'connected',
    last_sync_at: now,
    last_attempt_at: now,
    sync_started_at: null,
    has_credentials: true,
    has_password: true,
    username: 'you@indeed.example',
    has_session: false,
    session_updated_at: null,
    health: { score: 48, auto_paused: true, last_error: 'login expired', consecutive_failures: 3 },
  },
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
  {
    id: 'demo-q-3',
    question: 'Are you willing to relocate?',
    answer: 'Yes, for the right role',
    tags: ['from_apply'],
    portals: ['linkedin'],
    use_count: 1,
  },
];

export const demoBlockers = [
  {
    id: 'app-demo-app-1',
    application_id: 'demo-app-1',
    job_id: 'demo-job-1',
    status: 'needs_input',
    blocker_type: 'unknown_question',
    unknown_questions: ['Are you willing to relocate?'],
    error_message: 'Paused — answer unknown form questions to resume',
    session_steps: [
      { key: 'opened_jd', label: 'Opened job description', status: 'ok' },
      { key: 'clicked_apply', label: 'Clicked LinkedIn Easy Apply', status: 'ok' },
      { key: 'needs_input', label: 'Paused for unknown questions', status: 'pending' },
    ],
    portal: 'linkedin',
    title: 'Senior Frontend Engineer',
    company: 'Northwind Labs',
    updated_at: now,
  },
  {
    id: 'portal-demo-portal-2',
    application_id: '',
    portal_id: 'demo-portal-2',
    job_id: '',
    status: 'login_expired',
    blocker_type: 'login_expired',
    unknown_questions: [],
    error_message: 'Portal session expired — re-authenticate',
    session_steps: [],
    portal: 'indeed',
    title: 'indeed connection',
    company: '',
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
    linkedin_url: 'https://www.linkedin.com/in/guest-explorer/',
    github_url: 'https://github.com/guest-explorer',
    portfolio_url: 'https://guest.jobpilot.ai',
    salary_expectation: { min: 120000, max: 160000, currency: 'USD' },
  },
};

export const demoResumes = [
  {
    id: 'demo-resume-1',
    name: 'Guest_Explorer_Resume.pdf',
    file_type: 'pdf',
    is_default: true,
    created_at: now,
  },
  {
    id: 'demo-resume-2',
    name: 'Guest_Explorer_Resume_v2.pdf',
    file_type: 'pdf',
    is_default: false,
    created_at: now,
  },
  {
    id: 'demo-resume-3',
    name: 'Guest_Explorer_Cover_Letter.pdf',
    file_type: 'pdf',
    is_default: false,
    created_at: now,
  },
];

export const demoAutomationStatus = {
  user_id: 'demo-user',
  total_logs: 12,
  workers: { fetch: 'idle', match: 'idle', apply: 'idle', notification: 'idle', report: 'idle' },
  playwright_available: true,
  playwright_message: null,
  kafka_enabled: true,
  recent: [],
};

export const demoAutomationLogs = {
  items: [
    {
      id: 'demo-log-3',
      created_at: now,
      portal: 'linkedin',
      action: 'fetch.complete',
      level: 'success',
      message: 'linkedin: found 18, added 18 new job(s)',
      correlation_id: 'demo-sync-1',
    },
    {
      id: 'demo-log-2',
      created_at: now,
      portal: 'linkedin',
      action: 'fetch.extract',
      level: 'info',
      message: 'Found 18 job listing(s)',
      correlation_id: 'demo-sync-1',
    },
    {
      id: 'demo-log-1',
      created_at: now,
      portal: 'linkedin',
      action: 'fetch.portal',
      level: 'info',
      message: 'Fetching jobs from linkedin…',
      correlation_id: 'demo-sync-1',
    },
  ],
  total: 3,
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

export const demoEmailAccounts = [
  {
    id: 'demo-email-1',
    label: 'Gmail',
    email_address: 'you@gmail.com',
    imap_host: 'imap.gmail.com',
    imap_port: 993,
    username: 'you@gmail.com',
    use_ssl: true,
    mailbox: 'INBOX',
    enabled: true,
    auto_apply: true,
    last_sync_at: now,
    last_error: '',
    has_password: true,
  },
];

export const demoEmailMessages = {
  items: [
    {
      id: 'demo-mail-1',
      account_id: 'demo-email-1',
      message_id: '<demo-1@acme.com>',
      subject: 'Interview scheduled — Platform Engineer',
      sender: 'Talent at Acme <recruiter@acme.com>',
      recipients: ['you@gmail.com'],
      received_at: now,
      snippet: 'We would like to schedule an interview on Tuesday at 3pm via Zoom.',
      body_text: 'Hi, interview scheduled for Tuesday Mar 10 at 3pm via Zoom https://zoom.us/j/123',
      event_type: 'interview_schedule',
      confidence: 0.9,
      matched_job_id: 'demo-job-3',
      matched_company: 'Acme',
      extracted: {
        company: 'Acme',
        job_title: 'Platform Engineer',
        interview_at: now,
        meeting_url: 'https://zoom.us/j/123',
      },
      sync_status: 'pending',
      applied_actions: [],
      created_at: now,
    },
    {
      id: 'demo-mail-2',
      account_id: 'demo-email-1',
      message_id: '<demo-2@harbor.ai>',
      subject: 'Job description for Full-Stack Engineer',
      sender: 'Harbor Talent <talent@harbor.ai>',
      recipients: ['you@gmail.com'],
      received_at: now,
      snippet: "Here's the full job description for the Full-Stack Engineer role.",
      body_text: "Here's the full job description for the Full-Stack Engineer role at Harbor.",
      event_type: 'jd_received',
      confidence: 0.85,
      matched_job_id: 'demo-job-2',
      matched_company: 'Harbor',
      extracted: { company: 'Harbor', job_title: 'Full-Stack Engineer' },
      sync_status: 'applied',
      applied_actions: ['jd_updated:demo-job-2'],
      created_at: now,
    },
  ],
  total: 2,
  page: 1,
  page_size: 50,
  pages: 1,
};

/** Map API paths (without query) to demo payloads. */
export function resolveDemoData(url = '', method = 'get'): unknown | undefined {
  if (method.toLowerCase() !== 'get') return undefined;
  const path = url.split('?')[0].replace(/\/$/, '');

  if (path.endsWith('/reports/analytics') || path.includes('/reports/analytics')) return demoAnalytics;
  if (path.includes('/reports/weekly-story')) return demoWeeklyStory;
  if (path.includes('/jobs/pipeline')) return demoPipeline;
  if (path.match(/\/jobs\/[^/]+\/activity$/)) return demoActivity;
  if (path.includes('/jobs/tracked') || path.includes('/jobs/applied') || path.includes('/jobs/history')) {
    return demoJobs;
  }
  if (path.match(/\/jobs\/[^/]+$/) && !path.endsWith('/jobs')) {
    const id = path.split('/').pop();
    return demoJobs.items.find((job) => job.id === id) || demoJobs.items[0];
  }
  if (path.endsWith('/jobs') || path.includes('/jobs?')) return demoJobs;
  if (path.includes('/approvals/blockers')) return demoBlockers;
  if (path.includes('/approvals')) return demoApprovals;
  if (path.includes('/activity') || path.includes('/users/me/activity')) return demoActivity;
  if (path.includes('/job-portals')) return demoPortals;
  if (path.includes('/companies')) return demoCompanies;
  if (path.includes('/settings')) return demoSettings;
  if (path.endsWith('/users/me') || path.includes('/users/me?')) return demoProfile;
  if (path.includes('/users/me/resumes') && !path.includes('/download')) return demoResumes;
  if (path.includes('/automation/status')) return demoAutomationStatus;
  if (path.includes('/automation/logs')) return demoAutomationLogs;
  if (
    path.includes('/reports') &&
    !path.includes('analytics') &&
    !path.includes('download') &&
    !path.includes('weekly-story')
  ) {
    return demoReports;
  }
  if (path.includes('/onboarding')) return demoOnboarding;
  if (path.includes('/calendar')) return demoCalendar;
  if (path.includes('/reminders')) return demoReminders;
  if (path.includes('/email/accounts')) return demoEmailAccounts;
  if (path.includes('/email/messages')) return demoEmailMessages;
  if (path.includes('/questions')) return demoQuestions;
  if (path.includes('/notification-channels')) return [];
  if (path.includes('/applications')) return demoApplications;

  return { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
}
