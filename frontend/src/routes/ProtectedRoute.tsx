import { Outlet } from 'react-router-dom';

/**
 * App shell is publicly browsable. Write actions are gated by LoginGateDialog
 * via the API client / useRequireAuth — guests are no longer redirected away.
 */
export default function ProtectedRoute() {
  return <Outlet />;
}
