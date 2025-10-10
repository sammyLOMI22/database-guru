import { useQuery } from '@tanstack/react-query';
import { modelsAPI } from '../services/api';

export function useModels() {
  return useQuery({
    queryKey: ['models'],
    queryFn: () => modelsAPI.listModels(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useModelDetails() {
  return useQuery({
    queryKey: ['models', 'details'],
    queryFn: () => modelsAPI.getModelDetails(),
    staleTime: 5 * 60 * 1000,
  });
}
