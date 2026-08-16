import { describe, expect, it } from 'vitest';
import {
  applyStatusLabel,
  isJobApplying,
  isLiveApplyStatus,
  isStaleApply,
  latestSessionStep,
  mergeApplySnapshots,
  pipelineHasLiveApply,
  STALE_APPLY_MS,
} from '../src/lib/applyLive';

describe('apply live helpers', () => {
  it('treats applying jobs and in-progress apps as live', () => {
    expect(isJobApplying('applying', 'pending')).toBe(true);
    expect(isJobApplying('matched', 'in_progress')).toBe(true);
    expect(isJobApplying('applied', 'success')).toBe(false);
    expect(isLiveApplyStatus('needs_otp')).toBe(true);
    expect(applyStatusLabel('in_progress')).toBe('Applying now');
  });

  it('flags applies with no worker update past the stale window', () => {
    const now = Date.parse('2026-08-16T12:00:00Z');
    expect(isStaleApply('2026-08-13T12:00:00Z', now)).toBe(true);
    expect(isStaleApply('2026-08-16T11:50:00Z', now)).toBe(false);
    expect(isStaleApply('2026-08-16T11:00:00Z', now, STALE_APPLY_MS)).toBe(true);
  });

  it('merges snapshots preferring newer updates and longer step lists', () => {
    const older = {
      id: 'a1',
      status: 'in_progress',
      updated_at: '2026-08-16T11:00:00Z',
      session_steps: [
        { key: 'queued', label: 'Queued' },
        { key: 'started', label: 'Started' },
        { key: 'opened_jd', label: 'Opened JD' },
      ],
    };
    const newer = {
      id: 'a1',
      status: 'in_progress',
      updated_at: '2026-08-16T11:01:00Z',
      session_steps: [{ key: 'queued', label: 'Queued' }],
    };
    const merged = mergeApplySnapshots(older, newer);
    expect(merged?.updated_at).toBe('2026-08-16T11:01:00Z');
    expect(merged?.session_steps).toHaveLength(3);
    expect(latestSessionStep(merged?.session_steps)?.key).toBe('opened_jd');
  });

  it('detects live applies on the pipeline board', () => {
    expect(
      pipelineHasLiveApply({
        fetched: [{ status: 'matched' }],
        queued: [{ status: 'applying', application: { id: 'a1', status: 'in_progress' } }],
      }),
    ).toBe(true);
    expect(pipelineHasLiveApply({ fetched: [{ status: 'matched' }], queued: [] })).toBe(false);
  });
});
