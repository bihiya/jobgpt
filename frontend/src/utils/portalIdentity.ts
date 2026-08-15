export type SessionIdentity = {
  display_name?: string;
  headline?: string;
  location?: string;
  profile_url?: string;
  public_id?: string;
  captured_at?: string | null;
};

export type PortalAccount = {
  name: string;
  location: string;
  headline: string;
  profileUrl: string;
  email: string;
};

export function accountFromPortal(portal: {
  username?: string;
  session_identity?: SessionIdentity | null;
}): PortalAccount {
  const ident = portal.session_identity || {};
  return {
    name: String(ident.display_name || '').trim(),
    location: String(ident.location || '').trim(),
    headline: String(ident.headline || '').trim(),
    profileUrl: String(ident.profile_url || '').trim(),
    email: String(portal.username || '').trim(),
  };
}

export function hasAccountDetails(account: PortalAccount): boolean {
  return Boolean(account.name || account.location || account.email);
}

export function compactProfileUrl(url: string): string {
  return url.replace(/^https?:\/\/(www\.)?/i, '').replace(/\/$/, '');
}
