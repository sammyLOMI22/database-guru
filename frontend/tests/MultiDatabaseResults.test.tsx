/**
 * MultiDatabaseResults Component Tests
 *
 * Tests the multi-database results display with pagination
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import MultiDatabaseResults from '../src/components/MultiDatabaseResults';

// Mock child components
vi.mock('../src/components/AgentTrace', () => ({
  AgentTrace: ({ trace }: any) => (
    <div data-testid="agent-trace">Agent Trace</div>
  ),
}));

vi.mock('../src/components/CorrectionHistory', () => ({
  CorrectionHistory: () => <div data-testid="correction-history">Correction History</div>,
}));

vi.mock('../src/components/QueryPlanVisualization', () => ({
  QueryPlanVisualization: () => <div data-testid="query-plan">Query Plan</div>,
}));

vi.mock('../src/components/VerificationWarnings', () => ({
  VerificationWarnings: () => <div data-testid="verification-warnings">Verification Warnings</div>,
}));

vi.mock('../src/components/FeedbackModal', () => ({
  FeedbackModal: ({ onClose }: any) => (
    <div data-testid="feedback-modal">
      <button onClick={onClose}>Close Modal</button>
    </div>
  ),
}));

vi.mock('../src/components/ResultSummary', () => ({
  ResultSummary: () => <div data-testid="result-summary">Result Summary</div>,
}));

vi.mock('../src/components/visualization/ChartVisualization', () => ({
  ChartVisualization: () => <div data-testid="chart">Chart</div>,
}));

vi.mock('../src/components/visualization/ChartToggle', () => ({
  ChartToggle: () => <div data-testid="chart-toggle">Chart Toggle</div>,
}));

vi.mock('../src/components/visualization/ExportDropdown', () => ({
  ExportDropdown: () => <div data-testid="export-dropdown">Export</div>,
}));

vi.mock('../src/components/visualization/CombinedExportDropdown', () => ({
  CombinedExportDropdown: () => <div data-testid="combined-export">Combined Export</div>,
}));

vi.mock('../src/components/visualization/CrossDatabaseChart', () => ({
  CrossDatabaseChart: () => <div data-testid="cross-db-chart">Cross DB Chart</div>,
}));

vi.mock('../src/components/edit/EditModeWrapper', () => ({
  EditModeWrapper: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('../src/services/api', () => ({
  feedbackAPI: {
    submitFeedback: vi.fn(),
  },
}));

// Mock clipboard API
Object.defineProperty(navigator, 'clipboard', {
  value: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
  writable: true,
  configurable: true,
});

describe('MultiDatabaseResults', () => {
  // Generate 25 rows for pagination testing
  const generateRows = (count: number) =>
    Array.from({ length: count }, (_, i) => ({
      id: i + 1,
      name: `Record ${i + 1}`,
      value: i * 10,
    }));

  const createDatabaseResult = (
    connectionId: number,
    connectionName: string,
    rowCount: number
  ) => ({
    connection_id: connectionId,
    connection_name: connectionName,
    database_type: 'postgresql',
    sql: 'SELECT * FROM table',
    success: true,
    results: generateRows(rowCount),
    row_count: rowCount,
    execution_time_ms: 50,
    error: null,
  });

  const defaultProps = {
    results: [createDatabaseResult(1, 'Database 1', 25)],
    totalRows: 25,
    totalExecutionTime: 50,
    question: 'Show all records',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('renders summary header', () => {
      render(<MultiDatabaseResults {...defaultProps} />);

      expect(screen.getByText('Multi-Database Insights')).toBeInTheDocument();
    });

    it('renders database result cards', () => {
      render(<MultiDatabaseResults {...defaultProps} />);

      expect(screen.getByText('Database 1')).toBeInTheDocument();
    });

    it('shows total rows in summary', () => {
      render(<MultiDatabaseResults {...defaultProps} />);

      // Total Rows label should be present
      expect(screen.getByText('Total Rows')).toBeInTheDocument();
    });
  });

  describe('Pagination', () => {
    it('shows pagination controls when database has more than 10 rows', () => {
      render(<MultiDatabaseResults {...defaultProps} />);

      expect(screen.getByText('Rows per page:')).toBeInTheDocument();
      expect(screen.getByText('1-10 of 25')).toBeInTheDocument();
    });

    it('does not show pagination controls when database has 10 or fewer rows', () => {
      const propsWithFewRows = {
        ...defaultProps,
        results: [createDatabaseResult(1, 'Database 1', 8)],
        totalRows: 8,
      };
      render(<MultiDatabaseResults {...propsWithFewRows} />);

      expect(screen.queryByText('Rows per page:')).not.toBeInTheDocument();
    });

    it('shows first 10 rows by default', () => {
      render(<MultiDatabaseResults {...defaultProps} />);

      expect(screen.getByText('Record 1')).toBeInTheDocument();
      expect(screen.getByText('Record 10')).toBeInTheDocument();
      expect(screen.queryByText('Record 11')).not.toBeInTheDocument();
    });

    it('can navigate to next page', async () => {
      const user = userEvent.setup();
      render(<MultiDatabaseResults {...defaultProps} />);

      // Click next page button
      const nextButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('svg.lucide-chevron-right')
      );
      expect(nextButton).toBeDefined();
      await user.click(nextButton!);

      await waitFor(() => {
        expect(screen.getByText('Record 11')).toBeInTheDocument();
        expect(screen.getByText('Record 20')).toBeInTheDocument();
        expect(screen.queryByText('Record 1')).not.toBeInTheDocument();
        expect(screen.getByText('11-20 of 25')).toBeInTheDocument();
      });
    });

    it('can navigate to previous page', async () => {
      const user = userEvent.setup();
      render(<MultiDatabaseResults {...defaultProps} />);

      // Navigate to page 2 first
      const nextButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('svg.lucide-chevron-right')
      );
      await user.click(nextButton!);

      await waitFor(() => {
        expect(screen.getByText('Record 11')).toBeInTheDocument();
      });

      // Click previous page button
      const prevButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('svg.lucide-chevron-left')
      );
      await user.click(prevButton!);

      await waitFor(() => {
        expect(screen.getByText('Record 1')).toBeInTheDocument();
        expect(screen.getByText('1-10 of 25')).toBeInTheDocument();
      });
    });

    it('disables previous button on first page', () => {
      render(<MultiDatabaseResults {...defaultProps} />);

      const prevButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('svg.lucide-chevron-left')
      );

      expect(prevButton).toBeDisabled();
    });

    it('disables next button on last page', async () => {
      const user = userEvent.setup();
      render(<MultiDatabaseResults {...defaultProps} />);

      // Navigate to last page (page 3)
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
      render(<MultiDatabaseResults {...defaultProps} />);

      // Change to 25 rows per page
      const pageSizeSelect = screen.getByRole('combobox');
      await user.selectOptions(pageSizeSelect, '25');

      await waitFor(() => {
        expect(screen.getByText('Record 1')).toBeInTheDocument();
        expect(screen.getByText('Record 25')).toBeInTheDocument();
        expect(screen.getByText('1-25 of 25')).toBeInTheDocument();
      });
    });

    it('resets to page 1 when page size changes', async () => {
      const user = userEvent.setup();
      render(<MultiDatabaseResults {...defaultProps} />);

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

      await waitFor(() => {
        expect(screen.getByText('Record 1')).toBeInTheDocument();
        expect(screen.getByText('1-25 of 25')).toBeInTheDocument();
      });
    });
  });

  describe('Multiple Databases Pagination', () => {
    const multiDbProps = {
      results: [
        createDatabaseResult(1, 'Database 1', 15),
        createDatabaseResult(2, 'Database 2', 20),
      ],
      totalRows: 35,
      totalExecutionTime: 100,
      question: 'Show records from both databases',
    };

    it('each database has independent pagination', async () => {
      const user = userEvent.setup();
      render(<MultiDatabaseResults {...multiDbProps} />);

      // Both databases should show their own pagination controls
      const paginationControls = screen.getAllByText('Rows per page:');
      expect(paginationControls).toHaveLength(2);

      // Both should start at page 1
      expect(screen.getByText('1-10 of 15')).toBeInTheDocument();
      expect(screen.getByText('1-10 of 20')).toBeInTheDocument();
    });

    it('navigating one database does not affect the other', async () => {
      const user = userEvent.setup();
      render(<MultiDatabaseResults {...multiDbProps} />);

      // Find all next buttons (one per database)
      const nextButtons = screen.getAllByRole('button').filter(btn =>
        btn.querySelector('svg.lucide-chevron-right')
      );
      expect(nextButtons).toHaveLength(2);

      // Click next on first database only
      await user.click(nextButtons[0]);

      await waitFor(() => {
        // First database should be on page 2
        expect(screen.getByText('11-15 of 15')).toBeInTheDocument();
        // Second database should still be on page 1
        expect(screen.getByText('1-10 of 20')).toBeInTheDocument();
      });
    });
  });

  describe('Expand/Collapse', () => {
    it('all databases are expanded by default', () => {
      render(<MultiDatabaseResults {...defaultProps} />);

      // Check that results table is visible
      expect(screen.getByText('Record 1')).toBeInTheDocument();
    });

    it('can collapse and expand databases', async () => {
      const user = userEvent.setup();
      render(<MultiDatabaseResults {...defaultProps} />);

      // Click to collapse
      await user.click(screen.getByText('Database 1'));

      await waitFor(() => {
        expect(screen.queryByText('Record 1')).not.toBeInTheDocument();
      });

      // Click to expand
      await user.click(screen.getByText('Database 1'));

      await waitFor(() => {
        expect(screen.getByText('Record 1')).toBeInTheDocument();
      });
    });
  });
});
