// Tests for CompilationStats Component
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import CompilationStats from '../src/components/CompilationStats';
import * as compilationApi from '../src/services/compilationApi';

// Mock the API module
vi.mock('../src/services/compilationApi', () => ({
  compilationAPI: {
    getStats: vi.fn(),
    getConnectionMetrics: vi.fn(),
    getInvalidationLog: vi.fn(),
  },
}));

describe('CompilationStats', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the component with header', async () => {
    const mockStats = {
      success: true,
      plan_cache: {
        total_plans: 25,
        cached_plans: 15,
        total_lookups: 500,
        hits: 300,
        misses: 200,
        hit_rate_percent: 60.0,
        avg_lookup_ms: 3.2,
      },
      statement_manager: {
        total_statements: 40,
        prepared_statements: 18,
        total_executions: 800,
        avg_executions_per_statement: 20,
        total_execution_ms: 4500.0,
        avg_execution_ms: 5.625,
      },
      databases: {
        postgres_db: {
          connection_id: 1,
          total_queries: 50,
          prepared_statements: 10,
          cached_plans: 12,
          total_executions: 200,
          total_execution_ms: 1500.0,
          avg_execution_ms: 7.5,
        },
      },
      timestamp: new Date().toISOString(),
    };

    (compilationApi.compilationAPI.getStats as any).mockResolvedValue(mockStats);

    render(<CompilationStats />);

    await waitFor(() => {
      expect(screen.getByText('⚡ Query Compilation')).toBeInTheDocument();
    });

    expect(screen.getByText('Real-time metrics for query normalization, plan caching, and prepared statements')).toBeInTheDocument();
  });

  it('displays overview tab by default', async () => {
    const mockStats = {
      success: true,
      plan_cache: {
        total_plans: 25,
        cached_plans: 15,
        total_lookups: 500,
        hits: 300,
        misses: 200,
        hit_rate_percent: 60.0,
        avg_lookup_ms: 3.2,
      },
      statement_manager: {
        total_statements: 40,
        prepared_statements: 18,
        total_executions: 800,
        avg_executions_per_statement: 20,
        total_execution_ms: 4500.0,
        avg_execution_ms: 5.625,
      },
      databases: {
        postgres_db: {
          connection_id: 1,
          total_queries: 50,
          prepared_statements: 10,
          cached_plans: 12,
          total_executions: 200,
          total_execution_ms: 1500.0,
          avg_execution_ms: 7.5,
        },
      },
      timestamp: new Date().toISOString(),
    };

    (compilationApi.compilationAPI.getStats as any).mockResolvedValue(mockStats);

    render(<CompilationStats />);

    await waitFor(() => {
      expect(screen.getByText('Plan Cache')).toBeInTheDocument();
    });

    // Check for overview stats cards
    expect(screen.getByText('60.0%')).toBeInTheDocument(); // plan cache hit rate
  });

  it('displays tab navigation buttons', async () => {
    const mockStats = {
      success: true,
      plan_cache: {
        total_plans: 25,
        cached_plans: 15,
        total_lookups: 500,
        hits: 300,
        misses: 200,
        hit_rate_percent: 60.0,
        avg_lookup_ms: 3.2,
      },
      statement_manager: {
        total_statements: 40,
        prepared_statements: 18,
        total_executions: 800,
        avg_executions_per_statement: 20,
        total_execution_ms: 4500.0,
        avg_execution_ms: 5.625,
      },
      databases: {},
      timestamp: new Date().toISOString(),
    };

    (compilationApi.compilationAPI.getStats as any).mockResolvedValue(mockStats);

    render(<CompilationStats />);

    await waitFor(() => {
      expect(screen.getByText('📊 Overview')).toBeInTheDocument();
    });

    expect(screen.getByText('🗄️ Per-Connection')).toBeInTheDocument();
    expect(screen.getByText('📝 Invalidation Log')).toBeInTheDocument();
  });

  it('handles error state gracefully', async () => {
    const errorMessage = 'Failed to fetch compilation statistics';
    (compilationApi.compilationAPI.getStats as any).mockRejectedValue(
      new Error(errorMessage)
    );

    render(<CompilationStats />);

    await waitFor(() => {
      expect(screen.getByText('Error Loading Compilation Stats')).toBeInTheDocument();
    });

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  it('displays database breakdown information', async () => {
    const mockStats = {
      success: true,
      plan_cache: {
        total_plans: 25,
        cached_plans: 15,
        total_lookups: 500,
        hits: 300,
        misses: 200,
        hit_rate_percent: 60.0,
        avg_lookup_ms: 3.2,
      },
      statement_manager: {
        total_statements: 40,
        prepared_statements: 18,
        total_executions: 800,
        avg_executions_per_statement: 20,
        total_execution_ms: 4500.0,
        avg_execution_ms: 5.625,
      },
      databases: {
        postgres_db: {
          connection_id: 1,
          total_queries: 50,
          prepared_statements: 10,
          cached_plans: 12,
          total_executions: 200,
          total_execution_ms: 1500.0,
          avg_execution_ms: 7.5,
        },
      },
      timestamp: new Date().toISOString(),
    };

    (compilationApi.compilationAPI.getStats as any).mockResolvedValue(mockStats);

    render(<CompilationStats />);

    await waitFor(() => {
      expect(screen.getByText('postgres_db')).toBeInTheDocument();
    });

    expect(screen.getByText('ID: 1')).toBeInTheDocument();
  });

  it('provides manual refresh functionality', async () => {
    const mockStats = {
      success: true,
      plan_cache: {
        total_plans: 25,
        cached_plans: 15,
        total_lookups: 500,
        hits: 300,
        misses: 200,
        hit_rate_percent: 60.0,
        avg_lookup_ms: 3.2,
      },
      statement_manager: {
        total_statements: 40,
        prepared_statements: 18,
        total_executions: 800,
        avg_executions_per_statement: 20,
        total_execution_ms: 4500.0,
        avg_execution_ms: 5.625,
      },
      databases: {},
      timestamp: new Date().toISOString(),
    };

    (compilationApi.compilationAPI.getStats as any).mockResolvedValue(mockStats);

    render(<CompilationStats />);

    await waitFor(() => {
      expect(screen.getByText(/🔄 Refresh/)).toBeInTheDocument();
    });

    const refreshButton = screen.getByText(/🔄 Refresh/);
    fireEvent.click(refreshButton);

    // Should call getStats at least twice (initial + manual refresh)
    await waitFor(() => {
      expect(compilationApi.compilationAPI.getStats).toHaveBeenCalledTimes(2);
    });
  });

  it('switches between tabs', async () => {
    const mockStats = {
      success: true,
      plan_cache: {
        total_plans: 25,
        cached_plans: 15,
        total_lookups: 500,
        hits: 300,
        misses: 200,
        hit_rate_percent: 60.0,
        avg_lookup_ms: 3.2,
      },
      statement_manager: {
        total_statements: 40,
        prepared_statements: 18,
        total_executions: 800,
        avg_executions_per_statement: 20,
        total_execution_ms: 4500.0,
        avg_execution_ms: 5.625,
      },
      databases: {},
      timestamp: new Date().toISOString(),
    };

    const mockMetrics = {
      success: true,
      connection: {
        id: 1,
        name: 'postgres_db',
        database_type: 'postgresql',
      },
      metrics: [],
      summary: {
        total_compiled_queries: 50,
        prepared_statements: 10,
        cached_plans: 12,
        total_executions: 200,
        total_execution_ms: 1500.0,
        avg_execution_ms: 7.5,
      },
      pagination: {
        limit: 50,
        offset: 0,
        has_more: false,
      },
    };

    (compilationApi.compilationAPI.getStats as any).mockResolvedValue(mockStats);
    (compilationApi.compilationAPI.getConnectionMetrics as any).mockResolvedValue(mockMetrics);

    render(<CompilationStats />);

    await waitFor(() => {
      expect(screen.getByText('📊 Overview')).toBeInTheDocument();
    });

    // Click on Per-Connection tab
    const metricsTab = screen.getByText('🗄️ Per-Connection');
    fireEvent.click(metricsTab);

    await waitFor(() => {
      expect(compilationApi.compilationAPI.getConnectionMetrics).toHaveBeenCalled();
    });
  });

  it('displays invalidation log tab content', async () => {
    const mockStats = {
      success: true,
      plan_cache: {
        total_plans: 25,
        cached_plans: 15,
        total_lookups: 500,
        hits: 300,
        misses: 200,
        hit_rate_percent: 60.0,
        avg_lookup_ms: 3.2,
      },
      statement_manager: {
        total_statements: 40,
        prepared_statements: 18,
        total_executions: 800,
        avg_executions_per_statement: 20,
        total_execution_ms: 4500.0,
        avg_execution_ms: 5.625,
      },
      databases: {},
      timestamp: new Date().toISOString(),
    };

    const mockLog = {
      success: true,
      entries: [
        {
          id: 1,
          connection_id: 1,
          table_name: 'products',
          invalidation_reason: 'schema_change',
          plans_invalidated: 5,
          statements_invalidated: 2,
          invalidated_at: new Date().toISOString(),
        },
      ],
      pagination: {
        limit: 50,
        offset: 0,
        has_more: false,
      },
    };

    (compilationApi.compilationAPI.getStats as any).mockResolvedValue(mockStats);
    (compilationApi.compilationAPI.getInvalidationLog as any).mockResolvedValue(mockLog);

    render(<CompilationStats />);

    await waitFor(() => {
      expect(screen.getByText('📝 Invalidation Log')).toBeInTheDocument();
    });

    // Click on Invalidation Log tab
    const logTab = screen.getByText('📝 Invalidation Log');
    fireEvent.click(logTab);

    await waitFor(() => {
      expect(compilationApi.compilationAPI.getInvalidationLog).toHaveBeenCalled();
    });
  });

  it('displays compilation statistics correctly', async () => {
    const mockStats = {
      success: true,
      plan_cache: {
        total_plans: 25,
        cached_plans: 15,
        total_lookups: 500,
        hits: 300,
        misses: 200,
        hit_rate_percent: 60.0,
        avg_lookup_ms: 3.2,
      },
      statement_manager: {
        total_statements: 40,
        prepared_statements: 18,
        total_executions: 800,
        avg_executions_per_statement: 20,
        total_execution_ms: 4500.0,
        avg_execution_ms: 5.625,
      },
      databases: {},
      timestamp: new Date().toISOString(),
    };

    (compilationApi.compilationAPI.getStats as any).mockResolvedValue(mockStats);

    render(<CompilationStats />);

    await waitFor(() => {
      // Check plan cache stats
      expect(screen.getByText('25')).toBeInTheDocument(); // total_plans
      expect(screen.getByText('18')).toBeInTheDocument(); // prepared_statements
    });
  });
});
