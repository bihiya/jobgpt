import { api } from './client';

export { api } from './client';
export { authApi } from './auth';
export { jobsApi } from './jobs';

export const companiesApi = {
  list: (params?: Record<string, unknown>) => api.get('/companies', { params }),
  create: (payload: Record<string, unknown>) => api.post('/companies', payload),
  update: (id: string, payload: Record<string, unknown>) => api.patch(`/companies/${id}`, payload),
  remove: (id: string) => api.delete(`/companies/${id}`),
};

export const portalsApi = {
  list: () => api.get('/job-portals'),
  create: (payload: Record<string, unknown>) => api.post('/job-portals', payload),
  update: (id: string, payload: Record<string, unknown>) => api.patch(`/job-portals/${id}`, payload),
  clearCredentials: (id: string) => api.delete(`/job-portals/${id}/credentials`),
  sync: (id: string) => api.post(`/job-portals/${id}/sync`),
  reauth: (id: string, payload?: Record<string, unknown>) =>
    api.post(`/job-portals/${id}/reauth`, payload || {}),
  remove: (id: string) => api.delete(`/job-portals/${id}`),
};

export const applicationsApi = {
  list: (params?: Record<string, unknown>) => api.get('/applications', { params }),
  get: (id: string) => api.get(`/applications/${id}`),
  create: (payload: { job_id: string; resume_id?: string }) => api.post('/applications', payload),
  retry: (id: string) => api.post(`/applications/${id}/retry`),
  cancel: (id: string) => api.post(`/applications/${id}/cancel`),
  submitOtp: (id: string, payload: { code: string; save_totp_secret?: string }) =>
    api.post(`/applications/${id}/otp`, payload),
};

export const reportsApi = {
  list: () => api.get('/reports'),
  create: (payload: Record<string, unknown>) => api.post('/reports', payload),
  analytics: () => api.get('/reports/analytics'),
  weeklyStory: () => api.get('/reports/weekly-story'),
  download: (id: string) => api.get(`/reports/${id}/download`, { responseType: 'blob' }),
};

export const automationApi = {
  status: () => api.get('/automation/status'),
  logs: (params?: Record<string, unknown>) => api.get('/automation/logs', { params }),
  run: (job_type = 'fetch') => api.post(`/automation/run?job_type=${job_type}`),
};

export const settingsApi = {
  get: () => api.get('/settings'),
  update: (payload: Record<string, unknown>) => api.patch('/settings', payload),
};

export const approvalsApi = {
  list: (params?: Record<string, unknown>) => api.get('/approvals', { params }),
  blockers: () => api.get('/approvals/blockers'),
  batch: (payload: Record<string, unknown>) => api.post('/approvals/batch', payload),
  approve: (id: string, note = '') => api.post(`/approvals/${id}/approve`, { note }),
  reject: (id: string, note = '') => api.post(`/approvals/${id}/reject`, { note }),
};

export const questionsApi = {
  list: () => api.get('/questions'),
  upsert: (payload: Record<string, unknown>) => api.post('/questions', payload),
  remove: (id: string) => api.delete(`/questions/${id}`),
  answerAndResume: (payload: Record<string, unknown>) =>
    api.post('/questions/answer-and-resume', payload),
};

export const onboardingApi = {
  status: () => api.get('/onboarding/status'),
  advance: (step: string) => api.post('/onboarding/advance', { step }),
  firstSync: () => api.post('/onboarding/first-sync'),
};

export const calendarApi = {
  month: (month?: number, year?: number) =>
    api.get('/calendar', { params: { month, year } }),
  dueReminders: () => api.get('/reminders/due'),
  completeReminder: (id: string) => api.post(`/reminders/${id}/complete`),
};

export const channelsApi = {
  list: () => api.get('/notification-channels'),
  create: (payload: Record<string, unknown>) => api.post('/notification-channels', payload),
  remove: (id: string) => api.delete(`/notification-channels/${id}`),
};

export const usersApi = {
  me: () => api.get('/users/me'),
  update: (payload: Record<string, unknown>) => api.patch('/users/me', payload),
  resumes: () => api.get('/users/me/resumes'),
  uploadResume: (form: FormData) =>
    api.post('/users/me/resumes', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  activity: (params?: Record<string, unknown>) => api.get('/users/me/activity', { params }),
};

export const activityApi = {
  list: (params?: Record<string, unknown>) => api.get('/activity', { params }),
  forJob: (jobId: string, params?: Record<string, unknown>) =>
    api.get(`/jobs/${jobId}/activity`, { params }),
};

export const emailApi = {
  accounts: () => api.get('/email/accounts'),
  upsertAccount: (payload: Record<string, unknown>) => api.post('/email/accounts', payload),
  removeAccount: (id: string) => api.delete(`/email/accounts/${id}`),
  testAccount: (id: string) => api.post(`/email/accounts/${id}/test`),
  syncAccount: (id: string) => api.post(`/email/accounts/${id}/sync`),
  syncAll: () => api.post('/email/sync'),
  messages: (params?: Record<string, unknown>) => api.get('/email/messages', { params }),
  ingest: (payload: Record<string, unknown>) => api.post('/email/ingest', payload),
  apply: (id: string) => api.post(`/email/messages/${id}/apply`),
  ignore: (id: string) => api.post(`/email/messages/${id}/ignore`),
};
