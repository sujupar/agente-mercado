import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';

export function useAllMarketStates() {
  return useQuery({
    queryKey: ['marketStates'],
    queryFn: async () => {
      const response = await api.getAllMarketStates();
      return response.data;
    },
    refetchInterval: 60000,
    staleTime: 55000,
    retry: 1,
  });
}

export function useMarketState(instrument) {
  return useQuery({
    queryKey: ['marketState', instrument],
    queryFn: async () => {
      const response = await api.getMarketState(instrument);
      return response.data;
    },
    enabled: !!instrument,
    refetchInterval: 60000,
    staleTime: 55000,
    retry: 1,
  });
}
