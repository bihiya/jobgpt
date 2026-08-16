export type ProfileForm = {
  full_name: string;
  email: string;
  skills: string;
  location: string;
  keywords: string;
  experience_years: number;
  notice_period_days: number;
  salary_min: number;
  salary_max: number;
  salary_currency: string;
  linkedin_url: string;
  github_url: string;
  portfolio_url: string;
  phone: string;
};

export type ProfileApiUser = {
  full_name?: string;
  email?: string;
  profile?: {
    skills?: string[];
    keywords?: string[];
    location?: string;
    experience_years?: number;
    notice_period_days?: number;
    linkedin_url?: string;
    github_url?: string;
    portfolio_url?: string;
    phone?: string;
    salary_expectation?: {
      min?: number;
      max?: number;
      currency?: string;
    };
  };
};

export function emptyProfileForm(): ProfileForm {
  return {
    full_name: '',
    email: '',
    skills: '',
    location: '',
    keywords: '',
    experience_years: 0,
    notice_period_days: 0,
    salary_min: 0,
    salary_max: 0,
    salary_currency: 'USD',
    linkedin_url: '',
    github_url: '',
    portfolio_url: '',
    phone: '',
  };
}

export function splitCsv(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

export function profileFromApi(data: ProfileApiUser | null | undefined): ProfileForm {
  const profile = data?.profile || {};
  const salary = profile.salary_expectation || {};
  return {
    full_name: data?.full_name || '',
    email: data?.email || '',
    skills: (profile.skills || []).join(', '),
    location: profile.location || '',
    keywords: (profile.keywords || []).join(', '),
    experience_years: profile.experience_years || 0,
    notice_period_days: profile.notice_period_days || 0,
    salary_min: salary.min || 0,
    salary_max: salary.max || 0,
    salary_currency: salary.currency || 'USD',
    linkedin_url: profile.linkedin_url || '',
    github_url: profile.github_url || '',
    portfolio_url: profile.portfolio_url || '',
    phone: profile.phone || '',
  };
}

export function profileToUpdate(form: ProfileForm) {
  return {
    full_name: form.full_name,
    profile: {
      skills: splitCsv(form.skills),
      keywords: splitCsv(form.keywords),
      location: form.location,
      experience_years: Number(form.experience_years) || 0,
      notice_period_days: Number(form.notice_period_days) || 0,
      salary_expectation: {
        min: Number(form.salary_min) || 0,
        max: Number(form.salary_max) || 0,
        currency: form.salary_currency || 'USD',
      },
      linkedin_url: form.linkedin_url,
      github_url: form.github_url,
      portfolio_url: form.portfolio_url,
      phone: form.phone,
    },
  };
}
