/**
 * Hooks para el selector DEMO/LIVE del broker.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/endpoints';

export function useBrokerEnvironment() {
  return useQuery({
    queryKey: ['brokerEnvironment'],
    queryFn: async () => {
      const response = await api.getBrokerEnvironment();
      return response.data;
    },
    refetchInterval: 30000,
    staleTime: 25000,
    retry: 1,
  });
}

export function useSetBrokerEnvironment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ environment, confirm_live }) => {
      const response = await api.setBrokerEnvironment({ environment, confirm_live });
      return response.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['brokerEnvironment'] });
      qc.invalidateQueries({ queryKey: ['brokerAccount'] });
      qc.invalidateQueries({ queryKey: ['brokerPositions'] });
      qc.invalidateQueries({ queryKey: ['brokerSync'] });
      qc.invalidateQueries({ queryKey: ['agentStatus'] });
      qc.invalidateQueries({ queryKey: ['strategies'] });
    },
  });
}
