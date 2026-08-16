import { describe, expect, it } from 'vitest';
import { profileFromApi, profileToUpdate, splitCsv } from '../src/pages/profile/profileForm';

describe('profile form', () => {
  it('splits comma lists and drops blanks', () => {
    expect(splitCsv('React, TypeScript, , Python')).toEqual(['React', 'TypeScript', 'Python']);
  });

  it('maps API user into personal and job fields', () => {
    const form = profileFromApi({
      full_name: 'Ada Lovelace',
      email: 'ada@example.com',
      profile: {
        skills: ['Python', 'Math'],
        keywords: ['remote'],
        location: 'London',
        experience_years: 8,
        notice_period_days: 14,
        phone: '555-0100',
        linkedin_url: 'https://www.linkedin.com/in/ada',
        github_url: 'https://github.com/ada',
        portfolio_url: 'https://ada.dev',
        salary_expectation: { min: 120000, max: 160000, currency: 'GBP' },
      },
    });

    expect(form.full_name).toBe('Ada Lovelace');
    expect(form.email).toBe('ada@example.com');
    expect(form.location).toBe('London');
    expect(form.linkedin_url).toContain('linkedin.com');
    expect(form.phone).toBe('555-0100');
    expect(form.skills).toBe('Python, Math');
    expect(form.keywords).toBe('remote');
    expect(form.experience_years).toBe(8);
    expect(form.salary_min).toBe(120000);
    expect(form.salary_currency).toBe('GBP');
  });

  it('builds an update payload that keeps salary instead of wiping it', () => {
    const payload = profileToUpdate({
      full_name: 'Ada Lovelace',
      email: 'ada@example.com',
      skills: 'Python, FastAPI',
      location: 'London',
      keywords: 'backend, remote',
      experience_years: 8,
      notice_period_days: 14,
      salary_min: 120000,
      salary_max: 160000,
      salary_currency: 'GBP',
      linkedin_url: 'https://www.linkedin.com/in/ada',
      github_url: '',
      portfolio_url: '',
      phone: '555-0100',
    });

    expect(payload.full_name).toBe('Ada Lovelace');
    expect(payload.profile.skills).toEqual(['Python', 'FastAPI']);
    expect(payload.profile.keywords).toEqual(['backend', 'remote']);
    expect(payload.profile.salary_expectation).toEqual({
      min: 120000,
      max: 160000,
      currency: 'GBP',
    });
    expect(payload.profile.linkedin_url).toContain('linkedin.com');
    expect(payload.profile.phone).toBe('555-0100');
  });
});
