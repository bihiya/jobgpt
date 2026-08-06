import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Box, Button, Link, Paper, Stack, TextField, Typography } from '@mui/material';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { authApi } from '../../api/auth';

const schema = z.object({
  full_name: z.string().min(1),
  email: z.string().email(),
  password: z.string().min(8),
});

type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setError('');
    try {
      await authApi.register(values);
      navigate('/login');
    } catch {
      setError('Unable to register. Email may already exist.');
    }
  };

  return (
    <Paper sx={{ p: 4 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Create account
      </Typography>
      <Box component="form" onSubmit={handleSubmit(onSubmit)}>
        <Stack spacing={2}>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField label="Full name" {...register('full_name')} error={!!errors.full_name} helperText={errors.full_name?.message} fullWidth />
          <TextField label="Email" type="email" {...register('email')} error={!!errors.email} helperText={errors.email?.message} fullWidth />
          <TextField label="Password" type="password" {...register('password')} error={!!errors.password} helperText={errors.password?.message} fullWidth />
          <Button type="submit" variant="contained" size="large" disabled={isSubmitting}>
            Register
          </Button>
          <Typography variant="body2">
            Already have an account? <Link component={RouterLink} to="/login">Sign in</Link>
          </Typography>
        </Stack>
      </Box>
    </Paper>
  );
}
