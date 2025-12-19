/**
 * CombinedExportDropdown Component Tests
 *
 * Tests for the combined multi-database export dropdown
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { CombinedExportDropdown } from '../src/components/visualization/CombinedExportDropdown';
import type { DatabaseResultForExport } from '../src/utils/exportUtils';

// Mock the export utilities
vi.mock('../src/utils/exportUtils', async () => {
  const actual = await vi.importActual('../src/utils/exportUtils');
  return {
    ...actual,
    exportCombinedCSV: vi.fn(),
    exportCombinedJSON: vi.fn(),
    exportSeparateFiles: vi.fn().mockResolvedValue(undefined),
  };
});

describe('CombinedExportDropdown', () => {
  const mockResults: DatabaseResultForExport[] = [
    {
      connection_id: 1,
      connection_name: 'Production DB',
      database_type: 'postgresql',
      results: [
        { name: 'Alice', sales: 100 },
        { name: 'Bob', sales: 200 },
      ],
      success: true,
      sql: 'SELECT * FROM users',
    },
    {
      connection_id: 2,
      connection_name: 'Staging DB',
      database_type: 'mysql',
      results: [
        { name: 'Charlie', sales: 150 },
      ],
      success: true,
      sql: 'SELECT * FROM users',
    },
  ];

  const emptyResults: DatabaseResultForExport[] = [
    {
      connection_id: 1,
      connection_name: 'Empty DB',
      database_type: 'postgresql',
      results: [],
      success: true,
      sql: 'SELECT * FROM users',
    },
  ];

  const failedResults: DatabaseResultForExport[] = [
    {
      connection_id: 1,
      connection_name: 'Failed DB',
      database_type: 'postgresql',
      results: null,
      success: false,
      sql: 'SELECT * FROM users',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders export button', () => {
    render(<CombinedExportDropdown results={mockResults} />);
    expect(screen.getByText('Export All')).toBeInTheDocument();
  });

  it('disables button when no data', () => {
    render(<CombinedExportDropdown results={emptyResults} />);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('disables button when all results failed', () => {
    render(<CombinedExportDropdown results={failedResults} />);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('disables button when disabled prop is true', () => {
    render(<CombinedExportDropdown results={mockResults} disabled={true} />);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('opens dropdown on click', () => {
    render(<CombinedExportDropdown results={mockResults} />);

    fireEvent.click(screen.getByText('Export All'));

    expect(screen.getByText(/Export as CSV/)).toBeInTheDocument();
    expect(screen.getByText(/Export as JSON/)).toBeInTheDocument();
  });

  it('shows row count and database count in dropdown', () => {
    render(<CombinedExportDropdown results={mockResults} />);

    fireEvent.click(screen.getByText('Export All'));

    expect(screen.getByText(/3 rows from 2 databases/)).toBeInTheDocument();
  });

  it('shows singular form for 1 row', () => {
    const singleRowResults: DatabaseResultForExport[] = [
      {
        connection_id: 1,
        connection_name: 'DB1',
        database_type: 'postgresql',
        results: [{ name: 'Alice' }],
        success: true,
        sql: 'SELECT',
      },
      {
        connection_id: 2,
        connection_name: 'DB2',
        database_type: 'mysql',
        results: [],
        success: true,
        sql: 'SELECT',
      },
    ];

    render(<CombinedExportDropdown results={singleRowResults} />);

    fireEvent.click(screen.getByText('Export All'));

    expect(screen.getByText(/1 row from 1 database/)).toBeInTheDocument();
  });

  it('has stacked mode selected by default', () => {
    render(<CombinedExportDropdown results={mockResults} />);

    fireEvent.click(screen.getByText('Export All'));

    const stackedRadio = screen.getByLabelText(/Stacked/);
    expect(stackedRadio).toBeChecked();
  });

  it('can switch to separate files mode', () => {
    render(<CombinedExportDropdown results={mockResults} />);

    fireEvent.click(screen.getByText('Export All'));
    fireEvent.click(screen.getByLabelText(/Separate Files/));

    const separateRadio = screen.getByLabelText(/Separate Files/);
    expect(separateRadio).toBeChecked();
  });

  it('shows mode description', () => {
    render(<CombinedExportDropdown results={mockResults} />);

    fireEvent.click(screen.getByText('Export All'));

    expect(screen.getByText(/All rows combined in one file/)).toBeInTheDocument();
  });

  it('updates mode description when switching', () => {
    render(<CombinedExportDropdown results={mockResults} />);

    fireEvent.click(screen.getByText('Export All'));
    fireEvent.click(screen.getByLabelText(/Separate Files/));

    expect(screen.getByText(/One file per database in a ZIP/)).toBeInTheDocument();
  });

  it('closes dropdown when clicking outside', () => {
    render(
      <div>
        <CombinedExportDropdown results={mockResults} />
        <button>Outside</button>
      </div>
    );

    // Open dropdown
    fireEvent.click(screen.getByText('Export All'));
    expect(screen.getByText(/Export as CSV/)).toBeInTheDocument();

    // Click outside
    fireEvent.mouseDown(screen.getByText('Outside'));

    // Dropdown should close
    expect(screen.queryByText(/Export as CSV/)).not.toBeInTheDocument();
  });

  it('closes dropdown after export action', async () => {
    const { exportCombinedCSV } = await import('../src/utils/exportUtils');

    render(<CombinedExportDropdown results={mockResults} />);

    fireEvent.click(screen.getByText('Export All'));
    fireEvent.click(screen.getByText(/Export as CSV/));

    expect(exportCombinedCSV).toHaveBeenCalledWith(mockResults);
    expect(screen.queryByText(/Export as JSON/)).not.toBeInTheDocument();
  });

  it('calls exportCombinedCSV in stacked mode', async () => {
    const { exportCombinedCSV } = await import('../src/utils/exportUtils');

    render(<CombinedExportDropdown results={mockResults} />);

    fireEvent.click(screen.getByText('Export All'));
    fireEvent.click(screen.getByText(/Export as CSV/));

    expect(exportCombinedCSV).toHaveBeenCalledWith(mockResults);
  });

  it('calls exportCombinedJSON in stacked mode', async () => {
    const { exportCombinedJSON } = await import('../src/utils/exportUtils');

    render(<CombinedExportDropdown results={mockResults} question="Test question" />);

    fireEvent.click(screen.getByText('Export All'));
    fireEvent.click(screen.getByText(/Export as JSON/));

    expect(exportCombinedJSON).toHaveBeenCalledWith(mockResults, 'Test question');
  });

  it('calls exportSeparateFiles for CSV in separate mode', async () => {
    const { exportSeparateFiles } = await import('../src/utils/exportUtils');

    render(<CombinedExportDropdown results={mockResults} />);

    fireEvent.click(screen.getByText('Export All'));
    fireEvent.click(screen.getByLabelText(/Separate Files/));
    fireEvent.click(screen.getByText(/Export as CSV/));

    expect(exportSeparateFiles).toHaveBeenCalledWith(mockResults, 'csv');
  });

  it('calls exportSeparateFiles for JSON in separate mode', async () => {
    const { exportSeparateFiles } = await import('../src/utils/exportUtils');

    render(<CombinedExportDropdown results={mockResults} />);

    fireEvent.click(screen.getByText('Export All'));
    fireEvent.click(screen.getByLabelText(/Separate Files/));
    fireEvent.click(screen.getByText(/Export as JSON/));

    expect(exportSeparateFiles).toHaveBeenCalledWith(mockResults, 'json');
  });
});
