import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(relativeTime);

export function browserTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
}

/** Prefer an explicit user setting, but skip the default "UTC" so device local time wins. */
export function resolveTimeZone(settingsTz?: string | null): string {
  const trimmed = (settingsTz || '').trim();
  if (trimmed && trimmed.toUpperCase() !== 'UTC') return trimmed;
  return browserTimeZone();
}

export function parseApiDate(value?: string | null) {
  if (!value) return null;
  const trimmed = String(value).trim();
  if (!trimmed) return null;
  const hasTz = /Z$/i.test(trimmed) || /[+-]\d{2}:?\d{2}$/.test(trimmed);
  const parsed = hasTz ? dayjs(trimmed) : dayjs.utc(trimmed);
  return parsed.isValid() ? parsed : null;
}

export function formatLocal(
  value?: string | null,
  timeZone?: string,
  fmt = 'MMM D, YYYY h:mm A',
): string {
  const parsed = parseApiDate(value);
  if (!parsed) return '—';
  const zone = timeZone || browserTimeZone();
  try {
    return parsed.tz(zone).format(fmt);
  } catch {
    return parsed.local().format(fmt);
  }
}

export function fromNowLocal(value?: string | null): string {
  const parsed = parseApiDate(value);
  if (!parsed) return '—';
  return parsed.fromNow();
}

/** e.g. "1:52 PM · just now" in the user's timezone. */
export function formatWhen(value?: string | null, timeZone?: string): string {
  const parsed = parseApiDate(value);
  if (!parsed) return '—';
  const clock = formatLocal(value, timeZone, 'h:mm A');
  return `${clock} · ${parsed.fromNow()}`;
}

export function formatWhenLong(value?: string | null, timeZone?: string): string {
  const parsed = parseApiDate(value);
  if (!parsed) return '—';
  return `${formatLocal(value, timeZone, 'MMM D, YYYY h:mm:ss A')} · ${parsed.fromNow()}`;
}
