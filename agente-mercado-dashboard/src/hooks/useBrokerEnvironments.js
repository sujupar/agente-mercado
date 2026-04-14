/**
 * Hook dual-mode: retorna estado de DEMO y LIVE en paralelo.
 * Reemplaza al antiguo useBrokerEnvironment (singular).
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';

export function useBrokerEnvironments() {
  return useQuery({
    queryKey: ['brokerEnvironments'],
    queryFn: async () => {
      const response = await api.getBrokerEnvironment();
      return response.data; // { environments: [{DEMO}, {LIVE}] }
    },
    refetchInterval: 30000,
    staleTime: 25000,
    retry: 1,
  });
}
