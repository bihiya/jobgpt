import { describe, expect, it } from 'vitest';
import {
  PIPELINE_COLUMNS,
  columnForStatus,
  moveJobInColumns,
  shouldQueueApply,
  statusForColumn,
} from '../src/pages/pipeline/pipelineColumns';

describe('pipeline columns', () => {
  it('has fetched → queued → applied → interview → shortlisted', () => {
    expect(PIPELINE_COLUMNS.map((c) => c.key)).toEqual([
      'fetched',
      'queued',
      'applied',
      'interview',
      'shortlisted',
    ]);
    expect(PIPELINE_COLUMNS.map((c) => c.label)).toEqual([
      'Fetched',
      'Applying',
      'Applied',
      'Interview',
      'Shortlisted',
    ]);
    expect(PIPELINE_COLUMNS.find((c) => c.key === 'queued')?.hint).toMatch(/Live worker steps/);
  });

  it('maps job statuses onto the five stages', () => {
    expect(columnForStatus('new')).toBe('fetched');
    expect(columnForStatus('matched')).toBe('fetched');
    expect(columnForStatus('applying')).toBe('queued');
    expect(columnForStatus('applied')).toBe('applied');
    expect(columnForStatus('interview')).toBe('interview');
    expect(columnForStatus('offer')).toBe('shortlisted');
    expect(columnForStatus('shortlisted')).toBe('shortlisted');
  });

  it('starts auto-apply when dropping onto queued', () => {
    expect(shouldQueueApply('fetched', 'queued')).toBe(true);
    expect(shouldQueueApply('applied', 'queued')).toBe(true);
    expect(shouldQueueApply('queued', 'queued')).toBe(false);
    expect(shouldQueueApply('queued', 'applied')).toBe(false);
    expect(statusForColumn('queued')).toBe('applying');
  });

  it('moves a job between columns for optimistic UI', () => {
    const next = moveJobInColumns(
      {
        fetched: [{ id: '1', title: 'Eng', company: 'Acme', portal: 'linkedin', status: 'matched', match_score: 0.9 }],
        queued: [],
      },
      '1',
      'fetched',
      'queued',
      'applying',
    );
    expect(next.fetched).toHaveLength(0);
    expect(next.queued[0]).toMatchObject({ id: '1', status: 'applying' });
  });
});
