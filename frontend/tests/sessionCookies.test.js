import { describe, expect, it } from 'vitest';
import { hasAuthCookie, parseCookiePaste } from '../src/utils/sessionCookies';

describe('parseCookiePaste', () => {
  it('accepts a bare li_at token', () => {
    const cookies = parseCookiePaste('AQEDASA' + 'x'.repeat(20));
    expect(cookies[0].name).toBe('li_at');
    expect(hasAuthCookie(cookies, 'linkedin')).toBe(true);
  });

  it('accepts Cookie header text', () => {
    const cookies = parseCookiePaste('li_at=tok123; JSESSIONID=abc');
    expect(cookies.map((c) => c.name)).toEqual(['li_at', 'JSESSIONID']);
    expect(cookies[0].domain).toBe('.linkedin.com');
  });

  it('accepts Playwright JSON', () => {
    const cookies = parseCookiePaste(
      JSON.stringify([{ name: 'li_at', value: 'abc', domain: '.linkedin.com' }]),
    );
    expect(cookies).toHaveLength(1);
    expect(hasAuthCookie(cookies)).toBe(true);
  });

  it('accepts a flat map', () => {
    const cookies = parseCookiePaste(JSON.stringify({ li_at: 'abc', domain: '.linkedin.com' }));
    expect(hasAuthCookie(cookies)).toBe(true);
  });

  it('returns empty for blank paste', () => {
    expect(parseCookiePaste('')).toEqual([]);
    expect(hasAuthCookie([], 'linkedin')).toBe(false);
  });
});
