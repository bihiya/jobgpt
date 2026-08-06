import { Button, Stack, TextField, Typography } from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { usersApi } from '../../api';

export default function ProfilePage() {
  const queryClient = useQueryClient();
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
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['profile'] }),
  });

  const uploadResume = async (file: File) => {
    const body = new FormData();
    body.append('file', file);
    body.append('is_default', 'true');
    await usersApi.uploadResume(body);
  };

  return (
    <Stack spacing={2} maxWidth={720}>
      <Typography variant="h4">Profile</Typography>
      <TextField label="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
      <TextField label="Skills (comma separated)" value={form.skills} onChange={(e) => setForm({ ...form, skills: e.target.value })} />
      <TextField label="Keywords" value={form.keywords} onChange={(e) => setForm({ ...form, keywords: e.target.value })} />
      <TextField label="Location" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
      <TextField label="Experience (years)" type="number" value={form.experience_years} onChange={(e) => setForm({ ...form, experience_years: Number(e.target.value) })} />
      <TextField label="Notice period (days)" type="number" value={form.notice_period_days} onChange={(e) => setForm({ ...form, notice_period_days: Number(e.target.value) })} />
      <TextField label="LinkedIn URL" value={form.linkedin_url} onChange={(e) => setForm({ ...form, linkedin_url: e.target.value })} />
      <TextField label="GitHub URL" value={form.github_url} onChange={(e) => setForm({ ...form, github_url: e.target.value })} />
      <TextField label="Portfolio URL" value={form.portfolio_url} onChange={(e) => setForm({ ...form, portfolio_url: e.target.value })} />
      <Button variant="contained" onClick={() => saveMutation.mutate()} sx={{ alignSelf: 'flex-start' }}>
        Save profile
      </Button>
      <Button variant="outlined" component="label" sx={{ alignSelf: 'flex-start' }}>
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
  );
}
