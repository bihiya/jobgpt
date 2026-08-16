import { Box, Button, Link, Paper, Stack, TextField, Typography } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { useToast } from '../../hooks/useToast';

export default function ForgotPasswordPage() {
  const { success } = useToast();

  return (
    <Paper
      elevation={1}
      sx={{
        p: { xs: 3, sm: 4 },
        borderRadius: 4,
        animation: 'jp-scale-in 0.45s cubic-bezier(0.22, 1, 0.36, 1)',
        boxShadow: '0 18px 50px rgba(226, 24, 111, 0.14)',
      }}
    >
      <Typography variant="h5" sx={{ mb: 2 }}>
        Reset password
      </Typography>
      <Box
        component="form"
        onSubmit={(e) => {
          e.preventDefault();
          success('If the email exists, a reset link will be sent');
        }}
      >
        <Stack spacing={2}>
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
