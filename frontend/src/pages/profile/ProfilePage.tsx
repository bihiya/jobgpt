import { Person, Work } from '@mui/icons-material';
import { Box, Button, Divider, Paper, Stack, TextField, Typography } from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState, type ChangeEvent, type ReactNode } from 'react';
import { usersApi } from '../../api';
import ActivityTimeline from '../../components/activity/ActivityTimeline';
import PageShell from '../../components/common/PageShell';
import ResumeVersions, { type ResumeVersion } from '../../components/profile/ResumeVersions';
import { useToast } from '../../hooks/useToast';
import { emptyProfileForm, profileFromApi, profileToUpdate, type ProfileForm } from './profileForm';

function ProfileSection({
  id,
  icon,
  title,
  hint,
  children,
}: {
  id: string;
  icon: ReactNode;
  title: string;
  hint: string;
  children: ReactNode;
}) {
  return (
    <Paper
      id={id}
      data-testid={id}
      variant="outlined"
      sx={{ p: { xs: 2, sm: 2.5 }, borderRadius: 3, flex: 1, minWidth: 0 }}
    >
      <Stack spacing={2}>
        <Box>
          <Stack direction="row" spacing={1} alignItems="center">
            {icon}
            <Typography variant="h6">{title}</Typography>
          </Stack>
          <Typography color="text.secondary" variant="body2">
            {hint}
          </Typography>
        </Box>
        {children}
      </Stack>
    </Paper>
  );
}

const NUMBER_FIELDS = new Set<keyof ProfileForm>([
  'experience_years',
  'notice_period_days',
  'salary_min',
  'salary_max',
]);

export default function ProfilePage() {
  const queryClient = useQueryClient();
  const { apiSuccess, apiError } = useToast();
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['profile'],
    queryFn: async () => (await usersApi.me()).data,
  });
  const {
    data: activity,
    isLoading: activityLoading,
    isFetching: activityFetching,
  } = useQuery({
    queryKey: ['user-activity', 'profile'],
    queryFn: async () => (await usersApi.activity({ page_size: 20 })).data,
  });
  const [form, setForm] = useState(emptyProfileForm);

  useEffect(() => {
    if (!data) return;
    setForm(profileFromApi(data));
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: () => usersApi.update(profileToUpdate(form)),
    meta: { successMessage: 'Profile saved', errorMessage: 'Could not save profile' },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['profile'] }),
  });

  const {
    data: resumeRows,
    isLoading: resumesLoading,
    isFetching: resumesFetching,
  } = useQuery({
    queryKey: ['resumes'],
    queryFn: async () => (await usersApi.resumes()).data as ResumeVersion[],
  });
  const resumes = resumeRows || [];

  const [uploading, setUploading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);

  const previewResume = useMemo(() => {
    if (previewId) {
      return resumes.find((row) => row.id === previewId) || null;
    }
    return resumes.find((row) => row.is_default) || resumes[0] || null;
  }, [resumes, previewId]);

  useEffect(() => {
    if (!previewResume || (previewResume.file_type || '').toLowerCase() !== 'pdf') {
      setPreviewUrl(null);
      return;
    }
    let objectUrl = '';
    let cancelled = false;
    void (async () => {
      try {
        const res = await usersApi.downloadResume(previewResume.id, true);
        if (res.headers?.['x-jobpilot-demo'] === '1') {
          if (!cancelled) setPreviewUrl(null);
          return;
        }
        const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
        objectUrl = url;
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        setPreviewUrl(url);
      } catch {
        if (!cancelled) setPreviewUrl(null);
      }
    })();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [previewResume?.id, previewResume?.file_type]);

  const uploadResume = async (file: File) => {
    setUploading(true);
    try {
      const body = new FormData();
      body.append('file', file);
      body.append('is_default', 'true');
      await usersApi.uploadResume(body);
      setPreviewId(null);
      apiSuccess('Resume uploaded');
      void queryClient.invalidateQueries({ queryKey: ['resumes'] });
      void queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    } catch (err) {
      apiError(err, 'Resume upload failed');
    } finally {
      setUploading(false);
    }
  };

  const downloadResume = async (resume: ResumeVersion) => {
    setBusyId(resume.id);
    try {
      const res = await usersApi.downloadResume(resume.id);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = resume.name || `resume.${resume.file_type || 'pdf'}`;
      a.click();
      window.URL.revokeObjectURL(url);
      apiSuccess('Download started');
    } catch (err) {
      apiError(err, 'Resume download failed');
    } finally {
      setBusyId(null);
    }
  };

  const deleteResume = async (resume: ResumeVersion) => {
    setBusyId(resume.id);
    try {
      await usersApi.deleteResume(resume.id);
      if (previewId === resume.id) setPreviewId(null);
      apiSuccess('Resume deleted');
      void queryClient.invalidateQueries({ queryKey: ['resumes'] });
      void queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    } catch (err) {
      apiError(err, 'Could not delete resume');
    } finally {
      setBusyId(null);
    }
  };

  const setField = (key: keyof ProfileForm) => (event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setForm((prev) => ({
      ...prev,
      [key]: NUMBER_FIELDS.has(key) ? Number(value) : value,
    }));
  };

  return (
    <PageShell
      sx={{ maxWidth: 1100 }}
      skeleton="form"
      loading={isLoading}
      fetching={
        (!isLoading && isFetching) ||
        (!activityLoading && activityFetching) ||
        (!resumesLoading && resumesFetching)
      }
      busy={saveMutation.isPending || uploading || Boolean(busyId)}
    >
      <Box>
        <Typography variant="h4">Profile</Typography>
        <Typography color="text.secondary">
          Personal details and job preferences used for matching and auto-apply.
        </Typography>
      </Box>

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="stretch">
        <ProfileSection
          id="profile-personal"
          icon={<Person color="primary" fontSize="small" />}
          title="Personal"
          hint="Who you are and how employers can find you."
        >
          <TextField label="Full name" value={form.full_name} onChange={setField('full_name')} fullWidth />
          <TextField label="Email" value={form.email} fullWidth disabled helperText="Sign-in email" />
          <TextField label="Location" value={form.location} onChange={setField('location')} fullWidth />
          <TextField label="LinkedIn URL" value={form.linkedin_url} onChange={setField('linkedin_url')} fullWidth />
          <TextField label="GitHub URL" value={form.github_url} onChange={setField('github_url')} fullWidth />
          <TextField label="Portfolio URL" value={form.portfolio_url} onChange={setField('portfolio_url')} fullWidth />
        </ProfileSection>

        <ProfileSection
          id="profile-job"
          icon={<Work color="primary" fontSize="small" />}
          title="Job"
          hint="What you want to apply for — used to score matches and fill forms."
        >
          <TextField
            label="Skills (comma separated)"
            value={form.skills}
            onChange={setField('skills')}
            fullWidth
          />
          <TextField
            label="Keywords"
            value={form.keywords}
            onChange={setField('keywords')}
            fullWidth
            helperText="Roles, stacks, or filters such as remote, frontend"
          />
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <TextField
              label="Experience (years)"
              type="number"
              value={form.experience_years}
              onChange={setField('experience_years')}
              fullWidth
            />
            <TextField
              label="Notice period (days)"
              type="number"
              value={form.notice_period_days}
              onChange={setField('notice_period_days')}
              fullWidth
            />
          </Stack>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <TextField
              label="Salary min"
              type="number"
              value={form.salary_min}
              onChange={setField('salary_min')}
              fullWidth
            />
            <TextField
              label="Salary max"
              type="number"
              value={form.salary_max}
              onChange={setField('salary_max')}
              fullWidth
            />
            <TextField
              label="Currency"
              value={form.salary_currency}
              onChange={setField('salary_currency')}
              sx={{ minWidth: { sm: 120 } }}
            />
          </Stack>
        </ProfileSection>
      </Stack>

      <Box data-testid="profile-job-resumes">
        <ResumeVersions
          resumes={resumes}
          uploading={uploading}
          loading={resumesLoading}
          busyId={busyId}
          previewUrl={previewUrl}
          previewName={previewResume?.name || ''}
          selectedId={previewResume?.id || null}
          onUpload={(file) => void uploadResume(file)}
          onDownload={(resume) => void downloadResume(resume)}
          onDelete={(resume) => void deleteResume(resume)}
          onSelect={(resume) => setPreviewId(resume.id)}
        />
      </Box>

      <Button
        variant="contained"
        onClick={() => saveMutation.mutate()}
        disabled={saveMutation.isPending}
        sx={{ alignSelf: 'flex-start' }}
      >
        {saveMutation.isPending ? 'Saving…' : 'Save profile'}
      </Button>

      <Divider sx={{ my: 1 }} />
      <Typography variant="h5">Your activity</Typography>
      <Typography color="text.secondary">
        Account-level audit trail — sign-in, profile edits, resumes, settings, and more.
      </Typography>
      <ActivityTimeline
        dense
        items={activity?.items || []}
        emptyText="No account activity recorded yet."
      />
    </PageShell>
  );
}
