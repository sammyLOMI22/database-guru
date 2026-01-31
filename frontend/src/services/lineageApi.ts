/**
 * Lineage API Service - Phase 11 + Phase 12.1 + Phase 12.2 + Phase 12.3 + Phase 12.4
 *
 * API client for data lineage endpoints.
 * Follows cacheApi.ts patterns.
 *
 * Phase 12.1 adds LLM narrative support via explain parameter.
 * Phase 12.2 adds Impact Advisor with migration plans and SQL patches.
 * Phase 12.3 adds Schema Health Analyzer for database design quality.
 * Phase 12.4 adds Pattern Intelligence for bottleneck analysis and anti-patterns.
 */
import axios from 'axios';
import type {
  LineageGraphResponse,
  ImpactAnalysisResponse,
  LineageStatsResponse,
  TableQueriesResponse,
  HeatmapDataResponse,
  ImpactAdviceRequest,
  ImpactAdviceResponse,
  ChangeType,
  SchemaHealthReport,
  PatternIntelligenceReport,
  BottleneckAnalysis,
  LineageAnswer,
} from '../types/lineage';

const api = axios.create({
  baseURL: (import.meta as any).env?.VITE_API_URL || '',
  timeout: 15000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[Lineage API] Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const lineageAPI = {
  /**
   * Parse SQL and return lineage graph.
   *
   * @param sql - SQL query to parse
   * @param connectionId - Optional connection ID for context
   * @param explain - If true, generate LLM narrative explanation (Phase 12.1)
   * @param question - Original natural language question for narrative context
   */
  async parseSql(
    sql: string,
    connectionId?: number,
    explain: boolean = false,
    question?: string,
  ): Promise<LineageGraphResponse> {
    const params: Record<string, any> = {};
    if (explain) {
      params.explain = true;
    }

    const { data } = await api.post<LineageGraphResponse>(
      '/api/lineage/parse',
      {
        sql,
        connection_id: connectionId,
        question,
      },
      { params }
    );
    return data;
  },

  /**
   * Get lineage for a query from history.
   */
  async getQueryLineage(queryId: number): Promise<LineageGraphResponse> {
    const { data } = await api.get<LineageGraphResponse>(`/api/lineage/query/${queryId}`);
    return data;
  },

  /**
   * Analyze impact of a schema change.
   */
  async analyzeImpact(tableName: string, columnName?: string): Promise<ImpactAnalysisResponse> {
    const { data } = await api.post<ImpactAnalysisResponse>('/api/lineage/impact', {
      table_name: tableName,
      column_name: columnName,
    });
    return data;
  },

  /**
   * Get queries referencing a table.
   */
  async getTableQueries(tableName: string): Promise<TableQueriesResponse> {
    const { data } = await api.get<TableQueriesResponse>(`/api/lineage/table/${tableName}/queries`);
    return data;
  },

  /**
   * Get lineage statistics.
   */
  async getStats(): Promise<LineageStatsResponse> {
    const { data } = await api.get<LineageStatsResponse>('/api/lineage/stats');
    return data;
  },

  /**
   * Get query pattern heatmap data for a connection.
   * Pass connectionId=0 for all connections.
   */
  async getHeatmapData(connectionId: number, timeRange?: number): Promise<HeatmapDataResponse> {
    const params: Record<string, number> = {};
    if (timeRange != null) {
      params.time_range = timeRange;
    }
    const { data } = await api.get<HeatmapDataResponse>(
      `/api/lineage/patterns/${connectionId}`,
      { params }
    );
    return data;
  },

  /**
   * Get LLM-enhanced impact analysis with recommendations.
   * Phase 12.2: Returns risk explanation, migration plan, and SQL patches.
   *
   * @param changeType - Type of change (rename_column, drop_table, etc.)
   * @param tableName - Table being modified
   * @param columnName - Column being modified (for column-level changes)
   * @param newValue - New name/type (for renames/type changes)
   * @param includePatches - Whether to generate SQL patches
   */
  async getImpactAdvice(
    changeType: ChangeType,
    tableName: string,
    columnName?: string,
    newValue?: string,
    includePatches: boolean = true,
  ): Promise<ImpactAdviceResponse> {
    const request: ImpactAdviceRequest = {
      change_type: changeType,
      table_name: tableName,
      column_name: columnName,
      new_value: newValue,
      include_patches: includePatches,
    };
    const { data } = await api.post<ImpactAdviceResponse>(
      '/api/lineage/impact/advise',
      request,
      { timeout: 30000 }  // Longer timeout for LLM processing
    );
    return data;
  },

  /**
   * Get schema health analysis for a connection.
   * Phase 12.3: Returns comprehensive health report with grade, issues, and suggestions.
   *
   * @param connectionId - Connection to analyze
   * @param includePatterns - Include query pattern analysis for index suggestions
   */
  async getSchemaHealth(
    connectionId: number,
    includePatterns: boolean = true,
  ): Promise<SchemaHealthReport> {
    const params: Record<string, boolean> = {};
    if (!includePatterns) {
      params.include_patterns = false;
    }
    const { data } = await api.get<SchemaHealthReport>(
      `/api/lineage/schema/health/${connectionId}`,
      { params, timeout: 45000 }  // Longer timeout for schema analysis
    );
    return data;
  },

  /**
   * Get pattern intelligence analysis for a connection.
   * Phase 12.4: Returns bottleneck analysis, anti-patterns, and optimization suggestions.
   *
   * @param connectionId - Connection to analyze (0 for all)
   * @param timeRange - Time range in days (default: 30)
   * @param includeTrends - Include usage trend analysis
   */
  async analyzePatterns(
    connectionId: number,
    timeRange: number = 30,
    includeTrends: boolean = true,
  ): Promise<PatternIntelligenceReport> {
    const params: Record<string, any> = {
      time_range: timeRange,
      include_trends: includeTrends,
    };
    const { data } = await api.get<PatternIntelligenceReport>(
      `/api/lineage/patterns/${connectionId}/analyze`,
      { params, timeout: 30000 }
    );
    return data;
  },

  /**
   * Get detailed bottleneck analysis for a specific table.
   * Phase 12.4: Returns root cause analysis and optimization suggestions.
   *
   * @param connectionId - Connection ID
   * @param tableName - Table to analyze
   */
  async analyzeBottleneck(
    connectionId: number,
    tableName: string,
  ): Promise<BottleneckAnalysis> {
    const { data } = await api.get<BottleneckAnalysis>(
      `/api/lineage/patterns/${connectionId}/bottlenecks/${encodeURIComponent(tableName)}`,
      { timeout: 20000 }
    );
    return data;
  },

  /**
   * Ask a natural language question about lineage, schema, or patterns.
   * Phase 12.5: Conversational Lineage with multi-turn support.
   *
   * @param question - Natural language question
   * @param connectionId - Connection to query
   * @param sessionId - Optional session ID for multi-turn conversations
   */
  async askLineageQuestion(
    question: string,
    connectionId: number,
    sessionId?: string,
  ): Promise<LineageAnswer> {
    const { data } = await api.post<LineageAnswer>(
      '/api/lineage/ask',
      {
        question,
        connection_id: connectionId,
        session_id: sessionId,
      },
      { timeout: 20000 }
    );
    return data;
  },
};

export default lineageAPI;
