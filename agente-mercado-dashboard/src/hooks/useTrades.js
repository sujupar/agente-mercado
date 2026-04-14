import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import { useDashboardContext } from '../context/DashboardContext';

export function useTrades(filters = {}) {
  const { activeEnvironment } = useDashboardContext();
  const { limit = 50, offset = 0, status = null, winner = null } = filters;

  return useQuery({
    queryKey: ['trades', { limit, offset, status, winner, env: activeEnvironment }],
    queryFn: async () => {
      const params = { limit, offset, environment: activeEnvironment };
      if (status) params.status = status;
      if (winner !== null) params.winner = winner;
      const response = await api.getTrades(params);
      return response.data;
    },
    refetchInterval: 15000,
    refetchOnWindowFocus: true,
    staleTime: 12000,
    retry: 2,
    retryDelay: 1000,
  });
}
