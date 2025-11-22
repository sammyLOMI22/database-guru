/**
 * Tests for FeedbackStats component
 *
 * Testing the actual dashboard component
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { FeedbackStats } from '../src/components/FeedbackStats';
import { feedbackAPI } from '../src/services/api';

// Mock the API
vi.mock('../src/services/api', () => ({
  feedbackAPI: {
    getStats: vi.fn(),
    getRecentFeedback: vi.fn(),
    applyFeedback: vi.fn(),
    deleteFeedback: vi.fn(),
  },
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  CheckCircle: () => <div data-testid="check-circle-icon" />,
  Clock: () => <div data-testid="clock-icon" />,
  TrendingUp: () => <div data-testid="trending-up-icon" />,
  ChevronDown: () => <div data-testid="chevron-down-icon" />,
  ChevronUp: () => <div data-testid="chevron-up-icon" />,
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
      original_sql: 'SELECT * FROM prodcuts',
      corrected_sql: 'SELECT * FROM products',
      correction_description: 'Fixed table name',
      user_confidence: 0.9,
      applied_successfully: false,
      learned_correction_id: null,
      user_notes: null,
      created_at: '2024-01-01T10:00:00Z',
      applied_at: null,
    },
    {
      id: 2,
      query_id: 102,
      feedback_type: 'column_name',
      original_sql: 'SELECT pric FROM products',
      corrected_sql: 'SELECT price FROM products',
      correction_description: 'Wrong column reference',
      correction_details: { from: 'pric', to: 'price' },
      user_confidence: 0.85,
      applied_successfully: true,
      learned_correction_id: 42,
      user_notes: null,
      created_at: '2024-01-01T11:00:00Z',
      applied_at: '2024-01-01T11:01:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading State', () => {
    it('shows loading skeleton while fetching data', () => {
      (feedbackAPI.getStats as any).mockImplementation(() => new Promise(() => {}));
      (feedbackAPI.getRecentFeedback as any).mockImplementation(() => new Promise(() => {}));

      render(<FeedbackStats />);

      // Should show animated skeleton
      const skeletons = document.querySelectorAll('.animate-pulse');
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe('Error State', () => {
    it('displays error message when API fails', async () => {
      (feedbackAPI.getStats as any).mockRejectedValue(new Error('Network error'));
      (feedbackAPI.getRecentFeedback as any).mockRejectedValue(new Error('Network error'));

      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText(/Error:/)).toBeInTheDocument();
        expect(screen.getByText(/Network error/)).toBeInTheDocument();
      });
    });
  });

  describe('Successful Data Loading', () => {
    beforeEach(() => {
      (feedbackAPI.getStats as any).mockResolvedValue(mockStats);
      (feedbackAPI.getRecentFeedback as any).mockResolvedValue(mockRecentFeedback);
    });

    it('renders dashboard title and description', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText('Feedback Dashboard')).toBeInTheDocument();
        expect(screen.getByText(/continuous learning insights/i)).toBeInTheDocument();
      });
    });

    it('displays total feedback count', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText('25')).toBeInTheDocument();
        expect(screen.getByText(/Total Feedback/i)).toBeInTheDocument();
      });
    });

    it('displays applied count', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText('15')).toBeInTheDocument();
        expect(screen.getByText(/Applied to Learning/i)).toBeInTheDocument();
      });
    });

    it('displays pending count', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText('10')).toBeInTheDocument();
        expect(screen.getByText(/Pending Review/i)).toBeInTheDocument();
      });
    });

    it('displays feedback by type breakdown', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText(/SQL Corrections/i)).toBeInTheDocument();
        expect(screen.getByText('12')).toBeInTheDocument(); // sql_correction count

        expect(screen.getByText(/Column Names/i)).toBeInTheDocument();
        expect(screen.getByText('8')).toBeInTheDocument(); // column_name count

        expect(screen.getByText(/Table Names/i)).toBeInTheDocument();
        expect(screen.getByText('3')).toBeInTheDocument(); // table_name count

        expect(screen.getByText(/Result Issues/i)).toBeInTheDocument();
        expect(screen.getByText('2')).toBeInTheDocument(); // result_issue count
      });
    });

    it('displays recent feedback items', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText('Fixed table name')).toBeInTheDocument();
        expect(screen.getByText('Wrong column reference')).toBeInTheDocument();
      });
    });

    it('shows confidence percentage for feedback items', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText(/90% conf/)).toBeInTheDocument(); // 0.9 * 100
        expect(screen.getByText(/85% conf/)).toBeInTheDocument(); // 0.85 * 100
      });
    });

    it('shows apply button for pending feedback', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        const applyButtons = screen.getAllByRole('button', { name: /Apply/i });
        // Should have button for the pending feedback (id: 1)
        expect(applyButtons.length).toBeGreaterThan(0);
      });
    });

    it('shows applied status for already applied feedback', async () => {
      render(<FeedbackStats />);

      await waitFor(() => {
        // Should show "✓ Applied" for the second feedback item
        expect(screen.getByText(/✓ Applied/i)).toBeInTheDocument();
      });
    });
  });

  describe('Applying Feedback', () => {
    beforeEach(() => {
      (feedbackAPI.getStats as any).mockResolvedValue(mockStats);
      (feedbackAPI.getRecentFeedback as any).mockResolvedValue(mockRecentFeedback);
      (feedbackAPI.applyFeedback as any).mockResolvedValue({ success: true });
    });

    it('calls API when apply button is clicked', async () => {
      const user = userEvent.setup();
      render(<FeedbackStats />);

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Fixed table name')).toBeInTheDocument();
      });

      // Click apply button
      const applyButtons = screen.getAllByRole('button', { name: /Apply/i });
      await user.click(applyButtons[0]);

      // Should call apply API with feedback id and test_before_learning=true
      expect(feedbackAPI.applyFeedback).toHaveBeenCalledWith(1, true);
    });

    it('reloads stats after successfully applying feedback', async () => {
      const user = userEvent.setup();
      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText('Fixed table name')).toBeInTheDocument();
      });

      // Apply feedback
      const applyButtons = screen.getAllByRole('button', { name: /Apply/i });
      await user.click(applyButtons[0]);

      // Should reload both stats and recent feedback
      await waitFor(() => {
        expect(feedbackAPI.getStats).toHaveBeenCalledTimes(2); // Initial + reload
        expect(feedbackAPI.getRecentFeedback).toHaveBeenCalledTimes(2);
      });
    });

    it('shows alert when apply fails', async () => {
      const user = userEvent.setup();
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
      (feedbackAPI.applyFeedback as any).mockRejectedValue(new Error('Validation failed'));

      render(<FeedbackStats />);

      await waitFor(() => {
        expect(screen.getByText('Fixed table name')).toBeInTheDocument();
      });

      const applyButtons = screen.getAllByRole('button', { name: /Apply/i });
      await user.click(applyButtons[0]);

      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalledWith(
          expect.stringContaining('Failed to apply feedback')
        );
      });

      alertSpy.mockRestore();
    });
  });

  describe('API Integration', () => {
    it('fetches stats and recent feedback on mount', async () => {
      (feedbackAPI.getStats as any).mockResolvedValue(mockStats);
      (feedbackAPI.getRecentFeedback as any).mockResolvedValue(mockRecentFeedback);

      render(<FeedbackStats />);

      await waitFor(() => {
        expect(feedbackAPI.getStats).toHaveBeenCalledTimes(1);
        expect(feedbackAPI.getRecentFeedback).toHaveBeenCalledWith(20, 0, 'pending'); // limit=20, offset=0, filter='pending'
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles zero feedback gracefully', async () => {
      (feedbackAPI.getStats as any).mockResolvedValue({
        total_feedback: 0,
        applied_to_learning: 0,
        pending: 0,
        by_type: {},
      });
      (feedbackAPI.getRecentFeedback as any).mockResolvedValue([]);

      render(<FeedbackStats />);

      await waitFor(() => {
        // Check for Total Feedback label and that at least one 0 exists
        expect(screen.getByText(/Total Feedback/i)).toBeInTheDocument();
        expect(screen.getAllByText('0').length).toBeGreaterThan(0);
      });
    });

    it('handles missing feedback types in breakdown', async () => {
      (feedbackAPI.getStats as any).mockResolvedValue({
        total_feedback: 5,
        applied_to_learning: 5,
        pending: 0,
        by_type: {
          sql_correction: 5, // Only one type
        },
      });
      (feedbackAPI.getRecentFeedback as any).mockResolvedValue([]);

      render(<FeedbackStats />);

      await waitFor(() => {
        // Should show all type labels
        expect(screen.getByText(/SQL Corrections/i)).toBeInTheDocument();
        // Check that at least one '5' appears (could be in multiple stats)
        expect(screen.getAllByText('5').length).toBeGreaterThan(0);
      });
    });
  });
});
