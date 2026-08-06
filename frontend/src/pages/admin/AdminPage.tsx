import { Alert, Stack, Typography } from '@mui/material';
import { memo } from 'react';
import { useAppSelector } from '../../store/hooks';
import { selectIsAdmin } from '../../store/selectors/authSelectors';

function AdminPage() {
  const isAdmin = useAppSelector(selectIsAdmin);

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

export default memo(AdminPage);
