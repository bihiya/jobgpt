import { accountFromPortal, compactProfileUrl, hasAccountDetails } from '../src/utils/portalIdentity';

describe('portalIdentity', () => {
  it('prefers LinkedIn session name and location over a blank email', () => {
    const account = accountFromPortal({
      username: '',
      session_identity: {
        display_name: 'Ada Lovelace',
        location: 'Bengaluru, Karnataka, India',
        headline: 'Software Engineer',
        profile_url: 'https://www.linkedin.com/in/ada-lovelace/',
      },
    });
    expect(account.name).toBe('Ada Lovelace');
    expect(account.location).toBe('Bengaluru, Karnataka, India');
    expect(hasAccountDetails(account)).toBe(true);
  });

  it('falls back to saved portal email when identity is missing', () => {
    const account = accountFromPortal({ username: 'you@indeed.example' });
    expect(account.email).toBe('you@indeed.example');
    expect(account.name).toBe('');
    expect(hasAccountDetails(account)).toBe(true);
  });

  it('compacts a LinkedIn profile URL', () => {
    expect(compactProfileUrl('https://www.linkedin.com/in/ada-lovelace/')).toBe(
      'linkedin.com/in/ada-lovelace',
    );
  });
});
