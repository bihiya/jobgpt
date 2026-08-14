import { LinearProgress } from '@mui/material';
import { useIsFetching, useIsMutating } from '@tanstack/react-query';
import { memo } from 'react';

/** Global top progress bar for first-load fetches and mutations — not background refetches. */
function ApiLoadingBarComponent() {
  const fetching = useIsFetching({
    predicate: (query) => query.state.data === undefined,
  });
  const mutating = useIsMutating();
  const active = fetching + mutating > 0;

  if (!active) return null;

  return (
    <LinearProgress
      color="secondary"
      aria-label="Loading"
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: (t) => t.zIndex.appBar + 2,
        height: 3,
      }}
    />
  );
}

export default memo(ApiLoadingBarComponent);
