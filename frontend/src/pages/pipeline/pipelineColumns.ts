export const PIPELINE_COLUMNS = [
  {
    key: 'fetched',
    label: 'Fetched jobs',
    hint: 'New matches land here. Drag onto Queued to auto-apply.',
    dropHint: 'Drop to keep in fetched',
  },
  {
    key: 'queued',
    label: 'Queued jobs',
    hint: 'Drop a fetched job here to start auto-applying.',
    dropHint: 'Drop to queue auto-apply',
  },
  {
    key: 'applied',
    label: 'Applied jobs',
    hint: 'Submitted applications.',
    dropHint: 'Drop to mark applied',
  },
  {
    key: 'interview',
    label: 'Interview',
    hint: 'Recruiter / interview stage.',
    dropHint: 'Drop to mark interview',
  },
  {
    key: 'shortlisted',
    label: 'Shortlisted',
    hint: 'Shortlist or offer.',
    dropHint: 'Drop to shortlist',
  },
] as const;

export type PipelineColumnKey = (typeof PIPELINE_COLUMNS)[number]['key'];

export type PipeJob = {
  id: string;
  title: string;
  company: string;
  portal: string;
  status: string;
  match_score: number;
  location?: string;
};

export type PipelineColumnsState = Record<string, PipeJob[]>;

const STATUS_TO_COLUMN: Record<string, PipelineColumnKey> = {
  new: 'fetched',
  matched: 'fetched',
  awaiting_approval: 'fetched',
  tracked: 'fetched',
  failed: 'fetched',
  approved: 'queued',
  applying: 'queued',
  applied: 'applied',
  interview: 'interview',
  shortlisted: 'shortlisted',
  offer: 'shortlisted',
};

const COLUMN_STATUS: Record<PipelineColumnKey, string> = {
  fetched: 'matched',
  queued: 'applying',
  applied: 'applied',
  interview: 'interview',
  shortlisted: 'shortlisted',
};

export function columnForStatus(status?: string | null): PipelineColumnKey | null {
  if (!status) return null;
  return STATUS_TO_COLUMN[status] ?? null;
}

export function statusForColumn(column: PipelineColumnKey): string {
  return COLUMN_STATUS[column];
}

/** Dropping onto Queued from any other stage starts auto-apply. */
export function shouldQueueApply(fromColumn: string | null | undefined, toColumn: string): boolean {
  return toColumn === 'queued' && fromColumn !== 'queued';
}

export function moveJobInColumns(
  columns: PipelineColumnsState,
  jobId: string,
  fromColumn: string,
  toColumn: string,
  nextStatus: string,
): PipelineColumnsState {
  const next: PipelineColumnsState = {};
  let moved: PipeJob | null = null;
  for (const [key, jobs] of Object.entries(columns)) {
    const remaining = jobs.filter((job) => {
      if (job.id !== jobId) return true;
      moved = { ...job, status: nextStatus };
      return false;
    });
    next[key] = remaining;
  }
  if (!moved) return columns;
  const dest = [...(next[toColumn] || [])];
  dest.unshift(moved);
  next[toColumn] = dest;
  next[fromColumn] = next[fromColumn] || [];
  return next;
}
