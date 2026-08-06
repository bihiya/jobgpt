import { Alert, Box, Button, Link, Paper, Stack, TextField, Typography } from '@mui/material';
import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);

  return (
    <Paper sx={{ p: 4 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Reset password
      </Typography>
      <Box
        component="form"
        onSubmit={(e) => {
          e.preventDefault();
          setSent(true);
        }}
      >
        <Stack spacing={2}>
          {sent && <Alert severity="success">If the email exists, a reset link will be sent.</Alert>}
          <TextField label="Email" type="email" required fullWidth />
          <Button type="submit" variant="contained" size="large">
            Send reset link
          </Button>
          <Typography variant="body2">
            <Link component={RouterLink} to="/login">Back to sign in</Link>
          </Typography>
        </Stack>
      </Box>
    </Paper>
  );
}
