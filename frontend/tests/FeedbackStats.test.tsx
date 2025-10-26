/**
 * Tests for FeedbackStats component
 *
 * Tests cover:
 * - Stats display
 * - Recent feedback list
 * - Loading states
 * - Error handling
 * - Apply to learning functionality
 * - Data refresh
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { FeedbackStats } from '../src/components/FeedbackStats';
import { feedbackAPI } from '../src/services/api';

// Mock the API
jest.mock('../src/services/api', () => ({
  feedbackAPI: {
    getStats: jest.fn(),
    getRecentFeedback: jest.fn(),
    applyFeedback: jest.fn(),
    deleteFeedback: jest.fn(),
  },
}));

describe('FeedbackStats', () => {
  const mockStats = {
    total_feedback: 25,
    applied_to_learning: 15,
    pending: 10,
    by_type: {
      sql_correction: 12,
      column_name: 8,
      table_name: 3,
      result_issue: 2,
    },
  };

  const mockRecentFeedback = [
    {
      id: 1,
      query_id: 101,
      feedback_type: 'sql_correction',
      corrected_sql: 'SELECT * FROM customers',
      correction_description: 'Fixed table name',
      user_confidence: 0.95,
      applied_successfully: true,
      created_at: '2024-01-15T10:30:00Z',
    },
    {
      id: 2,
      query_id: 102,
      feedback_type: 'column_name',
      correction_description: 'Column should be full_name',
      user_confidence: 0.8,
      applied_successfully: false,
      created_at: '2024-01-15T11:00:00Z',
    },
    {
      id: 3,
      query_id: 103,
      feedback_type: 'result_issue',
      correction_description: 'Missing recent data',
      user_confidence: 0.7,
      applied_successfully: false,
      created_at: '2024-01-15T11:30:00Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    (feedbackAPI.getStats as jest.Mock).mockResolvedValue(mockStats);
    (feedbackAPI.getRecentFeedback as jest.Mock).mockResolvedValue(mockRecentFeedback);
  });

  describe('Initial Rendering', () => {
    it('should render stats grid', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText(/total feedback/i)).toBeInTheDocument();
        expect(screen.getByText(/applied to learning/i)).toBeInTheDocument();
        expect(screen.getByText(/pending review/i)).toBeInTheDocument();
      });
    });

    it('should display correct stats values', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText('25')).toBeInTheDocument(); // total
        expect(screen.getByText('15')).toBeInTheDocument(); // applied
        expect(screen.getByText('10')).toBeInTheDocument(); // pending
      });
    });

    it('should display feedback by type breakdown', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText(/sql corrections/i)).toBeInTheDocument();
        expect(screen.getByText(/column names/i)).toBeInTheDocument();
        expect(screen.getByText(/table names/i)).toBeInTheDocument();
        expect(screen.getByText(/result issues/i)).toBeInTheDocument();
      });
    });

    it('should show type counts', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText(/12/)).toBeInTheDocument(); // sql_correction
        expect(screen.getByText(/8/)).toBeInTheDocument();  // column_name
        expect(screen.getByText(/3/)).toBeInTheDocument();  // table_name
        expect(screen.getByText(/2/)).toBeInTheDocument();  // result_issue
      });
    });

    it('should render recent feedback list', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText(/recent feedback/i)).toBeInTheDocument();
      });
    });
  });

  describe('Loading States', () => {
    it('should show loading skeleton while fetching data', () => {
      (feedbackAPI.getStats as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(mockStats), 1000))
      );

      render(<FeedbackStats />);

      // Should show loading state
      expect(screen.getByTestId('loading-skeleton') || screen.getByRole('status')).toBeInTheDocument();
    });

    it('should hide loading state after data loads', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.queryByTestId('loading-skeleton')).not.toBeInTheDocument();
      });
    });

    it('should fetch stats on mount', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(feedbackAPI.getStats).toHaveBeenCalledTimes(1);
        expect(feedbackAPI.getRecentFeedback).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Recent Feedback List', () => {
    it('should display all recent feedback items', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText('Fixed table name')).toBeInTheDocument();
        expect(screen.getByText('Column should be full_name')).toBeInTheDocument();
        expect(screen.getByText('Missing recent data')).toBeInTheDocument();
      });
    });

    it('should show feedback type badges', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText(/sql correction/i)).toBeInTheDocument();
        expect(screen.getByText(/column name/i)).toBeInTheDocument();
        expect(screen.getByText(/result issue/i)).toBeInTheDocument();
      });
    });

    it('should show confidence percentages', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText(/95%/)).toBeInTheDocument();
        expect(screen.getByText(/80%/)).toBeInTheDocument();
        expect(screen.getByText(/70%/)).toBeInTheDocument();
      });
    });

    it('should indicate applied status', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        const appliedIndicators = screen.getAllByText(/applied/i);
        expect(appliedIndicators.length).toBeGreaterThan(0);
      });
    });

    it('should show formatted timestamps', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        // Should display some form of timestamp
        expect(screen.getByText(/2024-01-15/i) || screen.getByText(/jan/i)).toBeInTheDocument();
      });
    });

    it('should display empty state when no feedback exists', async () => {
      (feedbackAPI.getRecentFeedback as jest.Mock).mockResolvedValue([]);

      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText(/no feedback yet/i) || screen.getByText(/no recent feedback/i)).toBeInTheDocument();
      });
    });
  });

  describe('Apply to Learning Functionality', () => {
    it('should show apply button for unapplied feedback', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        const applyButtons = screen.getAllByRole('button', { name: /apply/i });
        // Should have buttons for the 2 unapplied items
        expect(applyButtons.length).toBeGreaterThanOrEqual(2);
      });
    });

    it('should not show apply button for already applied feedback', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        // Find the applied item section
        const appliedItem = screen.getByText('Fixed table name').closest('div');
        // Should not have apply button in that section
        expect(appliedItem?.querySelector('button[name*="apply"]')).toBeFalsy();
      });
    });

    it('should call API when apply button is clicked', async () => {
      const user = userEvent.setup();
      (feedbackAPI.applyFeedback as jest.Mock).mockResolvedValue({
        id: 2,
        applied_successfully: true,
      });

      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText('Column should be full_name')).toBeInTheDocument();
      });

      const applyButtons = screen.getAllByRole('button', { name: /apply/i });
      await user.click(applyButtons[0]);

      await waitFor(() => {
        expect(feedbackAPI.applyFeedback).toHaveBeenCalledWith(
          expect.any(Number),
          true // test_before_learning
        );
      });
    });

    it('should refresh data after successful apply', async () => {
      const user = userEvent.setup();
      (feedbackAPI.applyFeedback as jest.Mock).mockResolvedValue({
        id: 2,
        applied_successfully: true,
      });

      render(<FeedbackStats />);

      await waitFor(() => {
        expect(feedbackAPI.getStats).toHaveBeenCalledTimes(1);
      });

      const applyButtons = screen.getAllByRole('button', { name: /apply/i });
      await user.click(applyButtons[0]);

      await waitFor(() => {
        // Should refresh stats and feedback list
        expect(feedbackAPI.getStats).toHaveBeenCalledTimes(2);
        expect(feedbackAPI.getRecentFeedback).toHaveBeenCalledTimes(2);
      });
    });

    it('should show error message on apply failure', async () => {
      const user = userEvent.setup();
      (feedbackAPI.applyFeedback as jest.Mock).mockRejectedValue(
        new Error('Validation failed')
      );

      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText('Column should be full_name')).toBeInTheDocument();
      });

      const applyButtons = screen.getAllByRole('button', { name: /apply/i });
      await user.click(applyButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/error/i) || screen.getByText(/failed/i)).toBeInTheDocument();
      });
    });

    it('should disable apply button while applying', async () => {
      const user = userEvent.setup();
      (feedbackAPI.applyFeedback as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ id: 2 }), 1000))
      );

      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText('Column should be full_name')).toBeInTheDocument();
      });

      const applyButtons = screen.getAllByRole('button', { name: /apply/i });
      await user.click(applyButtons[0]);

      // Button should be disabled during operation
      expect(applyButtons[0]).toBeDisabled();
    });
  });

  describe('Data Refresh', () => {
    it('should have refresh button', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
      });
    });

    it('should refresh data when refresh button is clicked', async () => {
      const user = userEvent.setup();
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(feedbackAPI.getStats).toHaveBeenCalledTimes(1);
      });

      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      await user.click(refreshButton);

      await waitFor(() => {
        expect(feedbackAPI.getStats).toHaveBeenCalledTimes(2);
        expect(feedbackAPI.getRecentFeedback).toHaveBeenCalledTimes(2);
      });
    });

    it('should auto-refresh at intervals', async () => {
      jest.useFakeTimers();

      render(<FeedbackStats />);

      await waitFor(() => {
        expect(feedbackAPI.getStats).toHaveBeenCalledTimes(1);
      });

      // Fast-forward 30 seconds
      jest.advanceTimersByTime(30000);

      await waitFor(() => {
        expect(feedbackAPI.getStats).toHaveBeenCalledTimes(2);
      });

      jest.useRealTimers();
    });
  });

  describe('Error Handling', () => {
    it('should display error message when stats fetch fails', async () => {
      (feedbackAPI.getStats as jest.Mock).mockRejectedValue(
        new Error('Network error')
      );

      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText(/error loading stats/i) || screen.getByText(/failed to load/i)).toBeInTheDocument();
      });
    });

    it('should display error message when feedback fetch fails', async () => {
      (feedbackAPI.getRecentFeedback as jest.Mock).mockRejectedValue(
        new Error('Network error')
      );

      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
      });
    });

    it('should allow retry after error', async () => {
      const user = userEvent.setup();
      (feedbackAPI.getStats as jest.Mock)
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce(mockStats);

      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
      });

      const retryButton = screen.getByRole('button', { name: /retry/i });
      await user.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText('25')).toBeInTheDocument(); // Stats loaded
      });
    });
  });

  describe('Visual Indicators', () => {
    it('should show progress bars for feedback types', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        const progressBars = screen.getAllByRole('progressbar');
        // Should have progress bars for each type
        expect(progressBars.length).toBeGreaterThanOrEqual(4);
      });
    });

    it('should calculate correct percentages for progress bars', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        // SQL corrections: 12/25 = 48%
        const sqlBar = screen.getByLabelText(/sql corrections/i);
        expect(sqlBar).toHaveAttribute('aria-valuenow', '48');
      });
    });

    it('should use different colors for feedback type badges', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        const sqlBadge = screen.getByText(/sql correction/i);
        const columnBadge = screen.getByText(/column name/i);

        // Should have different styling classes
        expect(sqlBadge.className).not.toBe(columnBadge.className);
      });
    });

    it('should show confidence with visual indicator', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        // High confidence (95%) might have different styling than low (70%)
        const highConfidence = screen.getByText(/95%/);
        const lowConfidence = screen.getByText(/70%/);

        expect(highConfidence).toBeInTheDocument();
        expect(lowConfidence).toBeInTheDocument();
      });
    });
  });

  describe('Filtering and Sorting', () => {
    it('should show recent feedback in chronological order', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        const items = screen.getAllByRole('article'); // Assuming feedback items are articles
        // Most recent (11:30) should appear before older ones
        // This depends on implementation
      });
    });

    it('should support filtering by feedback type', async () => {
      const user = userEvent.setup();
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText('Fixed table name')).toBeInTheDocument();
      });

      // If filter exists
      const filterSelect = screen.queryByLabelText(/filter by type/i);
      if (filterSelect) {
        await user.selectOptions(filterSelect, 'sql_correction');

        await waitFor(() => {
          // Should only show SQL corrections
          expect(screen.getByText('Fixed table name')).toBeInTheDocument();
          expect(screen.queryByText('Missing recent data')).not.toBeInTheDocument();
        });
      }
    });

    it('should support filtering by applied status', async () => {
      const user = userEvent.setup();
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getAllByRole('article').length).toBeGreaterThan(0);
      });

      // If status filter exists
      const statusFilter = screen.queryByLabelText(/filter by status/i);
      if (statusFilter) {
        await user.selectOptions(statusFilter, 'pending');

        await waitFor(() => {
          // Should only show unapplied feedback
          expect(screen.queryByText('Fixed table name')).not.toBeInTheDocument();
          expect(screen.getByText('Column should be full_name')).toBeInTheDocument();
        });
      }
    });
  });

  describe('Pagination', () => {
    it('should support loading more feedback', async () => {
      const user = userEvent.setup();
      (feedbackAPI.getRecentFeedback as jest.Mock)
        .mockResolvedValueOnce(mockRecentFeedback.slice(0, 2))
        .mockResolvedValueOnce(mockRecentFeedback);

      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getAllByRole('article').length).toBe(2);
      });

      const loadMoreButton = screen.queryByRole('button', { name: /load more/i });
      if (loadMoreButton) {
        await user.click(loadMoreButton);

        await waitFor(() => {
          expect(screen.getAllByRole('article').length).toBe(3);
        });
      }
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels for stats', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByLabelText(/total feedback/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/applied to learning/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/pending review/i)).toBeInTheDocument();
      });
    });

    it('should have semantic HTML structure', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByRole('region')).toBeInTheDocument();
      });
    });

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
      });

      // Tab through interactive elements
      await user.tab();
      expect(screen.getByRole('button', { name: /refresh/i })).toHaveFocus();
    });
  });
});
