/** Extract a human-readable message from Axios / FastAPI errors. */
export function getApiErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (!error || typeof error !== 'object') return fallback;
  const err = error as {
    message?: string;
    response?: { data?: { detail?: unknown; message?: string }; status?: number };
  };
  const detail = err.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  if (typeof err.response?.data?.message === 'string') return err.response.data.message;
  if (err.response?.status === 401) return 'Session expired — please sign in again';
  if (err.response?.status === 403) return 'You do not have permission for this action';
  if (err.response?.status === 404) return 'Resource not found';
  if (err.response?.status === 429) return 'Too many requests — slow down and try again';
  if (typeof err.message === 'string' && err.message !== 'Network Error') return err.message;
  if (err.message === 'Network Error') return 'Network error — check your connection';
  return fallback;
}
