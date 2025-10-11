import { useState } from 'react';
import { multiQueryAPI } from '../services/api';
import type { MultiDatabaseQueryRequest, MultiDatabaseQueryResponse, ChatSession } from '../types/api';

export function useMultiQuery() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MultiDatabaseQueryResponse | null>(null);

  const executeQuery = async (
    question: string,
    currentSession: ChatSession | null,
    options: Partial<MultiDatabaseQueryRequest> = {}
  ) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const request: MultiDatabaseQueryRequest = {
        question,
        chat_session_id: currentSession?.id,
        allow_write: false,
        use_cache: true,
        ...options,
      };

      const response = await multiQueryAPI.processQuery(request);
      setResult(response);
      return response;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to execute query';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setLoading(false);
    setError(null);
    setResult(null);
  };

  return {
    loading,
    error,
    result,
    executeQuery,
    reset,
  };
}
