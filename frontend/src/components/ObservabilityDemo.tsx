import React from 'react';
import QueryResults from './QueryResults';
import { QueryResponse } from '../types/api';

/**
 * Demo component to showcase all observability features
 * This demonstrates what the UI looks like with full observability data
 * including confidence scoring, agent traces, query planning, verification warnings,
 * conversational memory (Phase 1), and streaming results (Phase 2)
 */
export const ObservabilityDemo: React.FC = () => {
  // Mock data showing a query that was auto-corrected with full observability
  const mockQueryResponse: QueryResponse = {
    query_id: 123,
    question: "Show all users who registered in 2024",
    sql: "SELECT * FROM user WHERE created_at >= '2024-01-01'",
    is_valid: true,
    is_read_only: true,
    warnings: ["✨ Query auto-corrected after 1 error(s)"],
    results: [
      { id: 1, name: "Alice Johnson", email: "alice@example.com", created_at: "2024-03-15" },
      { id: 2, name: "Bob Smith", email: "bob@example.com", created_at: "2024-05-20" },
      { id: 3, name: "Carol White", email: "carol@example.com", created_at: "2024-08-10" },
    ],
    row_count: 3,
    execution_time_ms: 45.2,
    cached: false,
    timestamp: new Date().toISOString(),

    // Observability data
    self_corrected: true,
    total_attempts: 2,
    used_planning: false,
    verification_warnings: [
      "⚠️ Result verification: Only 3 rows returned - verify this matches your expectations"
    ],

    agent_trace: {
      steps: [
        {
          timestamp: new Date().toISOString(),
          elapsed_ms: 0.0,
          type: "analysis",
          message: "Analyzing question: Show all users who registered in 2024",
          metadata: { database_type: "postgresql", model: "llama3" },
          icon: "🔍"
        },
        {
          timestamp: new Date().toISOString(),
          elapsed_ms: 50.0,
          type: "generation",
          message: "Generated SQL: SELECT * FROM users WHERE created_at >= '2024-01-01'",
          metadata: { sql: "SELECT * FROM users WHERE created_at >= '2024-01-01'" },
          icon: "✨"
        },
        {
          timestamp: new Date().toISOString(),
          elapsed_ms: 75.0,
          type: "execution",
          message: "Executing SQL query",
          metadata: {},
          icon: "⚡"
        },
        {
          timestamp: new Date().toISOString(),
          elapsed_ms: 80.0,
          type: "error",
          message: "Attempt 1 failed: table users does not exist",
          metadata: {},
          icon: "❌"
        },
        {
          timestamp: new Date().toISOString(),
          elapsed_ms: 85.0,
          type: "fix_attempt",
          message: "Attempting to fix error: table users does not exist",
          metadata: {},
          icon: "🔧"
        },
        {
          timestamp: new Date().toISOString(),
          elapsed_ms: 90.0,
          type: "quick_fix",
          message: "Applied quick fix: Changed 'users' to 'user'",
          metadata: { confidence: 0.95, method: "table_name_correction" },
          icon: "⚡"
        },
        {
          timestamp: new Date().toISOString(),
          elapsed_ms: 120.0,
          type: "execution",
          message: "Executing SQL query",
          metadata: {},
          icon: "⚡"
        },
        {
          timestamp: new Date().toISOString(),
          elapsed_ms: 165.0,
          type: "success",
          message: "Query executed successfully (rows: 3, time: 45.2ms)",
          metadata: { row_count: 3, execution_time_ms: 45.2 },
          icon: "✅"
        },
        {
          timestamp: new Date().toISOString(),
          elapsed_ms: 170.0,
          type: "verification",
          message: "Verifying query results for accuracy",
          metadata: {},
          icon: "🔍"
        },
        {
          timestamp: new Date().toISOString(),
          elapsed_ms: 185.0,
          type: "verification_warning",
          message: "Suspicious results detected: Low row count",
          metadata: { confidence: 0.6, issue: "low_row_count" },
          icon: "⚠️"
        }
      ],
      total_elapsed_ms: 185.0,
      start_time: new Date().toISOString()
    },

    attempts: [
      {
        attempt_number: 1,
        sql: "SELECT * FROM users WHERE created_at >= '2024-01-01'",
        success: false,
        error: "relation \"users\" does not exist",
        error_type: "table_not_found",
        execution_time_ms: 5.2,
        row_count: null,
        fix_method: null,
        confidence_prediction: null  // First attempt never has confidence
      },
      {
        attempt_number: 2,
        sql: "SELECT * FROM user WHERE created_at >= '2024-01-01'",
        success: true,
        error: null,
        error_type: null,
        execution_time_ms: 45.2,
        row_count: 3,
        fix_method: "quick_fix",
        confidence_prediction: {
          overall: 0.925,
          level: 'HIGH' as const,
          factors: {
            error_type: 0.255,
            schema_match: 0.250,
            historical_success: 0.170,
            correction_complexity: 0.150,
            similarity: 0.100
          },
          reasoning: "This correction has high confidence (92.5%). Table Not Found errors are relatively easy to fix. The correction references valid schema objects. The correction is relatively simple.",
          recommendation: "EXECUTE - High confidence, likely to succeed"
        }
      }
    ]
  };

  // Mock data with query planning
  const mockWithPlanningResponse: QueryResponse = {
    ...mockQueryResponse,
    query_id: 456,
    question: "Show total sales by category for each month in 2024",
    sql: "SELECT category, DATE_TRUNC('month', sale_date) as month, SUM(amount) as total FROM sales WHERE sale_date >= '2024-01-01' GROUP BY category, month ORDER BY month DESC",
    self_corrected: false,
    total_attempts: 1,
    used_planning: true,
    verification_warnings: [],

    query_plan: {
      complexity: "complex",
      intent: "Aggregate sales data by category and month for year 2024",
      confidence: 0.92,
      reasoning: "Query involves aggregation, grouping, and date manipulation - using query planning for better structure",
      tables: [
        {
          name: "sales",
          alias: "s",
          purpose: "Main table containing sales transactions"
        }
      ],
      joins: [],
      filters: [
        {
          column: "sale_date",
          operator: ">=",
          value: "'2024-01-01'",
          purpose: "Limit to sales in 2024"
        }
      ],
      aggregations: [
        {
          function: "SUM",
          column: "amount",
          alias: "total",
          purpose: "Calculate total sales amount"
        }
      ],
      grouping: {
        columns: ["category", "month"],
        purpose: "Group by category and month to get totals for each combination"
      },
      ordering: {
        column: "month",
        direction: "DESC",
        purpose: "Show most recent months first"
      },
      limit: null,
      joins_count: 0,
      filters_count: 1,
      aggregations_count: 1
    },

    attempts: [
      {
        attempt_number: 1,
        sql: "SELECT category, DATE_TRUNC('month', sale_date) as month, SUM(amount) as total FROM sales WHERE sale_date >= '2024-01-01' GROUP BY category, month ORDER BY month DESC",
        success: true,
        error: null,
        error_type: null,
        execution_time_ms: 125.5,
        row_count: 24,
        fix_method: null
      }
    ]
  };

  return (
    <div className="min-h-screen bg-gray-100 p-4 md:p-8 overflow-x-hidden">
      <div className="max-w-7xl mx-auto space-y-4 md:space-y-6 lg:space-y-8">
        <div className="bg-white rounded-lg shadow p-4 md:p-6 overflow-hidden">
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
            Database Guru - Complete Feature Demo
          </h1>
          <p className="text-sm md:text-base text-gray-600 mb-3">
            This page demonstrates all observability and UX enhancement features with mock data.
            Scroll down to see different scenarios including the NEW Phase 1 & 2 features!
          </p>
          <div className="flex gap-1.5 md:gap-2 flex-wrap">
            <span className="px-2 md:px-3 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
              ✨ Phase 1: Conversational Memory
            </span>
            <span className="px-2 md:px-3 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
              🌊 Phase 2: Streaming Results
            </span>
            <span className="px-2 md:px-3 py-1 bg-orange-100 text-orange-700 text-xs font-medium rounded-full">
              ⚡ Parallel Execution
            </span>
            <span className="px-2 md:px-3 py-1 bg-teal-100 text-teal-700 text-xs font-medium rounded-full">
              🗺️ Mapping Management
            </span>
            <span className="px-2 md:px-3 py-1 bg-amber-100 text-amber-700 text-xs font-medium rounded-full">
              🔧 Tool-Using Agent
            </span>
            <span className="px-2 md:px-3 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
              📊 Phase 4.1: Chart Viz
            </span>
            <span className="px-2 md:px-3 py-1 bg-purple-100 text-purple-700 text-xs font-medium rounded-full">
              🗂️ Phase 4.2: Index Recommendations
            </span>
          </div>
        </div>

        {/* Scenario 1: Auto-corrected query with verification warning */}
        <div className="bg-white rounded-lg shadow p-4 md:p-6 overflow-hidden">
          <h2 className="text-lg md:text-xl font-semibold text-gray-900 mb-4">
            Scenario 1: Auto-Corrected Query with Confidence Scoring
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Shows a query that failed initially due to wrong table name, was auto-corrected using
            quick fix with <strong>92.5% HIGH confidence</strong>, and has a verification warning about low row count.
            Click on the correction history to see the confidence badge and factor breakdown!
          </p>
          <QueryResults
            queryId={mockQueryResponse.query_id}
            sql={mockQueryResponse.sql}
            results={mockQueryResponse.results}
            rowCount={mockQueryResponse.row_count}
            executionTime={mockQueryResponse.execution_time_ms}
            isValid={mockQueryResponse.is_valid}
            warnings={mockQueryResponse.warnings}
            agentTrace={mockQueryResponse.agent_trace}
            queryPlan={mockQueryResponse.query_plan}
            attempts={mockQueryResponse.attempts}
            selfCorrected={mockQueryResponse.self_corrected}
            totalAttempts={mockQueryResponse.total_attempts}
            verificationWarnings={mockQueryResponse.verification_warnings}
            usedPlanning={mockQueryResponse.used_planning}
          />
        </div>

        {/* Scenario 2: Complex query with planning */}
        <div className="bg-white rounded-lg shadow p-4 md:p-6 overflow-hidden">
          <h2 className="text-lg md:text-xl font-semibold text-gray-900 mb-4">
            Scenario 2: Complex Query with Planning
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Shows a complex query that used query planning for better structure.
            Includes aggregations, grouping, and ordering.
          </p>
          <QueryResults
            queryId={mockWithPlanningResponse.query_id}
            sql={mockWithPlanningResponse.sql}
            results={[
              { category: "Electronics", month: "2024-10-01", total: 15420.50 },
              { category: "Books", month: "2024-10-01", total: 3250.75 },
              { category: "Electronics", month: "2024-09-01", total: 18900.25 },
              { category: "Books", month: "2024-09-01", total: 2890.00 },
            ]}
            rowCount={24}
            executionTime={125.5}
            isValid={true}
            warnings={[]}
            agentTrace={mockQueryResponse.agent_trace}
            queryPlan={mockWithPlanningResponse.query_plan}
            attempts={mockWithPlanningResponse.attempts}
            selfCorrected={false}
            totalAttempts={1}
            verificationWarnings={[]}
            usedPlanning={true}
          />
        </div>

        {/* Scenario 3: Conversational Memory */}
        <div className="bg-white rounded-lg shadow p-4 md:p-6 overflow-hidden">
          <h2 className="text-lg md:text-xl font-semibold text-gray-900 mb-4">
            Scenario 3: Conversational Memory (Phase 1) ✨ NEW!
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Shows the conversation context panel that enables natural multi-turn dialogue.
            The system remembers your previous queries and understands follow-up questions like
            "Filter that", "Sort it", or "Show more details".
          </p>
          <div className="border-2 border-blue-200 rounded-lg p-4 bg-blue-50">
            <div className="mb-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Example Conversation Flow:</h3>
              <div className="space-y-2 text-sm">
                <div className="bg-white p-2 rounded">
                  <strong>User:</strong> "Show me all products"
                  <br />
                  <strong>System:</strong> <code className="text-xs bg-gray-100 px-1">SELECT * FROM products</code>
                </div>
                <div className="bg-white p-2 rounded">
                  <strong>User:</strong> "Filter by electronics" ← Contextual!
                  <br />
                  <strong>System:</strong> <code className="text-xs bg-gray-100 px-1">SELECT * FROM products WHERE category = 'electronics'</code>
                  <br />
                  <span className="text-xs text-blue-600">💡 Used conversation context!</span>
                </div>
                <div className="bg-white p-2 rounded">
                  <strong>User:</strong> "Sort by price" ← Also contextual!
                  <br />
                  <strong>System:</strong> <code className="text-xs bg-gray-100 px-1">SELECT * FROM products WHERE category = 'electronics' ORDER BY price</code>
                  <br />
                  <span className="text-xs text-blue-600">💡 Used context from both previous queries!</span>
                </div>
              </div>
            </div>

            <p className="text-xs text-gray-600 mb-3">
              <strong>Note:</strong> In a real session, the ConversationContextPanel would show your query history.
              Create a chat session and ask follow-up questions to see it in action!
            </p>

            <div className="bg-gray-100 p-3 rounded">
              <p className="text-xs text-gray-500 italic">
                💡 Tip: The context panel appears automatically when you have a chat session active.
                It shows the last 3 queries by default and lets you clear context anytime.
              </p>
            </div>
          </div>
        </div>

        {/* Scenario 4: Streaming Results */}
        <div className="bg-white rounded-lg shadow p-4 md:p-6 overflow-hidden">
          <h2 className="text-lg md:text-xl font-semibold text-gray-900 mb-4">
            Scenario 4: Streaming Results (Phase 2) 🌊 NEW!
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Shows progressive result streaming with Server-Sent Events.
            Results appear in real-time as they're fetched (100 rows per batch by default).
            Watch the progress bar and batch counter update live!
          </p>
          <div className="border-2 border-green-200 rounded-lg p-3 md:p-4 bg-green-50 overflow-x-auto">
            <div className="mb-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Performance Comparison:</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm min-w-fit">
                <div className="bg-white p-3 rounded">
                  <div className="font-semibold text-red-600 mb-1">❌ Before Streaming:</div>
                  <div className="text-xs space-y-1">
                    <div>• Wait 5+ seconds</div>
                    <div>• No feedback</div>
                    <div>• All 1000 rows at once</div>
                    <div>• Blocking UI</div>
                  </div>
                </div>
                <div className="bg-white p-3 rounded">
                  <div className="font-semibold text-green-600 mb-1">✅ With Streaming:</div>
                  <div className="text-xs space-y-1">
                    <div>• First rows in 150ms!</div>
                    <div>• Real-time progress</div>
                    <div>• Batches of 100 rows</div>
                    <div>• Responsive UI</div>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white p-3 rounded mb-3">
              <h4 className="text-xs font-semibold text-gray-700 mb-2">Event Flow:</h4>
              <div className="text-xs space-y-1 font-mono">
                <div>→ <span className="text-blue-600">status</span>: "Generating SQL..."</div>
                <div>→ <span className="text-purple-600">sql_generated</span>: SQL query ready</div>
                <div>→ <span className="text-yellow-600">metadata</span>: Column names</div>
                <div>→ <span className="text-green-600">data</span>: Batch 1 (100 rows)</div>
                <div>→ <span className="text-green-600">data</span>: Batch 2 (200 rows total)</div>
                <div>→ <span className="text-green-600">data</span>: Batch 3 (300 rows total)...</div>
                <div>→ <span className="text-indigo-600">complete</span>: 1000 rows in 1.5s</div>
              </div>
            </div>

            <div className="bg-gray-100 p-3 rounded">
              <p className="text-xs text-gray-500 italic">
                💡 Tip: To see streaming in action, use the <code className="bg-white px-1">/api/query/stream</code> endpoint
                or enable streaming mode in your query interface. Perfect for large datasets!
              </p>
            </div>
          </div>
        </div>

        {/* Scenario 5: Parallel Execution */}
        <div className="bg-white rounded-lg shadow p-4 md:p-6 overflow-hidden">
          <h2 className="text-lg md:text-xl font-semibold text-gray-900 mb-4">
            Scenario 5: Parallel Execution (Production-Ready) ⚡ NEW!
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Shows queries executing in parallel for massive performance improvements.
            Features dual timeout protection, comprehensive metrics, and intelligent throttling.
          </p>
          <div className="border-2 border-orange-200 rounded-lg p-3 md:p-4 bg-orange-50 overflow-x-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4 min-w-fit">
              {/* Multi-Database Parallel Execution */}
              <div className="bg-white rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                  <span>⚡</span>
                  Multi-Database Parallel Execution
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Sequential:</span>
                    <span className="font-mono">3.0s</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Parallel:</span>
                    <span className="font-mono text-green-600 font-bold">1.0s</span>
                  </div>
                  <div className="pt-2 border-t border-gray-200">
                    <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full">
                      3.0x faster ⚡
                    </span>
                  </div>
                </div>
              </div>

              {/* Parallel Correction Strategies */}
              <div className="bg-white rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                  <span>🏆</span>
                  Parallel Correction Strategies
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Sequential:</span>
                    <span className="font-mono">1.6s</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Parallel:</span>
                    <span className="font-mono text-green-600 font-bold">1.0s</span>
                  </div>
                  <div className="pt-2 border-t border-gray-200">
                    <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs font-bold rounded-full">
                      Quick Fix wins! ⚡
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Key Features */}
            <div className="bg-white rounded-lg p-3 md:p-4 mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Key Features:</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>3.0x speedup for multi-database queries</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>1.6x speedup for error corrections</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Dual timeout protection (10s + 35s)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Intelligent throttling (max 10 concurrent)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Comprehensive metrics & observability</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Graceful degradation & fault isolation</span>
                </div>
              </div>
            </div>

            {/* Live Demo */}
            <QueryResults
              queryId={789}
              sql="SELECT category, SUM(sales) FROM sales_us UNION ALL SELECT category, SUM(sales) FROM sales_eu"
              results={[
                { category: "Electronics", total_sales: 45000 },
                { category: "Books", total_sales: 12000 },
              ]}
              rowCount={2}
              executionTime={1050}
              isValid={true}
              warnings={["✨ Query executed across 2 databases in parallel"]}
              selfCorrected={true}
              totalAttempts={2}
              attempts={[
                {
                  attempt_number: 1,
                  sql: "SELECT category, SUM(sales) FROM sales UNION ALL...",
                  success: false,
                  error: "Table 'sales' does not exist",
                  error_type: "table_not_found",
                  execution_time_ms: null,
                  row_count: null,
                  fix_method: null,
                },
                {
                  attempt_number: 2,
                  sql: "SELECT category, SUM(sales) FROM sales_us UNION ALL SELECT category, SUM(sales) FROM sales_eu",
                  success: true,
                  error: null,
                  error_type: null,
                  execution_time_ms: 1050,
                  row_count: 2,
                  fix_method: "quick_fix",
                  confidence_prediction: {
                    overall: 0.95,
                    level: 'HIGH' as const,
                    factors: {
                      error_type: 0.27,
                      schema_match: 0.25,
                      historical_success: 0.19,
                      correction_complexity: 0.14,
                      similarity: 0.10,
                    },
                    reasoning: "Table name correction with high schema match",
                    recommendation: "EXECUTE - Very high confidence",
                  },
                  metrics: {
                    strategies_attempted: 3,
                    strategies_succeeded: 1,
                    strategies_failed: 2,
                    strategies_timed_out: 0,
                    winning_strategy: "quick_fix",
                    elapsed_ms: 125,
                    timed_out: false,
                  }
                },
              ]}
              parallelExecutionMetrics={{
                total_queries: 2,
                max_concurrent: 10,
                actual_concurrent: 2,
                successful_queries: 2,
                failed_queries: 0,
                elapsed_ms: 1050,
                average_query_time_ms: 525,
                estimated_sequential_ms: 3100,
                speedup: 2.95,
              }}
              parallelCorrectionMetrics={{
                strategies_attempted: 3,
                strategies_succeeded: 1,
                strategies_failed: 2,
                strategies_timed_out: 0,
                winning_strategy: "quick_fix",
                elapsed_ms: 125,
                timed_out: false,
              }}
            />

            <div className="bg-gray-100 p-3 rounded mt-4">
              <p className="text-xs text-gray-500 italic">
                💡 Tip: Parallel execution is automatically enabled for multi-database queries and error corrections.
                See the orange ⚡ metrics panels above for detailed performance stats!
              </p>
            </div>
          </div>
        </div>

        {/* Scenario 6: Mapping Management */}
        <div className="bg-white rounded-lg shadow p-4 md:p-6 overflow-hidden">
          <h2 className="text-lg md:text-xl font-semibold text-gray-900 mb-4">
            Scenario 6: Mapping Management (Phase 2 Complete) 🗺️ NEW!
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Shows learned column/table name mappings and result validation patterns with comprehensive
            statistics and management UI. Patterns are automatically applied during query execution.
          </p>
          <div className="border-2 border-teal-200 rounded-lg p-3 md:p-4 bg-teal-50 overflow-x-auto">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 min-w-fit">
              {/* Column Mappings */}
              <div className="bg-white rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <span>🗂️</span>
                  Column Mappings
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="bg-gray-50 rounded p-2">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs text-red-700 line-through">price</span>
                      <span className="text-gray-400">→</span>
                      <span className="font-mono text-xs text-green-700 font-semibold">unit_price</span>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">products</span>
                      <span className="px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded">✓ 15x</span>
                      <span className="px-1.5 py-0.5 bg-yellow-100 text-yellow-700 text-xs rounded">95%</span>
                    </div>
                  </div>
                  <div className="text-xs text-gray-600 pt-2 border-t border-gray-200">
                    <strong>Total:</strong> 23 mappings | <strong>Applied:</strong> 156 times
                  </div>
                </div>
              </div>

              {/* Table Mappings */}
              <div className="bg-white rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <span>📊</span>
                  Table Mappings
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="bg-gray-50 rounded p-2">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs text-red-700 line-through">customer</span>
                      <span className="text-gray-400">→</span>
                      <span className="font-mono text-xs text-green-700 font-semibold">customers</span>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      <span className="px-1.5 py-0.5 bg-indigo-100 text-indigo-700 text-xs rounded">alias</span>
                      <span className="px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded">✓ 8x</span>
                      <span className="px-1.5 py-0.5 bg-yellow-100 text-yellow-700 text-xs rounded">90%</span>
                    </div>
                  </div>
                  <div className="text-xs text-gray-600 pt-2 border-t border-gray-200">
                    <strong>Total:</strong> 12 mappings | <strong>Applied:</strong> 84 times
                  </div>
                </div>
              </div>

              {/* Result Patterns */}
              <div className="bg-white rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <span>🎯</span>
                  Validation Patterns
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="bg-gray-50 rounded p-2">
                    <div className="text-xs mb-1">
                      <span className="px-1.5 py-0.5 bg-red-100 text-red-700 rounded font-medium">empty_result</span>
                    </div>
                    <div className="text-xs text-gray-700 mb-1">
                      WHERE status = 'active'
                    </div>
                    <div className="flex flex-wrap gap-1">
                      <span className="px-1.5 py-0.5 bg-purple-100 text-purple-700 text-xs rounded">13 triggers</span>
                      <span className="px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded">85% helpful</span>
                    </div>
                  </div>
                  <div className="text-xs text-gray-600 pt-2 border-t border-gray-200">
                    <strong>Total:</strong> 7 patterns | <strong>Triggers:</strong> 42 times
                  </div>
                </div>
              </div>
            </div>

            {/* Key Features */}
            <div className="bg-white rounded-lg p-3 md:p-4 mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Key Features:</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Auto-learns from user feedback</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Column/table name corrections</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Result validation patterns</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Comprehensive statistics dashboard</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Management UI with filtering</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Success rate & helpfulness tracking</span>
                </div>
              </div>
            </div>

            <div className="bg-gray-100 p-3 rounded">
              <p className="text-xs text-gray-500 italic">
                💡 Tip: Access the mapping management dashboard to view all learned patterns, filter by
                connection/table, and manage mappings. Patterns are automatically applied during query execution!
              </p>
            </div>
          </div>
        </div>

        {/* Scenario 7: Tool-Using Agent */}
        <div className="bg-white rounded-lg shadow p-4 md:p-6 overflow-hidden">
          <h2 className="text-lg md:text-xl font-semibold text-gray-900 mb-4">
            Scenario 7: Tool-Using Agent (Phase 3.1) 🔧 NEW!
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Shows the Tool-Using Agent automatically exploring database schema before generating SQL.
            Tools gather context about tables, columns, and sample values for better first-attempt accuracy.
            Tool execution steps are visible in the Agent Trace (orange highlights).
          </p>
          <div className="border-2 border-amber-200 rounded-lg p-3 md:p-4 bg-amber-50 overflow-x-auto">
            {/* Tool Categories */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 min-w-fit">
              {/* Schema Tools */}
              <div className="bg-white rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <span>📋</span>
                  Schema Tools
                </h3>
                <div className="space-y-2 text-xs">
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-mono text-amber-700 font-semibold">search_schema</div>
                    <div className="text-gray-600">Find tables/columns by keyword</div>
                  </div>
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-mono text-amber-700 font-semibold">get_table_info</div>
                    <div className="text-gray-600">Get columns, PKs, relationships</div>
                  </div>
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-mono text-amber-700 font-semibold">find_columns</div>
                    <div className="text-gray-600">Search columns across tables</div>
                  </div>
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-mono text-amber-700 font-semibold">get_relationships</div>
                    <div className="text-gray-600">Foreign key & join suggestions</div>
                  </div>
                </div>
              </div>

              {/* Data Tools */}
              <div className="bg-white rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <span>📊</span>
                  Data Tools
                </h3>
                <div className="space-y-2 text-xs">
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-mono text-amber-700 font-semibold">get_sample_data</div>
                    <div className="text-gray-600">Sample rows from tables</div>
                  </div>
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-mono text-amber-700 font-semibold">get_column_values</div>
                    <div className="text-gray-600">Distinct values (CA vs California)</div>
                  </div>
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-mono text-amber-700 font-semibold">count_rows</div>
                    <div className="text-gray-600">Row counts with filters</div>
                  </div>
                </div>
              </div>

              {/* Query Tools */}
              <div className="bg-white rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <span>✅</span>
                  Query Tools
                </h3>
                <div className="space-y-2 text-xs">
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-mono text-amber-700 font-semibold">test_query</div>
                    <div className="text-gray-600">Test SQL syntax (EXPLAIN)</div>
                  </div>
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-mono text-amber-700 font-semibold">validate_sql</div>
                    <div className="text-gray-600">Validate schema references</div>
                  </div>
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-mono text-amber-700 font-semibold">explain_query</div>
                    <div className="text-gray-600">Get execution plan</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Live Demo with Tool Trace */}
            <QueryResults
              queryId={1001}
              sql="SELECT * FROM customers WHERE state = 'CA'"
              results={[
                { id: 1, name: "Alice Johnson", email: "alice@example.com", state: "CA" },
                { id: 2, name: "Bob Smith", email: "bob@example.com", state: "CA" },
              ]}
              rowCount={2}
              executionTime={85}
              isValid={true}
              warnings={["🔧 Used 3 tools to gather schema context before SQL generation"]}
              selfCorrected={false}
              totalAttempts={1}
              agentTrace={{
                steps: [
                  {
                    timestamp: new Date().toISOString(),
                    elapsed_ms: 0.0,
                    type: "analysis",
                    message: "Analyzing question: Show me customers from California",
                    metadata: { database_type: "postgresql" },
                    icon: "🔍"
                  },
                  {
                    timestamp: new Date().toISOString(),
                    elapsed_ms: 5.0,
                    type: "tool_planning",
                    message: "Planning 3 tool calls to gather schema context",
                    metadata: { planned_tools: ["search_schema", "get_table_info", "get_column_values"] },
                    icon: "🔧"
                  },
                  {
                    timestamp: new Date().toISOString(),
                    elapsed_ms: 15.0,
                    type: "tool_success",
                    message: "Tool 'search_schema' executed successfully (8.2ms)",
                    metadata: { tool: "search_schema", args: { keyword: "customer" }, success: true, time_ms: 8.2 },
                    icon: "✅"
                  },
                  {
                    timestamp: new Date().toISOString(),
                    elapsed_ms: 25.0,
                    type: "tool_success",
                    message: "Tool 'get_table_info' executed successfully (6.5ms)",
                    metadata: { tool: "get_table_info", args: { table_name: "customers" }, success: true, time_ms: 6.5 },
                    icon: "✅"
                  },
                  {
                    timestamp: new Date().toISOString(),
                    elapsed_ms: 35.0,
                    type: "tool_success",
                    message: "Tool 'get_column_values' executed successfully (5.1ms) (cached)",
                    metadata: { tool: "get_column_values", args: { table_name: "customers", column_name: "state" }, success: true, cache_hit: true, time_ms: 5.1 },
                    icon: "✅"
                  },
                  {
                    timestamp: new Date().toISOString(),
                    elapsed_ms: 40.0,
                    type: "tool_context",
                    message: "Built enriched context from 3 tools",
                    metadata: { tools_used: ["search_schema", "get_table_info", "get_column_values"], context_length: 450 },
                    icon: "📝"
                  },
                  {
                    timestamp: new Date().toISOString(),
                    elapsed_ms: 65.0,
                    type: "generation",
                    message: "Generated SQL: SELECT * FROM customers WHERE state = 'CA'",
                    metadata: { sql: "SELECT * FROM customers WHERE state = 'CA'" },
                    icon: "✨"
                  },
                  {
                    timestamp: new Date().toISOString(),
                    elapsed_ms: 70.0,
                    type: "execution",
                    message: "Executing SQL query",
                    metadata: {},
                    icon: "⚡"
                  },
                  {
                    timestamp: new Date().toISOString(),
                    elapsed_ms: 85.0,
                    type: "success",
                    message: "Query executed successfully (rows: 2, time: 15ms)",
                    metadata: { row_count: 2, execution_time_ms: 15 },
                    icon: "✅"
                  }
                ],
                total_elapsed_ms: 85.0,
                start_time: new Date().toISOString()
              }}
              attempts={[
                {
                  attempt_number: 1,
                  sql: "SELECT * FROM customers WHERE state = 'CA'",
                  success: true,
                  error: null,
                  error_type: null,
                  execution_time_ms: 15,
                  row_count: 2,
                  fix_method: null,
                }
              ]}
            />

            {/* Key Features */}
            <div className="bg-white rounded-lg p-3 md:p-4 mt-4 mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Key Features:</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>10 specialized tools across 4 categories</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Automatic schema exploration before SQL</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Sample value discovery (CA vs California)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Tool execution visible in Agent Trace</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>10-second timeout protection per tool</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Schema validation with "Did you mean?" suggestions</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Result caching for performance (5min TTL)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>SQL injection prevention (parameterized queries)</span>
                </div>
              </div>
            </div>

            <div className="bg-gray-100 p-3 rounded">
              <p className="text-xs text-gray-500 italic">
                💡 Tip: Expand the Agent Trace above to see tool execution steps (orange highlights).
                Tools help discover correct table/column names and actual data values before generating SQL!
              </p>
            </div>
          </div>
        </div>

        {/* Scenario 8: Chart Visualizations */}
        <div className="bg-white rounded-lg shadow p-4 md:p-6 overflow-hidden">
          <h2 className="text-lg md:text-xl font-semibold text-gray-900 mb-4">
            Scenario 8: Chart Visualizations (Phase 4.1) 📊 NEW!
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Shows automatic chart detection and visualization with Table/Chart toggle.
            AutoChart intelligently selects the best chart type based on data structure with confidence scoring.
            Supports time-series line charts, categorical bar charts, and pie/donut charts with PNG/SVG/CSV export.
          </p>
          <div className="border-2 border-blue-200 rounded-lg p-3 md:p-4 bg-blue-50 overflow-x-auto">
            {/* Chart Detection Rules */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4 min-w-fit">
              {/* Detection Algorithm */}
              <div className="bg-white rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <span>🧠</span>
                  Chart Detection Algorithm
                </h3>
                <div className="space-y-2 text-xs">
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-semibold text-blue-700 mb-1">Time-Series (0.85-0.95)</div>
                    <div className="text-gray-600">Date/time column + 1-5 numeric values</div>
                    <div className="text-gray-500 text-[10px]">Higher confidence if data is ordered</div>
                  </div>
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-semibold text-purple-700 mb-1">Pie Chart (0.85)</div>
                    <div className="text-gray-600">2-12 categories, ≤20 rows, 1 value</div>
                    <div className="text-gray-500 text-[10px]">Perfect for small categorical sets</div>
                  </div>
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-semibold text-green-700 mb-1">Bar Chart (0.80)</div>
                    <div className="text-gray-600">Categorical + 1-3 numeric (2-50 rows)</div>
                    <div className="text-gray-500 text-[10px]">Vertical or horizontal bars</div>
                  </div>
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-semibold text-gray-700 mb-1">Table Fallback (0.50)</div>
                    <div className="text-gray-600">Complex/large datasets (&gt;50 rows)</div>
                    <div className="text-gray-500 text-[10px]">Always available as option</div>
                  </div>
                </div>
              </div>

              {/* Features */}
              <div className="bg-white rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <span>✨</span>
                  Visualization Features
                </h3>
                <div className="space-y-1.5 text-sm">
                  <div className="flex items-start gap-2">
                    <span className="text-green-600">✓</span>
                    <span>Auto-detection with confidence badges</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-600">✓</span>
                    <span>Manual chart type override</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-600">✓</span>
                    <span>Table/Chart toggle in QueryResults</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-600">✓</span>
                    <span>Export to PNG, SVG, or CSV</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-600">✓</span>
                    <span>Responsive Recharts components</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-600">✓</span>
                    <span>Interactive tooltips & legends</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-600">✓</span>
                    <span>Color-coded confidence levels</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-600">✓</span>
                    <span>Lightweight (~30KB Recharts)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Sample Charts */}
            <div className="bg-white rounded-lg p-3 md:p-4 mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Sample Visualizations:</h4>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-3 rounded">
                  <div className="font-semibold text-blue-800 mb-1">📈 Time-Series</div>
                  <div className="text-blue-700">Monthly sales over time</div>
                  <div className="text-blue-600 text-[10px] mt-1">Multi-line support</div>
                </div>
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-3 rounded">
                  <div className="font-semibold text-purple-800 mb-1">🥧 Pie Chart</div>
                  <div className="text-purple-700">Market share by category</div>
                  <div className="text-purple-600 text-[10px] mt-1">Donut variant available</div>
                </div>
                <div className="bg-gradient-to-br from-green-50 to-green-100 p-3 rounded">
                  <div className="font-semibold text-green-800 mb-1">📊 Bar Chart</div>
                  <div className="text-green-700">Sales by region</div>
                  <div className="text-green-600 text-[10px] mt-1">Grouped bars for multiple values</div>
                </div>
              </div>
            </div>

            <div className="bg-gray-100 p-3 rounded">
              <p className="text-xs text-gray-500 italic">
                💡 Tip: In QueryResults, toggle between Table and Chart views using the buttons above the results.
                Charts auto-detect the best visualization type, but you can manually override. Try asking for
                "monthly sales trends" or "category breakdown" to see different chart types!
              </p>
            </div>
          </div>
        </div>

        {/* Scenario 9: Index Recommendations */}
        <div className="bg-white rounded-lg shadow p-4 md:p-6 overflow-hidden">
          <h2 className="text-lg md:text-xl font-semibold text-gray-900 mb-4">
            Scenario 9: Index Recommendations (Phase 4.2) 🗂️ NEW!
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Shows automatic slow query detection and index recommendations.
            When queries take &gt;500ms, the system analyzes them with EXPLAIN and suggests optimal indexes
            with estimated performance improvements. All recommendations are passive - you manually apply them.
          </p>
          <div className="border-2 border-purple-200 rounded-lg p-3 md:p-4 bg-purple-50 overflow-x-auto">
            {/* Recommendation Flow */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 min-w-fit">
              {/* Detection */}
              <div className="bg-white rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <span>🔍</span>
                  Automatic Detection
                </h3>
                <div className="space-y-2 text-xs">
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-semibold text-purple-700 mb-1">Trigger: &gt;500ms queries</div>
                    <div className="text-gray-600">Background task launched</div>
                  </div>
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-semibold text-purple-700 mb-1">EXPLAIN Analysis</div>
                    <div className="text-gray-600">PostgreSQL, MySQL, SQLite</div>
                  </div>
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-semibold text-purple-700 mb-1">AgentTrace Logging</div>
                    <div className="text-gray-600">Full metadata tracking</div>
                  </div>
                </div>
              </div>

              {/* Recommendation */}
              <div className="bg-white rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <span>📊</span>
                  Index Analysis
                </h3>
                <div className="space-y-2 text-xs">
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-semibold text-purple-700 mb-1">Column Extraction</div>
                    <div className="text-gray-600">WHERE + ORDER BY columns</div>
                  </div>
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-semibold text-purple-700 mb-1">Conflict Detection</div>
                    <div className="text-gray-600">Check existing indexes</div>
                  </div>
                  <div className="bg-gray-50 rounded p-2">
                    <div className="font-semibold text-purple-700 mb-1">Impact Estimation</div>
                    <div className="text-gray-600">% improvement prediction</div>
                  </div>
                </div>
              </div>

              {/* Priority Calculation */}
              <div className="bg-white rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <span>🎯</span>
                  Priority Levels
                </h3>
                <div className="space-y-2 text-xs">
                  <div className="bg-red-50 rounded p-2 border border-red-200">
                    <div className="font-semibold text-red-700 mb-1">HIGH Priority</div>
                    <div className="text-red-600">&gt;2000ms OR &gt;60% improvement</div>
                  </div>
                  <div className="bg-amber-50 rounded p-2 border border-amber-200">
                    <div className="font-semibold text-amber-700 mb-1">MEDIUM Priority</div>
                    <div className="text-amber-600">&gt;1000ms OR &gt;70% confidence</div>
                  </div>
                  <div className="bg-green-50 rounded p-2 border border-green-200">
                    <div className="font-semibold text-green-700 mb-1">LOW Priority</div>
                    <div className="text-green-600">Everything else</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Live Demo with Slow Query */}
            <QueryResults
              queryId={2001}
              sql="SELECT * FROM orders WHERE customer_id = 123 AND status = 'pending' ORDER BY created_at DESC"
              results={[
                { id: 501, customer_id: 123, status: "pending", total: 89.99, created_at: "2024-11-25" },
                { id: 502, customer_id: 123, status: "pending", total: 129.50, created_at: "2024-11-24" },
              ]}
              rowCount={2}
              executionTime={750}
              isValid={true}
              warnings={[]}
              selfCorrected={false}
              totalAttempts={1}
              agentTrace={{
                steps: [
                  {
                    timestamp: new Date().toISOString(),
                    elapsed_ms: 0.0,
                    type: "analysis",
                    message: "Analyzing question: Show pending orders for customer 123",
                    metadata: {},
                    icon: "🔍"
                  },
                  {
                    timestamp: new Date().toISOString(),
                    elapsed_ms: 50.0,
                    type: "generation",
                    message: "Generated SQL query",
                    metadata: {},
                    icon: "✨"
                  },
                  {
                    timestamp: new Date().toISOString(),
                    elapsed_ms: 55.0,
                    type: "execution",
                    message: "Executing SQL query",
                    metadata: {},
                    icon: "⚡"
                  },
                  {
                    timestamp: new Date().toISOString(),
                    elapsed_ms: 805.0,
                    type: "success",
                    message: "Query executed successfully (rows: 2, time: 750ms)",
                    metadata: { row_count: 2, execution_time_ms: 750 },
                    icon: "✅"
                  },
                  {
                    timestamp: new Date().toISOString(),
                    elapsed_ms: 810.0,
                    type: "index_recommendation",
                    message: "Index recommendation generated: idx_orders_customer_status on orders",
                    metadata: {
                      table: "orders",
                      columns: ["customer_id", "status", "created_at"],
                      estimated_improvement: 65,
                      priority: "medium",
                      confidence: 0.82
                    },
                    icon: "🗂️"
                  }
                ],
                total_elapsed_ms: 810.0,
                start_time: new Date().toISOString()
              }}
              attempts={[
                {
                  attempt_number: 1,
                  sql: "SELECT * FROM orders WHERE customer_id = 123 AND status = 'pending' ORDER BY created_at DESC",
                  success: true,
                  error: null,
                  error_type: null,
                  execution_time_ms: 750,
                  row_count: 2,
                  fix_method: null,
                }
              ]}
            />

            {/* Key Features */}
            <div className="bg-white rounded-lg p-3 md:p-4 mt-4 mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Key Features:</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Auto-detect slow queries (&gt;500ms)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>EXPLAIN plan analysis (PostgreSQL, MySQL, SQLite)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Smart column extraction (WHERE + ORDER BY)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Conflict detection (existing indexes)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Performance improvement estimation</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Priority calculation (high/medium/low)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Passive system (manual apply only)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-600">✓</span>
                  <span>Full UI with filters & charts</span>
                </div>
              </div>
            </div>

            {/* UI Tour */}
            <div className="bg-white rounded-lg p-3 md:p-4 mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Indexes Tab UI:</h4>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="bg-purple-50 p-3 rounded border border-purple-200">
                  <div className="font-semibold text-purple-800 mb-1">📊 Overview</div>
                  <div className="text-purple-700">Stats cards, priority bars, status badges, quick actions</div>
                </div>
                <div className="bg-purple-50 p-3 rounded border border-purple-200">
                  <div className="font-semibold text-purple-800 mb-1">💡 Recommendations</div>
                  <div className="text-purple-700">Filterable list, expandable details, Accept/Reject/Delete</div>
                </div>
                <div className="bg-purple-50 p-3 rounded border border-purple-200">
                  <div className="font-semibold text-purple-800 mb-1">📈 Statistics</div>
                  <div className="text-purple-700">5 AutoChart visualizations (priority, status, improvement, etc.)</div>
                </div>
              </div>
            </div>

            <div className="bg-gray-100 p-3 rounded">
              <p className="text-xs text-gray-500 italic">
                💡 Tip: Notice the purple "Slow Query Detected" banner above in the QueryResults? That appears for
                queries taking &gt;500ms and directs you to the Indexes tab. Navigate to the 🗂️ Indexes tab to see
                all recommendations with CREATE INDEX SQL, estimated improvements, and management tools!
              </p>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="bg-white rounded-lg shadow p-4 md:p-6 overflow-hidden">
          <h2 className="text-lg md:text-xl font-semibold text-gray-900 mb-4">
            Component Legend
          </h2>
          <div className="space-y-3 text-sm overflow-x-auto">
            <div className="flex items-start gap-3">
              <span className="text-xl">✨</span>
              <div>
                <strong>Auto-Corrected Query:</strong> Shows when the system automatically fixed errors.
                Displays all attempts with error messages and fix methods used (Quick Fix, Learned, LLM).
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-xl">📋</span>
              <div>
                <strong>Query Plan:</strong> Displays the query plan for complex queries.
                Shows tables, joins, filters, aggregations, grouping, and ordering details.
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-xl">📊</span>
              <div>
                <strong>Agent Execution Trace:</strong> Step-by-step timeline of the agent's decision-making process.
                Shows analysis, generation, execution, fixes, verification, and learning steps.
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-xl">⚠️</span>
              <div>
                <strong>Verification Warnings:</strong> Alerts about potentially suspicious results
                that may not match user expectations.
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-xl">💬</span>
              <div>
                <strong>Feedback Button:</strong> Click the "Feedback" button next to the SQL to submit corrections.
                High-confidence feedback (≥90%) is automatically validated and applied to improve future queries.
                Destructive operations (DELETE, UPDATE, DROP) are blocked for safety.
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-xl">🗨️</span>
              <div>
                <strong>Conversational Memory (Phase 1):</strong> NEW! Enables natural multi-turn conversations.
                The system remembers your previous queries (default: 3) and understands contextual follow-ups.
                Smart detection knows when questions reference history vs. standalone queries.
                Features: Context panel, smart detection, session isolation, &lt;10ms retrieval.
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-xl">🌊</span>
              <div>
                <strong>Streaming Results (Phase 2):</strong> NEW! Progressive result delivery using Server-Sent Events.
                See results immediately as they arrive (100 rows/batch) instead of waiting for completion.
                Features: Real-time progress bars, batch indicators, &lt;50ms first batch, 30x faster perceived performance.
                Works seamlessly with conversational memory!
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-xl">⚡</span>
              <div>
                <strong>Parallel Execution (Production-Ready):</strong> NEW! Execute queries and corrections in parallel for massive speedups.
                Multi-database queries run simultaneously (3.0x faster), correction strategies race to find fastest fix (1.6x faster).
                Features: Dual timeout protection, intelligent throttling, comprehensive metrics, graceful degradation.
                See the orange metrics panels for detailed performance stats!
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-xl">🗺️</span>
              <div>
                <strong>Mapping Management (Phase 2 Complete):</strong> NEW! Automatically learn and apply column/table name corrections and result validation patterns.
                User feedback teaches the system to remember: column mappings (price → unit_price), table mappings (customer → customers),
                and result patterns (empty result warnings). Features: Auto-application, statistics dashboard, filtering, success rate tracking, 85% helpfulness rate.
                Access the management UI to view all learned patterns!
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-xl">🔧</span>
              <div>
                <strong>Tool-Using Agent (Phase 3.1):</strong> NEW! Automatically explores database schema before generating SQL using 10 specialized tools.
                Tools discover: table/column names (search_schema), relationships (get_relationships), and actual data values (get_column_values - essential for 'CA' vs 'California').
                Features: 4 tool categories, visible in Agent Trace (orange), 10s timeout protection, schema validation with suggestions, result caching, SQL injection prevention.
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-xl">📊</span>
              <div>
                <strong>Chart Visualizations (Phase 4.1):</strong> NEW! Automatic chart detection and visualization with Table/Chart toggle.
                AutoChart intelligently selects the best chart type (time-series, bar, pie) based on data structure with confidence scoring (0.80-0.95).
                Features: 4 detection rules, manual override, PNG/SVG/CSV export, interactive tooltips, Recharts components (~30KB), color-coded confidence badges.
                Toggle between Table and Chart views in QueryResults for instant visualizations!
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-xl">🗂️</span>
              <div>
                <strong>Index Recommendations (Phase 4.2):</strong> NEW! Automatic slow query detection (&gt;500ms) with database index recommendations.
                System analyzes queries with EXPLAIN, extracts WHERE/ORDER BY columns, estimates performance improvements, and calculates priority (high/medium/low).
                Features: Background analysis, EXPLAIN plan parsing (PostgreSQL/MySQL/SQLite), conflict detection, passive recommendations (manual apply), full UI with 3 tabs (Overview, Recommendations, Statistics).
                See the purple "Slow Query Detected" banner and navigate to the 🗂️ Indexes tab for CREATE INDEX SQL and management tools!
              </div>
            </div>
          </div>
        </div>

        {/* What's New Section */}
        <div className="bg-gradient-to-r from-blue-50 via-green-50 via-orange-50 via-teal-50 via-amber-50 to-purple-50 rounded-lg shadow p-4 md:p-6 border-2 border-blue-300 overflow-x-auto">
          <h2 className="text-lg md:text-xl font-semibold text-gray-900 mb-3 md:mb-4">
            🎉 What's New - Complete System with Visualizations, Recommendations & More!
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-7 gap-3 md:gap-4 min-w-fit">
            <div className="bg-white p-3 md:p-4 rounded-lg">
              <h3 className="font-semibold text-blue-600 mb-2">✨ Conversational Memory</h3>
              <ul className="text-sm space-y-1 text-gray-700">
                <li>• Natural multi-turn dialogue</li>
                <li>• Context-aware follow-ups</li>
                <li>• Smart question detection</li>
                <li>• Session-based isolation</li>
                <li>• &lt;10ms context retrieval</li>
              </ul>
            </div>
            <div className="bg-white p-3 md:p-4 rounded-lg">
              <h3 className="font-semibold text-green-600 mb-2">🌊 Streaming Results</h3>
              <ul className="text-sm space-y-1 text-gray-700">
                <li>• Progressive result delivery</li>
                <li>• Real-time batch streaming</li>
                <li>• Server-Sent Events (SSE)</li>
                <li>• Progress indicators</li>
                <li>• 30x faster perceived speed</li>
              </ul>
            </div>
            <div className="bg-white p-3 md:p-4 rounded-lg">
              <h3 className="font-semibold text-orange-600 mb-2">⚡ Parallel Execution</h3>
              <ul className="text-sm space-y-1 text-gray-700">
                <li>• 3.0x multi-database speedup</li>
                <li>• 1.6x correction speedup</li>
                <li>• Dual timeout protection</li>
                <li>• Intelligent throttling</li>
                <li>• Production-ready resilience</li>
              </ul>
            </div>
            <div className="bg-white p-3 md:p-4 rounded-lg">
              <h3 className="font-semibold text-teal-600 mb-2">🗺️ Mapping Management</h3>
              <ul className="text-sm space-y-1 text-gray-700">
                <li>• Auto-learns from feedback</li>
                <li>• Column/table corrections</li>
                <li>• Result validation patterns</li>
                <li>• Statistics dashboard</li>
                <li>• 85% helpfulness rate</li>
              </ul>
            </div>
            <div className="bg-white p-3 md:p-4 rounded-lg">
              <h3 className="font-semibold text-amber-600 mb-2">🔧 Tool-Using Agent</h3>
              <ul className="text-sm space-y-1 text-gray-700">
                <li>• 10 specialized tools</li>
                <li>• Auto schema exploration</li>
                <li>• Value discovery (CA vs CA)</li>
                <li>• Visible in Agent Trace</li>
                <li>• SQL injection prevention</li>
              </ul>
            </div>
            <div className="bg-white p-3 md:p-4 rounded-lg">
              <h3 className="font-semibold text-blue-600 mb-2">📊 Chart Visualizations</h3>
              <ul className="text-sm space-y-1 text-gray-700">
                <li>• Auto chart detection</li>
                <li>• Table/Chart toggle</li>
                <li>• Time-series, bar, pie charts</li>
                <li>• PNG/SVG/CSV export</li>
                <li>• Confidence scoring (0.80-0.95)</li>
              </ul>
            </div>
            <div className="bg-white p-3 md:p-4 rounded-lg">
              <h3 className="font-semibold text-purple-600 mb-2">🗂️ Index Recommendations</h3>
              <ul className="text-sm space-y-1 text-gray-700">
                <li>• Auto slow query detection (&gt;500ms)</li>
                <li>• EXPLAIN plan analysis</li>
                <li>• Performance improvement estimates</li>
                <li>• Priority calculation</li>
                <li>• Full management UI</li>
              </ul>
            </div>
          </div>
          <div className="mt-3 md:mt-4 bg-white p-2.5 md:p-3 rounded text-xs md:text-sm">
            <strong className="text-indigo-600">💡 Combined Power:</strong> Tools explore schema automatically,
            see results stream in real-time as interactive charts, get 3x faster multi-database execution, AND receive intelligent index recommendations!
            Example: "Show monthly sales trends" → Tools find data → Auto-detects time-series → Displays line chart → If slow (&gt;500ms) → Suggests indexes → All automated!
          </div>
        </div>
      </div>
    </div>
  );
};
