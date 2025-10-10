import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { schemaAPI } from '../services/api';

export function useSchema() {
  return useQuery({
    queryKey: ['schema'],
    queryFn: () => schemaAPI.getSchema(false),
    staleTime: 60 * 60 * 1000, // 1 hour
  });
}

export function useRefreshSchema() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => schemaAPI.refreshSchema(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schema'] });
    },
  });
}

export function useTables() {
  return useQuery({
    queryKey: ['tables'],
    queryFn: () => schemaAPI.getTables(),
    staleTime: 60 * 60 * 1000,
  });
}
