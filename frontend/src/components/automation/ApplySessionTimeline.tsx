import { Chip, Stack, Step, StepLabel, Stepper, Typography } from '@mui/material';
import { memo } from 'react';

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
};

function colorFor(status?: string): 'success' | 'error' | 'warning' | 'info' | 'default' {
  if (status === 'ok') return 'success';
  if (status === 'error') return 'error';
  if (status === 'warn' || status === 'pending') return 'warning';
  if (status === 'skipped') return 'default';
  return 'info';
}

function ApplySessionTimeline({ steps, dense }: Props) {
  if (!steps?.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        No apply session steps yet.
      </Typography>
    );
  }

  if (dense) {
    return (
      <Stack spacing={1}>
        {steps.map((step, idx) => (
          <Stack key={`${step.key}-${idx}`} direction="row" spacing={1} alignItems="center">
            <Chip size="small" label={step.status || 'ok'} color={colorFor(step.status)} />
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {step.label || step.key}
            </Typography>
            {step.detail ? (
              <Typography variant="caption" color="text.secondary" noWrap sx={{ maxWidth: 220 }}>
                {step.detail}
              </Typography>
            ) : null}
          </Stack>
        ))}
      </Stack>
    );
  }

  return (
    <Stepper orientation="vertical" activeStep={steps.length}>
      {steps.map((step, idx) => (
        <Step key={`${step.key}-${idx}`} completed={step.status === 'ok'}>
          <StepLabel error={step.status === 'error'}>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              {step.label || step.key}
            </Typography>
            {step.detail ? (
              <Typography variant="caption" color="text.secondary" display="block">
                {step.detail}
              </Typography>
            ) : null}
          </StepLabel>
        </Step>
      ))}
    </Stepper>
  );
}

export default memo(ApplySessionTimeline);
