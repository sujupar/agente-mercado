import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import { useDashboardContext } from '../context/DashboardContext';

export function useBrokerAccount(environment) {
  // Si se pasa environment explícito, usarlo (BrokerPage lo usa para mostrar DEMO+LIVE).
  // Si no, usar el activeEnvironment del context.
  const { activeEnvironment } = useDashboardContext();
  const env = environment || activeEnvironment;
  return useQuery({
    queryKey: ['brokerAccount', env],
    queryFn: async () => {
      const response = await api.getBrokerAccount(env);
      return response.data;
    },
    refetchInterval: 10000,
    staleTime: 8000,
    retry: 1,
  });
}

export function useBrokerPositions(environment) {
  const { activeEnvironment } = useDashboardContext();
  const env = environment || activeEnvironment;
  return useQuery({
    queryKey: ['brokerPositions', env],
    queryFn: async () => {
      const response = await api.getBrokerPositions(env);
      return response.data;
    },
    refetchInterval: 10000,
    staleTime: 8000,
    retry: 1,
  });
}

export function useBrokerSync() {
  return useQuery({
    queryKey: ['brokerSync'],
    queryFn: async () => {
      const response = await api.getBrokerSyncStatus();
      return response.data;
    },
    refetchInterval: 30000,
    staleTime: 25000,
    retry: 1,
  });
}

export function useForceBrokerSync() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const response = await api.forceBrokerSync();
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brokerSync'] });
      queryClient.invalidateQueries({ queryKey: ['brokerPositions'] });
      queryClient.invalidateQueries({ queryKey: ['brokerAccount'] });
    },
  });
}
