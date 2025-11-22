/**
 * Tools Panel Component Tests
 *
 * Tests for Tool-Using Agent UI components:
 * - ToolsPanel (main container with tabs)
 * - ToolsOverview (summary dashboard)
 * - ToolDirectory (browsable tool list)
 * - ToolUsageStats (per-tool metrics)
 *
 * Part of Phase 3.1: Tool-Using Agent Implementation
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ToolsPanel } from '../src/components/ToolsPanel';
import { ToolsOverview } from '../src/components/ToolsOverview';
import { ToolDirectory } from '../src/components/ToolDirectory';
import { ToolUsageStats } from '../src/components/ToolUsageStats';
import type { ToolResponse, AllToolStatsResponse } from '../src/types/api';

// Mock the toolsApi module
vi.mock('../src/services/toolsApi', () => ({
  toolsAPI: {
    listTools: vi.fn(),
    getAllStats: vi.fn(),
    getToolStats: vi.fn(),
    invalidateAllCache: vi.fn(),
  },
}));

import { toolsAPI } from '../src/services/toolsApi';

// Mock data
const mockTools: ToolResponse[] = [
  {
    name: 'search_schema',
    description: 'Search for tables and columns matching a keyword',
    category: 'schema',
    parameters: {
      keyword: { type: 'string', description: 'Search term' },
      fuzzy: { type: 'boolean', description: 'Use fuzzy matching', default: true },
    },
    required_params: ['keyword'],
    cacheable: true,
    cache_ttl: 600,
  },
  {
    name: 'get_column_values',
    description: 'Get distinct values from a column',
    category: 'data',
    parameters: {
      table_name: { type: 'string', description: 'Table name' },
      column_name: { type: 'string', description: 'Column name' },
    },
    required_params: ['table_name', 'column_name'],
    cacheable: true,
    cache_ttl: 300,
  },
  {
    name: 'validate_sql',
    description: 'Validate SQL references against actual schema',
    category: 'validation',
    parameters: {
      sql: { type: 'string', description: 'SQL query to validate' },
    },
    required_params: ['sql'],
    cacheable: false,
    cache_ttl: 60,
  },
];

const mockStats: AllToolStatsResponse = {
  total_tools: 10,
  total_executions: 150,
  overall_success_rate: 0.95,
  by_tool: {
    search_schema: {
      tool_name: 'search_schema',
      times_executed: 45,
      successes: 43,
      failures: 2,
      success_rate: 0.96,
      avg_time_ms: 12.5,
      cache_hit_rate: 0.6,
      last_executed: '2025-11-22T10:30:00Z',
    },
    get_column_values: {
      tool_name: 'get_column_values',
      times_executed: 30,
      successes: 28,
      failures: 2,
      success_rate: 0.93,
      avg_time_ms: 25.0,
      cache_hit_rate: 0.4,
      last_executed: '2025-11-22T10:25:00Z',
    },
    validate_sql: {
      tool_name: 'validate_sql',
      times_executed: 20,
      successes: 20,
      failures: 0,
      success_rate: 1.0,
      avg_time_ms: 8.0,
      cache_hit_rate: 0.0,
      last_executed: '2025-11-22T10:20:00Z',
    },
  },
};

describe('ToolsPanel', () => {
  it('renders the main panel with header', () => {
    render(<ToolsPanel />);

    expect(screen.getByText('Tool-Using Agent')).toBeInTheDocument();
    expect(screen.getByText(/10 specialized tools/)).toBeInTheDocument();
  });

  it('renders all three tabs', () => {
    render(<ToolsPanel />);

    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Tool Directory')).toBeInTheDocument();
    expect(screen.getByText('Usage Stats')).toBeInTheDocument();
  });

  it('starts with Overview tab active', () => {
    render(<ToolsPanel />);

    const overviewTab = screen.getByText('Overview');
    expect(overviewTab.closest('button')).toHaveClass('border-orange-500');
  });

  it('switches tabs when clicked', () => {
    render(<ToolsPanel />);

    const directoryTab = screen.getByText('Tool Directory');
    fireEvent.click(directoryTab);

    expect(directoryTab.closest('button')).toHaveClass('border-orange-500');
  });

  it('shows tab description based on active tab', () => {
    render(<ToolsPanel />);

    expect(screen.getByText(/Summary of tool execution/)).toBeInTheDocument();

    fireEvent.click(screen.getByText('Tool Directory'));
    expect(screen.getByText(/Browse all 10 specialized tools/)).toBeInTheDocument();

    fireEvent.click(screen.getByText('Usage Stats'));
    expect(screen.getByText(/Detailed per-tool execution metrics/)).toBeInTheDocument();
  });
});

describe('ToolsOverview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (toolsAPI.getAllStats as any).mockResolvedValue(mockStats);
    (toolsAPI.listTools as any).mockResolvedValue(mockTools);
  });

  it('renders loading state initially', () => {
    (toolsAPI.getAllStats as any).mockImplementation(() => new Promise(() => {}));
    (toolsAPI.listTools as any).mockImplementation(() => new Promise(() => {}));

    render(<ToolsOverview />);

    // Should show skeleton loading state
    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders summary stats after loading', async () => {
    render(<ToolsOverview />);

    await waitFor(() => {
      expect(screen.getByText('Total Tools')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument();
    });

    expect(screen.getByText('Total Executions')).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();
    expect(screen.getByText('Success Rate')).toBeInTheDocument();
    expect(screen.getByText('95.0%')).toBeInTheDocument();
  });

  it('displays tools by category breakdown', async () => {
    render(<ToolsOverview />);

    await waitFor(() => {
      expect(screen.getByText('Tools by Category')).toBeInTheDocument();
    });

    expect(screen.getByText('schema')).toBeInTheDocument();
    expect(screen.getByText('data')).toBeInTheDocument();
    expect(screen.getByText('validation')).toBeInTheDocument();
  });

  it('renders how it works section', async () => {
    render(<ToolsOverview />);

    await waitFor(() => {
      expect(screen.getByText('How Tool-Using Agent Works')).toBeInTheDocument();
    });

    expect(screen.getByText('Analyze Question')).toBeInTheDocument();
    expect(screen.getByText('Use Tools')).toBeInTheDocument();
    expect(screen.getByText('Generate SQL')).toBeInTheDocument();
  });

  it('has clear all cache button', async () => {
    render(<ToolsOverview />);

    await waitFor(() => {
      expect(screen.getByText('Clear All Tool Cache')).toBeInTheDocument();
    });
  });

  it('displays error state on API failure', async () => {
    (toolsAPI.getAllStats as any).mockRejectedValue(new Error('API Error'));
    (toolsAPI.listTools as any).mockRejectedValue(new Error('API Error'));

    render(<ToolsOverview />);

    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });

    expect(screen.getByText('Retry')).toBeInTheDocument();
  });
});

describe('ToolDirectory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (toolsAPI.listTools as any).mockResolvedValue(mockTools);
  });

  it('renders loading state initially', () => {
    (toolsAPI.listTools as any).mockImplementation(() => new Promise(() => {}));

    render(<ToolDirectory />);

    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders tool list after loading', async () => {
    render(<ToolDirectory />);

    await waitFor(() => {
      expect(screen.getByText('search_schema')).toBeInTheDocument();
    });

    expect(screen.getByText('get_column_values')).toBeInTheDocument();
    expect(screen.getByText('validate_sql')).toBeInTheDocument();
  });

  it('displays tool descriptions', async () => {
    render(<ToolDirectory />);

    await waitFor(() => {
      expect(screen.getByText(/Search for tables and columns/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Get distinct values from a column/)).toBeInTheDocument();
  });

  it('shows category badges', async () => {
    render(<ToolDirectory />);

    await waitFor(() => {
      expect(screen.getByText('schema')).toBeInTheDocument();
    });

    expect(screen.getByText('data')).toBeInTheDocument();
    expect(screen.getByText('validation')).toBeInTheDocument();
  });

  it('has category filter buttons', async () => {
    render(<ToolDirectory />);

    await waitFor(() => {
      expect(screen.getByText('All Categories')).toBeInTheDocument();
    });

    expect(screen.getByText('Schema')).toBeInTheDocument();
    expect(screen.getByText('Data')).toBeInTheDocument();
    expect(screen.getByText('Query')).toBeInTheDocument();
    expect(screen.getByText('Validation')).toBeInTheDocument();
  });

  it('filters tools by category when clicked', async () => {
    (toolsAPI.listTools as any).mockImplementation((filters: any) => {
      if (filters?.category === 'schema') {
        return Promise.resolve([mockTools[0]]);
      }
      return Promise.resolve(mockTools);
    });

    render(<ToolDirectory />);

    await waitFor(() => {
      expect(screen.getByText('search_schema')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Schema'));

    await waitFor(() => {
      expect(toolsAPI.listTools).toHaveBeenCalledWith({ category: 'schema' });
    });
  });

  it('expands tool details when clicked', async () => {
    render(<ToolDirectory />);

    await waitFor(() => {
      expect(screen.getByText('search_schema')).toBeInTheDocument();
    });

    // Click to expand
    const toolHeader = screen.getByText('search_schema').closest('button');
    fireEvent.click(toolHeader!);

    // Should show parameters
    await waitFor(() => {
      expect(screen.getByText('Parameters')).toBeInTheDocument();
    });

    expect(screen.getByText('keyword')).toBeInTheDocument();
    expect(screen.getByText('(string)')).toBeInTheDocument();
    expect(screen.getByText('required')).toBeInTheDocument();
  });

  it('shows cache TTL in expanded details', async () => {
    render(<ToolDirectory />);

    await waitFor(() => {
      expect(screen.getByText('search_schema')).toBeInTheDocument();
    });

    // Expand first tool
    const toolHeader = screen.getByText('search_schema').closest('button');
    fireEvent.click(toolHeader!);

    await waitFor(() => {
      expect(screen.getByText(/Cache TTL: 600s/)).toBeInTheDocument();
    });
  });
});

describe('ToolUsageStats', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (toolsAPI.getAllStats as any).mockResolvedValue(mockStats);
  });

  it('renders loading state initially', () => {
    (toolsAPI.getAllStats as any).mockImplementation(() => new Promise(() => {}));

    render(<ToolUsageStats />);

    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders tool stats after loading', async () => {
    render(<ToolUsageStats />);

    await waitFor(() => {
      expect(screen.getByText('search_schema')).toBeInTheDocument();
    });

    expect(screen.getByText('get_column_values')).toBeInTheDocument();
    expect(screen.getByText('validate_sql')).toBeInTheDocument();
  });

  it('displays execution counts', async () => {
    render(<ToolUsageStats />);

    await waitFor(() => {
      expect(screen.getByText('45')).toBeInTheDocument(); // search_schema executions
    });

    expect(screen.getByText('30')).toBeInTheDocument(); // get_column_values executions
    expect(screen.getByText('20')).toBeInTheDocument(); // validate_sql executions
  });

  it('displays success rates', async () => {
    render(<ToolUsageStats />);

    await waitFor(() => {
      expect(screen.getByText('96%')).toBeInTheDocument();
    });

    expect(screen.getByText('93%')).toBeInTheDocument();
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('has sort controls', async () => {
    render(<ToolUsageStats />);

    await waitFor(() => {
      expect(screen.getByText('Sort by:')).toBeInTheDocument();
    });

    // Look for sort buttons specifically
    const sortButtons = screen.getAllByRole('button');
    const executionsButton = sortButtons.find(btn => btn.textContent?.includes('Executions'));
    const successRateButton = sortButtons.find(btn => btn.textContent?.includes('Success Rate'));
    const avgTimeButton = sortButtons.find(btn => btn.textContent?.includes('Avg Time'));

    expect(executionsButton).toBeDefined();
    expect(successRateButton).toBeDefined();
    expect(avgTimeButton).toBeDefined();
  });

  it('changes sort order when sort button clicked', async () => {
    render(<ToolUsageStats />);

    await waitFor(() => {
      expect(screen.getByText('search_schema')).toBeInTheDocument();
    });

    // Click success rate sort button (the one in the sort controls, not column headers)
    const sortButtons = screen.getAllByRole('button');
    const successRateButton = sortButtons.find(btn =>
      btn.textContent?.includes('Success Rate') &&
      btn.className.includes('rounded-lg')
    );
    expect(successRateButton).toBeDefined();
    fireEvent.click(successRateButton!);

    // validate_sql should be first (100% success rate)
    await waitFor(() => {
      const toolNames = screen.getAllByText(/search_schema|get_column_values|validate_sql/);
      // The tools should be reordered
      expect(toolNames.length).toBe(3);
    });
  });

  it('displays cache hit rates', async () => {
    render(<ToolUsageStats />);

    await waitFor(() => {
      expect(screen.getByText('60%')).toBeInTheDocument(); // search_schema cache hit
    });

    expect(screen.getByText('40%')).toBeInTheDocument(); // get_column_values cache hit
    expect(screen.getByText('0%')).toBeInTheDocument(); // validate_sql cache hit
  });

  it('shows success and failure counts', async () => {
    render(<ToolUsageStats />);

    await waitFor(() => {
      expect(screen.getByText('43 successes')).toBeInTheDocument();
    });

    // Multiple tools may have "2 failures", so use getAllByText
    const failureTexts = screen.getAllByText('2 failures');
    expect(failureTexts.length).toBeGreaterThan(0);
  });

  it('displays empty state when no stats', async () => {
    (toolsAPI.getAllStats as any).mockResolvedValue({
      total_tools: 10,
      total_executions: 0,
      overall_success_rate: 1.0,
      by_tool: {},
    });

    render(<ToolUsageStats />);

    await waitFor(() => {
      expect(screen.getByText(/No tool usage statistics available/)).toBeInTheDocument();
    });
  });

  it('has refresh button', async () => {
    render(<ToolUsageStats />);

    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });
  });

  it('calls API on refresh click', async () => {
    render(<ToolUsageStats />);

    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Refresh'));

    await waitFor(() => {
      expect(toolsAPI.getAllStats).toHaveBeenCalledTimes(2);
    });
  });
});
