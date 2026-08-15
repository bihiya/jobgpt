import type { InternalAxiosRequestConfig } from 'axios';

/** Drop a preset JSON Content-Type so the runtime can set multipart boundaries. */
export function dropFormDataContentType(config: InternalAxiosRequestConfig): void {
  if (typeof FormData === 'undefined' || !(config.data instanceof FormData)) return;
  const headers = config.headers;
  if (!headers) return;
  if (typeof headers.delete === 'function') {
    headers.delete('Content-Type');
    return;
  }
  delete (headers as Record<string, unknown>)['Content-Type'];
  delete (headers as Record<string, unknown>)['content-type'];
}
