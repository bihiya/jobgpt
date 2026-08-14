import { api } from './client';

export const jobsApi = {
  list: (params?: Record<string, unknown>) => api.get('/jobs', { params }),
  tracked: (params?: Record<string, unknown>) => api.get('/jobs/tracked', { params }),
  applied: (params?: Record<string, unknown>) => api.get('/jobs/applied', { params }),
  history: (params?: Record<string, unknown>) => api.get('/jobs/history', { params }),
  pipeline: () => api.get('/jobs/pipeline'),
  get: (id: string) => api.get(`/jobs/${id}`),
  update: (id: string, payload: Record<string, unknown>) => api.patch(`/jobs/${id}`, payload),
  move: (id: string, payload: { column: string; resume_id?: string }) =>
    api.post(`/jobs/${id}/move`, payload),
  track: (id: string) => api.post(`/jobs/${id}/track`),
  ignore: (id: string) => api.post(`/jobs/${id}/ignore`),
  ingest: (payload: Record<string, unknown>) => api.post('/jobs/ingest', payload),
};
