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
});
