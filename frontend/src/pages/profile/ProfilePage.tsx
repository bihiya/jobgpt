import { Button, Stack, TextField, Typography } from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { usersApi } from '../../api';
import PageShell from '../../components/common/PageShell';
import { useToast } from '../../hooks/useToast';

export default function ProfilePage() {
  const queryClient = useQueryClient();
  const { apiSuccess, apiError } = useToast();
  const { data } = useQuery({
    queryKey: ['profile'],
    queryFn: async () => (await usersApi.me()).data,
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

  const uploadResume = async (file: File) => {
    try {
      const body = new FormData();
      body.append('file', file);
      body.append('is_default', 'true');
      await usersApi.uploadResume(body);
      apiSuccess('Resume uploaded');
      void queryClient.invalidateQueries({ queryKey: ['profile'] });
    } catch (err) {
      apiError(err, 'Resume upload failed');
    }
  };

  return (
    <PageShell sx={{ maxWidth: 720 }}>
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
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
        <Button variant="contained" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
          {saveMutation.isPending ? 'Saving…' : 'Save profile'}
        </Button>
        <Button variant="outlined" component="label">
          Upload resume
          <input
            hidden
            type="file"
            accept=".pdf,.doc,.docx"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void uploadResume(file);
            }}
          />
        </Button>
      </Stack>
    </PageShell>
  );
}
