import { Box, Skeleton } from '@mui/material';
import { memo } from 'react';

function DataGridSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <Box sx={{ width: '100%', bgcolor: 'background.paper', borderRadius: 2, p: 2 }}>
      {Array.from({ length: rows }).map((_, i) => (
        <Box key={i} sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
          <Skeleton variant="rectangular" width={56} height={56} sx={{ borderRadius: 1 }} />
          <Box sx={{ flex: 1 }}>
            <Skeleton width="60%" height={24} />
            <Skeleton width="40%" height={18} sx={{ mt: 1 }} />
          </Box>
        </Box>
      ))}
    </Box>
  );
}

export default memo(DataGridSkeleton);
