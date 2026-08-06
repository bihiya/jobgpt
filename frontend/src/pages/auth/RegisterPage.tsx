import { zodResolver } from '@hookform/resolvers/zod';
import { Box, Button, Link, Paper, Stack, TextField, Typography } from '@mui/material';
import { useForm } from 'react-hook-form';
import { Link as RouterLink, useNavigate, useSearchParams } from 'react-router-dom';
import { z } from 'zod';
import { authApi } from '../../api/auth';
import { useToast } from '../../hooks/useToast';

const schema = z.object({
  full_name: z.string().min(1),
  email: z.string().email(),
  password: z.string().min(8),
});

type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { apiSuccess, apiError } = useToast();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    try {
      await authApi.register(values);
      apiSuccess('Account created — sign in to continue');
      const redirect = params.get('redirect');
      navigate(redirect ? `/login?redirect=${encodeURIComponent(redirect)}` : '/login');
    } catch (err) {
      apiError(err, 'Unable to register. Email may already exist.');
    }
  };

  return (
    <Paper
      elevation={1}
      sx={{
        p: { xs: 3, sm: 4 },
        borderRadius: 3,
        animation: 'jp-scale-in 0.4s cubic-bezier(0.22, 1, 0.36, 1)',
      }}
    >
      <Typography variant="h5" sx={{ mb: 2 }}>
        Create account
      </Typography>
      <Box component="form" onSubmit={handleSubmit(onSubmit)}>
        <Stack spacing={2}>
          <TextField label="Full name" {...register('full_name')} error={!!errors.full_name} helperText={errors.full_name?.message} fullWidth />
          <TextField label="Email" type="email" {...register('email')} error={!!errors.email} helperText={errors.email?.message} fullWidth />
          <TextField label="Password" type="password" {...register('password')} error={!!errors.password} helperText={errors.password?.message} fullWidth />
          <Button type="submit" variant="contained" size="large" disabled={isSubmitting}>
            Register
          </Button>
          <Typography variant="body2">
            Already have an account? <Link component={RouterLink} to="/login">Sign in</Link>
            {' · '}
            <Link component={RouterLink} to="/dashboard">Browse as guest</Link>
          </Typography>
        </Stack>
      </Box>
    </Paper>
  );
}
