import { Grid, Skeleton, Stack } from '@mui/material';
import { memo } from 'react';

function PageSkeletonComponent() {
  return (
    <Stack spacing={2}>
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
