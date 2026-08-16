/** Reconstruct a public listing URL from stored job fields. */

const LINKEDIN_JOB_ID = /(?:\/jobs\/view\/|currentJobId=|linkedin-)(\d{5,})/i;

export function linkedinJobId(value = ''): string {
  const match = String(value || '').match(LINKEDIN_JOB_ID);
  return match?.[1] || '';
}

export function listingUrlFor(job: {
  portal?: string;
  apply_url?: string;
  listing_url?: string;
  external_id?: string;
} | null | undefined): string {
  if (!job) return '';
  const explicit = (job.listing_url || job.apply_url || '').trim();
  if (explicit) {
    const id = linkedinJobId(explicit);
    if ((job.portal || '').toLowerCase() === 'linkedin' && id) {
      return `https://www.linkedin.com/jobs/view/${id}/`;
    }
    return explicit;
  }
  if ((job.portal || '').toLowerCase() === 'linkedin') {
    const id = linkedinJobId(job.external_id || '');
    if (id) return `https://www.linkedin.com/jobs/view/${id}/`;
  }
  return '';
}
