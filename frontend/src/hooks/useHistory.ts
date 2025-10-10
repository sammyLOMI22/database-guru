import { useQuery } from '@tanstack/react-query';
import { queryAPI } from '../services/api';

export function useHistory(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['history', limit, offset],
    queryFn: () => queryAPI.getHistory(limit, offset),
    staleTime: 30 * 1000, // 30 seconds
  });
}
