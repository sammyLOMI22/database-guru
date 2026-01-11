/**
 * Semantic Cache Panel Component Tests
 *
 * Tests for Semantic Caching UI components:
 * - SemanticCachePanel (main container with tabs)
 * - CacheOverview (summary dashboard)
 * - CacheStatistics (hit rate distribution)
 * - RecentCachedQueries (query browser)
 * - QueryResults cache badge
 *
 * Part of Phase 3.3: Semantic Caching UI Components
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SemanticCachePanel } from '../src/components/SemanticCachePanel';
import { CacheOverview } from '../src/components/CacheOverview';
import { CacheStatistics } from '../src/components/CacheStatistics';
import { RecentCachedQueries } from '../src/components/RecentCachedQueries';
import QueryResults from '../src/components/QueryResults';
import type { CacheStatsResponse, RecentQueriesResponse } from '../src/services/cacheApi';

// Mock the cacheApi module
vi.mock('../src/services/cacheApi', () => ({
  cacheAPI: {
    getStats: vi.fn(),
    getRecentQueries: vi.fn(),
    clearSemanticCache: vi.fn(),
    clearLLMCache: vi.fn(),
    clearAllCaches: vi.fn(),
    clearConnectionCache: vi.fn(),
  },
}));

import { cacheAPI } from '../src/services/cacheApi';

// Mock data
const mockStats: CacheStatsResponse = {
  semantic_cache: {
    total_lookups: 100,
    total_hits: 50,
    exact_hits: 20,
    semantic_hits: 30,
    misses: 50,
    hit_rate_percent: 50.0,
    semantic_hit_rate_percent: 30.0,
    total_stores: 60,
    similarity_threshold: 0.85,
    ttl_seconds: 86400,
    memory_entries: 25,
  },
  llm_cache: {
    total_lookups: 80,
    hits: 45,
    misses: 35,
    hit_rate_percent: 56.25,
    total_stores: 50,
    similarity_threshold: 0.88,
    ttl_seconds: 43200,
  },
  embedding_service: {
    total_requests: 200,
    cache_hits: 150,
    cache_hit_rate_percent: 75.0,
    ollama_calls: 40,
    tfidf_fallbacks: 10,
    ollama_available: true,
  },
};

const mockRecentQueries: RecentQueriesResponse = {
  queries: [
    {
      question: 'Show me all customers from California',
      sql: "SELECT * FROM customers WHERE state = 'CA'",
      connection_id: 1,
      database_type: 'postgresql',
      created_at: '2025-11-22T10:00:00',
      hits: 5,
      last_hit_at: '2025-11-22T11:00:00',
    },
    {
      question: 'List all orders',
      sql: 'SELECT * FROM orders',
      connection_id: 1,
      database_type: 'mysql',
      created_at: '2025-11-22T09:00:00',
      hits: 2,
      last_hit_at: null,
    },
  ],
  total: 2,
};

// ============================================================================
// SemanticCachePanel Tests
// ============================================================================

describe('SemanticCachePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (cacheAPI.getStats as ReturnType<typeof vi.fn>).mockResolvedValue(mockStats);
    (cacheAPI.getRecentQueries as ReturnType<typeof vi.fn>).mockResolvedValue(mockRecentQueries);
  });

  it('renders the panel header with title', () => {
    render(<SemanticCachePanel />);
    expect(screen.getByText('Semantic Cache')).toBeInTheDocument();
    expect(screen.getByText(/intelligent caching/i)).toBeInTheDocument();
  });

  it('renders all three tabs', () => {
    render(<SemanticCachePanel />);
    expect(screen.getByRole('button', { name: /overview/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /statistics/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /recent/i })).toBeInTheDocument();
  });

  it('shows Overview tab by default', () => {
    render(<SemanticCachePanel />);
    const overviewTab = screen.getByRole('button', { name: /overview/i });
    expect(overviewTab).toHaveClass('border-amber-500');
  });

  it('switches to Statistics tab when clicked', async () => {
    render(<SemanticCachePanel />);
    const statsTab = screen.getByRole('button', { name: /statistics/i });
    fireEvent.click(statsTab);
    await waitFor(() => {
      expect(statsTab).toHaveClass('border-amber-500');
    });
  });

  it('switches to Recent Queries tab when clicked', async () => {
    render(<SemanticCachePanel />);
    const recentTab = screen.getByRole('button', { name: /recent/i });
    fireEvent.click(recentTab);
    await waitFor(() => {
      expect(recentTab).toHaveClass('border-amber-500');
    });
  });
});

// ============================================================================
// CacheOverview Tests
// ============================================================================

describe('CacheOverview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (cacheAPI.getStats as ReturnType<typeof vi.fn>).mockResolvedValue(mockStats);
  });

  it('renders loading state initially', () => {
    render(<CacheOverview />);
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('displays cache statistics after loading', async () => {
    render(<CacheOverview />);
    await waitFor(() => {
      // Check for stats that appear after loading - look for the hit rate percentage
      expect(screen.getByText('50.0%')).toBeInTheDocument();
    });
    // Verify we're showing cached entries
    expect(screen.getByText('25')).toBeInTheDocument();
  });

  it('displays semantic hits info', async () => {
    render(<CacheOverview />);
    await waitFor(() => {
      // Look for semantic hits percentage text
      expect(screen.getByText(/30\.0% of lookups/)).toBeInTheDocument();
    });
  });

  it('displays cached entries count', async () => {
    render(<CacheOverview />);
    await waitFor(() => {
      expect(screen.getByText('Cache Size')).toBeInTheDocument();
    });
    expect(screen.getByText('25')).toBeInTheDocument();
  });

  it('shows "How Semantic Caching Works" section', async () => {
    render(<CacheOverview />);
    await waitFor(() => {
      expect(screen.getByText('How Semantic Caching Works')).toBeInTheDocument();
    });
  });

  it('displays quick action buttons', async () => {
    render(<CacheOverview />);
    await waitFor(() => {
      expect(screen.getByText('Clear Semantic Cache')).toBeInTheDocument();
    });
    expect(screen.getByText('Clear LLM Cache')).toBeInTheDocument();
    expect(screen.getByText('Clear All Caches')).toBeInTheDocument();
  });

  it('calls clearSemanticCache when button clicked', async () => {
    (cacheAPI.clearSemanticCache as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'Cleared',
      entries_cleared: 25,
    });
    window.confirm = vi.fn(() => true);

    render(<CacheOverview />);
    await waitFor(() => {
      expect(screen.getByText('Clear Semantic Cache')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Clear Semantic Cache'));
    await waitFor(() => {
      expect(cacheAPI.clearSemanticCache).toHaveBeenCalled();
    });
  });

  it('shows embedding service status as Online', async () => {
    render(<CacheOverview />);
    // First wait for stats to load (indicated by hit rate showing)
    await waitFor(() => {
      expect(screen.getByText('50.0%')).toBeInTheDocument();
    });
    // Now check for Online status (ollama_available: true in mockStats)
    // There are multiple "Online" elements on the page
    const onlineElements = screen.getAllByText('Online');
    expect(onlineElements.length).toBeGreaterThan(0);
  });

  it('handles error state', async () => {
    (cacheAPI.getStats as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Failed'));
    render(<CacheOverview />);
    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
    expect(screen.getByText('Retry Connection')).toBeInTheDocument();
  });
});

// ============================================================================
// CacheStatistics Tests
// ============================================================================

describe('CacheStatistics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (cacheAPI.getStats as ReturnType<typeof vi.fn>).mockResolvedValue(mockStats);
  });

  it('renders loading state initially', () => {
    render(<CacheStatistics />);
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('displays hit type distribution', async () => {
    render(<CacheStatistics />);
    await waitFor(() => {
      expect(screen.getByText('Hit Type Distribution')).toBeInTheDocument();
    });
    expect(screen.getByText('Exact Hits')).toBeInTheDocument();
    expect(screen.getByText('Semantic Hits')).toBeInTheDocument();
    expect(screen.getByText('Cache Misses')).toBeInTheDocument();
  });

  it('displays LLM cache statistics', async () => {
    render(<CacheStatistics />);
    await waitFor(() => {
      expect(screen.getByText('LLM Response Cache')).toBeInTheDocument();
    });
  });

  it('displays embedding service efficiency', async () => {
    render(<CacheStatistics />);
    await waitFor(() => {
      expect(screen.getByText('Embedding Service Efficiency')).toBeInTheDocument();
    });
  });

  it('shows estimated performance impact', async () => {
    render(<CacheStatistics />);
    await waitFor(() => {
      expect(screen.getByText('Estimated Performance Impact')).toBeInTheDocument();
    });
  });

  it('shows refresh button', async () => {
    render(<CacheStatistics />);
    await waitFor(() => {
      expect(screen.getByText('Refresh Statistics')).toBeInTheDocument();
    });
  });
});

// ============================================================================
// RecentCachedQueries Tests
// ============================================================================

describe('RecentCachedQueries', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (cacheAPI.getRecentQueries as ReturnType<typeof vi.fn>).mockResolvedValue(mockRecentQueries);
  });

  it('renders loading state initially', () => {
    render(<RecentCachedQueries />);
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('displays cached queries after loading', async () => {
    render(<RecentCachedQueries />);
    await waitFor(() => {
      expect(screen.getByText('Show me all customers from California')).toBeInTheDocument();
    });
    expect(screen.getByText('List all orders')).toBeInTheDocument();
  });

  it('shows query count', async () => {
    render(<RecentCachedQueries />);
    await waitFor(() => {
      expect(screen.getByText(/showing 2 of 2/i)).toBeInTheDocument();
    });
  });

  it('displays database type badges', async () => {
    render(<RecentCachedQueries />);
    await waitFor(() => {
      expect(screen.getByText('postgresql')).toBeInTheDocument();
    });
    expect(screen.getByText('mysql')).toBeInTheDocument();
  });

  it('shows hit count for queries', async () => {
    render(<RecentCachedQueries />);
    await waitFor(() => {
      expect(screen.getByText('5 hits')).toBeInTheDocument();
    });
    expect(screen.getByText('2 hits')).toBeInTheDocument();
  });

  it('expands SQL when View SQL clicked', async () => {
    render(<RecentCachedQueries />);
    await waitFor(() => {
      expect(screen.getAllByText('View SQL')[0]).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByText('View SQL')[0]);
    await waitFor(() => {
      expect(screen.getByText(/SELECT \* FROM customers/)).toBeInTheDocument();
    });
  });

  it('shows empty state when no queries', async () => {
    (cacheAPI.getRecentQueries as ReturnType<typeof vi.fn>).mockResolvedValue({
      queries: [],
      total: 0,
    });

    render(<RecentCachedQueries />);
    await waitFor(() => {
      expect(screen.getByText('No cached queries yet')).toBeInTheDocument();
    });
  });

  it('has page size selector', async () => {
    render(<RecentCachedQueries />);
    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });
  });
});

// ============================================================================
// QueryResults Cache Badge Tests
// ============================================================================

describe('QueryResults Cache Badge', () => {
  const baseProps = {
    sql: 'SELECT * FROM customers',
    results: [{ id: 1, name: 'Test' }],
    rowCount: 1,
    executionTime: 10,
    isValid: true,
    warnings: [],
  };

  it('does not show cache badge when no cache type', () => {
    render(<QueryResults {...baseProps} />);
    expect(screen.queryByText('Cache Hit')).not.toBeInTheDocument();
    expect(screen.queryByText('Instant Response')).not.toBeInTheDocument();
  });

  it('shows exact cache hit badge', () => {
    render(<QueryResults {...baseProps} cacheType="exact" />);
    expect(screen.getByText('Exact Cache Hit')).toBeInTheDocument();
    expect(screen.getByText('Instant Response')).toBeInTheDocument();
  });

  it('shows semantic cache hit badge with similarity', () => {
    render(
      <QueryResults
        {...baseProps}
        cacheType="semantic"
        semanticSimilarity={0.92}
      />
    );
    expect(screen.getByText('Semantic Cache Hit')).toBeInTheDocument();
    expect(screen.getByText('(92% match)')).toBeInTheDocument();
  });

  it('shows matched question for semantic hits', () => {
    render(
      <QueryResults
        {...baseProps}
        cacheType="semantic"
        semanticSimilarity={0.88}
        matchedQuestion="Show customers in CA"
      />
    );
    expect(screen.getByText(/Matched:/)).toBeInTheDocument();
    expect(screen.getByText(/"Show customers in CA"/)).toBeInTheDocument();
  });

  it('uses green styling for exact hits', () => {
    const { container } = render(<QueryResults {...baseProps} cacheType="exact" />);
    // Find the badge container with green styling
    const greenBadge = container.querySelector('.bg-green-50');
    expect(greenBadge).toBeInTheDocument();
  });

  it('uses amber styling for semantic hits', () => {
    const { container } = render(<QueryResults {...baseProps} cacheType="semantic" semanticSimilarity={0.9} />);
    // Find the badge container with amber styling
    const amberBadge = container.querySelector('.bg-amber-50');
    expect(amberBadge).toBeInTheDocument();
  });
});
