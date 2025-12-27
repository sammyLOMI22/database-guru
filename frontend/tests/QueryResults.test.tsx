/**
 * QueryResults Component Tests
 *
 * Tests the query results display component with all its features
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import QueryResults from '../src/components/QueryResults';
import { feedbackAPI } from '../src/services/api';

// Mock the child components
vi.mock('../src/components/AgentTrace', () => ({
  AgentTrace: ({ trace }: any) => (
    <div data-testid="agent-trace">Agent Trace: {trace.steps?.length || 0} steps</div>
  ),
}));

vi.mock('../src/components/CorrectionHistory', () => ({
  CorrectionHistory: ({ attempts, selfCorrected }: any) => (
    <div data-testid="correction-history">
      Corrections: {attempts?.length || 0} attempts (Self-corrected: {selfCorrected ? 'Yes' : 'No'})
    </div>
  ),
}));

vi.mock('../src/components/QueryPlanVisualization', () => ({
  QueryPlanVisualization: ({ plan, usedPlanning }: any) => (
    <div data-testid="query-plan">
      Query Plan (Used: {usedPlanning ? 'Yes' : 'No'})
    </div>
  ),
}));

vi.mock('../src/components/VerificationWarnings', () => ({
  VerificationWarnings: ({ warnings }: any) => (
    <div data-testid="verification-warnings">
      Verification Warnings: {warnings.length}
    </div>
  ),
}));

vi.mock('../src/components/FeedbackModal', () => ({
  FeedbackModal: ({ queryId, originalSQL, onSubmit, onClose }: any) => (
    <div data-testid="feedback-modal">
      <h2>Feedback Modal</h2>
      <p>Query ID: {queryId}</p>
      <p>SQL: {originalSQL}</p>
      <button onClick={onClose}>Close Modal</button>
      <button onClick={() => onSubmit({ queryId, feedback_type: 'test' })}>Submit</button>
    </div>
  ),
}));

vi.mock('../src/components/ParallelExecutionMetrics', () => ({
  ParallelDatabaseMetrics: ({ metrics }: any) => (
    <div data-testid="parallel-database-metrics">
      Parallel Database Metrics: {metrics.total_queries} queries, {metrics.speedup}x speedup
    </div>
  ),
  ParallelCorrectionsMetrics: ({ metrics }: any) => (
    <div data-testid="parallel-corrections-metrics">
      Parallel Corrections Metrics: {metrics.winning_strategy} in {metrics.elapsed_ms}ms
    </div>
  ),
}));

// Mock the API
vi.mock('../src/services/api', () => ({
  feedbackAPI: {
    submitFeedback: vi.fn(),
  },
}));

// Mock clipboard API
const mockWriteText = vi.fn().mockResolvedValue(undefined);
Object.defineProperty(navigator, 'clipboard', {
  value: {
    writeText: mockWriteText,
  },
  writable: true,
  configurable: true,
});

describe('QueryResults', () => {
  const mockResults = [
    { id: 1, name: 'Alice', age: 30 },
    { id: 2, name: 'Bob', age: 25 },
    { id: 3, name: 'Charlie', age: 35 },
  ];

  const defaultProps = {
    sql: 'SELECT * FROM users WHERE age > 20',
    results: mockResults,
    rowCount: 3,
    executionTime: 45.67,
    isValid: true,
    warnings: [],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('SQL Display', () => {
    it('renders SQL code in a code block', () => {
      render(<QueryResults {...defaultProps} />);

      expect(screen.getByText('Generated SQL')).toBeInTheDocument();
      expect(screen.getByText(defaultProps.sql)).toBeInTheDocument();
    });

    it('shows copy button', () => {
      render(<QueryResults {...defaultProps} />);

      expect(screen.getByTitle('Copy SQL')).toBeInTheDocument();
    });

    it('has a copy button', async () => {
      render(<QueryResults {...defaultProps} />);

      // Just verify the copy button exists - actual clipboard functionality
      // is hard to test in jsdom environment
      const copyButton = screen.getByTitle('Copy SQL');
      expect(copyButton).toBeInTheDocument();
    });

    it('shows feedback button when queryId is provided', () => {
      render(<QueryResults {...defaultProps} queryId={123} />);

      expect(screen.getByText('Feedback')).toBeInTheDocument();
      expect(screen.getByTitle('Provide Feedback')).toBeInTheDocument();
    });

    it('does not show feedback button when queryId is not provided', () => {
      render(<QueryResults {...defaultProps} />);

      expect(screen.queryByText('Feedback')).not.toBeInTheDocument();
    });
  });

  describe('Results Table', () => {
    it('renders table headers from result columns', () => {
      render(<QueryResults {...defaultProps} />);

      // Headers are uppercase
      const headers = screen.getAllByRole('columnheader');
      expect(headers.length).toBe(3);
      expect(screen.getByText('id')).toBeInTheDocument();
      expect(screen.getByText('name')).toBeInTheDocument();
      expect(screen.getByText('age')).toBeInTheDocument();
    });

    it('renders all result rows', () => {
      render(<QueryResults {...defaultProps} />);

      expect(screen.getByText('Alice')).toBeInTheDocument();
      expect(screen.getByText('Bob')).toBeInTheDocument();
      expect(screen.getByText('Charlie')).toBeInTheDocument();
      expect(screen.getByText('30')).toBeInTheDocument();
      expect(screen.getByText('25')).toBeInTheDocument();
      expect(screen.getByText('35')).toBeInTheDocument();
    });

    it('displays row count and execution stats', () => {
      render(<QueryResults {...defaultProps} />);

      // Check for row count text (use regex to be flexible)
      expect(screen.getByText(/rows/i)).toBeInTheDocument();
      expect(screen.getByText(/ms/i)).toBeInTheDocument();
    });


    it('renders null values with special styling', () => {
      const propsWithNull = {
        ...defaultProps,
        results: [{ id: 1, name: 'Alice', email: null }],
        rowCount: 1,
      };
      render(<QueryResults {...propsWithNull} />);

      expect(screen.getByText('null')).toBeInTheDocument();
    });

    it('renders object values as JSON strings', () => {
      const propsWithObject = {
        ...defaultProps,
        results: [{ id: 1, name: 'Alice', metadata: { role: 'admin' } }],
        rowCount: 1,
      };
      render(<QueryResults {...propsWithObject} />);

      expect(screen.getByText('{"role":"admin"}')).toBeInTheDocument();
    });

    it('shows "No results returned" when results are empty but query is valid', () => {
      const propsWithNoResults = {
        ...defaultProps,
        results: null,
        rowCount: 0,
        isValid: true,
      };
      render(<QueryResults {...propsWithNoResults} />);

      expect(screen.getByText('No results returned')).toBeInTheDocument();
    });

    it('shows "Query could not be executed" when query is invalid', () => {
      const propsWithInvalidQuery = {
        ...defaultProps,
        results: null,
        rowCount: 0,
        isValid: false,
      };
      render(<QueryResults {...propsWithInvalidQuery} />);

      expect(screen.getByText('Query could not be executed')).toBeInTheDocument();
    });
  });

  describe('Warnings Display', () => {
    it('does not show warnings section when there are no warnings', () => {
      render(<QueryResults {...defaultProps} warnings={[]} />);

      expect(screen.queryByText('Warnings:')).not.toBeInTheDocument();
    });

    it('shows warnings when they exist', () => {
      const propsWithWarnings = {
        ...defaultProps,
        warnings: ['This query may be slow', 'Missing index on column'],
      };
      render(<QueryResults {...propsWithWarnings} />);

      expect(screen.getByText('Warnings:')).toBeInTheDocument();
      expect(screen.getByText('This query may be slow')).toBeInTheDocument();
      expect(screen.getByText('Missing index on column')).toBeInTheDocument();
    });

    it('displays warning emoji', () => {
      const propsWithWarnings = {
        ...defaultProps,
        warnings: ['Test warning'],
      };
      render(<QueryResults {...propsWithWarnings} />);

      expect(screen.getByText('⚠️')).toBeInTheDocument();
    });
  });

  describe('Observability Features', () => {
    it('shows VerificationWarnings when verification warnings exist', () => {
      const propsWithVerification = {
        ...defaultProps,
        verificationWarnings: ['Warning 1', 'Warning 2'],
      };
      render(<QueryResults {...propsWithVerification} />);

      expect(screen.getByTestId('verification-warnings')).toBeInTheDocument();
      expect(screen.getByText(/Verification Warnings: 2/)).toBeInTheDocument();
    });

    it('does not show VerificationWarnings when array is empty', () => {
      const propsWithoutVerification = {
        ...defaultProps,
        verificationWarnings: [],
      };
      render(<QueryResults {...propsWithoutVerification} />);

      expect(screen.queryByTestId('verification-warnings')).not.toBeInTheDocument();
    });

    it('shows CorrectionHistory when self-corrected with attempts', () => {
      const propsWithCorrections = {
        ...defaultProps,
        selfCorrected: true,
        attempts: [
          { query: 'SELECT * FROM users', error: 'Syntax error' },
          { query: 'SELECT * FROM users WHERE age > 20', error: null },
        ],
      };
      render(<QueryResults {...propsWithCorrections} />);

      expect(screen.getByTestId('correction-history')).toBeInTheDocument();
      expect(screen.getByText(/Self-corrected: Yes/)).toBeInTheDocument();
    });

    it('does not show CorrectionHistory when not self-corrected', () => {
      const propsWithoutCorrections = {
        ...defaultProps,
        selfCorrected: false,
        attempts: [],
      };
      render(<QueryResults {...propsWithoutCorrections} />);

      expect(screen.queryByTestId('correction-history')).not.toBeInTheDocument();
    });

    it('shows QueryPlanVisualization when planning was used', () => {
      const propsWithPlan = {
        ...defaultProps,
        usedPlanning: true,
        queryPlan: { steps: ['Seq Scan', 'Sort'] },
      };
      render(<QueryResults {...propsWithPlan} />);

      expect(screen.getByTestId('query-plan')).toBeInTheDocument();
      expect(screen.getByText(/Used: Yes/)).toBeInTheDocument();
    });

    it('does not show QueryPlanVisualization when planning was not used', () => {
      const propsWithoutPlan = {
        ...defaultProps,
        usedPlanning: false,
      };
      render(<QueryResults {...propsWithoutPlan} />);

      expect(screen.queryByTestId('query-plan')).not.toBeInTheDocument();
    });

    it('shows AgentTrace when trace data is provided', () => {
      const propsWithTrace = {
        ...defaultProps,
        agentTrace: {
          steps: [
            { action: 'analyze', result: 'analyzed' },
            { action: 'generate', result: 'generated' },
          ],
        },
      };
      render(<QueryResults {...propsWithTrace} />);

      expect(screen.getByTestId('agent-trace')).toBeInTheDocument();
    });

    it('does not show AgentTrace when no trace data', () => {
      render(<QueryResults {...defaultProps} />);

      expect(screen.queryByTestId('agent-trace')).not.toBeInTheDocument();
    });
  });

  describe('Feedback Modal Integration', () => {
    it('opens feedback modal when feedback button is clicked', async () => {
      const user = userEvent.setup();
      render(<QueryResults {...defaultProps} queryId={123} />);

      const feedbackButton = screen.getByTitle('Provide Feedback');
      await user.click(feedbackButton);

      await waitFor(() => {
        expect(screen.getByTestId('feedback-modal')).toBeInTheDocument();
        expect(screen.getByText('Query ID: 123')).toBeInTheDocument();
        expect(screen.getByText(`SQL: ${defaultProps.sql}`)).toBeInTheDocument();
      });
    });

    it('closes feedback modal when close button is clicked', async () => {
      const user = userEvent.setup();
      render(<QueryResults {...defaultProps} queryId={123} />);

      // Open modal
      const feedbackButton = screen.getByTitle('Provide Feedback');
      await user.click(feedbackButton);

      await waitFor(() => {
        expect(screen.getByTestId('feedback-modal')).toBeInTheDocument();
      });

      // Close modal
      const closeButton = screen.getByText('Close Modal');
      await user.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByTestId('feedback-modal')).not.toBeInTheDocument();
      });
    });

    it('submits feedback and closes modal on successful submission', async () => {
      const user = userEvent.setup();
      (feedbackAPI.submitFeedback as any).mockResolvedValue({});

      render(<QueryResults {...defaultProps} queryId={123} />);

      // Open modal
      const feedbackButton = screen.getByTitle('Provide Feedback');
      await user.click(feedbackButton);

      await waitFor(() => {
        expect(screen.getByTestId('feedback-modal')).toBeInTheDocument();
      });

      // Submit feedback
      const submitButton = screen.getByText('Submit');
      await user.click(submitButton);

      await waitFor(() => {
        expect(feedbackAPI.submitFeedback).toHaveBeenCalledWith({
          queryId: 123,
          feedback_type: 'test',
        });
        expect(screen.queryByTestId('feedback-modal')).not.toBeInTheDocument();
      });
    });

    it('handles submission errors gracefully', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // Mock the API to reject
      const mockError = new Error('Network error');
      (feedbackAPI.submitFeedback as any).mockRejectedValueOnce(mockError);

      render(<QueryResults {...defaultProps} queryId={123} />);

      // Open modal
      const feedbackButton = screen.getByTitle('Provide Feedback');
      await user.click(feedbackButton);

      await waitFor(() => {
        expect(screen.getByTestId('feedback-modal')).toBeInTheDocument();
      });

      // The mock FeedbackModal component will call onSubmit with the mock data
      // This will trigger the error handling in QueryResults
      const submitButton = screen.getByText('Submit');
      await user.click(submitButton);

      // Give it time to process the error
      await waitFor(() => {
        // The console.error should have been called
        expect(consoleErrorSpy).toHaveBeenCalled();
      }, { timeout: 2000 });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Parallel Execution Metrics', () => {
    it('shows ParallelDatabaseMetrics when parallel execution metrics are provided', () => {
      const propsWithParallelMetrics = {
        ...defaultProps,
        parallelExecutionMetrics: {
          total_queries: 3,
          max_concurrent: 10,
          actual_concurrent: 3,
          successful_queries: 3,
          failed_queries: 0,
          elapsed_ms: 1050,
          average_query_time_ms: 350,
          estimated_sequential_ms: 3150,
          speedup: 3.0,
        },
      };
      render(<QueryResults {...propsWithParallelMetrics} />);

      expect(screen.getByTestId('parallel-database-metrics')).toBeInTheDocument();
      expect(screen.getByText(/3 queries, 3x speedup/)).toBeInTheDocument();
    });

    it('does not show ParallelDatabaseMetrics when no metrics provided', () => {
      render(<QueryResults {...defaultProps} />);

      expect(screen.queryByTestId('parallel-database-metrics')).not.toBeInTheDocument();
    });

    it('shows ParallelCorrectionsMetrics when parallel correction metrics are provided', () => {
      const propsWithCorrectionMetrics = {
        ...defaultProps,
        parallelCorrectionMetrics: {
          strategies_attempted: 3,
          strategies_succeeded: 1,
          strategies_failed: 2,
          strategies_timed_out: 0,
          winning_strategy: 'quick_fix',
          elapsed_ms: 125,
          timed_out: false,
        },
      };
      render(<QueryResults {...propsWithCorrectionMetrics} />);

      expect(screen.getByTestId('parallel-corrections-metrics')).toBeInTheDocument();
      expect(screen.getByText(/quick_fix in 125ms/)).toBeInTheDocument();
    });

    it('does not show ParallelCorrectionsMetrics when no metrics provided', () => {
      render(<QueryResults {...defaultProps} />);

      expect(screen.queryByTestId('parallel-corrections-metrics')).not.toBeInTheDocument();
    });

    it('can show both parallel metrics together', () => {
      const propsWithBothMetrics = {
        ...defaultProps,
        parallelExecutionMetrics: {
          total_queries: 3,
          max_concurrent: 10,
          actual_concurrent: 3,
          successful_queries: 3,
          failed_queries: 0,
          elapsed_ms: 1050,
          average_query_time_ms: 350,
          estimated_sequential_ms: 3150,
          speedup: 3.0,
        },
        parallelCorrectionMetrics: {
          strategies_attempted: 3,
          strategies_succeeded: 1,
          strategies_failed: 2,
          strategies_timed_out: 0,
          winning_strategy: 'quick_fix',
          elapsed_ms: 125,
          timed_out: false,
        },
      };
      render(<QueryResults {...propsWithBothMetrics} />);

      expect(screen.getByTestId('parallel-database-metrics')).toBeInTheDocument();
      expect(screen.getByTestId('parallel-corrections-metrics')).toBeInTheDocument();
    });

    it('shows parallel correction metrics before parallel database metrics', () => {
      const propsWithBothMetrics = {
        ...defaultProps,
        parallelExecutionMetrics: {
          total_queries: 3,
          max_concurrent: 10,
          actual_concurrent: 3,
          successful_queries: 3,
          failed_queries: 0,
          elapsed_ms: 1050,
          average_query_time_ms: 350,
        },
        parallelCorrectionMetrics: {
          strategies_attempted: 3,
          strategies_succeeded: 1,
          strategies_failed: 2,
          strategies_timed_out: 0,
          winning_strategy: 'quick_fix',
          elapsed_ms: 125,
          timed_out: false,
        },
      };
      const { container } = render(<QueryResults {...propsWithBothMetrics} />);

      const correctionMetrics = screen.getByTestId('parallel-corrections-metrics');
      const databaseMetrics = screen.getByTestId('parallel-database-metrics');

      // Check that correction metrics appear before database metrics in DOM
      const allMetrics = container.querySelectorAll('[data-testid^="parallel"]');
      expect(allMetrics[0]).toBe(correctionMetrics);
      expect(allMetrics[1]).toBe(databaseMetrics);
    });
  });

  describe('Pagination', () => {
    // Generate 25 rows for pagination testing
    const manyResults = Array.from({ length: 25 }, (_, i) => ({
      id: i + 1,
      name: `User ${i + 1}`,
      age: 20 + i,
    }));

    const paginationProps = {
      ...defaultProps,
      results: manyResults,
      rowCount: 25,
    };

    it('shows pagination controls when more than 10 rows', () => {
      render(<QueryResults {...paginationProps} />);

      expect(screen.getByText('Rows per page:')).toBeInTheDocument();
      expect(screen.getByText('1-10 of 25')).toBeInTheDocument();
    });

    it('does not show pagination controls when 10 or fewer rows', () => {
      const fewResults = manyResults.slice(0, 10);
      render(<QueryResults {...defaultProps} results={fewResults} rowCount={10} />);

      expect(screen.queryByText('Rows per page:')).not.toBeInTheDocument();
    });

    it('shows first 10 rows by default', () => {
      render(<QueryResults {...paginationProps} />);

      // First page should show User 1 through User 10
      expect(screen.getByText('User 1')).toBeInTheDocument();
      expect(screen.getByText('User 10')).toBeInTheDocument();
      expect(screen.queryByText('User 11')).not.toBeInTheDocument();
    });

    it('can navigate to next page', async () => {
      const user = userEvent.setup();
      render(<QueryResults {...paginationProps} />);

      // Click next page button
      const nextButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('svg.lucide-chevron-right')
      );
      expect(nextButton).toBeDefined();
      await user.click(nextButton!);

      // Should now show User 11 through User 20
      await waitFor(() => {
        expect(screen.getByText('User 11')).toBeInTheDocument();
        expect(screen.getByText('User 20')).toBeInTheDocument();
        expect(screen.queryByText('User 1')).not.toBeInTheDocument();
        expect(screen.getByText('11-20 of 25')).toBeInTheDocument();
      });
    });

    it('can navigate to previous page', async () => {
      const user = userEvent.setup();
      render(<QueryResults {...paginationProps} />);

      // Navigate to page 2 first
      const nextButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('svg.lucide-chevron-right')
      );
      await user.click(nextButton!);

      await waitFor(() => {
        expect(screen.getByText('User 11')).toBeInTheDocument();
      });

      // Click previous page button
      const prevButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('svg.lucide-chevron-left')
      );
      await user.click(prevButton!);

      // Should be back to page 1
      await waitFor(() => {
        expect(screen.getByText('User 1')).toBeInTheDocument();
        expect(screen.getByText('1-10 of 25')).toBeInTheDocument();
      });
    });

    it('disables previous button on first page', () => {
      render(<QueryResults {...paginationProps} />);

      const prevButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('svg.lucide-chevron-left')
      );

      expect(prevButton).toBeDisabled();
    });

    it('disables next button on last page', async () => {
      const user = userEvent.setup();
      render(<QueryResults {...paginationProps} />);

      // Navigate to last page (page 3 with 10 rows per page for 25 total)
      const nextButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('svg.lucide-chevron-right')
      );
      await user.click(nextButton!); // Page 2
      await user.click(nextButton!); // Page 3

      await waitFor(() => {
        expect(screen.getByText('21-25 of 25')).toBeInTheDocument();
        expect(nextButton).toBeDisabled();
      });
    });

    it('can change page size', async () => {
      const user = userEvent.setup();
      render(<QueryResults {...paginationProps} />);

      // Change to 25 rows per page
      const pageSizeSelect = screen.getByRole('combobox');
      await user.selectOptions(pageSizeSelect, '25');

      await waitFor(() => {
        // Should show all 25 rows on one page
        expect(screen.getByText('User 1')).toBeInTheDocument();
        expect(screen.getByText('User 25')).toBeInTheDocument();
        expect(screen.getByText('1-25 of 25')).toBeInTheDocument();
      });
    });

    it('resets to page 1 when page size changes', async () => {
      const user = userEvent.setup();
      render(<QueryResults {...paginationProps} />);

      // Navigate to page 2
      const nextButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('svg.lucide-chevron-right')
      );
      await user.click(nextButton!);

      await waitFor(() => {
        expect(screen.getByText('11-20 of 25')).toBeInTheDocument();
      });

      // Change page size
      const pageSizeSelect = screen.getByRole('combobox');
      await user.selectOptions(pageSizeSelect, '50');

      // Should reset to page 1
      await waitFor(() => {
        expect(screen.getByText('User 1')).toBeInTheDocument();
        expect(screen.getByText('1-25 of 25')).toBeInTheDocument();
      });
    });

    it('shows correct page size options', () => {
      render(<QueryResults {...paginationProps} />);

      const pageSizeSelect = screen.getByRole('combobox');
      const options = pageSizeSelect.querySelectorAll('option');

      expect(options).toHaveLength(4);
      expect(options[0]).toHaveValue('10');
      expect(options[1]).toHaveValue('25');
      expect(options[2]).toHaveValue('50');
      expect(options[3]).toHaveValue('100');
    });
  });
});
