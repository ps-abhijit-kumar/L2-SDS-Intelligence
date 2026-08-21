import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: () => api.getStats(),
    refetchInterval: 15000,
  });
}
