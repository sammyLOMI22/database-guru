import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryAPI } from '../services/api';
import type { QueryRequest, QueryResponse } from '../types/api';

export function useQuerySubmit() {
  const queryClient = useQueryClient();

  return useMutation<QueryResponse, Error, QueryRequest>({
    mutationFn: (request) => queryAPI.processQuery(request),
    onSuccess: () => {
      // Invalidate history to show new query
      queryClient.invalidateQueries({ queryKey: ['history'] });
    },
  });
}
