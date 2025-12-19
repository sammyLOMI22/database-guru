/**
 * Cross-Database Utilities Tests
 *
 * Tests for cross-database analysis and comparison utilities
 */

import { describe, it, expect } from 'vitest';
import {
  findCommonNumericColumns,
  aggregateByDatabase,
  detectCrossDbComparison,
  formatMetricValue,
  DatabaseResultForCrossDb,
} from '../src/utils/crossDbUtils';

describe('findCommonNumericColumns', () => {
  it('returns empty array when less than 2 databases', () => {
    const results: DatabaseResultForCrossDb[] = [
      {
        connection_id: 1,
        connection_name: 'DB1',
        database_type: 'postgresql',
        results: [{ name: 'Alice', value: 100 }],
        success: true,
      },
    ];

    expect(findCommonNumericColumns(results)).toEqual([]);
  });

  it('finds common numeric columns across databases', () => {
    const results: DatabaseResultForCrossDb[] = [
      {
        connection_id: 1,
        connection_name: 'DB1',
        database_type: 'postgresql',
        results: [{ name: 'Alice', sales: 100, revenue: 500 }],
        success: true,
      },
      {
        connection_id: 2,
        connection_name: 'DB2',
        database_type: 'mysql',
        results: [{ name: 'Bob', sales: 200, revenue: 800 }],
        success: true,
      },
    ];

    const columns = findCommonNumericColumns(results);
    expect(columns).toContain('sales');
    expect(columns).toContain('revenue');
    expect(columns).not.toContain('name');
  });

  it('excludes ID columns', () => {
    const results: DatabaseResultForCrossDb[] = [
      {
        connection_id: 1,
        connection_name: 'DB1',
        database_type: 'postgresql',
        results: [{ id: 1, user_id: 100, sales: 500 }],
        success: true,
      },
      {
        connection_id: 2,
        connection_name: 'DB2',
        database_type: 'mysql',
        results: [{ id: 2, user_id: 200, sales: 600 }],
        success: true,
      },
    ];

    const columns = findCommonNumericColumns(results);
    expect(columns).not.toContain('id');
    expect(columns).not.toContain('user_id');
    expect(columns).toContain('sales');
  });

  it('only returns columns present in ALL databases', () => {
    const results: DatabaseResultForCrossDb[] = [
      {
        connection_id: 1,
        connection_name: 'DB1',
        database_type: 'postgresql',
        results: [{ sales: 100, revenue: 500 }],
        success: true,
      },
      {
        connection_id: 2,
        connection_name: 'DB2',
        database_type: 'mysql',
        results: [{ sales: 200, profit: 300 }], // no revenue column
        success: true,
      },
    ];

    const columns = findCommonNumericColumns(results);
    expect(columns).toContain('sales');
    expect(columns).not.toContain('revenue');
    expect(columns).not.toContain('profit');
  });

  it('skips failed databases', () => {
    const results: DatabaseResultForCrossDb[] = [
      {
        connection_id: 1,
        connection_name: 'DB1',
        database_type: 'postgresql',
        results: [{ sales: 100 }],
        success: true,
      },
      {
        connection_id: 2,
        connection_name: 'DB2',
        database_type: 'mysql',
        results: null,
        success: false,
      },
    ];

    // Only 1 successful, should return empty
    expect(findCommonNumericColumns(results)).toEqual([]);
  });
});

describe('aggregateByDatabase', () => {
  const mockResults: DatabaseResultForCrossDb[] = [
    {
      connection_id: 1,
      connection_name: 'Production',
      database_type: 'postgresql',
      results: [
        { sales: 100, revenue: 500 },
        { sales: 200, revenue: 800 },
      ],
      success: true,
    },
    {
      connection_id: 2,
      connection_name: 'Staging',
      database_type: 'mysql',
      results: [
        { sales: 50, revenue: 200 },
      ],
      success: true,
    },
  ];

  it('aggregates using sum by default', () => {
    const aggregated = aggregateByDatabase(mockResults, ['sales', 'revenue']);

    expect(aggregated).toHaveLength(2);
    expect(aggregated[0].databaseName).toBe('Production');
    expect(aggregated[0].metrics.sales).toBe(300); // 100 + 200
    expect(aggregated[0].metrics.revenue).toBe(1300); // 500 + 800
    expect(aggregated[1].databaseName).toBe('Staging');
    expect(aggregated[1].metrics.sales).toBe(50);
  });

  it('aggregates using avg method', () => {
    const aggregated = aggregateByDatabase(mockResults, ['sales'], 'avg');

    expect(aggregated[0].metrics.sales).toBe(150); // (100 + 200) / 2
    expect(aggregated[1].metrics.sales).toBe(50); // 50 / 1
  });

  it('aggregates using count method', () => {
    const aggregated = aggregateByDatabase(mockResults, ['sales'], 'count');

    expect(aggregated[0].metrics.sales).toBe(2); // 2 rows
    expect(aggregated[1].metrics.sales).toBe(1); // 1 row
  });

  it('includes row count', () => {
    const aggregated = aggregateByDatabase(mockResults, ['sales']);

    expect(aggregated[0].rowCount).toBe(2);
    expect(aggregated[1].rowCount).toBe(1);
  });

  it('assigns colors to each database', () => {
    const aggregated = aggregateByDatabase(mockResults, ['sales']);

    expect(aggregated[0].color).toBeDefined();
    expect(aggregated[1].color).toBeDefined();
    expect(aggregated[0].color).not.toBe(aggregated[1].color);
  });
});

describe('detectCrossDbComparison', () => {
  it('returns null when less than 2 successful databases', () => {
    const results: DatabaseResultForCrossDb[] = [
      {
        connection_id: 1,
        connection_name: 'DB1',
        database_type: 'postgresql',
        results: [{ sales: 100 }],
        success: true,
      },
    ];

    expect(detectCrossDbComparison(results)).toBeNull();
  });

  it('returns null when no common numeric columns', () => {
    const results: DatabaseResultForCrossDb[] = [
      {
        connection_id: 1,
        connection_name: 'DB1',
        database_type: 'postgresql',
        results: [{ name: 'Alice' }],
        success: true,
      },
      {
        connection_id: 2,
        connection_name: 'DB2',
        database_type: 'mysql',
        results: [{ name: 'Bob' }],
        success: true,
      },
    ];

    expect(detectCrossDbComparison(results)).toBeNull();
  });

  it('returns config when comparison is possible', () => {
    const results: DatabaseResultForCrossDb[] = [
      {
        connection_id: 1,
        connection_name: 'DB1',
        database_type: 'postgresql',
        results: [{ sales: 100, revenue: 500 }],
        success: true,
      },
      {
        connection_id: 2,
        connection_name: 'DB2',
        database_type: 'mysql',
        results: [{ sales: 200, revenue: 800 }],
        success: true,
      },
    ];

    const config = detectCrossDbComparison(results);

    expect(config).not.toBeNull();
    expect(config!.commonColumns).toContain('sales');
    expect(config!.commonColumns).toContain('revenue');
    expect(config!.primaryMetric).toBe('sales'); // First common column
    expect(config!.aggregatedData).toHaveLength(2);
    expect(config!.aggregationMethod).toBe('sum');
  });

  it('sets primary metric to first common column', () => {
    const results: DatabaseResultForCrossDb[] = [
      {
        connection_id: 1,
        connection_name: 'DB1',
        database_type: 'postgresql',
        results: [{ amount: 100, total: 500 }],
        success: true,
      },
      {
        connection_id: 2,
        connection_name: 'DB2',
        database_type: 'mysql',
        results: [{ amount: 200, total: 800 }],
        success: true,
      },
    ];

    const config = detectCrossDbComparison(results);
    expect(config!.primaryMetric).toBe('amount');
  });
});

describe('formatMetricValue', () => {
  it('formats millions with M suffix', () => {
    expect(formatMetricValue(1500000)).toBe('1.5M');
    expect(formatMetricValue(2000000)).toBe('2.0M');
  });

  it('formats thousands with K suffix', () => {
    expect(formatMetricValue(1500)).toBe('1.5K');
    expect(formatMetricValue(2000)).toBe('2.0K');
  });

  it('formats small numbers with locale string', () => {
    expect(formatMetricValue(999)).toBe('999');
    expect(formatMetricValue(100.5)).toBe('100.5');
  });

  it('handles zero', () => {
    expect(formatMetricValue(0)).toBe('0');
  });

  it('handles decimal precision', () => {
    expect(formatMetricValue(1234.567)).toBe('1.2K');
  });
});
