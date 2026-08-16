/** Turn scraped listing text into LinkedIn-style About the job blocks. */

export type JobDescriptionBlock =
  | { type: 'heading'; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'list'; items: string[] };

export type JobDescriptionHeader = {
  title?: string;
  company?: string;
  location?: string;
  salary?: string;
};

const BULLET_RE = /^\s*(?:[•●○▪►▸·]|[-–—*]|(\d+)[.)])\s+/;
const ABOUT_HEADING_RE = /^about the job$/i;
const HEADING_HINT_RE =
  /^(about(\s+the)?(\s+\w+)?|the role|overview|summary|job description|responsibilities|key responsibilities|requirements|qualifications|basic qualifications|preferred qualifications|must[- ]have|nice[- ]to[- ]have|skills|experience|education|benefits|perks|what (you.?ll|you will|we.?re|we are|we offer)|who you are|compensation|pay|how to apply|equal opportunity|our (mission|values|team)|why (join|you.?ll love)|the team)\b/i;

function key(value = ''): string {
  return value.toLowerCase().replace(/\s+/g, ' ').trim();
}

function looksLikeHeading(line: string): boolean {
  if (line.length > 80 || line.length < 2) return false;
  if (/[.!?:]$/.test(line) && line.length > 40) return false;
  if (HEADING_HINT_RE.test(line)) return true;
  if (line === line.toUpperCase() && /[A-Z]/.test(line) && line.split(/\s+/).length <= 8) return true;
  return false;
}

export function stripHtml(value = ''): string {
  return value
    .replace(/<\s*br\s*\/?\s*>/gi, '\n')
    .replace(/<\s*\/\s*p\s*>/gi, '\n')
    .replace(/<\s*li\s*>/gi, '• ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .trim();
}

/** Drop title/company/location/salary lines that already appear in the header. */
export function stripListingHeader(description: string, job: JobDescriptionHeader = {}): string {
  const raw = stripHtml(description || '').replace(/\r\n/g, '\n');
  if (!raw) return '';
  const skip = new Set(
    [job.title, job.company, job.location, job.salary]
      .filter((value): value is string => Boolean(value && String(value).trim()))
      .map((value) => key(value)),
  );
  const lines = raw.split('\n');
  let start = 0;
  while (start < lines.length) {
    const line = lines[start].trim();
    if (!line) {
      start += 1;
      continue;
    }
    if (skip.has(key(line))) {
      start += 1;
      continue;
    }
    break;
  }
  const rest = lines.slice(start).join('\n').trim();
  return rest;
}

export function parseJobDescription(text: string): JobDescriptionBlock[] {
  const source = stripHtml(text || '').replace(/\r\n/g, '\n');
  if (!source) return [];

  const blocks: JobDescriptionBlock[] = [];
  let paragraph: string[] = [];
  let list: string[] = [];

  const flushParagraph = () => {
    const joined = paragraph.join(' ').replace(/\s+/g, ' ').trim();
    paragraph = [];
    if (joined) blocks.push({ type: 'paragraph', text: joined });
  };
  const flushList = () => {
    if (!list.length) return;
    blocks.push({ type: 'list', items: list });
    list = [];
  };

  for (const raw of source.split('\n')) {
    const line = raw.trim();
    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }
    if (BULLET_RE.test(line)) {
      flushParagraph();
      list.push(line.replace(BULLET_RE, '').trim());
      continue;
    }
    if (looksLikeHeading(line)) {
      flushParagraph();
      flushList();
      const heading = line.replace(/:$/, '');
      if (blocks.length === 0 && ABOUT_HEADING_RE.test(heading)) continue;
      blocks.push({ type: 'heading', text: heading });
      continue;
    }
    flushList();
    paragraph.push(line);
  }
  flushParagraph();
  flushList();
  return blocks;
}

export function jobDescriptionBody(description: string, job: JobDescriptionHeader = {}): string {
  return stripListingHeader(description, job);
}
