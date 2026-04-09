/**
 * Hook: useRegime
 *
 * Trae el régimen macro actual (clasificación LLM).
 * Refresca cada 60 segundos (el backend actualiza cada 60 min,
 * pero el polling corto permite ver cambios cuando ocurren).
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';

export function useRegime() {
  return useQuery({
    queryKey: ['macroRegime'],
    queryFn: async () => {
      const response = await api.getCurrentRegime();
      return response.data;
    },
    refetchInterval: 60000,      // Cada 60s
    refetchOnWindowFocus: true,
    staleTime: 50000,
    retry: 2,
  });
}
