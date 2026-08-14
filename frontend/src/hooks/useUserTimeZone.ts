import { useQuery } from '@tanstack/react-query';
import { settingsApi } from '../api';
import { useAppSelector } from '../store/hooks';
import { selectIsAuthenticated } from '../store/selectors/authSelectors';
import { resolveTimeZone } from '../utils/datetime';

/** Device timezone, unless the user set a non-UTC timezone in Settings. */
export function useUserTimeZone(): string {
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const { data } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => (await settingsApi.get()).data,
    staleTime: 60_000,
    enabled: isAuthenticated,
  });
  return resolveTimeZone(data?.timezone);
}
