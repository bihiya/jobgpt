import { useMemo, useRef } from 'react';
import { throttle } from '../utils/throttle';

/** Stable throttled callback that always invokes the latest function. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function useThrottleCallback<T extends (...args: any[]) => void>(fn: T, wait = 200) {
  const fnRef = useRef(fn);
  fnRef.current = fn;
  return useMemo(
    () => throttle((...args: Parameters<T>) => fnRef.current(...args), wait),
    [wait],
  );
}
