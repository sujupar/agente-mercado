import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';

export function useStrategies({ fromDate, toDate } = {}) {
  return useQuery({
    queryKey: ['strategies', fromDate, toDate],
    queryFn: async () => {
      const params = {};
      if (fromDate) params.from_date = fromDate;
      if (toDate) params.to_date = toDate;
      const response = await api.getStrategies(params);
      return response.data;
    },
    refetchInterval: 15000,
    staleTime: 12000,
    retry: 2,
  });
}

export function useStrategyTrades(strategyId, { fromDate, toDate } = {}) {
  return useQuery({
    queryKey: ['strategyTrades', strategyId, fromDate, toDate],
    queryFn: async () => {
      const params = { limit: 50 };
      if (fromDate) params.from_date = fromDate;
      if (toDate) params.to_date = toDate;
      const response = await api.getStrategyTrades(strategyId, params);
      return response.data;
    },
    enabled: !!strategyId,
    refetchInterval: 15000,
    staleTime: 12000,
  });
}

export function useStrategyBitacora(strategyId) {
  return useQuery({
    queryKey: ['strategyBitacora', strategyId],
    queryFn: async () => {
      const response = await api.getStrategyBitacora(strategyId, 30);
      return response.data;
    },
    enabled: !!strategyId,
    refetchInterval: 30000,
    staleTime: 25000,
  });
}

export function useStrategyReports(strategyId) {
  return useQuery({
    queryKey: ['strategyReports', strategyId],
    queryFn: async () => {
      const response = await api.getStrategyReports(strategyId, 10);
      return response.data;
    },
    enabled: !!strategyId,
    refetchInterval: 60000,
    staleTime: 55000,
  });
}

export function useStrategyPerformance(strategyId) {
  return useQuery({
    queryKey: ['strategyPerformance', strategyId],
    queryFn: async () => {
      const response = await api.getStrategyPerformance(strategyId);
      return response.data;
    },
    enabled: !!strategyId,
    refetchInterval: 30000,
    staleTime: 25000,
  });
}

export function useImprovementCycles(strategyId) {
  return useQuery({
    queryKey: ['improvementCycles', strategyId],
    queryFn: async () => {
      const response = await api.getImprovementCycles(strategyId, 10);
      return response.data;
    },
    enabled: !!strategyId,
    refetchInterval: 30000,
    staleTime: 25000,
  });
}

export function useImprovementRules(strategyId) {
  return useQuery({
    queryKey: ['improvementRules', strategyId],
    queryFn: async () => {
      const response = await api.getImprovementRules(strategyId);
      return response.data;
    },
    enabled: !!strategyId,
    refetchInterval: 30000,
    staleTime: 25000,
  });
}
