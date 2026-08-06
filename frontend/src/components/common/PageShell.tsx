import { Stack, type StackProps } from '@mui/material';
import { memo } from 'react';

type Props = StackProps & {
  stagger?: boolean;
};

/** Animated responsive page wrapper used across the app. */
function PageShell({ children, stagger = true, className, sx, ...rest }: Props) {
  return (
    <Stack
      spacing={2}
      className={[stagger ? 'jp-page jp-stagger' : 'jp-page', className].filter(Boolean).join(' ')}
      sx={{
        width: '100%',
        maxWidth: 1400,
        mx: 'auto',
        ...sx,
      }}
      {...rest}
    >
      {children}
    </Stack>
  );
}

export default memo(PageShell);
