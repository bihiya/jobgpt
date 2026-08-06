import { zodResolver } from '@hookform/resolvers/zod';
import { Box, Button, Link, Paper, Stack, TextField, Typography } from '@mui/material';
import { useForm } from 'react-hook-form';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { authApi } from '../../api/auth';
import { useToast } from '../../hooks/useToast';
import { useAppDispatch } from '../../store/hooks';
import { setCredentials } from '../../store/slices/authSlice';

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { apiSuccess, apiError } = useToast();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    try {
      const { data } = await authApi.login(values);
      localStorage.setItem('refresh_token', data.refresh_token);
      dispatch(
        setCredentials({
          user: { email: values.email, full_name: values.email.split('@')[0] },
          accessToken: data.access_token,
        }),
      );
      const me = await authApi.me();
      dispatch(
        setCredentials({
          user: me.data,
          accessToken: data.access_token,
        }),
      );
      apiSuccess('Welcome back');
      navigate('/dashboard');
    } catch (err) {
      apiError(err, 'Invalid email or password');
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
        Sign in
      </Typography>
      <Box component="form" onSubmit={handleSubmit(onSubmit)}>
        <Stack spacing={2}>
          <TextField
            label="Email"
            type="email"
            {...register('email')}
            error={!!errors.email}
            helperText={errors.email?.message}
            fullWidth
          />
          <TextField
            label="Password"
            type="password"
            {...register('password')}
            error={!!errors.password}
            helperText={errors.password?.message}
            fullWidth
          />
          <Button type="submit" variant="contained" size="large" disabled={isSubmitting}>
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </Button>
          <Typography variant="body2">
            No account? <Link component={RouterLink} to="/register">Register</Link>
            {' · '}
            <Link component={RouterLink} to="/forgot-password">Forgot password</Link>
          </Typography>
        </Stack>
      </Box>
    </Paper>
  );
}
