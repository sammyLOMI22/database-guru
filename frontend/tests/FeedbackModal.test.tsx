/**
 * Tests for FeedbackModal component
 *
 * Tests cover:
 * - Component rendering
 * - Form field interactions
 * - Validation
 * - Submission flow
 * - Error handling
 * - User interactions
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { FeedbackModal } from '../src/components/FeedbackModal';
import { feedbackAPI } from '../src/services/api';

// Mock the API
jest.mock('../src/services/api', () => ({
  feedbackAPI: {
    submitFeedback: jest.fn(),
  },
}));

describe('FeedbackModal', () => {
  const mockOnClose = jest.fn();
  const mockOnSuccess = jest.fn();

  const defaultProps = {
    isOpen: true,
    onClose: mockOnClose,
    onSuccess: mockOnSuccess,
    queryId: 123,
    originalSql: 'SELECT * FROM customer',
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render when open', () => {
      render(<FeedbackModal {...defaultProps} />);

      expect(screen.getByText(/submit feedback/i)).toBeInTheDocument();
      expect(screen.getByText(/original sql/i)).toBeInTheDocument();
    });

    it('should not render when closed', () => {
      render(<FeedbackModal {...defaultProps} isOpen={false} />);

      expect(screen.queryByText(/submit feedback/i)).not.toBeInTheDocument();
    });

    it('should display original SQL in read-only field', () => {
      render(<FeedbackModal {...defaultProps} />);

      const originalSqlField = screen.getByDisplayValue(defaultProps.originalSql);
      expect(originalSqlField).toBeInTheDocument();
      expect(originalSqlField).toHaveAttribute('readonly');
    });

    it('should render all feedback type options', () => {
      render(<FeedbackModal {...defaultProps} />);

      expect(screen.getByText(/sql correction/i)).toBeInTheDocument();
      expect(screen.getByText(/column name/i)).toBeInTheDocument();
      expect(screen.getByText(/table name/i)).toBeInTheDocument();
      expect(screen.getByText(/result issue/i)).toBeInTheDocument();
    });

    it('should render confidence slider', () => {
      render(<FeedbackModal {...defaultProps} />);

      const slider = screen.getByRole('slider');
      expect(slider).toBeInTheDocument();
      expect(slider).toHaveAttribute('type', 'range');
    });

    it('should render submit and cancel buttons', () => {
      render(<FeedbackModal {...defaultProps} />);

      expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });
  });

  describe('Form Interactions', () => {
    it('should allow selecting feedback type', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'sql_correction');

      expect(select).toHaveValue('sql_correction');
    });

    it('should show corrected SQL field when SQL correction is selected', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'sql_correction');

      expect(screen.getByLabelText(/corrected sql/i)).toBeInTheDocument();
    });

    it('should allow entering corrected SQL', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'sql_correction');

      const correctedSqlField = screen.getByLabelText(/corrected sql/i);
      await user.type(correctedSqlField, 'SELECT * FROM customers');

      expect(correctedSqlField).toHaveValue('SELECT * FROM customers');
    });

    it('should allow entering description', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Fixed table name from customer to customers');

      expect(descriptionField).toHaveValue('Fixed table name from customer to customers');
    });

    it('should allow entering notes', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const notesField = screen.getByLabelText(/additional notes/i);
      await user.type(notesField, 'The error message clearly indicated the issue');

      expect(notesField).toHaveValue('The error message clearly indicated the issue');
    });

    it('should allow adjusting confidence slider', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const slider = screen.getByRole('slider');
      await user.clear(slider);
      await user.type(slider, '85');

      expect(slider).toHaveValue('85');
    });

    it('should display confidence percentage', () => {
      render(<FeedbackModal {...defaultProps} />);

      const slider = screen.getByRole('slider');
      const confidenceValue = slider.getAttribute('value') || '100';

      expect(screen.getByText(new RegExp(`${confidenceValue}%`))).toBeInTheDocument();
    });
  });

  describe('Validation', () => {
    it('should require description field', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      // Should show validation error
      await waitFor(() => {
        expect(screen.getByText(/description is required/i)).toBeInTheDocument();
      });
    });

    it('should require corrected SQL for SQL correction type', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'sql_correction');

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Test description');

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      // Should show validation error for missing corrected SQL
      await waitFor(() => {
        expect(screen.getByText(/corrected sql is required/i)).toBeInTheDocument();
      });
    });

    it('should validate confidence is between 0 and 100', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const slider = screen.getByRole('slider');

      // Try setting invalid value
      fireEvent.change(slider, { target: { value: '150' } });

      // Should be clamped or show error
      expect(parseInt(slider.value)).toBeLessThanOrEqual(100);
    });

    it('should not allow empty corrected SQL for SQL correction', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'sql_correction');

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Test');

      const correctedSqlField = screen.getByLabelText(/corrected sql/i);
      await user.clear(correctedSqlField);

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      // Should prevent submission
      expect(feedbackAPI.submitFeedback).not.toHaveBeenCalled();
    });
  });

  describe('Submission', () => {
    it('should submit valid feedback', async () => {
      const user = userEvent.setup();
      (feedbackAPI.submitFeedback as jest.Mock).mockResolvedValue({
        id: 1,
        query_id: 123,
        feedback_type: 'sql_correction',
        corrected_sql: 'SELECT * FROM customers',
        user_confidence: 0.95,
      });

      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'sql_correction');

      const correctedSqlField = screen.getByLabelText(/corrected sql/i);
      await user.type(correctedSqlField, 'SELECT * FROM customers');

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Fixed table name');

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(feedbackAPI.submitFeedback).toHaveBeenCalledWith({
          query_id: 123,
          feedback_type: 'sql_correction',
          corrected_sql: 'SELECT * FROM customers',
          correction_description: 'Fixed table name',
          user_notes: '',
          user_confidence: 1.0, // Default value
        });
      });
    });

    it('should call onSuccess after successful submission', async () => {
      const user = userEvent.setup();
      (feedbackAPI.submitFeedback as jest.Mock).mockResolvedValue({
        id: 1,
        applied_successfully: true,
      });

      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'sql_correction');

      const correctedSqlField = screen.getByLabelText(/corrected sql/i);
      await user.type(correctedSqlField, 'SELECT * FROM customers');

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Fixed table name');

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });

    it('should close modal after successful submission', async () => {
      const user = userEvent.setup();
      (feedbackAPI.submitFeedback as jest.Mock).mockResolvedValue({ id: 1 });

      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'sql_correction');

      const correctedSqlField = screen.getByLabelText(/corrected sql/i);
      await user.type(correctedSqlField, 'SELECT * FROM customers');

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Fixed table name');

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalled();
      });
    });

    it('should submit with custom confidence value', async () => {
      const user = userEvent.setup();
      (feedbackAPI.submitFeedback as jest.Mock).mockResolvedValue({ id: 1 });

      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'column_name');

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Column name issue');

      const slider = screen.getByRole('slider');
      await user.clear(slider);
      await user.type(slider, '75');

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(feedbackAPI.submitFeedback).toHaveBeenCalledWith(
          expect.objectContaining({
            user_confidence: 0.75,
          })
        );
      });
    });

    it('should submit metadata correction with details', async () => {
      const user = userEvent.setup();
      (feedbackAPI.submitFeedback as jest.Mock).mockResolvedValue({ id: 1 });

      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'table_name');

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Table should be customers not customer');

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(feedbackAPI.submitFeedback).toHaveBeenCalled();
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error message on submission failure', async () => {
      const user = userEvent.setup();
      (feedbackAPI.submitFeedback as jest.Mock).mockRejectedValue(
        new Error('Network error')
      );

      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'result_issue');

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Results are wrong');

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
      });
    });

    it('should not close modal on submission failure', async () => {
      const user = userEvent.setup();
      (feedbackAPI.submitFeedback as jest.Mock).mockRejectedValue(
        new Error('Validation failed')
      );

      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'sql_correction');

      const correctedSqlField = screen.getByLabelText(/corrected sql/i);
      await user.type(correctedSqlField, 'INVALID SQL');

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Test');

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
      });

      // Modal should still be visible
      expect(screen.getByText(/submit feedback/i)).toBeInTheDocument();
    });

    it('should allow retry after error', async () => {
      const user = userEvent.setup();
      (feedbackAPI.submitFeedback as jest.Mock)
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({ id: 1 });

      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'result_issue');

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Test');

      const submitButton = screen.getByRole('button', { name: /submit/i });

      // First attempt - fails
      await user.click(submitButton);
      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
      });

      // Second attempt - succeeds
      await user.click(submitButton);
      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });
  });

  describe('Cancel Interaction', () => {
    it('should close modal when cancel is clicked', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('should not submit when cancel is clicked', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Some feedback');

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(feedbackAPI.submitFeedback).not.toHaveBeenCalled();
    });

    it('should reset form when closed and reopened', async () => {
      const user = userEvent.setup();
      const { rerender } = render(<FeedbackModal {...defaultProps} />);

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Test feedback');

      // Close modal
      rerender(<FeedbackModal {...defaultProps} isOpen={false} />);

      // Reopen modal
      rerender(<FeedbackModal {...defaultProps} isOpen={true} />);

      const newDescriptionField = screen.getByLabelText(/description/i);
      expect(newDescriptionField).toHaveValue('');
    });
  });

  describe('Loading States', () => {
    it('should disable submit button while submitting', async () => {
      const user = userEvent.setup();
      (feedbackAPI.submitFeedback as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ id: 1 }), 1000))
      );

      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'result_issue');

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Test');

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      // Button should be disabled during submission
      expect(submitButton).toBeDisabled();
    });

    it('should show loading indicator while submitting', async () => {
      const user = userEvent.setup();
      (feedbackAPI.submitFeedback as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ id: 1 }), 1000))
      );

      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'result_issue');

      const descriptionField = screen.getByLabelText(/description/i);
      await user.type(descriptionField, 'Test');

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      // Should show loading text or spinner
      expect(screen.getByText(/submitting/i) || screen.getByRole('status')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<FeedbackModal {...defaultProps} />);

      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByLabelText(/feedback type/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    });

    it('should allow keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      // Tab through form elements
      await user.tab();
      expect(screen.getByRole('combobox')).toHaveFocus();

      await user.tab();
      expect(screen.getByLabelText(/description/i)).toHaveFocus();
    });

    it('should support ESC key to close', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      await user.keyboard('{Escape}');

      expect(mockOnClose).toHaveBeenCalled();
    });
  });
});
