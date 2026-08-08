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
import PageShell from '../../components/common/PageShell';

const LABELS = ['Profile', 'Resume', 'Portals', 'First sync', 'Done'];

function OnboardingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['onboarding'],
    queryFn: async () => (await onboardingApi.status()).data,
  });

  const advance = useMutation({
    mutationFn: (step: string) => onboardingApi.advance(step),
    meta: { successMessage: 'Step completed', errorMessage: 'Could not advance' },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['onboarding'] }),
  });

  const firstSync = useMutation({
    mutationFn: () => onboardingApi.firstSync(),
    meta: { successMessage: 'First sync started', errorMessage: 'Sync failed' },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding'] });
      navigate('/approvals');
    },
  });

  const activeStep = useMemo(() => {
    const steps = data?.steps || ['profile', 'resume', 'portals', 'sync', 'done'];
    return Math.max(0, steps.indexOf(data?.step || 'profile'));
  }, [data]);

  if (isLoading || !data) {
    return <PageShell skeleton="form" loading />;
  }

  if (data.completed) {
    return (
      <PageShell sx={{ maxWidth: 640 }} fetching={isFetching}>
        <Typography variant="h4">You&apos;re all set</Typography>
        <Alert severity="success">Onboarding complete. Review approvals or open the dashboard.</Alert>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <Button variant="contained" onClick={() => navigate('/dashboard')}>
            Dashboard
          </Button>
          <Button variant="outlined" onClick={() => navigate('/approvals')}>
            Approvals
          </Button>
        </Stack>
      </PageShell>
    );
  }

  return (
    <PageShell
      sx={{ maxWidth: 720 }}
      fetching={!isLoading && isFetching}
      busy={advance.isPending || firstSync.isPending}
    >
      <Box>
        <Typography variant="h4" sx={{ mb: 1 }}>
          Welcome to JobPilot AI
        </Typography>
        <Typography color="text.secondary">
          Configure once — profile, resume, portals — then start syncing.
        </Typography>
      </Box>
      <Stepper
        activeStep={activeStep}
        alternativeLabel
        sx={{
          mb: 1,
          overflowX: 'auto',
          '& .MuiStepLabel-label': { fontSize: { xs: '0.7rem', sm: '0.85rem' } },
        }}
      >
        {LABELS.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {data.step === 'profile' && (
        <Stack spacing={2}>
          <Alert severity="info">Add skills, location, and keywords in your profile.</Alert>
          <Button variant="contained" onClick={() => navigate('/profile')} sx={{ alignSelf: 'flex-start' }}>
            Open profile
          </Button>
          <Button
            disabled={!data.checklist.profile || advance.isPending}
            onClick={() => advance.mutate('resume')}
            sx={{ alignSelf: 'flex-start' }}
          >
            Continue
          </Button>
        </Stack>
      )}

      {data.step === 'resume' && (
        <Stack spacing={2}>
          <Alert severity="info">Upload at least one resume (PDF/DOCX).</Alert>
          <Button variant="contained" onClick={() => navigate('/profile')} sx={{ alignSelf: 'flex-start' }}>
            Upload resume
          </Button>
          <Button
            disabled={!data.checklist.resume || advance.isPending}
            onClick={() => advance.mutate('portals')}
            sx={{ alignSelf: 'flex-start' }}
          >
            Continue
          </Button>
        </Stack>
      )}

      {data.step === 'portals' && (
        <Stack spacing={2}>
          <Alert severity="info">Connect LinkedIn, Indeed, Greenhouse, or another portal.</Alert>
          <Button variant="contained" onClick={() => navigate('/job-portals')} sx={{ alignSelf: 'flex-start' }}>
            Connect portals
          </Button>
          <Button
            disabled={!data.checklist.portals || advance.isPending}
            onClick={() => advance.mutate('sync')}
            sx={{ alignSelf: 'flex-start' }}
          >
            Continue
          </Button>
        </Stack>
      )}

      {data.step === 'sync' && (
        <Stack spacing={2}>
          <Alert severity="info">
            Kick off the first job fetch. Matched roles will land in your approval queue.
          </Alert>
          <Button
            variant="contained"
            onClick={() => firstSync.mutate()}
            disabled={firstSync.isPending}
            sx={{ alignSelf: 'flex-start' }}
          >
            Start first sync
          </Button>
        </Stack>
      )}
    </PageShell>
  );
}

export default memo(OnboardingPage);
