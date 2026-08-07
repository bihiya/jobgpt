import { Box, LinearProgress, Stack, type StackProps } from '@mui/material';
import { memo, type ReactNode } from 'react';
import PageSkeleton, { type PageSkeletonVariant } from './PageSkeleton';

type Props = StackProps & {
  stagger?: boolean;
  /** Initial query load — replaces children with a skeleton. */
  loading?: boolean;
  /** Background refetch / filter change — keeps content, shows a thin bar. */
  fetching?: boolean;
  skeleton?: PageSkeletonVariant;
  /** Optional overlay while a mutation is in flight (e.g. form save). */
  busy?: boolean;
  children?: ReactNode;
};

/** Animated responsive page wrapper used across the app. */
function PageShell({
  children,
  stagger = true,
  className,
  sx,
  loading = false,
  fetching = false,
  busy = false,
  skeleton = 'default',
  ...rest
}: Props) {
  if (loading) {
    return <PageSkeleton variant={skeleton} />;
  }

  return (
    <Box sx={{ position: 'relative', width: '100%' }}>
      {(fetching || busy) && (
        <LinearProgress
          color="secondary"
          aria-label={busy ? 'Saving' : 'Refreshing'}
          sx={{
            position: 'sticky',
            top: 0,
            zIndex: 2,
            mb: 1.5,
            borderRadius: 1,
            height: 3,
          }}
        />
      )}
      <Stack
        spacing={2}
        className={[stagger ? 'jp-page jp-stagger' : 'jp-page', className].filter(Boolean).join(' ')}
        sx={{
          width: '100%',
          maxWidth: 1400,
          mx: 'auto',
          opacity: busy ? 0.72 : 1,
          pointerEvents: busy ? 'none' : 'auto',
          transition: 'opacity 0.2s ease',
          ...sx,
        }}
        {...rest}
      >
        {children}
      </Stack>
    </Box>
  );
}

export default memo(PageShell);
