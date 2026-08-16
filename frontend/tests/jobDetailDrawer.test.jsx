import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import JobDetailDrawer from '../src/components/jobs/JobDetailDrawer';

vi.mock('../src/api', () => ({
  activityApi: {
    forJob: async () => ({ data: { items: [] } }),
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
  it('shows the listing URL, salary, and description for a LinkedIn job', () => {
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
  });
});
