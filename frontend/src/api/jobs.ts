import { api } from './client';

export const jobsApi = {
  list: (params?: Record<string, unknown>) => api.get('/jobs', { params }),
  tracked: (params?: Record<string, unknown>) => api.get('/jobs/tracked', { params }),
  applied: (params?: Record<string, unknown>) => api.get('/jobs/applied', { params }),
  history: (params?: Record<string, unknown>) => api.get('/jobs/history', { params }),
  get: (id: string) => api.get(`/jobs/${id}`),
  track: (id: string) => api.post(`/jobs/${id}/track`),
  ignore: (id: string) => api.post(`/jobs/${id}/ignore`),
};
