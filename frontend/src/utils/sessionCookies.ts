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

const LI_AT_TOKEN = /^[A-Za-z0-9_%=+-]{20,}$/;
const COOKIE_NAME = /^[A-Za-z0-9_.-]{1,80}$/;

function asLiAt(value: string): PortalCookie[] {
  return [{ name: 'li_at', value, domain: '.linkedin.com', path: '/' }];
}

function cookie(name: string, value: string, domain: string): PortalCookie {
  return { name, value, domain, path: '/' };
}

function fromNameValueLabels(text: string, domain: string): PortalCookie[] {
  const name = text.match(/^(?:name|cookie)\s*:\s*(\S+)\s*$/im)?.[1];
  const value = text.match(/^value\s*:\s*(\S+)\s*$/im)?.[1];
  return name && value ? [cookie(name, value, domain)] : [];
}

function fromTableOrNetscape(raw: string, domain: string): PortalCookie[] {
  const cookies: PortalCookie[] = [];
  for (const rawLine of raw.split('\n')) {
    let line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    if (line.toLowerCase().startsWith('#httponly_')) line = line.slice(10);
    let parts = line.split(/\t+/);
    if (parts.length === 1) parts = line.split(/ {2,}/);
    if (parts.length >= 7 && parts[5] && parts[6] && COOKIE_NAME.test(parts[5])) {
      const host = parts[0].replace(/^#HttpOnly_/, '');
      cookies.push(
        cookie(parts[5], parts[6], host.startsWith('.') || host.includes('linkedin') ? host : domain),
      );
      continue;
    }
    if (
      parts.length >= 2 &&
      COOKIE_NAME.test(parts[0]) &&
      !['name', 'cookie', 'key', 'domain'].includes(parts[0].toLowerCase()) &&
      parts[1]
    ) {
      cookies.push(cookie(parts[0], parts[1], domain));
    }
  }
  return cookies;
}

export function parseCookiePaste(raw: string, portal = 'linkedin'): PortalCookie[] {
  let text = (raw || '').replace(/\r/g, '').trim().replace(/^['"]|['"]$/g, '');
  const domain = DEFAULT_DOMAIN[portal] || '.linkedin.com';
  if (!text) return [];

  const labeled = fromNameValueLabels(text, domain);
  if (labeled.length) return labeled;

  const lines = text.split('\n').map((line) => line.trim()).filter(Boolean);
  const first = (lines[0] || '').toLowerCase().replace(/\s+/g, '').replace(/:$/, '');
  if (lines.length >= 2 && (first === 'li_at' || first === 'name:li_at')) {
    text = `li_at=${lines.slice(1).join('')}`;
  } else if (!text.startsWith('{') && !text.startsWith('[') && !text.includes('=')) {
    text = lines.join('');
  }

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
      /* fall through */
    }
  }

  let header = text;
  if (header.toLowerCase().startsWith('cookie:')) {
    header = header.slice(header.indexOf(':') + 1).trim();
  }
  if (header.toLowerCase().startsWith('li_at:') && !header.slice(0, 6).includes('=')) {
    header = `li_at=${header.slice(6).trim()}`;
  }
  if (header.includes('=')) {
    const cookies = header
      .replace(/\n/g, '')
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
      .filter((item) => {
        if (!item.name || !item.value) return false;
        if ((item.value === '=' || item.value === '==') && item.name.length >= 16) return false;
        return item.name.length <= 40 && COOKIE_NAME.test(item.name);
      });
    if (cookies.length) return cookies;
  }

  const table = fromTableOrNetscape(raw || '', domain);
  if (table.length) return table;

  const compact = text.replace(/\s+/g, '');
  if (isBareLiAt(compact)) return asLiAt(compact);
  return [];
}

function isBareLiAt(compact: string): boolean {
  if (!LI_AT_TOKEN.test(compact)) return false;
  if (compact.startsWith('AQED') && compact.length >= 20) return true;
  return compact.length >= 80;
}

export function hasAuthCookie(cookies: PortalCookie[], portal = 'linkedin'): boolean {
  const names = new Set(cookies.map((c) => c.name));
  if (portal === 'linkedin') return names.has('li_at');
  if (portal === 'indeed') {
    return ['PP', 'SHARED_SESSION', 'SOCK', 'SHOE', 'indeed_rcc'].some((n) => names.has(n));
  }
  return cookies.length > 0;
}
