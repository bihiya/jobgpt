import { describe, expect, it } from 'vitest';
import { linkedinJobId, listingUrlFor } from '../src/lib/jobListing';

describe('listingUrlFor', () => {
  it('canonicalizes a LinkedIn apply URL', () => {
    expect(
      listingUrlFor({
        portal: 'linkedin',
        apply_url: 'https://www.linkedin.com/jobs/view/4299000111/?trk=flagship',
      }),
    ).toBe('https://www.linkedin.com/jobs/view/4299000111/');
  });

  it('rebuilds the Product Engineer listing from external_id', () => {
    expect(
      listingUrlFor({
        portal: 'linkedin',
        apply_url: '',
        external_id: 'linkedin-4299000111',
      }),
    ).toBe('https://www.linkedin.com/jobs/view/4299000111/');
    expect(linkedinJobId('linkedin-4299000111')).toBe('4299000111');
  });
});
