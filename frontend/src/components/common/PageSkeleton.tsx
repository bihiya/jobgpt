import { Grid, Skeleton, Stack } from '@mui/material';
import { memo } from 'react';

export type PageSkeletonVariant = 'default' | 'form' | 'list';

type Props = {
  variant?: PageSkeletonVariant;
};

function PageSkeletonComponent({ variant = 'default' }: Props) {
  if (variant === 'form') {
    return (
      <Stack spacing={2} sx={{ width: '100%', maxWidth: 720 }}>
        <Skeleton variant="text" width={200} height={48} />
        <Skeleton variant="text" width={280} height={22} />
        {[1, 2, 3, 4, 5, 6].map((key) => (
          <Skeleton key={key} variant="rounded" height={56} />
        ))}
        <Skeleton variant="rounded" width={140} height={40} />
      </Stack>
    );
  }

  if (variant === 'list') {
    return (
      <Stack spacing={1.5} sx={{ width: '100%' }}>
        <Skeleton variant="text" width={220} height={48} />
        <Skeleton variant="text" width={360} height={22} />
        {[1, 2, 3, 4, 5, 6].map((key) => (
          <Skeleton key={key} variant="rounded" height={72} />
        ))}
      </Stack>
    );
  }

  return (
    <Stack spacing={2} sx={{ width: '100%' }}>
      <Skeleton variant="text" width={240} height={48} />
      <Skeleton variant="text" width={360} height={24} />
      <Grid container spacing={2}>
        {[1, 2, 3, 4].map((key) => (
          <Grid key={key} size={{ xs: 12, sm: 6, md: 3 }}>
            <Skeleton variant="rounded" height={120} />
          </Grid>
        ))}
      </Grid>
      <Skeleton variant="rounded" height={320} />
    </Stack>
  );
}

export default memo(PageSkeletonComponent);
