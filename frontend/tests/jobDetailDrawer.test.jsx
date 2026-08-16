import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import JobDetailDrawer from '../src/components/jobs/JobDetailDrawer';

vi.mock('../src/api', () => ({
  applicationsApi: {
    forJob: async () => ({ data: { items: [], total: 0 } }),
    retry: async () => ({ data: {} }),
    cancel: async () => ({ data: {} }),
  },
}));

function renderDrawer(job, extra = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ThemeProvider theme={createTheme()}>
        <JobDetailDrawer open job={job} onClose={() => {}} {...extra} />
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

const linkedinJob = {
  id: 'job-1',
  title: 'Full-Stack Software Engineer | $25-$30/hr',
  company: 'Hirely',
  location: 'India (Remote)',
  salary: '$25-$30/hr',
  portal: 'linkedin',
  status: 'new',
  match_score: 0.18,
  apply_url: 'https://www.linkedin.com/jobs/view/4451751943/',
  listing_url: 'https://www.linkedin.com/jobs/view/4451751943/',
  external_id: 'linkedin-4451751943',
  source: 'portal',
  fetched_at: '2026-08-16T10:11:00.000Z',
  description:
    'Full-Stack Software Engineer | $25-$30/hr\nHirely\nIndia (Remote)\n\nAbout the job\nHirely is hiring a full-stack engineer to ship product end to end.\n\nResponsibilities\n• Build APIs and React UIs\n• Own deploys\n\nRequirements\n• 3+ years of experience',
  skills: ['React', 'TypeScript'],
  match_breakdown: {
    skills: 0,
    keywords: 0,
    location: 0.5,
    experience: 0.5,
    reasons: ['Little skill overlap with your profile'],
  },
};

describe('JobDetailDrawer', () => {
  it('shows a LinkedIn-style listing with every field visible and no activity feed', () => {
    renderDrawer(linkedinJob);
    expect(
      screen.getByRole('heading', { name: 'Full-Stack Software Engineer | $25-$30/hr' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Hirely')).toBeInTheDocument();
    expect(screen.getAllByText('India (Remote)').length).toBeGreaterThan(0);
    expect(screen.getAllByText('$25-$30/hr').length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: 'About the job' })).toBeInTheDocument();
    expect(
      screen.getByText('Hirely is hiring a full-stack engineer to ship product end to end.'),
    ).toBeInTheDocument();
    expect(screen.getByText('Build APIs and React UIs')).toBeInTheDocument();
    expect(screen.getByText('3+ years of experience')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'How you match' })).toBeInTheDocument();
    expect(screen.getByText('Little skill overlap with your profile')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Job details' })).toBeInTheDocument();
    expect(screen.getByText('https://www.linkedin.com/jobs/view/4451751943/')).toBeInTheDocument();
    expect(screen.getByText('linkedin-4451751943')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open job listing' })).toHaveAttribute(
      'href',
      'https://www.linkedin.com/jobs/view/4451751943/',
    );
    expect(screen.getByText('React')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Activity' })).not.toBeInTheDocument();
    expect(screen.queryByText(/JobPilot fetched a new job/i)).not.toBeInTheDocument();
  });

  it('uses the paper background so listing text stays high-contrast', () => {
    renderDrawer(linkedinJob);
    const about = screen.getByRole('heading', { name: 'About the job' });
    const paper = about.closest('.MuiDrawer-paper');
    expect(paper).toBeTruthy();
    expect(paper).toHaveStyle({ color: 'rgba(0, 0, 0, 0.87)' });
  });

  it('offers Apply when the job can be submitted', () => {
    renderDrawer(linkedinJob, { onApply: () => {} });
    expect(screen.getByRole('button', { name: 'Apply' })).toBeInTheDocument();
  });

  it('shows the apply session timeline when a live apply is in progress', async () => {
    renderDrawer(
      { ...linkedinJob, status: 'applying' },
      {
        liveApplication: {
          id: 'app-1',
          job_id: 'job-1',
          status: 'in_progress',
          attempts: 1,
          session_steps: [
            { key: 'started', label: 'Worker started applying', status: 'ok', detail: 'linkedin' },
            { key: 'opened_jd', label: 'Opened job description', status: 'ok' },
            { key: 'clicked_apply', label: 'Clicked Easy Apply / Apply', status: 'ok' },
          ],
          updated_at: new Date().toISOString(),
        },
      },
    );
    await waitFor(() => {
      expect(screen.getByText('Apply session')).toBeInTheDocument();
    });
    expect(screen.getByText('Clicked Easy Apply / Apply')).toBeInTheDocument();
    expect(screen.getByText('Opened job description')).toBeInTheDocument();
  });
});
