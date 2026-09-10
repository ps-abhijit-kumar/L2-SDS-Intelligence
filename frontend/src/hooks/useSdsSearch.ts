/**
 * Interactive Single SDS Search Hook
 * ==================================
 * Architecture Role:
 *   Wraps the POST /api/sds/search endpoint using React Query mutation.
 *   Dispatches single chemical search requests to the backend LangGraph agent
 *   and automatically invalidates history, stats, and trace caches upon completion.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { SDSSearchRequest, SDSSearchResponse } from '../types/sds';

export function useSdsSearch() {
  const queryClient = useQueryClient();

  return useMutation<SDSSearchResponse, Error, SDSSearchRequest>({
    mutationFn: (payload: SDSSearchRequest) => api.searchSDS(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['history'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      queryClient.invalidateQueries({ queryKey: ['reviewQueue'] });
      queryClient.invalidateQueries({ queryKey: ['latestTrace'] });
    },
  });
}
