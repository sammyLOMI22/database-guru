 PR Review: Dark Mode Implementation

  Summary

  This PR adds dark mode support across 45 frontend components with a toggle in the header. The implementation uses Tailwind's dark: class variant with a custom useDarkMode hook that persists preference to localStorage and respects system preference.

  Overall Assessment: Needs Work - 2 critical issues must be resolved before merge.

  ---
  Critical Issues

  1. BUG: Pie Chart Not Loading Data (Severity: Critical)

  Location: frontend/src/components/visualization/PieChartView.tsx:87-95

  Problem: The pie chart displays "Unknown" for all categories with 0 values.

  Root Cause: Data transformation mismatch:
  - prepareChartData() in chartUtils.ts returns objects with { name, value } properties
  - But PieChartView tries to access item[xColumn] and item[yColumn] which don't exist in the returned objects

  // Line 87-95 - Current (BROKEN)
  const chartData = useMemo((): PieDataItem[] => {
    const prepared = prepareChartData(data, xColumn, yColumn, 'pie', 20);
    return prepared.map((item) => ({
      ...item,
      name: String(item[xColumn] ?? 'Unknown'),  // ❌ xColumn doesn't exist in prepared data
      value: Number(item[yColumn]) || 0,          // ❌ yColumn doesn't exist in prepared data
    }));
  }, [data, xColumn, yColumn]);

  Fix: The prepared data already has name and value, so just return it:
  const chartData = useMemo((): PieDataItem[] => {
    return prepareChartData(data, xColumn, yColumn, 'pie', 20) as PieDataItem[];
  }, [data, xColumn, yColumn]);

  ---
  2. 59 Test Failures - Missing matchMedia Mock (Severity: Critical)

  Location: frontend/tests/setup.ts

  Problem: All tests for chart components fail with:
  TypeError: window.matchMedia is not a function

  Root Cause: The useDarkMode hook calls window.matchMedia('(prefers-color-scheme: dark)') which doesn't exist in JSDOM.

  Fix: Add mock to tests/setup.ts:
  // Mock matchMedia for dark mode tests
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });

  ---
  Minor Issues

  3. CSS Selector Issue (Severity: Low)

  Location: frontend/src/index.css:20-23

  .dark:root {  /* ❌ This selector doesn't work as intended */
    color: rgba(255, 255, 255, 0.87);
    background-color: #111827;
  }

  Should be:
  :root.dark {  /* ✓ Correct selector */
    color: rgba(255, 255, 255, 0.87);
    background-color: #111827;
  }

  Note: This may not cause visible issues since Tailwind classes handle most styling, but it's technically incorrect.

  ---
  4. Inconsistent Dark Text Colors (Severity: Low)

  Some components use dark:text-gray-400 while others use dark:text-gray-500 for similar secondary text. Consider standardizing:
  - Primary text: dark:text-white or dark:text-gray-100
  - Secondary text: dark:text-gray-400
  - Muted text: dark:text-gray-500

  ---
  What's Good

  1. Solid Architecture: The useDarkMode hook is clean and handles:
    - LocalStorage persistence
    - System preference detection
    - Proper class toggling on <html> element
  2. Consistent Pattern: Most components follow the same dark mode pattern with dark: variants
  3. Chart Integration: All Recharts components properly adapt tooltip, grid, and axis colors for dark mode
  4. Tailwind Config: Correctly uses darkMode: 'class' for manual toggle control
  5. Header Toggle: Clean implementation with Sun/Moon icons

  ---
  Test Results
  ┌─────────┬───────┐
  │ Status  │ Count │
  ├─────────┼───────┤
  │ Passing │ 501   │
  ├─────────┼───────┤
  │ Failing │ 59    │
  ├─────────┼───────┤
  │ Total   │ 560   │
  └─────────┴───────┘
  Failing tests are all in chart-related components due to missing matchMedia mock.

  ---
  Files Changed Summary

  - 45 files modified
  - +2,173 / -2,042 lines changed
  - New file: frontend/src/hooks/useDarkMode.ts

  ---
  Checklist Before Merge

  - Fix pie chart data transformation bug
  - Add matchMedia mock to test setup
  - Verify all 560 tests pass
  - (Optional) Fix CSS selector in index.css
  - (Optional) Standardize dark text colors

  ---

⏺ PR Review Complete.

  Key Findings:
  1. Pie Chart Bug (Critical): In PieChartView.tsx:87-95, the code tries to access item[xColumn] but prepareChartData() returns { name, value } objects - the column names don't exist. This is why the pie chart shows no data.
  2. Test Failures (Critical): 59 tests fail because useDarkMode hook calls window.matchMedia() which doesn't exist in JSDOM. Need to add a mock to tests/setup.ts.
  3. CSS Issue (Minor): .dark:root selector in index.css is incorrect syntax.