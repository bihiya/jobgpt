import { Button, Divider, Stack, TextField, Typography } from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { usersApi } from '../../api';
import ActivityTimeline from '../../components/activity/ActivityTimeline';
import PageShell from '../../components/common/PageShell';
import ResumeVersions, { type ResumeVersion } from '../../components/profile/ResumeVersions';
import { useToast } from '../../hooks/useToast';

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
  const [form, setForm] = useState({
    full_name: '',
    skills: '',
    location: '',
    keywords: '',
    experience_years: 0,
    notice_period_days: 0,
    linkedin_url: '',
    github_url: '',
    portfolio_url: '',
  });

  useEffect(() => {
    if (!data) return;
    setForm({
      full_name: data.full_name || '',
      skills: (data.profile?.skills || []).join(', '),
      location: data.profile?.location || '',
      keywords: (data.profile?.keywords || []).join(', '),
      experience_years: data.profile?.experience_years || 0,
      notice_period_days: data.profile?.notice_period_days || 0,
      linkedin_url: data.profile?.linkedin_url || '',
      github_url: data.profile?.github_url || '',
      portfolio_url: data.profile?.portfolio_url || '',
    });
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: () =>
      usersApi.update({
        full_name: form.full_name,
        profile: {
          skills: form.skills.split(',').map((s) => s.trim()).filter(Boolean),
          keywords: form.keywords.split(',').map((s) => s.trim()).filter(Boolean),
          location: form.location,
          experience_years: Number(form.experience_years),
          notice_period_days: Number(form.notice_period_days),
          linkedin_url: form.linkedin_url,
          github_url: form.github_url,
          portfolio_url: form.portfolio_url,
        },
      }),
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

  const previewResume = useMemo(
    () => resumes.find((row) => row.is_default) || resumes[0] || null,
    [resumes],
  );

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
      apiSuccess('Resume deleted');
      void queryClient.invalidateQueries({ queryKey: ['resumes'] });
      void queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    } catch (err) {
      apiError(err, 'Could not delete resume');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <PageShell
      sx={{ maxWidth: 840 }}
      skeleton="form"
      loading={isLoading || activityLoading || resumesLoading}
      fetching={
        (!isLoading && isFetching) ||
        (!activityLoading && activityFetching) ||
        (!resumesLoading && resumesFetching)
      }
      busy={saveMutation.isPending || uploading || Boolean(busyId)}
    >
      <Typography variant="h4">Profile</Typography>
      <TextField label="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} fullWidth />
      <TextField label="Skills (comma separated)" value={form.skills} onChange={(e) => setForm({ ...form, skills: e.target.value })} fullWidth />
      <TextField label="Keywords" value={form.keywords} onChange={(e) => setForm({ ...form, keywords: e.target.value })} fullWidth />
      <TextField label="Location" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} fullWidth />
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <TextField label="Experience (years)" type="number" value={form.experience_years} onChange={(e) => setForm({ ...form, experience_years: Number(e.target.value) })} fullWidth />
        <TextField label="Notice period (days)" type="number" value={form.notice_period_days} onChange={(e) => setForm({ ...form, notice_period_days: Number(e.target.value) })} fullWidth />
      </Stack>
      <TextField label="LinkedIn URL" value={form.linkedin_url} onChange={(e) => setForm({ ...form, linkedin_url: e.target.value })} fullWidth />
      <TextField label="GitHub URL" value={form.github_url} onChange={(e) => setForm({ ...form, github_url: e.target.value })} fullWidth />
      <TextField label="Portfolio URL" value={form.portfolio_url} onChange={(e) => setForm({ ...form, portfolio_url: e.target.value })} fullWidth />
      <Button
        variant="contained"
        onClick={() => saveMutation.mutate()}
        disabled={saveMutation.isPending}
        sx={{ alignSelf: 'flex-start' }}
      >
        {saveMutation.isPending ? 'Saving…' : 'Save profile'}
      </Button>

      <Divider sx={{ my: 1 }} />
      <ResumeVersions
        resumes={resumes}
        uploading={uploading}
        busyId={busyId}
        previewUrl={previewUrl}
        previewName={previewResume?.name || ''}
        onUpload={(file) => void uploadResume(file)}
        onDownload={(resume) => void downloadResume(resume)}
        onDelete={(resume) => void deleteResume(resume)}
      />

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
