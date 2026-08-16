export const PIPELINE_COLUMNS = [
  {
    key: 'fetched',
    label: 'Fetched',
    hint: 'New matches. Queue one to auto-apply.',
    dropHint: 'Keep in fetched',
  },
  {
    key: 'queued',
    label: 'Applying',
    hint: 'Live worker steps show here. Open a card for the full log.',
    dropHint: 'Drop to auto-apply',
  },
  {
    key: 'applied',
    label: 'Applied',
    hint: 'Submitted.',
    dropHint: 'Mark applied',
  },
  {
    key: 'interview',
    label: 'Interview',
    hint: 'Recruiter stage.',
    dropHint: 'Mark interview',
  },
  {
    key: 'shortlisted',
    label: 'Shortlisted',
    hint: 'Offer / shortlist.',
    dropHint: 'Shortlist',
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
  updated_at?: string;
  application?: {
    id: string;
    job_id?: string;
    status: string;
    session_steps?: Array<{
      key?: string;
      label?: string;
      status?: string;
      detail?: string;
      at?: string;
    }>;
    error_message?: string;
    updated_at?: string;
    created_at?: string;
    attempts?: number;
    blocker_type?: string;
  };
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
