import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { graphAPI } from '../services/graphApi';
import type {
  GraphIntrospectOptions,
  GraphSchemaResponse,
  GraphSchemaSummaryResponse,
} from '../services/graphApi';

const SCHEMA_KEY = (connectionId: number | null) => ['graphSchema', connectionId];
const SUMMARY_KEY = (connectionId: number | null) => ['graphSchemaSummary', connectionId];

/**
 * Phase 25.2 — fetch the cached graph schema. Hook returns `null` data
 * when no connection is selected so callers can render an empty state
 * without juggling enabled flags themselves.
 */
export function useGraphSchema(connectionId: number | null) {
  return useQuery<GraphSchemaResponse>({
    queryKey: SCHEMA_KEY(connectionId),
    queryFn: () => graphAPI.getSchema(connectionId as number),
    enabled: connectionId !== null && connectionId !== undefined,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Force a fresh introspection. Invalidates the cached schema + summary
 * so dependent panels (Overview, Schema Explorer) re-render with fresh data.
 */
export function useIntrospectGraph(connectionId: number | null) {
  const queryClient = useQueryClient();
  return useMutation<GraphSchemaResponse, Error, GraphIntrospectOptions | void>({
    mutationFn: (opts) =>
      graphAPI.introspect(connectionId as number, opts || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SCHEMA_KEY(connectionId) });
      queryClient.invalidateQueries({ queryKey: SUMMARY_KEY(connectionId) });
    },
  });
}

/**
 * LLM-generated 2-3 sentence overview blurb. Lazy: only fetched when the
 * caller explicitly mutates (via the returned `generate` callable) so we
 * don't burn LLM tokens on every Graph tab open.
 */
export function useGraphSchemaSummary(connectionId: number | null) {
  return useMutation<GraphSchemaSummaryResponse, Error, void>({
    mutationFn: () => graphAPI.generateSchemaSummary(connectionId as number),
  });
}
