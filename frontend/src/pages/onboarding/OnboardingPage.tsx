import {
  Box,
  Button,
  Step,
  StepLabel,
  Stepper,
  Typography,
  Stack,
  Alert,
} from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { memo, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { onboardingApi } from '../../api';
import PageSkeleton from '../../components/common/PageSkeleton';

const LABELS = ['Profile', 'Resume', 'Portals', 'First sync', 'Done'];

function OnboardingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['onboarding'],
    queryFn: async () => (await onboardingApi.status()).data,
  });

  const advance = useMutation({
    mutationFn: (step: string) => onboardingApi.advance(step),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['onboarding'] }),
  });

  const firstSync = useMutation({
    mutationFn: () => onboardingApi.firstSync(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding'] });
      navigate('/approvals');
    },
  });

  const activeStep = useMemo(() => {
    const steps = data?.steps || ['profile', 'resume', 'portals', 'sync', 'done'];
    return Math.max(0, steps.indexOf(data?.step || 'profile'));
  }, [data]);

  if (isLoading || !data) return <PageSkeleton />;

  if (data.completed) {
    return (
      <Stack spacing={2} maxWidth={640}>
        <Typography variant="h4">You&apos;re all set</Typography>
        <Alert severity="success">Onboarding complete. Review approvals or open the dashboard.</Alert>
        <Stack direction="row" spacing={1}>
          <Button variant="contained" onClick={() => navigate('/dashboard')}>
            Dashboard
          </Button>
          <Button variant="outlined" onClick={() => navigate('/approvals')}>
            Approvals
          </Button>
        </Stack>
      </Stack>
    );
  }

  return (
    <Box maxWidth={720}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Welcome to JobPilot AI
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Configure once — profile, resume, portals — then start syncing.
      </Typography>
      <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 4 }}>
        {LABELS.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {data.step === 'profile' && (
        <Stack spacing={2}>
          <Alert severity="info">Add skills, location, and keywords in your profile.</Alert>
          <Button variant="contained" onClick={() => navigate('/profile')}>
            Open profile
          </Button>
          <Button
            disabled={!data.checklist.profile}
            onClick={() => advance.mutate('resume')}
          >
            Continue
          </Button>
        </Stack>
      )}

      {data.step === 'resume' && (
        <Stack spacing={2}>
          <Alert severity="info">Upload at least one resume (PDF/DOCX).</Alert>
          <Button variant="contained" onClick={() => navigate('/profile')}>
            Upload resume
          </Button>
          <Button disabled={!data.checklist.resume} onClick={() => advance.mutate('portals')}>
            Continue
          </Button>
        </Stack>
      )}

      {data.step === 'portals' && (
        <Stack spacing={2}>
          <Alert severity="info">Connect LinkedIn, Indeed, Greenhouse, or another portal.</Alert>
          <Button variant="contained" onClick={() => navigate('/job-portals')}>
            Connect portals
          </Button>
          <Button disabled={!data.checklist.portals} onClick={() => advance.mutate('sync')}>
            Continue
          </Button>
        </Stack>
      )}

      {data.step === 'sync' && (
        <Stack spacing={2}>
          <Alert severity="info">
            Kick off the first job fetch. Matched roles will land in your approval queue.
          </Alert>
          <Button variant="contained" onClick={() => firstSync.mutate()} disabled={firstSync.isPending}>
            Start first sync
          </Button>
        </Stack>
      )}
    </Box>
  );
}

export default memo(OnboardingPage);
