/**
 * Tests for FeedbackModal component
 *
 * Testing the actual component that exists in production
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { FeedbackModal } from '../src/components/FeedbackModal';

// Mock SQLEditor component since it's complex
vi.mock('../src/components/SQLEditor', () => ({
  SQLEditor: ({ initialSQL, onChange, readOnly, label }: any) => (
    <div data-testid={readOnly ? 'sql-editor-readonly' : 'sql-editor-editable'}>
      <label>{label}</label>
      {!readOnly && (
        <textarea
          data-testid="sql-editor-textarea"
          value={initialSQL}
          onChange={(e) => onChange?.(e.target.value)}
        />
      )}
      {readOnly && <div data-testid="readonly-sql">{initialSQL}</div>}
    </div>
  ),
}));

describe('FeedbackModal', () => {
  const mockOnSubmit = vi.fn();
  const mockOnClose = vi.fn();
  const defaultProps = {
    queryId: 123,
    originalSQL: 'SELECT * FROM users',
    onSubmit: mockOnSubmit,
    onClose: mockOnClose,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders the modal with correct title', () => {
      render(<FeedbackModal {...defaultProps} />);
      expect(screen.getByText('Provide Feedback')).toBeInTheDocument();
    });

    it('displays the original SQL in read-only editor', () => {
      render(<FeedbackModal {...defaultProps} />);
      expect(screen.getByTestId('sql-editor-readonly')).toBeInTheDocument();
      expect(screen.getByTestId('readonly-sql')).toHaveTextContent('SELECT * FROM users');
    });

    it('shows all feedback type options', () => {
      render(<FeedbackModal {...defaultProps} />);
      const select = screen.getByRole('combobox');
      expect(select).toBeInTheDocument();

      // Check for all options
      expect(screen.getByRole('option', { name: /SQL Correction/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /Column Name Issue/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /Table Name Issue/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /Result Issue/i })).toBeInTheDocument();
    });

    it('shows description field with required marker', () => {
      render(<FeedbackModal {...defaultProps} />);
      expect(screen.getByText(/What's Wrong/i)).toBeInTheDocument();
      // Required field now uses just an asterisk (*)
      expect(screen.getByText('*')).toBeInTheDocument();
    });

    it('shows confidence slider defaulting to 100%', () => {
      render(<FeedbackModal {...defaultProps} />);
      expect(screen.getByText(/Confidence Level/i)).toBeInTheDocument();
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('shows Submit and Cancel buttons', () => {
      render(<FeedbackModal {...defaultProps} />);
      expect(screen.getByRole('button', { name: /Submit Feedback/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
    });
  });

  describe('Feedback Type Selection', () => {
    it('defaults to sql_correction type', () => {
      render(<FeedbackModal {...defaultProps} />);
      const select = screen.getByRole('combobox') as HTMLSelectElement;
      expect(select.value).toBe('sql_correction');
    });

    it('shows corrected SQL editor when sql_correction is selected', () => {
      render(<FeedbackModal {...defaultProps} />);
      expect(screen.getByTestId('sql-editor-editable')).toBeInTheDocument();
    });

    it('hides corrected SQL editor when changing to column_name', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'column_name');

      expect(screen.queryByTestId('sql-editor-editable')).not.toBeInTheDocument();
    });

    it('shows appropriate help text for each feedback type', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const select = screen.getByRole('combobox');

      // SQL Correction
      await user.selectOptions(select, 'sql_correction');
      expect(screen.getByText(/Provide a corrected version/i)).toBeInTheDocument();

      // Column Name
      await user.selectOptions(select, 'column_name');
      expect(screen.getByText(/incorrect column name/i)).toBeInTheDocument();

      // Table Name
      await user.selectOptions(select, 'table_name');
      expect(screen.getByText(/incorrect table name/i)).toBeInTheDocument();

      // Result Issue
      await user.selectOptions(select, 'result_issue');
      expect(screen.getByText(/issue with the query results/i)).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('shows error when submitting without description', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const submitButton = screen.getByRole('button', { name: /Submit Feedback/i });
      await user.click(submitButton);

      expect(await screen.findByText(/Please provide a description/i)).toBeInTheDocument();
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it('shows error when corrected SQL is same as original', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      // Add description
      const descriptionField = screen.getByPlaceholderText(/E.g.,/i);
      await user.type(descriptionField, 'Test description');

      // Submit (corrected SQL is already same as original by default)
      const submitButton = screen.getByRole('button', { name: /Submit Feedback/i });
      await user.click(submitButton);

      expect(await screen.findByText(/Corrected SQL is the same/i)).toBeInTheDocument();
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it('clears error when user starts typing in description', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      // Trigger error first
      const submitButton = screen.getByRole('button', { name: /Submit Feedback/i });
      await user.click(submitButton);
      expect(await screen.findByText(/Please provide a description/i)).toBeInTheDocument();

      // Start typing
      const descriptionField = screen.getByPlaceholderText(/E.g.,/i);
      await user.type(descriptionField, 'Fix');

      // Error should be cleared
      await waitFor(() => {
        expect(screen.queryByText(/Please provide a description/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Form Submission', () => {
    it('submits valid feedback with all fields', async () => {
      const user = userEvent.setup();
      mockOnSubmit.mockResolvedValue(undefined);

      render(<FeedbackModal {...defaultProps} />);

      // Fill out form
      const descriptionField = screen.getByPlaceholderText(/E.g.,/i);
      await user.type(descriptionField, 'Should use category_name');

      const notesField = screen.getByPlaceholderText(/additional context/i);
      await user.type(notesField, 'Additional notes here');

      // Change corrected SQL
      const sqlTextarea = screen.getByTestId('sql-editor-textarea');
      await user.clear(sqlTextarea);
      await user.type(sqlTextarea, 'SELECT * FROM customers');

      // Adjust confidence
      const slider = screen.getByRole('slider');
      fireEvent.change(slider, { target: { value: '0.8' } });

      // Submit
      const submitButton = screen.getByRole('button', { name: /Submit Feedback/i });
      await user.click(submitButton);

      // Verify submission
      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          query_id: 123,
          feedback_type: 'sql_correction',
          corrected_sql: 'SELECT * FROM customers',
          correction_description: 'Should use category_name',
          user_notes: 'Additional notes here',
          user_confidence: 0.8,
        });
      });

      // Modal should close on success
      expect(mockOnClose).toHaveBeenCalled();
    });

    it('submits column_name feedback without corrected_sql', async () => {
      const user = userEvent.setup();
      mockOnSubmit.mockResolvedValue(undefined);

      render(<FeedbackModal {...defaultProps} />);

      // Change to column_name type
      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'column_name');

      // Fill description
      const descriptionField = screen.getByPlaceholderText(/E.g.,/i);
      await user.type(descriptionField, 'Column name is wrong');

      // Submit
      const submitButton = screen.getByRole('button', { name: /Submit Feedback/i });
      await user.click(submitButton);

      // Verify - should not include corrected_sql for non-SQL corrections
      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          query_id: 123,
          feedback_type: 'column_name',
          corrected_sql: undefined,
          correction_description: 'Column name is wrong',
          user_notes: undefined,
          user_confidence: 1.0,
        });
      });
    });

    it('shows submitting state during submission', async () => {
      const user = userEvent.setup();
      let resolveSubmit: any;
      mockOnSubmit.mockReturnValue(new Promise((resolve) => { resolveSubmit = resolve; }));

      render(<FeedbackModal {...defaultProps} />);

      // Fill and submit
      const descriptionField = screen.getByPlaceholderText(/E.g.,/i);
      await user.type(descriptionField, 'Test');

      // Change SQL to avoid same-as-original error
      const sqlTextarea = screen.getByTestId('sql-editor-textarea');
      await user.clear(sqlTextarea);
      await user.type(sqlTextarea, 'SELECT * FROM customers');

      const submitButton = screen.getByRole('button', { name: /Submit Feedback/i });
      await user.click(submitButton);

      // Should show submitting state
      expect(await screen.findByText(/Submitting.../i)).toBeInTheDocument();
      expect(submitButton).toBeDisabled();

      // Resolve
      resolveSubmit();
    });

    it('shows error message when submission fails', async () => {
      const user = userEvent.setup();
      mockOnSubmit.mockRejectedValue(new Error('Network error'));

      render(<FeedbackModal {...defaultProps} />);

      // Fill and submit
      const descriptionField = screen.getByPlaceholderText(/E.g.,/i);
      await user.type(descriptionField, 'Test');

      const sqlTextarea = screen.getByTestId('sql-editor-textarea');
      await user.clear(sqlTextarea);
      await user.type(sqlTextarea, 'SELECT * FROM customers');

      const submitButton = screen.getByRole('button', { name: /Submit Feedback/i });
      await user.click(submitButton);

      // Should show error
      expect(await screen.findByText(/Network error/i)).toBeInTheDocument();
      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  describe('Modal Interactions', () => {
    it('calls onClose when Cancel button is clicked', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      await user.click(cancelButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('calls onClose when X button is clicked', async () => {
      const user = userEvent.setup();
      render(<FeedbackModal {...defaultProps} />);

      // Find the close X button (it's the first button in the header)
      const buttons = screen.getAllByRole('button');
      const closeButton = buttons.find(btn =>
        btn.querySelector('svg') &&
        btn.className.includes('text-gray-400')
      );

      expect(closeButton).toBeDefined();
      await user.click(closeButton!);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('disables buttons during submission', async () => {
      const user = userEvent.setup();
      let resolveSubmit: any;
      mockOnSubmit.mockReturnValue(new Promise((resolve) => { resolveSubmit = resolve; }));

      render(<FeedbackModal {...defaultProps} />);

      // Fill and submit
      const descriptionField = screen.getByPlaceholderText(/E.g.,/i);
      await user.type(descriptionField, 'Test');

      const sqlTextarea = screen.getByTestId('sql-editor-textarea');
      await user.clear(sqlTextarea);
      await user.type(sqlTextarea, 'SELECT * FROM customers');

      const submitButton = screen.getByRole('button', { name: /Submit Feedback/i });
      await user.click(submitButton);

      // Both buttons should be disabled
      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      expect(submitButton).toBeDisabled();
      expect(cancelButton).toBeDisabled();

      resolveSubmit();
    });
  });

  describe('Confidence Slider', () => {
    it('updates confidence percentage when slider changes', async () => {
      render(<FeedbackModal {...defaultProps} />);

      const slider = screen.getByRole('slider');

      fireEvent.change(slider, { target: { value: '0.5' } });
      expect(screen.getByText('50%')).toBeInTheDocument();

      fireEvent.change(slider, { target: { value: '0.75' } });
      expect(screen.getByText('75%')).toBeInTheDocument();

      fireEvent.change(slider, { target: { value: '0' } });
      expect(screen.getByText('0%')).toBeInTheDocument();
    });
  });
});
