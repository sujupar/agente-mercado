import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import { useDashboardContext } from '../context/DashboardContext';

export function useAgentData() {
  const { activeEnvironment } = useDashboardContext();

  return useQuery({
    queryKey: ['agentStatus', activeEnvironment],
    queryFn: async () => {
      const response = await api.status(activeEnvironment);
      return response.data;
    },
    refetchInterval: 10000,
    refetchOnWindowFocus: true,
    staleTime: 8000,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}
