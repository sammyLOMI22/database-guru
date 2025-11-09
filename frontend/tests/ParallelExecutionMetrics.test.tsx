/**
 * ParallelExecutionMetrics Component Tests
 *
 * Tests the parallel execution metrics display components
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ParallelDatabaseMetrics, ParallelCorrectionsMetrics } from '../src/components/ParallelExecutionMetrics';
import { ParallelExecutionMetrics, ParallelCorrectionMetrics } from '../src/types/api';

describe('ParallelDatabaseMetrics', () => {
  const mockMetrics: ParallelExecutionMetrics = {
    total_queries: 3,
    max_concurrent: 10,
    actual_concurrent: 3,
    successful_queries: 3,
    failed_queries: 0,
    elapsed_ms: 1050,
    average_query_time_ms: 350,
    estimated_sequential_ms: 3150,
    speedup: 3.0,
  };

  it('renders the component with title', () => {
    render(<ParallelDatabaseMetrics metrics={mockMetrics} />);

    expect(screen.getByText('Parallel Execution Metrics')).toBeInTheDocument();
  });

  it('renders custom title when provided', () => {
    render(<ParallelDatabaseMetrics metrics={mockMetrics} title="Custom Title" />);

    expect(screen.getByText('Custom Title')).toBeInTheDocument();
  });

  it('displays speedup badge when speedup > 1', () => {
    render(<ParallelDatabaseMetrics metrics={mockMetrics} />);

    expect(screen.getByText(/3.0x faster/)).toBeInTheDocument();
  });

  it('does not display speedup badge when speedup is undefined', () => {
    const metricsWithoutSpeedup: ParallelExecutionMetrics = {
      ...mockMetrics,
      speedup: undefined,
    };
    render(<ParallelDatabaseMetrics metrics={metricsWithoutSpeedup} />);

    expect(screen.queryByText(/faster/)).not.toBeInTheDocument();
  });

  it('does not display speedup badge when speedup <= 1', () => {
    const metricsWithLowSpeedup: ParallelExecutionMetrics = {
      ...mockMetrics,
      speedup: 0.9,
    };
    render(<ParallelDatabaseMetrics metrics={metricsWithLowSpeedup} />);

    expect(screen.queryByText(/faster/)).not.toBeInTheDocument();
  });

  it('displays total queries metric', () => {
    render(<ParallelDatabaseMetrics metrics={mockMetrics} />);

    expect(screen.getByText('Total Queries')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('displays concurrency metric', () => {
    render(<ParallelDatabaseMetrics metrics={mockMetrics} />);

    expect(screen.getByText('Concurrent')).toBeInTheDocument();
    expect(screen.getByText('3/10')).toBeInTheDocument();
  });

  it('displays success rate with correct percentage', () => {
    render(<ParallelDatabaseMetrics metrics={mockMetrics} />);

    expect(screen.getByText('Success Rate')).toBeInTheDocument();
    expect(screen.getByText('100%')).toBeInTheDocument();
    expect(screen.getByText('3/3 OK')).toBeInTheDocument();
  });

  it('calculates success rate correctly when some queries fail', () => {
    const metricsWithFailures: ParallelExecutionMetrics = {
      ...mockMetrics,
      total_queries: 4,
      successful_queries: 3,
      failed_queries: 1,
    };
    render(<ParallelDatabaseMetrics metrics={metricsWithFailures} />);

    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('3/4 OK')).toBeInTheDocument();
  });

  it('handles 0 total queries gracefully', () => {
    const metricsWithZeroQueries: ParallelExecutionMetrics = {
      ...mockMetrics,
      total_queries: 0,
      successful_queries: 0,
    };
    render(<ParallelDatabaseMetrics metrics={metricsWithZeroQueries} />);

    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('displays execution time metrics', () => {
    render(<ParallelDatabaseMetrics metrics={mockMetrics} />);

    expect(screen.getByText('Execution Time')).toBeInTheDocument();
    // Note: 1050ms appears in multiple places when speedup comparison is shown
    expect(screen.getAllByText('1050ms').length).toBeGreaterThan(0);
    expect(screen.getByText(/avg: 350ms/)).toBeInTheDocument();
  });

  it('shows speedup comparison when estimated_sequential_ms is provided', () => {
    render(<ParallelDatabaseMetrics metrics={mockMetrics} />);

    expect(screen.getByText('Sequential would take:')).toBeInTheDocument();
    expect(screen.getByText('3150ms')).toBeInTheDocument();
    expect(screen.getByText('Parallel execution:')).toBeInTheDocument();
    // Note: 1050ms appears in multiple places (execution time metric and speedup comparison)
    expect(screen.getAllByText('1050ms').length).toBeGreaterThan(0);
    expect(screen.getByText(/3.0x speedup!/)).toBeInTheDocument();
  });

  it('does not show speedup comparison when estimated_sequential_ms is missing', () => {
    const metricsWithoutEstimate: ParallelExecutionMetrics = {
      ...mockMetrics,
      estimated_sequential_ms: undefined,
    };
    render(<ParallelDatabaseMetrics metrics={metricsWithoutEstimate} />);

    expect(screen.queryByText('Sequential would take:')).not.toBeInTheDocument();
  });

  it('shows throttling message when max_concurrent < total_queries', () => {
    const metricsWithThrottling: ParallelExecutionMetrics = {
      ...mockMetrics,
      total_queries: 15,
      max_concurrent: 10,
      actual_concurrent: 10,
    };
    render(<ParallelDatabaseMetrics metrics={metricsWithThrottling} />);

    expect(screen.getByText(/throttled to 10 max concurrent/)).toBeInTheDocument();
  });

  it('does not show throttling message when not throttled', () => {
    render(<ParallelDatabaseMetrics metrics={mockMetrics} />);

    expect(screen.queryByText(/throttled/)).not.toBeInTheDocument();
  });

  it('displays lightning bolt emoji in title', () => {
    render(<ParallelDatabaseMetrics metrics={mockMetrics} />);

    expect(screen.getByText('⚡')).toBeInTheDocument();
  });
});

describe('ParallelCorrectionsMetrics', () => {
  const mockMetrics: ParallelCorrectionMetrics = {
    strategies_attempted: 3,
    strategies_succeeded: 1,
    strategies_failed: 2,
    strategies_timed_out: 0,
    winning_strategy: 'quick_fix',
    elapsed_ms: 125,
    timed_out: false,
  };

  it('renders the component with title', () => {
    render(<ParallelCorrectionsMetrics metrics={mockMetrics} />);

    expect(screen.getByText('Parallel Correction Metrics')).toBeInTheDocument();
  });

  it('renders custom title when provided', () => {
    render(<ParallelCorrectionsMetrics metrics={mockMetrics} title="Custom Corrections Title" />);

    expect(screen.getByText('Custom Corrections Title')).toBeInTheDocument();
  });

  it('displays winning strategy with correct display name', () => {
    render(<ParallelCorrectionsMetrics metrics={mockMetrics} />);

    expect(screen.getByText('Winning Strategy')).toBeInTheDocument();
    expect(screen.getByText('Quick Fix')).toBeInTheDocument();
  });

  it('displays correct icon for quick_fix strategy', () => {
    render(<ParallelCorrectionsMetrics metrics={mockMetrics} />);

    expect(screen.getByText('⚡')).toBeInTheDocument();
  });

  it('displays correct display name for learned strategy', () => {
    const metricsWithLearned: ParallelCorrectionMetrics = {
      ...mockMetrics,
      winning_strategy: 'learned',
    };
    render(<ParallelCorrectionsMetrics metrics={metricsWithLearned} />);

    expect(screen.getByText('Learned Pattern')).toBeInTheDocument();
    expect(screen.getByText('🧠')).toBeInTheDocument();
  });

  it('displays correct display name for llm strategy', () => {
    const metricsWithLLM: ParallelCorrectionMetrics = {
      ...mockMetrics,
      winning_strategy: 'llm',
    };
    render(<ParallelCorrectionsMetrics metrics={metricsWithLLM} />);

    expect(screen.getByText('LLM Correction')).toBeInTheDocument();
    expect(screen.getByText('🤖')).toBeInTheDocument();
  });

  it('displays correct display name for llm_fallback strategy', () => {
    const metricsWithFallback: ParallelCorrectionMetrics = {
      ...mockMetrics,
      winning_strategy: 'llm_fallback',
    };
    render(<ParallelCorrectionsMetrics metrics={metricsWithFallback} />);

    expect(screen.getByText('LLM Fallback')).toBeInTheDocument();
  });

  it('displays correct display name for llm_fallback_timeout strategy', () => {
    const metricsWithTimeoutFallback: ParallelCorrectionMetrics = {
      ...mockMetrics,
      winning_strategy: 'llm_fallback_timeout',
    };
    render(<ParallelCorrectionsMetrics metrics={metricsWithTimeoutFallback} />);

    expect(screen.getByText('LLM Fallback (Timeout)')).toBeInTheDocument();
    expect(screen.getByText('⏱️')).toBeInTheDocument();
  });

  it('handles null winning strategy gracefully', () => {
    const metricsWithNullStrategy: ParallelCorrectionMetrics = {
      ...mockMetrics,
      winning_strategy: null,
    };
    render(<ParallelCorrectionsMetrics metrics={metricsWithNullStrategy} />);

    expect(screen.getByText('None')).toBeInTheDocument();
    expect(screen.getByText('❓')).toBeInTheDocument();
  });

  it('displays elapsed time', () => {
    render(<ParallelCorrectionsMetrics metrics={mockMetrics} />);

    expect(screen.getByText('in 125ms')).toBeInTheDocument();
  });

  it('displays total time metric', () => {
    render(<ParallelCorrectionsMetrics metrics={mockMetrics} />);

    expect(screen.getByText('Total Time')).toBeInTheDocument();
    expect(screen.getByText('125ms')).toBeInTheDocument();
  });

  it('displays strategy counts correctly', () => {
    render(<ParallelCorrectionsMetrics metrics={mockMetrics} />);

    expect(screen.getByText('Attempted')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();

    expect(screen.getByText('Succeeded')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();

    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('shows timeout warning badge when timed_out is true', () => {
    const metricsWithTimeout: ParallelCorrectionMetrics = {
      ...mockMetrics,
      timed_out: true,
      strategies_timed_out: 2,
    };
    render(<ParallelCorrectionsMetrics metrics={metricsWithTimeout} />);

    expect(screen.getByText(/Timed out/)).toBeInTheDocument();
  });

  it('does not show timeout warning when timed_out is false', () => {
    render(<ParallelCorrectionsMetrics metrics={mockMetrics} />);

    expect(screen.queryByText(/Timed out/)).not.toBeInTheDocument();
  });

  it('shows timeout protection message when timeout occurred', () => {
    const metricsWithTimeout: ParallelCorrectionMetrics = {
      ...mockMetrics,
      timed_out: true,
      strategies_timed_out: 2,
    };
    render(<ParallelCorrectionsMetrics metrics={metricsWithTimeout} />);

    expect(screen.getByText('Timeout Protection Triggered')).toBeInTheDocument();
    expect(screen.getByText(/2 strategies timed out/)).toBeInTheDocument();
  });

  it('displays singular "strategy" for single timeout', () => {
    const metricsWithSingleTimeout: ParallelCorrectionMetrics = {
      ...mockMetrics,
      timed_out: true,
      strategies_timed_out: 1,
    };
    render(<ParallelCorrectionsMetrics metrics={metricsWithSingleTimeout} />);

    expect(screen.getByText(/1 strategy timed out/)).toBeInTheDocument();
  });

  it('displays info message with correct strategy count', () => {
    render(<ParallelCorrectionsMetrics metrics={mockMetrics} />);

    expect(screen.getByText(/3 correction strategies executed in parallel/)).toBeInTheDocument();
  });

  it('shows "First successful strategy wins!" message when not timed out', () => {
    render(<ParallelCorrectionsMetrics metrics={mockMetrics} />);

    expect(screen.getByText(/First successful strategy wins!/)).toBeInTheDocument();
  });

  it('shows "with timeout protection" message when timed out', () => {
    const metricsWithTimeout: ParallelCorrectionMetrics = {
      ...mockMetrics,
      timed_out: true,
      strategies_timed_out: 1,
    };
    render(<ParallelCorrectionsMetrics metrics={metricsWithTimeout} />);

    expect(screen.getByText(/with timeout protection/)).toBeInTheDocument();
  });

  it('displays trophy emoji in title', () => {
    render(<ParallelCorrectionsMetrics metrics={mockMetrics} />);

    expect(screen.getByText('🏆')).toBeInTheDocument();
  });
});
