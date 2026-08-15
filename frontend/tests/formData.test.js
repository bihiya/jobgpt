import { describe, expect, it } from 'vitest';
import { dropFormDataContentType } from '../src/api/formData';

describe('dropFormDataContentType', () => {
  it('removes JSON content-type from FormData requests', () => {
    const headers = { 'Content-Type': 'application/json' };
    dropFormDataContentType({ data: new FormData(), headers });
    expect(headers['Content-Type']).toBeUndefined();
  });

  it('leaves JSON posts unchanged', () => {
    const headers = { 'Content-Type': 'application/json' };
    dropFormDataContentType({ data: { name: 'cv' }, headers });
    expect(headers['Content-Type']).toBe('application/json');
  });

  it('uses AxiosHeaders.delete when available', () => {
    const deleted = [];
    const headers = {
      delete: (key) => deleted.push(key),
    };
    dropFormDataContentType({ data: new FormData(), headers });
    expect(deleted).toContain('Content-Type');
  });
});
