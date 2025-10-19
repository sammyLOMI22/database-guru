import React from 'react';
import QueryResults from './QueryResults';
import { QueryResponse } from '../types/api';

/**
 * Demo component to showcase all observability features
 * This demonstrates what the UI looks like with full observability data
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
        fix_method: null
      },
      {
        attempt_number: 2,
        sql: "SELECT * FROM user WHERE created_at >= '2024-01-01'",
        success: true,
        error: null,
        error_type: null,
        execution_time_ms: 45.2,
        row_count: 3,
        fix_method: "quick_fix"
      }
    ]
  };

  // Mock data with query planning
  const mockWithPlanningResponse: QueryResponse = {
    ...mockQueryResponse,
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
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Observability Features Demo
          </h1>
          <p className="text-gray-600">
            This page demonstrates all the observability components with mock data.
            Scroll down to see different scenarios.
          </p>
        </div>

        {/* Scenario 1: Auto-corrected query with verification warning */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Scenario 1: Auto-Corrected Query
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Shows a query that failed initially due to wrong table name, was auto-corrected using
            quick fix, and has a verification warning about low row count.
          </p>
          <QueryResults
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
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Scenario 2: Complex Query with Planning
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Shows a complex query that used query planning for better structure.
            Includes aggregations, grouping, and ordering.
          </p>
          <QueryResults
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

        {/* Legend */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Component Legend
          </h2>
          <div className="space-y-3 text-sm">
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
          </div>
        </div>
      </div>
    </div>
  );
};
