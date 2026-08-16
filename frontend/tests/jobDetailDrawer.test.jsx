import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import JobDetailDrawer from '../src/components/jobs/JobDetailDrawer';

vi.mock('../src/api', () => ({
  activityApi: {
    forJob: async () => ({ data: { items: [] } }),
  },
  applicationsApi: {
    forJob: async () => ({
      data: {
        items: [
          {
            id: 'app-1',
            job_id: 'job-1',
            status: 'in_progress',
            attempts: 1,
            session_steps: [
              { key: 'started', label: 'Worker started applying', status: 'ok', detail: 'linkedin' },
              { key: 'opened_jd', label: 'Opened job description', status: 'ok', detail: 'https://linkedin.com/jobs/view/1' },
              { key: 'clicked_apply', label: 'Clicked Easy Apply / Apply', status: 'ok' },
            ],
            error_message: '',
            updated_at: new Date().toISOString(),
          },
        ],
        total: 1,
      },
    }),
    retry: async () => ({ data: {} }),
    cancel: async () => ({ data: {} }),
  },
}));

function renderDrawer(job) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ThemeProvider theme={createTheme()}>
        <JobDetailDrawer open job={job} onClose={() => {}} />
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

describe('JobDetailDrawer', () => {
  it('shows the listing URL, salary, and description for a LinkedIn job', async () => {
    renderDrawer({
      id: 'job-1',
      title: 'Product Engineer',
      company: 'AnswerThis (YC F25)',
      location: 'San Francisco Bay Area (Remote)',
      salary: '$150K/yr - $220K/yr',
      portal: 'linkedin',
      status: 'matched',
      match_score: 0.18,
      apply_url: 'https://www.linkedin.com/jobs/view/4299000111/',
      listing_url: 'https://www.linkedin.com/jobs/view/4299000111/',
      external_id: 'linkedin-4299000111',
      description: 'Build the AnswerThis product with TypeScript and LLMs.',
      skills: ['TypeScript', 'LLMs'],
      match_breakdown: {
        skills: 0,
        keywords: 0,
        location: 0.5,
        experience: 0.5,
        reasons: ['Little skill overlap with your profile'],
      },
    });
    expect(screen.getByRole('heading', { name: 'Product Engineer' })).toBeInTheDocument();
    expect(screen.getByText('AnswerThis (YC F25) · San Francisco Bay Area (Remote)')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open job listing' })).toHaveAttribute(
      'href',
      'https://www.linkedin.com/jobs/view/4299000111/',
    );
    expect(screen.getByText('https://www.linkedin.com/jobs/view/4299000111/')).toBeInTheDocument();
    expect(screen.getByText('$150K/yr - $220K/yr')).toBeInTheDocument();
    expect(screen.getByText(/Build the AnswerThis product/)).toBeInTheDocument();
    expect(screen.getByText('TypeScript')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Apply session')).toBeInTheDocument();
    });
    expect(screen.getByText(/Now: Clicked Easy Apply/)).toBeInTheDocument();
    expect(screen.getByText('Opened job description')).toBeInTheDocument();
  });
});
