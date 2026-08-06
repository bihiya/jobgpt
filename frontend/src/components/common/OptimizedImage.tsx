import { Box, Skeleton } from '@mui/material';
import { memo, useCallback, useState } from 'react';

type Props = {
  src: string;
  alt: string;
  width?: number | string;
  height?: number | string;
  /** Prefer modern formats via srcset when available */
  srcSet?: string;
  loading?: 'lazy' | 'eager';
  sizes?: string;
};

/**
 * Image optimization helper: lazy loading, aspect-box, skeleton, decode=async.
 * Pair with CDN/WebP assets in production.
 */
function OptimizedImageComponent({
  src,
  alt,
  width = '100%',
  height = 200,
  srcSet,
  loading = 'lazy',
  sizes,
}: Props) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);

  const onLoad = useCallback(() => setLoaded(true), []);
  const onError = useCallback(() => setError(true), []);

  return (
    <Box sx={{ position: 'relative', width, height, overflow: 'hidden', bgcolor: 'action.hover' }}>
      {!loaded && !error && (
        <Skeleton
          variant="rectangular"
          width="100%"
          height="100%"
          sx={{ position: 'absolute', inset: 0 }}
        />
      )}
      {!error && (
        <Box
          component="img"
          src={src}
          srcSet={srcSet}
          sizes={sizes}
          alt={alt}
          loading={loading}
          decoding="async"
          onLoad={onLoad}
          onError={onError}
          sx={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            opacity: loaded ? 1 : 0,
            transition: 'opacity 200ms ease',
          }}
        />
      )}
    </Box>
  );
}

export default memo(OptimizedImageComponent);
