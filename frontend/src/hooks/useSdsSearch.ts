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
