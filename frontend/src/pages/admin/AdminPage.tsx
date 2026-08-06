import { Alert, Stack, Typography } from '@mui/material';
import { useAppSelector } from '../../store/hooks';

export default function AdminPage() {
  const user = useAppSelector((s) => s.auth.user);
  const roles: string[] = user?.roles || [];
  const isAdmin = roles.includes('admin');

  return (
    <Stack spacing={2}>
      <Typography variant="h4">Admin</Typography>
      {isAdmin ? (
        <Alert severity="success">
          Admin console placeholder — manage users, roles, and global scheduler policies here.
        </Alert>
      ) : (
        <Alert severity="warning">You need the admin role to access this area.</Alert>
      )}
    </Stack>
  );
}
