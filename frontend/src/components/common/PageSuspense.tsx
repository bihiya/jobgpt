import { Box, CircularProgress } from '@mui/material';
import { Suspense, type ReactNode } from 'react';
import PageSkeleton from './PageSkeleton';

type Props = {
  children: ReactNode;
  fallback?: 'spinner' | 'skeleton';
};

function SpinnerFallback() {
  return (
    <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 240 }}>
      <CircularProgress size={36} />
    </Box>
  );
}

/** Route-level Suspense boundary for lazy pages + concurrent rendering. */
export default function PageSuspense({ children, fallback = 'skeleton' }: Props) {
  return (
    <Suspense fallback={fallback === 'spinner' ? <SpinnerFallback /> : <PageSkeleton />}>
      {children}
    </Suspense>
  );
}
