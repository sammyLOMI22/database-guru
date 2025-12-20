/**
 * Export Utilities Tests
 *
 * Tests for data export utilities (CSV, JSON, clipboard)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  exportToCSV,
  exportToJSON,
  copyToClipboard,
  formatNumber,
  truncateString,
} from '../src/utils/exportUtils';

// Mock DOM methods for file download
const mockCreateObjectURL = vi.fn(() => 'blob:mock-url');
const mockRevokeObjectURL = vi.fn();
const mockClick = vi.fn();
const mockAppendChild = vi.fn();
const mockRemoveChild = vi.fn();

beforeEach(() => {
  // Mock URL methods
  global.URL.createObjectURL = mockCreateObjectURL;
  global.URL.revokeObjectURL = mockRevokeObjectURL;

  // Mock document methods
  vi.spyOn(document, 'createElement').mockImplementation((tag) => {
    if (tag === 'a') {
      return {
        href: '',
        download: '',
        click: mockClick,
      } as unknown as HTMLAnchorElement;
    }
    return document.createElement(tag);
  });

  vi.spyOn(document.body, 'appendChild').mockImplementation(mockAppendChild);
  vi.spyOn(document.body, 'removeChild').mockImplementation(mockRemoveChild);

  // Mock console.warn
  vi.spyOn(console, 'warn').mockImplementation(() => {});
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('exportToCSV', () => {
  it('creates and downloads a CSV file', () => {
    const data = [
      { name: 'Alice', age: 30 },
      { name: 'Bob', age: 25 },
    ];

    exportToCSV(data);

    expect(mockCreateObjectURL).toHaveBeenCalled();
    expect(mockClick).toHaveBeenCalled();
    expect(mockRevokeObjectURL).toHaveBeenCalled();
  });

  it('warns and returns early for empty data', () => {
    exportToCSV([]);

    expect(console.warn).toHaveBeenCalledWith('No data to export');
    expect(mockCreateObjectURL).not.toHaveBeenCalled();
  });

  it('escapes fields with commas', () => {
    const data = [{ text: 'Hello, World' }];

    // Capture the blob content
    let blobContent = '';
    vi.spyOn(global, 'Blob').mockImplementation((content) => {
      blobContent = content?.[0] as string || '';
      return { type: 'text/csv' } as Blob;
    });

    exportToCSV(data);

    expect(blobContent).toContain('"Hello, World"');
  });

  it('escapes fields with quotes', () => {
    const data = [{ text: 'Say "Hello"' }];

    let blobContent = '';
    vi.spyOn(global, 'Blob').mockImplementation((content) => {
      blobContent = content?.[0] as string || '';
      return { type: 'text/csv' } as Blob;
    });

    exportToCSV(data);

    expect(blobContent).toContain('"Say ""Hello"""');
  });

  it('escapes fields with newlines', () => {
    const data = [{ text: 'Line 1\nLine 2' }];

    let blobContent = '';
    vi.spyOn(global, 'Blob').mockImplementation((content) => {
      blobContent = content?.[0] as string || '';
      return { type: 'text/csv' } as Blob;
    });

    exportToCSV(data);

    expect(blobContent).toContain('"Line 1\nLine 2"');
  });

  it('includes headers by default', () => {
    const data = [{ name: 'Alice', age: 30 }];

    let blobContent = '';
    vi.spyOn(global, 'Blob').mockImplementation((content) => {
      blobContent = content?.[0] as string || '';
      return { type: 'text/csv' } as Blob;
    });

    exportToCSV(data);

    expect(blobContent.startsWith('name,age')).toBe(true);
  });

  it('can exclude headers with option', () => {
    const data = [{ name: 'Alice', age: 30 }];

    let blobContent = '';
    vi.spyOn(global, 'Blob').mockImplementation((content) => {
      blobContent = content?.[0] as string || '';
      return { type: 'text/csv' } as Blob;
    });

    exportToCSV(data, { includeHeaders: false });

    expect(blobContent.startsWith('Alice')).toBe(true);
  });

  it('uses custom delimiter', () => {
    const data = [{ name: 'Alice', age: 30 }];

    let blobContent = '';
    vi.spyOn(global, 'Blob').mockImplementation((content) => {
      blobContent = content?.[0] as string || '';
      return { type: 'text/csv' } as Blob;
    });

    exportToCSV(data, { delimiter: ';' });

    expect(blobContent).toContain('name;age');
  });

  it('handles null values', () => {
    const data = [{ name: 'Alice', value: null }];

    let blobContent = '';
    vi.spyOn(global, 'Blob').mockImplementation((content) => {
      blobContent = content?.[0] as string || '';
      return { type: 'text/csv' } as Blob;
    });

    exportToCSV(data);

    // null should be converted to empty string
    expect(blobContent).toContain('Alice,');
  });
});

describe('exportToJSON', () => {
  it('creates and downloads a JSON file', () => {
    const data = [{ name: 'Alice', age: 30 }];
    const metadata = { rowCount: 1 };

    exportToJSON(data, metadata);

    expect(mockCreateObjectURL).toHaveBeenCalled();
    expect(mockClick).toHaveBeenCalled();
    expect(mockRevokeObjectURL).toHaveBeenCalled();
  });

  it('warns and returns early for empty data', () => {
    exportToJSON([], { rowCount: 0 });

    expect(console.warn).toHaveBeenCalledWith('No data to export');
    expect(mockCreateObjectURL).not.toHaveBeenCalled();
  });

  it('includes metadata in export', () => {
    const data = [{ name: 'Alice' }];
    const metadata = {
      query: 'Show all users',
      sql: 'SELECT * FROM users',
      rowCount: 1,
    };

    let blobContent = '';
    vi.spyOn(global, 'Blob').mockImplementation((content) => {
      blobContent = content?.[0] as string || '';
      return { type: 'application/json' } as Blob;
    });

    exportToJSON(data, metadata);

    const parsed = JSON.parse(blobContent);
    expect(parsed.metadata.query).toBe('Show all users');
    expect(parsed.metadata.sql).toBe('SELECT * FROM users');
  });

  it('includes column names in export', () => {
    const data = [{ name: 'Alice', age: 30 }];

    let blobContent = '';
    vi.spyOn(global, 'Blob').mockImplementation((content) => {
      blobContent = content?.[0] as string || '';
      return { type: 'application/json' } as Blob;
    });

    exportToJSON(data, { rowCount: 1 });

    const parsed = JSON.parse(blobContent);
    expect(parsed.columns).toEqual(['name', 'age']);
  });

  it('includes data array in export', () => {
    const data = [
      { name: 'Alice', age: 30 },
      { name: 'Bob', age: 25 },
    ];

    let blobContent = '';
    vi.spyOn(global, 'Blob').mockImplementation((content) => {
      blobContent = content?.[0] as string || '';
      return { type: 'application/json' } as Blob;
    });

    exportToJSON(data, { rowCount: 2 });

    const parsed = JSON.parse(blobContent);
    expect(parsed.data).toHaveLength(2);
    expect(parsed.data[0].name).toBe('Alice');
  });

  it('adds exportedAt timestamp', () => {
    const data = [{ name: 'Alice' }];

    let blobContent = '';
    vi.spyOn(global, 'Blob').mockImplementation((content) => {
      blobContent = content?.[0] as string || '';
      return { type: 'application/json' } as Blob;
    });

    exportToJSON(data, { rowCount: 1 });

    const parsed = JSON.parse(blobContent);
    expect(parsed.metadata.exportedAt).toBeDefined();
    expect(parsed.metadata.totalRows).toBe(1);
  });
});

describe('copyToClipboard', () => {
  it('returns false for empty data', async () => {
    const result = await copyToClipboard([]);

    expect(result).toBe(false);
  });

  it('copies tab-separated values to clipboard', async () => {
    const mockWriteText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: mockWriteText },
      writable: true,
    });

    const data = [
      { name: 'Alice', age: 30 },
      { name: 'Bob', age: 25 },
    ];

    const result = await copyToClipboard(data);

    expect(result).toBe(true);
    expect(mockWriteText).toHaveBeenCalled();

    const calledWith = mockWriteText.mock.calls[0][0];
    expect(calledWith).toContain('name\tage');
    expect(calledWith).toContain('Alice\t30');
    expect(calledWith).toContain('Bob\t25');
  });

  it('handles clipboard errors gracefully', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn().mockRejectedValue(new Error('Permission denied')) },
      writable: true,
    });

    const data = [{ name: 'Alice' }];
    const result = await copyToClipboard(data);

    expect(result).toBe(false);
    expect(console.error).toHaveBeenCalled();
  });

  it('handles null values', async () => {
    const mockWriteText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: mockWriteText },
      writable: true,
    });

    const data = [{ name: 'Alice', value: null }];
    await copyToClipboard(data);

    const calledWith = mockWriteText.mock.calls[0][0];
    expect(calledWith).toContain('Alice\t');
  });
});

describe('formatNumber', () => {
  it('formats integers with locale separators', () => {
    const result = formatNumber(1000000);
    expect(result).toBe('1,000,000');
  });

  it('formats decimals with limited precision', () => {
    const result = formatNumber(1234.5678);
    expect(result).toBe('1,234.57');
  });

  it('preserves integers without decimal places', () => {
    const result = formatNumber(42);
    expect(result).toBe('42');
  });

  it('handles zero', () => {
    const result = formatNumber(0);
    expect(result).toBe('0');
  });

  it('handles negative numbers', () => {
    const result = formatNumber(-1234.56);
    expect(result).toBe('-1,234.56');
  });
});

describe('truncateString', () => {
  it('returns short strings unchanged', () => {
    const result = truncateString('Hello', 50);
    expect(result).toBe('Hello');
  });

  it('truncates long strings with ellipsis', () => {
    const result = truncateString('This is a very long string that should be truncated', 20);
    expect(result).toBe('This is a very lo...');
    expect(result.length).toBe(20);
  });

  it('uses default maxLength of 50', () => {
    const longString = 'A'.repeat(100);
    const result = truncateString(longString);
    expect(result.length).toBe(50);
    expect(result.endsWith('...')).toBe(true);
  });

  it('handles string exactly at maxLength', () => {
    const exactString = 'A'.repeat(50);
    const result = truncateString(exactString, 50);
    expect(result).toBe(exactString);
    expect(result.length).toBe(50);
  });

  it('handles empty string', () => {
    const result = truncateString('', 10);
    expect(result).toBe('');
  });
});
