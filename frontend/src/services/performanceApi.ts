// Phase 22: Performance Guru API Service
import api from './api';
import type {
  PerformanceAnalysisRequest,
  PerformanceAnalysisResponse,
  ExplainOnlyResponse,
} from '../types/performance';

export const performanceAPI = {
  async analyzeQuery(request: PerformanceAnalysisRequest): Promise<PerformanceAnalysisResponse> {
    const { data } = await api.post<PerformanceAnalysisResponse>(
      '/api/performance/analyze',
      request,
      { timeout: 60_000 },
    );
    return data;
  },

  async explainOnly(
    connectionId: number,
    sql: string,
    runAnalyze = false,
  ): Promise<ExplainOnlyResponse> {
    const { data } = await api.post<ExplainOnlyResponse>(
      '/api/performance/explain-only',
      { connection_id: connectionId, sql, run_analyze: runAnalyze },
    );
    return data;
  },
};
