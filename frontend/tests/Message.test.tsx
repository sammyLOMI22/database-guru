/**
 * Message Component Tests
 *
 * Tests the chat message display component
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import Message from '../src/components/Message';

// Mock QueryResults component
vi.mock('../src/components/QueryResults', () => ({
  default: ({ sql, results, rowCount }: any) => (
    <div data-testid="query-results">
      <div>SQL: {sql}</div>
      <div>Results: {results ? results.length : 0}</div>
      <div>Rows: {rowCount}</div>
    </div>
  ),
}));

describe('Message', () => {
  describe('User Messages', () => {
    it('renders user message with correct content', () => {
      render(<Message type="user" content="Show me all users" />);

      expect(screen.getByText('Show me all users')).toBeInTheDocument();
    });

    it('applies user-specific styling', () => {
      const { container } = render(<Message type="user" content="Test message" />);

      // User messages should have primary background
      const messageContent = container.querySelector('.bg-primary-600');
      expect(messageContent).toBeInTheDocument();
    });

    it('does not render query results for user messages', () => {
      const mockQueryResponse = {
        sql: 'SELECT * FROM users',
        results: [{ id: 1, name: 'Test' }],
        row_count: 1,
        execution_time_ms: 10,
        is_valid: true,
        warnings: [],
      };

      render(<Message type="user" content="Test" queryResponse={mockQueryResponse} />);

      expect(screen.queryByTestId('query-results')).not.toBeInTheDocument();
    });
  });

  describe('Assistant Messages', () => {
    it('renders assistant message with correct content', () => {
      render(<Message type="assistant" content="Here are your results" />);

      expect(screen.getByText('Here are your results')).toBeInTheDocument();
    });

    it('applies assistant-specific styling', () => {
      const { container } = render(<Message type="assistant" content="Test message" />);

      // Assistant messages should have white background with border
      const messageContent = container.querySelector('.bg-white.border');
      expect(messageContent).toBeInTheDocument();
    });

    it('renders query results when provided', () => {
      const mockQueryResponse = {
        sql: 'SELECT * FROM users',
        results: [{ id: 1, name: 'Alice' }, { id: 2, name: 'Bob' }],
        row_count: 2,
        execution_time_ms: 15.5,
        is_valid: true,
        warnings: [],
      };

      render(<Message type="assistant" content="Results:" queryResponse={mockQueryResponse} />);

      expect(screen.getByTestId('query-results')).toBeInTheDocument();
      expect(screen.getByText('SQL: SELECT * FROM users')).toBeInTheDocument();
      expect(screen.getByText('Results: 2')).toBeInTheDocument();
      expect(screen.getByText('Rows: 2')).toBeInTheDocument();
    });

    it('does not render query results when not provided', () => {
      render(<Message type="assistant" content="No results" />);

      expect(screen.queryByTestId('query-results')).not.toBeInTheDocument();
    });
  });

  describe('Icons', () => {
    it('renders User icon for user messages', () => {
      const { container } = render(<Message type="user" content="Test" />);

      // The lucide-react User icon is rendered
      const icon = container.querySelector('.text-primary-600');
      expect(icon).toBeInTheDocument();
    });

    it('renders Bot icon for assistant messages', () => {
      const { container} = render(<Message type="assistant" content="Test" />);

      // The lucide-react Bot icon is rendered
      const icon = container.querySelector('.text-gray-600');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('QueryResponse Integration', () => {
    it('passes all query response props to QueryResults component', () => {
      const mockQueryResponse = {
        sql: 'SELECT * FROM users WHERE age > 30',
        results: [{ id: 1, name: 'Alice', age: 35 }],
        row_count: 1,
        execution_time_ms: 12.3,
        is_valid: true,
        warnings: ['Index missing on age column'],
        agent_trace: { steps: [], total_elapsed_ms: 100, start_time: '2024-01-01' },
        query_plan: null,
        attempts: [],
        self_corrected: false,
        total_attempts: 1,
        verification_warnings: [],
        used_planning: false,
      };

      render(<Message type="assistant" content="Query complete" queryResponse={mockQueryResponse} />);

      // Verify QueryResults is rendered (our mock just shows basic info)
      expect(screen.getByTestId('query-results')).toBeInTheDocument();
      expect(screen.getByText('SQL: SELECT * FROM users WHERE age > 30')).toBeInTheDocument();
    });

    it('handles query response with null results', () => {
      const mockQueryResponse = {
        sql: 'DELETE FROM users WHERE id = 999',
        results: null,
        row_count: 0,
        execution_time_ms: 5.2,
        is_valid: true,
        warnings: [],
      };

      render(<Message type="assistant" content="Deleted successfully" queryResponse={mockQueryResponse} />);

      expect(screen.getByTestId('query-results')).toBeInTheDocument();
      expect(screen.getByText('Results: 0')).toBeInTheDocument();
    });
  });
});
