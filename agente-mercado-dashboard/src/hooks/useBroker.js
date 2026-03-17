import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/endpoints';

export function useBrokerAccount() {
  return useQuery({
    queryKey: ['brokerAccount'],
    queryFn: async () => {
      const response = await api.getBrokerAccount();
      return response.data;
    },
    refetchInterval: 10000,
    staleTime: 8000,
    retry: 1,
  });
}

export function useBrokerPositions() {
  return useQuery({
    queryKey: ['brokerPositions'],
    queryFn: async () => {
      const response = await api.getBrokerPositions();
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
