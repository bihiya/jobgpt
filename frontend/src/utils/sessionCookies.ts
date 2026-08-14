export type PortalCookie = {
  name: string;
  value: string;
  domain: string;
  path: string;
};

const DEFAULT_DOMAIN: Record<string, string> = {
  linkedin: '.linkedin.com',
  indeed: '.indeed.com',
};

export function parseCookiePaste(raw: string, portal = 'linkedin'): PortalCookie[] {
  const text = (raw || '').trim();
  const domain = DEFAULT_DOMAIN[portal] || '.linkedin.com';
  if (!text) return [];

  if (text.startsWith('{') || text.startsWith('[')) {
    try {
      const parsed = JSON.parse(text) as unknown;
      if (Array.isArray(parsed)) {
        return parsed
          .filter((item): item is Record<string, unknown> => Boolean(item && typeof item === 'object'))
          .map((item) => ({
            name: String(item.name || ''),
            value: String(item.value ?? ''),
            domain: String(item.domain || domain),
            path: String(item.path || '/'),
          }))
          .filter((item) => item.name && item.value);
      }
      if (parsed && typeof parsed === 'object') {
        const obj = parsed as Record<string, unknown>;
        if (Array.isArray(obj.cookies)) {
          return parseCookiePaste(JSON.stringify(obj.cookies), portal);
        }
        const mappedDomain = String(obj.domain || domain);
        return Object.entries(obj)
          .filter(([key, value]) => !['domain', 'path', 'cookies'].includes(key) && value != null)
          .map(([name, value]) => ({
            name,
            value: String(value),
            domain: mappedDomain,
            path: '/',
          }));
      }
    } catch {
      /* fall through to header / bare token */
    }
  }

  let header = text;
  if (header.toLowerCase().startsWith('cookie:')) {
    header = header.slice(header.indexOf(':') + 1).trim();
  }
  if (header.includes('=')) {
    return header
      .split(';')
      .map((part) => part.trim())
      .filter((part) => part.includes('='))
      .map((part) => {
        const eq = part.indexOf('=');
        return {
          name: part.slice(0, eq).trim(),
          value: part.slice(eq + 1).trim().replace(/^"|"$/g, ''),
          domain,
          path: '/',
        };
      })
      .filter((item) => item.name && item.value);
  }

  if (!text.includes(' ') && !text.includes(';') && text.length >= 20) {
    return [{ name: 'li_at', value: text, domain: '.linkedin.com', path: '/' }];
  }
  return [];
}

export function hasAuthCookie(cookies: PortalCookie[], portal = 'linkedin'): boolean {
  const names = new Set(cookies.map((c) => c.name));
  if (portal === 'linkedin') return names.has('li_at');
  if (portal === 'indeed') {
    return ['PP', 'SHARED_SESSION', 'SOCK', 'SHOE', 'indeed_rcc'].some((n) => names.has(n));
  }
  return cookies.length > 0;
}
