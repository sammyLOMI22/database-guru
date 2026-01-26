/**
 * SortableTableHeader Component Tests
 *
 * Tests the sortable table header component with accessibility and interaction features
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { SortableTableHeader } from '../../src/components/SortableTableHeader';

describe('SortableTableHeader', () => {
  const defaultProps = {
    column: 'name',
    sortConfig: { column: null as string | null, direction: 'asc' as const },
    onSort: vi.fn(),
  };

  const renderInTable = (props: Parameters<typeof SortableTableHeader>[0]) => {
    return render(
      <table>
        <thead>
          <tr>
            <SortableTableHeader {...props} />
          </tr>
        </thead>
      </table>
    );
  };

  describe('rendering', () => {
    it('renders column name as label by default', () => {
      renderInTable(defaultProps);
      expect(screen.getByText('name')).toBeInTheDocument();
    });

    it('renders custom label when provided', () => {
      renderInTable({ ...defaultProps, label: 'Full Name' });
      expect(screen.getByText('Full Name')).toBeInTheDocument();
    });

    it('renders as a th element with columnheader role', () => {
      renderInTable(defaultProps);
      const header = screen.getByRole('columnheader');
      expect(header.tagName).toBe('TH');
    });

    it('applies custom className', () => {
      renderInTable({ ...defaultProps, className: 'custom-class' });
      const header = screen.getByRole('columnheader');
      expect(header.className).toContain('custom-class');
    });
  });

  describe('ARIA attributes', () => {
    it('has aria-sort="none" when unsorted', () => {
      renderInTable(defaultProps);
      expect(screen.getByRole('columnheader')).toHaveAttribute('aria-sort', 'none');
    });

    it('has aria-sort="ascending" when sorted ascending', () => {
      renderInTable({
        ...defaultProps,
        sortConfig: { column: 'name', direction: 'asc' },
      });
      expect(screen.getByRole('columnheader')).toHaveAttribute('aria-sort', 'ascending');
    });

    it('has aria-sort="descending" when sorted descending', () => {
      renderInTable({
        ...defaultProps,
        sortConfig: { column: 'name', direction: 'desc' },
      });
      expect(screen.getByRole('columnheader')).toHaveAttribute('aria-sort', 'descending');
    });

    it('has aria-sort="none" when different column is sorted', () => {
      renderInTable({
        ...defaultProps,
        sortConfig: { column: 'other', direction: 'asc' },
      });
      expect(screen.getByRole('columnheader')).toHaveAttribute('aria-sort', 'none');
    });
  });

  describe('click interaction', () => {
    it('calls onSort with column name when clicked', async () => {
      const onSort = vi.fn();
      const user = userEvent.setup();

      renderInTable({ ...defaultProps, onSort });
      await user.click(screen.getByRole('columnheader'));

      expect(onSort).toHaveBeenCalledWith('name');
      expect(onSort).toHaveBeenCalledTimes(1);
    });

    it('does not call onSort when disabled', async () => {
      const onSort = vi.fn();
      const user = userEvent.setup();

      renderInTable({ ...defaultProps, onSort, disabled: true });
      await user.click(screen.getByRole('columnheader'));

      expect(onSort).not.toHaveBeenCalled();
    });
  });

  describe('keyboard accessibility', () => {
    it('is focusable when enabled', () => {
      renderInTable(defaultProps);
      expect(screen.getByRole('columnheader')).toHaveAttribute('tabIndex', '0');
    });

    it('is not focusable when disabled', () => {
      renderInTable({ ...defaultProps, disabled: true });
      expect(screen.getByRole('columnheader')).toHaveAttribute('tabIndex', '-1');
    });

    it('calls onSort on Enter key', async () => {
      const onSort = vi.fn();
      const user = userEvent.setup();

      renderInTable({ ...defaultProps, onSort });
      const header = screen.getByRole('columnheader');
      header.focus();
      await user.keyboard('{Enter}');

      expect(onSort).toHaveBeenCalledWith('name');
    });

    it('calls onSort on Space key', async () => {
      const onSort = vi.fn();
      const user = userEvent.setup();

      renderInTable({ ...defaultProps, onSort });
      const header = screen.getByRole('columnheader');
      header.focus();
      await user.keyboard(' ');

      expect(onSort).toHaveBeenCalledWith('name');
    });

    it('does not call onSort on Enter when disabled', async () => {
      const onSort = vi.fn();
      const user = userEvent.setup();

      renderInTable({ ...defaultProps, onSort, disabled: true });
      const header = screen.getByRole('columnheader');
      header.focus();
      await user.keyboard('{Enter}');

      expect(onSort).not.toHaveBeenCalled();
    });

    it('does not call onSort on other keys', async () => {
      const onSort = vi.fn();
      const user = userEvent.setup();

      renderInTable({ ...defaultProps, onSort });
      const header = screen.getByRole('columnheader');
      header.focus();
      await user.keyboard('{a}');
      await user.keyboard('{Tab}');

      expect(onSort).not.toHaveBeenCalled();
    });
  });

  describe('visual styling', () => {
    it('has cursor-pointer class when enabled', () => {
      renderInTable(defaultProps);
      const header = screen.getByRole('columnheader');
      expect(header.className).toContain('cursor-pointer');
    });

    it('has cursor-default class when disabled', () => {
      renderInTable({ ...defaultProps, disabled: true });
      const header = screen.getByRole('columnheader');
      expect(header.className).toContain('cursor-default');
    });

    it('has group class for hover effects', () => {
      renderInTable(defaultProps);
      const header = screen.getByRole('columnheader');
      expect(header.className).toContain('group');
    });
  });

  describe('sort icon visibility', () => {
    it('renders sort icon container', () => {
      renderInTable({
        ...defaultProps,
        sortConfig: { column: 'name', direction: 'asc' },
      });
      // Icon should be visible (opacity-100) when active
      const header = screen.getByRole('columnheader');
      const svgIcon = header.querySelector('svg');
      expect(svgIcon).toBeInTheDocument();
    });

    it('hides sort icon when disabled', () => {
      renderInTable({
        ...defaultProps,
        sortConfig: { column: 'name', direction: 'asc' },
        disabled: true,
      });
      const header = screen.getByRole('columnheader');
      const svgIcon = header.querySelector('svg');
      // SVG elements use classList.contains() for class checking
      expect(svgIcon?.classList.contains('hidden')).toBe(true);
    });
  });
});
