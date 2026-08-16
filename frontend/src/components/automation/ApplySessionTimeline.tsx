import { Chip, CircularProgress, Stack, Step, StepLabel, Stepper, Typography } from '@mui/material';
import { memo } from 'react';
import { formatWhen } from '../../utils/datetime';

export type SessionStep = {
  key?: string;
  label?: string;
  status?: string;
  detail?: string;
  at?: string;
};

type Props = {
  steps: SessionStep[];
  dense?: boolean;
  live?: boolean;
};

function colorFor(status?: string): 'success' | 'error' | 'warning' | 'info' | 'default' {
  if (status === 'ok') return 'success';
  if (status === 'error') return 'error';
  if (status === 'warn' || status === 'pending') return 'warning';
  if (status === 'skipped') return 'default';
  return 'info';
}

function ApplySessionTimeline({ steps, dense, live }: Props) {
  if (!steps?.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        No apply session steps yet.
      </Typography>
    );
  }

  const lastIdx = steps.length - 1;

  if (dense) {
    return (
      <Stack spacing={1}>
        {steps.map((step, idx) => {
          const current = Boolean(live && idx === lastIdx);
          return (
            <Stack
              key={`${step.key}-${idx}`}
              direction="row"
              spacing={1}
              alignItems="flex-start"
              sx={current ? { animation: 'jp-step-in 0.35s ease' } : undefined}
            >
              {current ? (
                <CircularProgress size={16} sx={{ mt: 0.35 }} />
              ) : (
                <Chip size="small" label={step.status || 'ok'} color={colorFor(step.status)} />
              )}
              <Stack spacing={0.15} sx={{ minWidth: 0, flex: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: current ? 800 : 600 }}>
                  {step.label || step.key}
                </Typography>
                {step.detail ? (
                  <Typography variant="caption" color="text.secondary">
                    {step.detail}
                  </Typography>
                ) : null}
                {step.at ? (
                  <Typography variant="caption" color="text.disabled">
                    {formatWhen(step.at)}
                  </Typography>
                ) : null}
              </Stack>
            </Stack>
          );
        })}
      </Stack>
    );
  }

  return (
    <Stepper orientation="vertical" activeStep={live ? lastIdx : steps.length}>
      {steps.map((step, idx) => {
        const current = Boolean(live && idx === lastIdx);
        return (
          <Step key={`${step.key}-${idx}`} completed={!current && step.status === 'ok'} active={current}>
            <StepLabel error={step.status === 'error'} icon={current ? <CircularProgress size={18} /> : undefined}>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                {step.label || step.key}
              </Typography>
              {step.detail ? (
                <Typography variant="caption" color="text.secondary" display="block">
                  {step.detail}
                </Typography>
              ) : null}
              {step.at ? (
                <Typography variant="caption" color="text.disabled" display="block">
                  {formatWhen(step.at)}
                </Typography>
              ) : null}
            </StepLabel>
          </Step>
        );
      })}
    </Stepper>
  );
}

export default memo(ApplySessionTimeline);
