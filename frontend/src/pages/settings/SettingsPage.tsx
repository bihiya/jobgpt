import { Button, FormControlLabel, Switch, TextField, Typography } from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { settingsApi } from '../../api';
import PageShell from '../../components/common/PageShell';

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => (await settingsApi.get()).data,
  });
  const [form, setForm] = useState({
    match_threshold: 0.7,
    auto_apply: false,
    require_approval: true,
    use_llm_ranking: true,
    max_applications_per_day: 15,
    apply_cooldown_seconds: 45,
    batch_min_score: 0.85,
    headless: true,
    timezone: 'UTC',
    notification_email: true,
    follow_up_days: 7,
  });

  useEffect(() => {
    if (data) setForm((prev) => ({ ...prev, ...data }));
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: () => settingsApi.update(form),
    meta: { successMessage: 'Settings saved', errorMessage: 'Could not save settings' },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['settings'] }),
  });

  return (
    <PageShell
      sx={{ maxWidth: 560 }}
      skeleton="form"
      loading={isLoading}
      fetching={!isLoading && isFetching}
      busy={saveMutation.isPending}
    >
      <Typography variant="h4">Settings</Typography>
      <TextField
        label="Match threshold"
        type="number"
        inputProps={{ step: 0.05, min: 0, max: 1 }}
        value={form.match_threshold}
        onChange={(e) => setForm({ ...form, match_threshold: Number(e.target.value) })}
        fullWidth
      />
      <TextField
        label="Max applications / day"
        type="number"
        value={form.max_applications_per_day}
        onChange={(e) => setForm({ ...form, max_applications_per_day: Number(e.target.value) })}
        fullWidth
        helperText="Daily cap for batch + auto apply (anti-ban)"
      />
      <TextField
        label="Apply cooldown (seconds)"
        type="number"
        value={form.apply_cooldown_seconds}
        onChange={(e) => setForm({ ...form, apply_cooldown_seconds: Number(e.target.value) })}
        fullWidth
        helperText="Minimum wait between applications"
      />
      <TextField
        label="Batch min match score"
        type="number"
        inputProps={{ step: 0.05, min: 0, max: 1 }}
        value={form.batch_min_score}
        onChange={(e) => setForm({ ...form, batch_min_score: Number(e.target.value) })}
        fullWidth
        helperText="Default threshold for Smart batch approve (e.g. 0.85)"
      />
      <TextField
        label="Follow-up reminder (days)"
        type="number"
        value={form.follow_up_days}
        onChange={(e) => setForm({ ...form, follow_up_days: Number(e.target.value) })}
        fullWidth
      />
      <TextField
        label="Timezone"
        value={form.timezone}
        onChange={(e) => setForm({ ...form, timezone: e.target.value })}
        fullWidth
      />
      <FormControlLabel
        control={
          <Switch
            checked={form.require_approval}
            onChange={(e) => setForm({ ...form, require_approval: e.target.checked })}
          />
        }
        label="Require approval before apply (human-in-the-loop)"
      />
      <FormControlLabel
        control={
          <Switch
            checked={form.auto_apply}
            onChange={(e) => setForm({ ...form, auto_apply: e.target.checked })}
          />
        }
        label="Auto apply when approval is not required"
      />
      <FormControlLabel
        control={
          <Switch
            checked={form.use_llm_ranking}
            onChange={(e) => setForm({ ...form, use_llm_ranking: e.target.checked })}
          />
        }
        label="Use LLM-assisted ranking"
      />
      <FormControlLabel
        control={<Switch checked={form.headless} onChange={(e) => setForm({ ...form, headless: e.target.checked })} />}
        label="Headless browser automation"
      />
      <FormControlLabel
        control={
          <Switch
            checked={form.notification_email}
            onChange={(e) => setForm({ ...form, notification_email: e.target.checked })}
          />
        }
        label="Email notifications"
      />
      <Button
        variant="contained"
        onClick={() => saveMutation.mutate()}
        disabled={saveMutation.isPending}
        sx={{ alignSelf: 'flex-start' }}
      >
        {saveMutation.isPending ? 'Saving…' : 'Save settings'}
      </Button>
    </PageShell>
  );
}
