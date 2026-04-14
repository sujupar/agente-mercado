import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import { useDashboardContext } from '../context/DashboardContext';

export function useSignals(limit = 50) {
  const { activeEnvironment } = useDashboardContext();

  return useQuery({
    queryKey: ['signals', limit, activeEnvironment],
    queryFn: async () => {
      const response = await api.getSignals(limit, activeEnvironment);
      return response.data;
    },
    refetchInterval: 20000,
    refetchOnWindowFocus: true,
    staleTime: 15000,
    retry: 2,
    retryDelay: 1000,
  });
}
