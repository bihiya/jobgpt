import { describe, expect, it } from 'vitest';
import { fromNowLocal, parseApiDate } from '../src/utils/datetime';

describe('API datetime parsing', () => {
  it('treats naive ISO timestamps as UTC, not local', () => {
    const parsed = parseApiDate('2026-08-14T08:00:00');
    expect(parsed).not.toBeNull();
    expect(parsed.utc().format('YYYY-MM-DD HH:mm:ss')).toBe('2026-08-14 08:00:00');
    expect(parsed.valueOf()).toBe(Date.parse('2026-08-14T08:00:00.000Z'));
  });

  it('keeps explicit Z as UTC', () => {
    const parsed = parseApiDate('2026-08-14T08:00:00Z');
    expect(parsed.valueOf()).toBe(Date.parse('2026-08-14T08:00:00.000Z'));
  });

  it('shows a just-written naive UTC stamp as just now, not hours ago', () => {
    const naiveUtc = new Date().toISOString().replace(/\.\d{3}Z$/, '');
    expect(naiveUtc).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/);
    const label = fromNowLocal(naiveUtc);
    expect(label).toMatch(/a few seconds ago|a minute ago|seconds ago|just now/i);
    expect(label).not.toMatch(/hour/);
  });
});
