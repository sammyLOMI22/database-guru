/**
 * Connection Pool Metrics Component Tests
 *
 * Basic functional tests for the ConnectionPoolMetrics dashboard component.
 * Tests rendering, data loading, and user interactions.
 *
 * Part of Connection Pooling Implementation - Day 3 Frontend Dashboard
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ConnectionPoolMetrics } from '../src/components/ConnectionPoolMetrics';

// Mock the poolsApi module
vi.mock('../src/services/poolsApi', () => ({
  poolsAPI: {
    getPoolStats: vi.fn(),
    getPoolHealth: vi.fn(),
    evictConnectionPools: vi.fn(),
  },
}));

import { poolsAPI } from '../src/services/poolsApi';

describe('ConnectionPoolMetrics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should render loading state initially', () => {
    vi.mocked(poolsAPI.getPoolStats).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );
    vi.mocked(poolsAPI.getPoolHealth).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<ConnectionPoolMetrics />);

    // Should show skeleton loading
    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('should load and display pool stats', async () => {
    vi.mocked(poolsAPI.getPoolStats).mockResolvedValue({
      total_pools: 1,
      global_metrics: {
        total_active_connections: 5,
        total_idle_connections: 10,
        avg_utilization_percent: 33.3,
      },
      pools: [{
        connection_id: 1,
        connection_name: 'Test DB',
        database_type: 'postgresql',
        metrics: {
          active_connections: 5,
          idle_connections: 10,
          total_connections: 15,
          utilization_percent: 33.3,
          pool_size: 10,
          max_overflow: 20,
          age_seconds: 1800,
          total_checkouts: 100,
          total_checkins: 95,
          total_checkout_failures: 0,
          avg_checkout_time_ms: 3.5,
          total_wait_time_ms: 50.0,
          avg_wait_time_ms: 0.5,
          max_wait_time_ms: 10.0,
        },
      }],
      pooling_enabled: true,
    });

    vi.mocked(poolsAPI.getPoolHealth).mockResolvedValue({
      pooling_enabled: true,
      status: 'healthy',
      total_pools: 1,
      warnings: [],
      unhealthy_pools: [],
      high_utilization_pools: [],
      global_metrics: {
        total_active_connections: 5,
        total_idle_connections: 10,
        avg_utilization_percent: 33.3,
      },
    });

    render(<ConnectionPoolMetrics />);

    await waitFor(() => {
      expect(poolsAPI.getPoolStats).toHaveBeenCalledTimes(1);
      expect(poolsAPI.getPoolHealth).toHaveBeenCalledTimes(1);
    });
  });

  it('should show error state when API fails', async () => {
    vi.mocked(poolsAPI.getPoolStats).mockRejectedValue(new Error('Network error'));
    vi.mocked(poolsAPI.getPoolHealth).mockRejectedValue(new Error('Network error'));

    render(<ConnectionPoolMetrics />);

    await waitFor(() => {
      const errorText = screen.queryByText(/error/i);
      expect(errorText).toBeTruthy();
    });
  });

  it('should show disabled state when pooling is off', async () => {
    vi.mocked(poolsAPI.getPoolStats).mockResolvedValue({
      total_pools: 0,
      global_metrics: {
        total_active_connections: 0,
        total_idle_connections: 0,
        avg_utilization_percent: 0,
      },
      pools: [],
      pooling_enabled: false,
    });

    vi.mocked(poolsAPI.getPoolHealth).mockResolvedValue({
      pooling_enabled: false,
      status: 'disabled',
      total_pools: 0,
      warnings: [],
      unhealthy_pools: [],
      high_utilization_pools: [],
      global_metrics: {
        total_active_connections: 0,
        total_idle_connections: 0,
        avg_utilization_percent: 0,
      },
    });

    render(<ConnectionPoolMetrics />);

    await waitFor(() => {
      const disabledText = screen.queryByText(/Connection Pooling Disabled/i);
      expect(disabledText).toBeTruthy();
    });
  });
});
