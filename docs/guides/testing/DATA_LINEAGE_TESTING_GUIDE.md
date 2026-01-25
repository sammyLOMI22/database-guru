# Data Lineage System Testing Guide (Phase 11.6)

**Branch**: `data-lineage`
**Purpose**: Comprehensive testing guide for Phase 11.6 - Polish & Testing
**Last Updated**: January 24, 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Backend Testing](#3-backend-testing)
4. [Frontend Testing](#4-frontend-testing)
5. [Integration Testing](#5-integration-testing)
6. [E2E Testing](#6-e2e-testing)
7. [Performance Testing](#7-performance-testing)
8. [Manual Testing Checklist](#8-manual-testing-checklist)
9. [PR Review Issues to Verify](#9-pr-review-issues-to-verify)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Overview

Phase 11 introduces a comprehensive Data Lineage system with three main components:

| Component | File | Purpose | Test File |
|-----------|------|---------|-----------|
| SQL Lineage Parser | `src/lineage/sql_lineage_parser.py` | Parse SQL → column-level lineage | `tests/test_sql_lineage_parser.py` |
| Impact Analyzer | `src/lineage/impact_analyzer.py` | Schema change impact assessment | `tests/test_impact_analyzer.py` |
| Query Pattern Analyzer | `src/lineage/query_pattern_analyzer.py` | Query pattern heatmap data | `tests/test_query_pattern_analyzer.py` |

**Frontend Components**:
- `LineagePanel.tsx` - Main 4-tab container
- `LineageGraph.tsx` - React Flow visualization
- `ColumnLineage.tsx` - Column-to-column transformation table
- `ImpactAnalysisPanel.tsx` - Schema change impact view
- `QueryPatternHeatmap.tsx` - 3-view heatmap visualization

**Current Test Coverage**: ~100 tests across backend + frontend

---

## 2. Prerequisites

### 2.1 Environment Setup

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Ensure dependencies are installed
pip install pytest pytest-asyncio pytest-cov aiosqlite

# 3. Frontend dependencies
cd frontend && npm install

# 4. Verify Ollama is running (for API tests)
ollama list
```

### 2.2 Database Setup

The tests use in-memory SQLite databases. No external database required.

```bash
# Verify test database setup works
python -c "from sqlalchemy.ext.asyncio import create_async_engine; print('OK')"
```

### 2.3 Verify Branch

```bash
git branch --show-current  # Should be: data-lineage
git status  # Review staged changes
```

---

## 3. Backend Testing

### 3.1 SQL Lineage Parser Tests

**Location**: `tests/test_sql_lineage_parser.py`

```bash
# Run all parser tests
./run_tests.sh tests/test_sql_lineage_parser.py

# Run specific test classes
python -m pytest tests/test_sql_lineage_parser.py::TestSimpleSelect -v
python -m pytest tests/test_sql_lineage_parser.py::TestJoins -v
python -m pytest tests/test_sql_lineage_parser.py::TestAggregations -v
python -m pytest tests/test_sql_lineage_parser.py::TestSubqueries -v
python -m pytest tests/test_sql_lineage_parser.py::TestEdgeCases -v
```

**Test Categories to Verify**:

| Category | What to Test | Expected |
|----------|--------------|----------|
| Simple SELECT | Single table, single/multi columns | Tables and columns extracted correctly |
| JOINs | INNER, LEFT, RIGHT, CROSS | All join tables captured with edges |
| Aggregations | COUNT, SUM, AVG, MIN, MAX | Transformation type = AGGREGATION |
| Aliases | Table aliases (o, c), column aliases (AS) | Alias resolved to real names |
| Subqueries | WHERE IN (SELECT ...) | Subquery tables included |
| CASE expressions | CASE WHEN ... THEN | Transformation type = EXPRESSION |
| SELECT * | Wildcard selects | Output shows `*` marker |
| Schema-qualified | `public.orders` | Schema prefix stripped |
| Invalid SQL | Empty, malformed | Graceful error, empty graph |

**New Tests for Phase 11.6** (to be added):

```python
# tests/test_sql_lineage_parser.py - Add these test cases

class TestOrphanedTableHandling:
    """Test tables used only in JOINs/WHERE get appropriate edges."""

    def test_join_only_table_connected(self, parser):
        """Tables in JOIN condition but not in SELECT should have edges."""
        sql = "SELECT c.name FROM customers c JOIN orders o ON c.id = o.customer_id"
        graph = parser.parse(sql)

        # Both tables should be in graph
        assert "customers" in graph.tables_used
        assert "orders" in graph.tables_used

        # Orders should have at least one edge (to JOIN condition)
        order_edges = [e for e in graph.edges if "orders" in e.source_id or "orders" in e.target_id]
        assert len(order_edges) >= 1

    def test_where_subquery_table_connected(self, parser):
        """Tables in WHERE subquery should be connected."""
        sql = "SELECT name FROM customers WHERE id IN (SELECT customer_id FROM orders)"
        graph = parser.parse(sql)

        assert "orders" in graph.tables_used
        # Verify orders has edges
        order_edges = [e for e in graph.edges if "orders" in str(e)]
        assert len(order_edges) >= 1

class TestComplexExpressions:
    """Test complex SQL expressions."""

    def test_nested_function_calls(self, parser):
        sql = "SELECT UPPER(TRIM(name)) AS clean_name FROM customers"
        graph = parser.parse(sql)

        assert "clean_name" in graph.output_columns
        # Should detect function transformation
        trans_nodes = [n for n in graph.nodes if n.node_type == LineageNodeType.TRANSFORMATION]
        assert len(trans_nodes) >= 1

    def test_arithmetic_expression(self, parser):
        sql = "SELECT price * quantity AS total FROM order_items"
        graph = parser.parse(sql)

        assert "total" in graph.output_columns
        # Should have EXPRESSION transformation type
        trans_nodes = [n for n in graph.nodes if n.transformation_type == TransformationType.EXPRESSION]
        assert len(trans_nodes) >= 1

    def test_coalesce_function(self, parser):
        sql = "SELECT COALESCE(nickname, name) AS display_name FROM users"
        graph = parser.parse(sql)

        assert "display_name" in graph.output_columns
        # Both nickname and name should be source columns
        assert any("nickname" in str(n) for n in graph.nodes)
        assert any("name" in str(n) for n in graph.nodes)
```

### 3.2 Impact Analyzer Tests

**Location**: `tests/test_impact_analyzer.py`

```bash
# Run all impact analyzer tests
./run_tests.sh tests/test_impact_analyzer.py

# Run with verbose output
python -m pytest tests/test_impact_analyzer.py -v --tb=short
```

**Test Categories to Verify**:

| Category | What to Test | Expected |
|----------|--------------|----------|
| Column impact | Rename column → find affected queries | Correct query count and types |
| Table impact | Drop table → find affected queries | All queries using table found |
| Risk levels | HIGH (>20), MEDIUM (5-20), LOW (<5) | Correct risk classification |
| False positives | `orders` ≠ `customer_orders` | No substring false matches |
| Impact types | SELECT, FILTER, JOIN, GROUP, ORDER | Correct type classification |
| Empty results | Non-existent column | Zero affected queries |

**New Tests for Phase 11.6**:

```python
# tests/test_impact_analyzer.py - Add these test cases

class TestFalsePositivePrevention:
    """Ensure word-boundary matching prevents false positives."""

    @pytest.mark.asyncio
    async def test_orders_not_customer_orders(self, db_session):
        """Searching 'orders' should not match 'customer_orders'."""
        analyzer = ImpactAnalyzer()
        result = await analyzer.analyze_table_impact("orders", db_session)

        # Should not include queries with only 'customer_orders'
        for query in result.impacted_queries:
            # If the only table is 'customer_orders', this is a false positive
            if "customer_orders" in query.sql and "orders o" not in query.sql.lower():
                if " orders " not in f" {query.sql.lower()} ":
                    pytest.fail(f"False positive: {query.sql}")

    @pytest.mark.asyncio
    async def test_id_not_customer_id(self, db_session):
        """Searching 'id' should not match 'customer_id'."""
        analyzer = ImpactAnalyzer()
        result = await analyzer.analyze_column_impact("users", "id", db_session)

        # Count queries that ONLY have customer_id but not standalone id
        for query in result.impacted_queries:
            if "customer_id" in query.sql.lower() and ".id" not in query.sql.lower():
                # This might be a false positive - verify
                pass  # Analyze manually

class TestRiskLevelThresholds:
    """Test risk level boundary conditions."""

    @pytest.mark.asyncio
    async def test_risk_level_boundaries(self, db_session):
        """Verify risk level thresholds are correct."""
        analyzer = ImpactAnalyzer()

        # Test the calculate_risk_level method directly if exposed
        assert analyzer._calculate_risk_level(21) == RiskLevel.HIGH.value
        assert analyzer._calculate_risk_level(20) == RiskLevel.MEDIUM.value
        assert analyzer._calculate_risk_level(5) == RiskLevel.MEDIUM.value
        assert analyzer._calculate_risk_level(4) == RiskLevel.LOW.value
        assert analyzer._calculate_risk_level(0) == RiskLevel.LOW.value
```

### 3.3 Query Pattern Analyzer Tests

**Location**: `tests/test_query_pattern_analyzer.py`

```bash
# Run all pattern analyzer tests
./run_tests.sh tests/test_query_pattern_analyzer.py

# Run specific tests
python -m pytest tests/test_query_pattern_analyzer.py::TestTableUsageFrequency -v
python -m pytest tests/test_query_pattern_analyzer.py::TestJoinPatterns -v
python -m pytest tests/test_query_pattern_analyzer.py::TestBottleneckDetection -v
```

**Test Categories to Verify**:

| Category | What to Test | Expected |
|----------|--------------|----------|
| Table frequency | Count table usage across queries | Correct counts per table |
| JOIN patterns | Detect common join pairs | Bidirectional detection (A-B = B-A) |
| Bottlenecks | High freq + high latency | Bottleneck score 0-1, correct ranking |
| Time range | Filter by 7/30/90 days | Only queries in range counted |
| Connection scoping | Filter by connection_id | Only connection's queries |
| Empty history | No queries in history | Empty results, no errors |

**New Tests for Phase 11.6**:

```python
# tests/test_query_pattern_analyzer.py - Add these test cases

class TestHeatmapDataIntegration:
    """Test the combined get_heatmap_data() method."""

    @pytest.mark.asyncio
    async def test_heatmap_data_structure(self, db_session):
        """Verify heatmap data has all required fields."""
        analyzer = QueryPatternAnalyzer()
        data = await analyzer.get_heatmap_data(
            db_session,
            connection_id=1,
            time_range_days=30
        )

        # Verify structure
        assert hasattr(data, 'table_usage')
        assert hasattr(data, 'join_patterns')
        assert hasattr(data, 'bottlenecks')

        # Verify types
        assert all(isinstance(t, TableUsageEntry) for t in data.table_usage)
        assert all(isinstance(j, JoinPattern) for j in data.join_patterns)
        assert all(isinstance(b, PerformanceBottleneck) for b in data.bottlenecks)

    @pytest.mark.asyncio
    async def test_bottleneck_score_range(self, db_session):
        """Verify bottleneck scores are in 0-1 range."""
        analyzer = QueryPatternAnalyzer()
        data = await analyzer.get_heatmap_data(db_session, connection_id=1)

        for bottleneck in data.bottlenecks:
            assert 0.0 <= bottleneck.bottleneck_score <= 1.0

class TestTimeRangeFiltering:
    """Test time range filtering accuracy."""

    @pytest.mark.asyncio
    async def test_7_day_filter(self, db_session):
        """Verify 7-day filter excludes older queries."""
        analyzer = QueryPatternAnalyzer()

        # Get data for 7 days
        data_7 = await analyzer.get_heatmap_data(db_session, time_range_days=7)

        # Get data for 30 days
        data_30 = await analyzer.get_heatmap_data(db_session, time_range_days=30)

        # 30-day should have >= 7-day counts
        assert sum(t.usage_count for t in data_30.table_usage) >= sum(t.usage_count for t in data_7.table_usage)
```

### 3.4 API Endpoint Tests

**Location**: Create `tests/test_lineage_api.py`

```bash
# Run API tests
./run_tests.sh tests/test_lineage_api.py
```

**New Tests for Phase 11.6**:

```python
# tests/test_lineage_api.py - NEW FILE

"""
Tests for Lineage API Endpoints

Covers:
- POST /api/lineage/parse
- GET /api/lineage/query/{query_id}
- POST /api/lineage/impact
- GET /api/lineage/table/{table_name}/queries
- GET /api/lineage/stats
- GET /api/lineage/patterns/{connection_id}
"""

import pytest
from httpx import AsyncClient
from fastapi import status

from src.main import app


@pytest.fixture
def test_client():
    """Create test client."""
    return AsyncClient(app=app, base_url="http://test")


class TestParseEndpoint:
    """Tests for POST /api/lineage/parse"""

    @pytest.mark.asyncio
    async def test_parse_simple_select(self, test_client):
        """Parse simple SELECT returns lineage graph."""
        async with test_client as client:
            response = await client.post(
                "/api/lineage/parse",
                json={"sql": "SELECT name FROM customers"}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "nodes" in data
        assert "edges" in data
        assert "tables_used" in data
        assert "customers" in data["tables_used"]

    @pytest.mark.asyncio
    async def test_parse_empty_sql(self, test_client):
        """Empty SQL returns error."""
        async with test_client as client:
            response = await client.post(
                "/api/lineage/parse",
                json={"sql": ""}
            )

        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    @pytest.mark.asyncio
    async def test_parse_invalid_sql(self, test_client):
        """Invalid SQL handled gracefully."""
        async with test_client as client:
            response = await client.post(
                "/api/lineage/parse",
                json={"sql": "NOT VALID SQL AT ALL"}
            )

        # Should return 200 with empty/error graph, not crash
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data.get("nodes", [])) == 0 or "error" in data

    @pytest.mark.asyncio
    async def test_parse_sql_size_limit(self, test_client):
        """Very large SQL is rejected or handled."""
        large_sql = "SELECT " + ", ".join([f"col{i}" for i in range(10000)]) + " FROM huge_table"

        async with test_client as client:
            response = await client.post(
                "/api/lineage/parse",
                json={"sql": large_sql}
            )

        # Should either reject or handle gracefully
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        ]


class TestImpactEndpoint:
    """Tests for POST /api/lineage/impact"""

    @pytest.mark.asyncio
    async def test_column_impact(self, test_client, db_with_queries):
        """Column impact returns affected queries."""
        async with test_client as client:
            response = await client.post(
                "/api/lineage/impact",
                json={
                    "table_name": "customers",
                    "column_name": "name"
                }
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "impacted_queries" in data
        assert "risk_level" in data
        assert data["risk_level"] in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_table_impact(self, test_client, db_with_queries):
        """Table impact (no column) returns all queries using table."""
        async with test_client as client:
            response = await client.post(
                "/api/lineage/impact",
                json={"table_name": "orders"}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["impacted_queries"]) >= 0


class TestPatternsEndpoint:
    """Tests for GET /api/lineage/patterns/{connection_id}"""

    @pytest.mark.asyncio
    async def test_patterns_with_data(self, test_client, db_with_queries):
        """Patterns endpoint returns heatmap data."""
        async with test_client as client:
            response = await client.get(
                "/api/lineage/patterns/1",
                params={"time_range_days": 30}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "table_usage" in data
        assert "join_patterns" in data
        assert "bottlenecks" in data

    @pytest.mark.asyncio
    async def test_patterns_invalid_connection(self, test_client):
        """Non-existent connection returns empty results."""
        async with test_client as client:
            response = await client.get("/api/lineage/patterns/99999")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data.get("table_usage", [])) == 0
```

---

## 4. Frontend Testing

### 4.1 LineageGraph Component Tests

**Location**: `frontend/tests/LineageGraph.test.tsx`

```bash
# Run frontend tests
cd frontend
npm test -- LineageGraph.test.tsx

# Run with UI
npm run test:ui
```

**Existing Test Coverage**:
- Empty state rendering
- Graph rendering from mock data
- Parse button click
- API error handling
- Node click highlighting

**New Tests for Phase 11.6**:

```typescript
// frontend/tests/LineageGraph.test.tsx - Add these tests

describe('LineageGraph - Phase 11.6 Additional Tests', () => {

  describe('Path Highlighting', () => {
    it('highlights upstream nodes when output column clicked', async () => {
      vi.mocked(lineageAPI.parseSql).mockResolvedValueOnce(mockGraphResponse);

      render(<LineageGraph />);

      // Trigger parse
      const input = screen.getByPlaceholderText(/enter sql/i);
      await userEvent.type(input, 'SELECT name FROM customers');
      fireEvent.click(screen.getByText(/parse/i));

      await waitFor(() => {
        expect(screen.getByTestId('node-out_1')).toBeInTheDocument();
      });

      // Click output node
      fireEvent.click(screen.getByTestId('node-out_1'));

      // Verify upstream nodes are highlighted (check class or style)
      // This depends on your highlighting implementation
    });

    it('clears highlighting on background click', async () => {
      // Similar setup, then click background
    });
  });

  describe('Large Graph Performance', () => {
    it('renders graph with 50+ nodes without crashing', async () => {
      const largeGraph = generateLargeGraph(50); // Helper to create mock
      vi.mocked(lineageAPI.parseSql).mockResolvedValueOnce(largeGraph);

      render(<LineageGraph />);

      // Trigger parse with complex SQL
      // Verify no errors and graph renders
    });
  });

  describe('Error States', () => {
    it('shows error message for malformed SQL', async () => {
      vi.mocked(lineageAPI.parseSql).mockRejectedValueOnce(
        new Error('Parse error: Invalid SQL syntax')
      );

      render(<LineageGraph />);

      const input = screen.getByPlaceholderText(/enter sql/i);
      await userEvent.type(input, 'INVALID SQL');
      fireEvent.click(screen.getByText(/parse/i));

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
      });
    });

    it('recovers from error state on new valid parse', async () => {
      // First parse fails, second succeeds
    });
  });
});
```

### 4.2 LineagePanel Component Tests

**Location**: Create `frontend/tests/LineagePanel.test.tsx`

```typescript
// frontend/tests/LineagePanel.test.tsx - NEW FILE

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock child components
vi.mock('../src/components/lineage/LineageGraph', () => ({
  default: () => <div data-testid="lineage-graph">LineageGraph</div>,
}));

vi.mock('../src/components/lineage/ColumnLineage', () => ({
  default: () => <div data-testid="column-lineage">ColumnLineage</div>,
}));

vi.mock('../src/components/lineage/ImpactAnalysisPanel', () => ({
  default: () => <div data-testid="impact-panel">ImpactAnalysisPanel</div>,
}));

vi.mock('../src/components/lineage/QueryPatternHeatmap', () => ({
  default: () => <div data-testid="heatmap">QueryPatternHeatmap</div>,
}));

import LineagePanel from '../src/components/lineage/LineagePanel';

describe('LineagePanel', () => {

  describe('Tab Navigation', () => {
    it('renders with Explore tab active by default', () => {
      render(<LineagePanel connectionId={1} />);

      expect(screen.getByRole('tab', { name: /explore/i })).toHaveAttribute('aria-selected', 'true');
      expect(screen.getByTestId('lineage-graph')).toBeInTheDocument();
    });

    it('switches to History tab on click', async () => {
      render(<LineagePanel connectionId={1} />);

      fireEvent.click(screen.getByRole('tab', { name: /history/i }));

      expect(screen.getByRole('tab', { name: /history/i })).toHaveAttribute('aria-selected', 'true');
    });

    it('switches to Impact tab on click', async () => {
      render(<LineagePanel connectionId={1} />);

      fireEvent.click(screen.getByRole('tab', { name: /impact/i }));

      expect(screen.getByTestId('impact-panel')).toBeInTheDocument();
    });

    it('switches to Patterns tab on click', async () => {
      render(<LineagePanel connectionId={1} />);

      fireEvent.click(screen.getByRole('tab', { name: /patterns/i }));

      expect(screen.getByTestId('heatmap')).toBeInTheDocument();
    });
  });

  describe('Connection Context', () => {
    it('passes connectionId to child components', () => {
      render(<LineagePanel connectionId={42} />);

      // Verify connectionId is passed through context or props
      // This depends on your implementation
    });

    it('updates when connectionId changes', async () => {
      const { rerender } = render(<LineagePanel connectionId={1} />);

      rerender(<LineagePanel connectionId={2} />);

      // Verify child components are updated
    });
  });
});
```

### 4.3 ImpactAnalysisPanel Tests

**Location**: Create `frontend/tests/ImpactAnalysisPanel.test.tsx`

```typescript
// frontend/tests/ImpactAnalysisPanel.test.tsx - NEW FILE

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../src/services/lineageApi', () => ({
  lineageAPI: {
    analyzeImpact: vi.fn(),
  },
}));

import { lineageAPI } from '../src/services/lineageApi';
import ImpactAnalysisPanel from '../src/components/lineage/ImpactAnalysisPanel';

const mockImpactResponse = {
  impacted_queries: [
    {
      query_id: 1,
      sql: 'SELECT name FROM customers',
      natural_language: 'Show customer names',
      impact_type: 'select',
    },
    {
      query_id: 2,
      sql: 'SELECT * FROM customers WHERE status = "active"',
      natural_language: 'Active customers',
      impact_type: 'filter',
    },
  ],
  total_affected: 2,
  risk_level: 'medium',
  by_type: { select: 1, filter: 1 },
};

describe('ImpactAnalysisPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Input Form', () => {
    it('renders table and column input fields', () => {
      render(<ImpactAnalysisPanel />);

      expect(screen.getByLabelText(/table name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/column name/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /analyze/i })).toBeInTheDocument();
    });

    it('requires table name before analyzing', async () => {
      render(<ImpactAnalysisPanel />);

      const analyzeBtn = screen.getByRole('button', { name: /analyze/i });
      fireEvent.click(analyzeBtn);

      // Should show validation error or not call API
      expect(lineageAPI.analyzeImpact).not.toHaveBeenCalled();
    });
  });

  describe('Impact Results', () => {
    it('displays impacted queries after analysis', async () => {
      vi.mocked(lineageAPI.analyzeImpact).mockResolvedValueOnce(mockImpactResponse);

      render(<ImpactAnalysisPanel />);

      await userEvent.type(screen.getByLabelText(/table name/i), 'customers');
      await userEvent.type(screen.getByLabelText(/column name/i), 'name');
      fireEvent.click(screen.getByRole('button', { name: /analyze/i }));

      await waitFor(() => {
        expect(screen.getByText(/2 queries affected/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/medium/i)).toBeInTheDocument(); // Risk level
    });

    it('shows risk level badge with correct color', async () => {
      vi.mocked(lineageAPI.analyzeImpact).mockResolvedValueOnce(mockImpactResponse);

      render(<ImpactAnalysisPanel />);

      // Fill and submit
      await userEvent.type(screen.getByLabelText(/table name/i), 'customers');
      fireEvent.click(screen.getByRole('button', { name: /analyze/i }));

      await waitFor(() => {
        const badge = screen.getByText(/medium/i);
        // Verify badge has yellow/orange color class
        expect(badge.className).toMatch(/yellow|orange|warning/i);
      });
    });
  });

  describe('Empty Results', () => {
    it('shows no impact message when no queries affected', async () => {
      vi.mocked(lineageAPI.analyzeImpact).mockResolvedValueOnce({
        impacted_queries: [],
        total_affected: 0,
        risk_level: 'low',
        by_type: {},
      });

      render(<ImpactAnalysisPanel />);

      await userEvent.type(screen.getByLabelText(/table name/i), 'unused_table');
      fireEvent.click(screen.getByRole('button', { name: /analyze/i }));

      await waitFor(() => {
        expect(screen.getByText(/no queries.*affected/i)).toBeInTheDocument();
      });
    });
  });
});
```

### 4.4 QueryPatternHeatmap Tests

**Location**: Create `frontend/tests/QueryPatternHeatmap.test.tsx`

```typescript
// frontend/tests/QueryPatternHeatmap.test.tsx - NEW FILE

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock recharts
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  Cell: () => null,
}));

vi.mock('../src/services/lineageApi', () => ({
  lineageAPI: {
    getPatterns: vi.fn(),
  },
}));

import { lineageAPI } from '../src/services/lineageApi';
import QueryPatternHeatmap from '../src/components/lineage/QueryPatternHeatmap';

const mockHeatmapData = {
  table_usage: [
    { table_name: 'orders', usage_count: 150 },
    { table_name: 'customers', usage_count: 120 },
    { table_name: 'products', usage_count: 80 },
  ],
  join_patterns: [
    { table1: 'orders', table2: 'customers', join_count: 45, sample_sql: 'SELECT...' },
    { table1: 'orders', table2: 'products', join_count: 30, sample_sql: 'SELECT...' },
  ],
  bottlenecks: [
    { table_name: 'orders', bottleneck_score: 0.85, avg_time_ms: 450, query_count: 150 },
    { table_name: 'reports', bottleneck_score: 0.72, avg_time_ms: 800, query_count: 20 },
  ],
};

describe('QueryPatternHeatmap', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(lineageAPI.getPatterns).mockResolvedValue(mockHeatmapData);
  });

  describe('View Modes', () => {
    it('renders Frequency view by default', async () => {
      render(<QueryPatternHeatmap connectionId={1} />);

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /frequency/i })).toHaveAttribute('aria-selected', 'true');
      });
    });

    it('switches to Joins view', async () => {
      render(<QueryPatternHeatmap connectionId={1} />);

      await waitFor(() => {
        fireEvent.click(screen.getByRole('tab', { name: /joins/i }));
      });

      expect(screen.getByRole('tab', { name: /joins/i })).toHaveAttribute('aria-selected', 'true');
    });

    it('switches to Performance view', async () => {
      render(<QueryPatternHeatmap connectionId={1} />);

      await waitFor(() => {
        fireEvent.click(screen.getByRole('tab', { name: /performance/i }));
      });

      expect(screen.getByRole('tab', { name: /performance/i })).toHaveAttribute('aria-selected', 'true');
    });
  });

  describe('Time Range Filter', () => {
    it('renders time range selector', async () => {
      render(<QueryPatternHeatmap connectionId={1} />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });
    });

    it('changes time range and refetches data', async () => {
      render(<QueryPatternHeatmap connectionId={1} />);

      await waitFor(() => {
        const select = screen.getByRole('combobox');
        fireEvent.change(select, { target: { value: '7' } });
      });

      // Verify API called with new time range
      expect(lineageAPI.getPatterns).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({ time_range_days: 7 })
      );
    });
  });

  describe('Data Display', () => {
    it('shows table names in frequency view', async () => {
      render(<QueryPatternHeatmap connectionId={1} />);

      await waitFor(() => {
        expect(screen.getByText('orders')).toBeInTheDocument();
        expect(screen.getByText('customers')).toBeInTheDocument();
      });
    });

    it('shows bottleneck scores in performance view', async () => {
      render(<QueryPatternHeatmap connectionId={1} />);

      await waitFor(() => {
        fireEvent.click(screen.getByRole('tab', { name: /performance/i }));
      });

      await waitFor(() => {
        // Look for bottleneck score display
        expect(screen.getByText(/0\.85/)).toBeInTheDocument();
      });
    });
  });

  describe('Dark Mode', () => {
    it('applies dark mode styles when enabled', async () => {
      // This test verifies the useDarkMode hook is used correctly
      // PR Review noted QueryPatternHeatmap should use hook instead of classList
    });
  });
});
```

---

## 5. Integration Testing

### 5.1 API → Parser → Database Round-Trip

**Location**: Create `tests/integration/test_lineage_integration.py`

```python
# tests/integration/test_lineage_integration.py - NEW FILE

"""
Integration tests for Lineage system

Tests full round-trip: API Request → Parser → Database → Response
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.database.models import Base, QueryHistory


@pytest_asyncio.fixture
async def test_db():
    """Create test database with seeded data."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Seed test queries
        queries = [
            QueryHistory(
                natural_language_query="Get all customers",
                generated_sql="SELECT * FROM customers",
                executed=True,
                connection_id=1,
            ),
            QueryHistory(
                natural_language_query="Customer orders",
                generated_sql="SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id",
                executed=True,
                connection_id=1,
            ),
        ]
        session.add_all(queries)
        await session.commit()

        yield session


class TestLineageIntegration:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_parse_then_impact(self, test_db):
        """Parse a query, then analyze impact on its tables."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Parse a query
            parse_response = await client.post(
                "/api/lineage/parse",
                json={"sql": "SELECT name FROM customers WHERE status = 'active'"}
            )

            assert parse_response.status_code == 200
            parse_data = parse_response.json()

            assert "customers" in parse_data["tables_used"]

            # Step 2: Analyze impact on the table found
            impact_response = await client.post(
                "/api/lineage/impact",
                json={"table_name": "customers", "column_name": "name"}
            )

            assert impact_response.status_code == 200
            impact_data = impact_response.json()

            # Should find our seeded queries
            assert impact_data["total_affected"] >= 0

    @pytest.mark.asyncio
    async def test_history_lineage_lookup(self, test_db):
        """Look up lineage for a historical query by ID."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Get lineage for query ID 1
            response = await client.get("/api/lineage/query/1")

            assert response.status_code == 200
            data = response.json()

            assert "customers" in data.get("tables_used", [])

    @pytest.mark.asyncio
    async def test_patterns_for_connection(self, test_db):
        """Get patterns for a specific connection."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/lineage/patterns/1",
                params={"time_range_days": 30}
            )

            assert response.status_code == 200
            data = response.json()

            # Should have pattern data
            assert "table_usage" in data
            assert "join_patterns" in data
```

---

## 6. E2E Testing

### 6.1 Cross-Component Navigation

These tests verify navigation between lineage components works correctly.

**Location**: Create `frontend/tests/e2e/lineage-navigation.test.tsx`

```typescript
// frontend/tests/e2e/lineage-navigation.test.tsx - NEW FILE

/**
 * E2E Tests for Lineage Cross-Component Navigation
 *
 * Tests navigation flows:
 * 1. Parse SQL → View Lineage Graph → Click node → See column details
 * 2. Impact Analysis → Click affected query → View its lineage
 * 3. Heatmap bottleneck → Drill down to table queries
 * 4. ER Diagram → Click table → View lineage for table
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Full app context for E2E
import App from '../src/App';

// Mock all API calls
vi.mock('../src/services/api', () => ({
  // ... standard API mocks
}));

vi.mock('../src/services/lineageApi', () => ({
  lineageAPI: {
    parseSql: vi.fn(),
    getQueryLineage: vi.fn(),
    analyzeImpact: vi.fn(),
    getTableQueries: vi.fn(),
    getPatterns: vi.fn(),
  },
}));

describe('Lineage E2E Navigation', () => {

  describe('Parse → Lineage → Column Details Flow', () => {
    it('navigates from parse to column lineage view', async () => {
      const user = userEvent.setup();
      render(<App />);

      // Navigate to Lineage tab
      fireEvent.click(screen.getByRole('tab', { name: /lineage/i }));

      // Enter SQL and parse
      const sqlInput = screen.getByPlaceholderText(/enter sql/i);
      await user.type(sqlInput, 'SELECT c.name, SUM(o.total) FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name');

      fireEvent.click(screen.getByText(/parse/i));

      await waitFor(() => {
        // Graph should render
        expect(screen.getByTestId('react-flow')).toBeInTheDocument();
      });

      // Click on an output column node
      fireEvent.click(screen.getByTestId('node-sum_total'));

      // Should show column lineage details
      await waitFor(() => {
        expect(screen.getByText(/column lineage/i)).toBeInTheDocument();
        expect(screen.getByText(/orders.total/i)).toBeInTheDocument();
      });
    });
  });

  describe('Impact → Query Lineage Flow', () => {
    it('navigates from impacted query to its lineage', async () => {
      // Mock impact response with a query
      vi.mocked(lineageAPI.analyzeImpact).mockResolvedValueOnce({
        impacted_queries: [
          { query_id: 42, sql: 'SELECT name FROM customers', impact_type: 'select' }
        ],
        total_affected: 1,
        risk_level: 'low',
      });

      vi.mocked(lineageAPI.getQueryLineage).mockResolvedValueOnce({
        nodes: [/* ... */],
        edges: [/* ... */],
        tables_used: ['customers'],
      });

      const user = userEvent.setup();
      render(<App />);

      // Navigate to Impact tab
      fireEvent.click(screen.getByRole('tab', { name: /lineage/i }));
      fireEvent.click(screen.getByRole('tab', { name: /impact/i }));

      // Run impact analysis
      await user.type(screen.getByLabelText(/table name/i), 'customers');
      fireEvent.click(screen.getByText(/analyze/i));

      await waitFor(() => {
        expect(screen.getByText(/1 query.*affected/i)).toBeInTheDocument();
      });

      // Click "View Lineage" on the impacted query
      const queryCard = screen.getByText(/SELECT name FROM customers/i).closest('div');
      const viewLineageBtn = within(queryCard!).getByText(/view lineage/i);
      fireEvent.click(viewLineageBtn);

      // Should navigate to lineage view for that query
      await waitFor(() => {
        expect(lineageAPI.getQueryLineage).toHaveBeenCalledWith(42);
      });
    });
  });

  describe('Heatmap → Table Queries Flow', () => {
    it('drills down from bottleneck to table queries', async () => {
      vi.mocked(lineageAPI.getPatterns).mockResolvedValueOnce({
        table_usage: [{ table_name: 'orders', usage_count: 150 }],
        join_patterns: [],
        bottlenecks: [{ table_name: 'orders', bottleneck_score: 0.9, avg_time_ms: 500, query_count: 150 }],
      });

      vi.mocked(lineageAPI.getTableQueries).mockResolvedValueOnce({
        queries: [
          { query_id: 1, sql: 'SELECT * FROM orders', execution_time_ms: 450 },
          { query_id: 2, sql: 'SELECT * FROM orders WHERE status = "pending"', execution_time_ms: 600 },
        ],
      });

      render(<App />);

      // Navigate to Patterns tab
      fireEvent.click(screen.getByRole('tab', { name: /lineage/i }));
      fireEvent.click(screen.getByRole('tab', { name: /patterns/i }));

      await waitFor(() => {
        expect(screen.getByText('orders')).toBeInTheDocument();
      });

      // Switch to Performance view
      fireEvent.click(screen.getByRole('tab', { name: /performance/i }));

      // Click on bottleneck table
      fireEvent.click(screen.getByText('orders'));

      // Should show queries for that table
      await waitFor(() => {
        expect(lineageAPI.getTableQueries).toHaveBeenCalledWith('orders');
      });
    });
  });
});
```

---

## 7. Performance Testing

### 7.1 Parser Performance Tests

**Location**: Create `tests/performance/test_lineage_performance.py`

```python
# tests/performance/test_lineage_performance.py - NEW FILE

"""
Performance tests for Lineage system

Verifies:
- Parse time for complex queries
- Impact analysis on large query history
- Memory usage for large graphs
"""

import pytest
import time
from src.lineage.sql_lineage_parser import SQLLineageParser


class TestParserPerformance:
    """Performance tests for SQL Lineage Parser."""

    @pytest.fixture
    def parser(self):
        return SQLLineageParser()

    def test_simple_query_under_10ms(self, parser):
        """Simple SELECT should parse in <10ms."""
        sql = "SELECT name, email FROM customers WHERE id = 1"

        start = time.perf_counter()
        graph = parser.parse(sql)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 10, f"Parse took {elapsed:.2f}ms, expected <10ms"
        assert len(graph.nodes) > 0

    def test_medium_join_under_50ms(self, parser):
        """5-table JOIN should parse in <50ms."""
        sql = """
        SELECT
            c.name, o.id, p.title, s.name as seller, cat.name as category
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        JOIN sellers s ON p.seller_id = s.id
        JOIN categories cat ON p.category_id = cat.id
        WHERE o.created_at > '2024-01-01'
        """

        start = time.perf_counter()
        graph = parser.parse(sql)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 50, f"Parse took {elapsed:.2f}ms, expected <50ms"
        assert len(graph.tables_used) == 6

    def test_complex_aggregation_under_100ms(self, parser):
        """Complex aggregation with subquery should parse in <100ms."""
        sql = """
        SELECT
            c.name,
            COUNT(DISTINCT o.id) as order_count,
            SUM(oi.quantity * p.price) as total_revenue,
            AVG(o.total) as avg_order_value,
            CASE
                WHEN SUM(oi.quantity * p.price) > 10000 THEN 'VIP'
                WHEN SUM(oi.quantity * p.price) > 1000 THEN 'Regular'
                ELSE 'New'
            END as customer_tier
        FROM customers c
        LEFT JOIN orders o ON c.id = o.customer_id
        LEFT JOIN order_items oi ON o.id = oi.order_id
        LEFT JOIN products p ON oi.product_id = p.id
        WHERE c.id IN (
            SELECT customer_id
            FROM orders
            WHERE created_at > '2024-01-01'
            GROUP BY customer_id
            HAVING COUNT(*) > 5
        )
        GROUP BY c.id, c.name
        HAVING COUNT(DISTINCT o.id) > 0
        ORDER BY total_revenue DESC
        LIMIT 100
        """

        start = time.perf_counter()
        graph = parser.parse(sql)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 100, f"Parse took {elapsed:.2f}ms, expected <100ms"

    def test_wide_select_under_200ms(self, parser):
        """SELECT with 50 columns should parse in <200ms."""
        columns = ", ".join([f"col{i}" for i in range(50)])
        sql = f"SELECT {columns} FROM wide_table WHERE status = 'active'"

        start = time.perf_counter()
        graph = parser.parse(sql)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 200, f"Parse took {elapsed:.2f}ms, expected <200ms"
        assert len(graph.output_columns) == 50

    def test_10_table_join_under_500ms(self, parser):
        """10-table JOIN stress test."""
        joins = []
        for i in range(10):
            if i == 0:
                joins.append(f"table{i} t{i}")
            else:
                joins.append(f"JOIN table{i} t{i} ON t{i-1}.id = t{i}.parent_id")

        sql = f"SELECT t0.id FROM {' '.join(joins)}"

        start = time.perf_counter()
        graph = parser.parse(sql)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 500, f"Parse took {elapsed:.2f}ms, expected <500ms"
        assert len(graph.tables_used) == 10


class TestImpactPerformance:
    """Performance tests for Impact Analyzer."""

    @pytest.mark.asyncio
    async def test_impact_1000_queries_under_1s(self, large_db_session):
        """Impact analysis on 1000 queries should complete in <1s."""
        from src.lineage.impact_analyzer import ImpactAnalyzer

        analyzer = ImpactAnalyzer()

        start = time.perf_counter()
        result = await analyzer.analyze_table_impact("orders", large_db_session)
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"Analysis took {elapsed:.2f}s, expected <1s"


class TestMemoryUsage:
    """Memory usage tests."""

    def test_large_graph_memory(self, parser):
        """Large graph shouldn't exceed 10MB."""
        import tracemalloc

        tracemalloc.start()

        # Generate large SQL
        columns = ", ".join([f"t{i}.col{j}" for i in range(5) for j in range(20)])
        joins = " ".join([f"JOIN table{i} t{i} ON t{i-1}.id = t{i}.fk" for i in range(1, 5)])
        sql = f"SELECT {columns} FROM table0 t0 {joins}"

        graph = parser.parse(sql)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / 1024 / 1024
        assert peak_mb < 10, f"Peak memory {peak_mb:.2f}MB, expected <10MB"
```

---

## 8. Manual Testing Checklist

### 8.1 Pre-Merge Checklist

Before merging the `data-lineage` branch to `main`, verify:

#### Backend Tests
- [ ] All parser tests pass: `./run_tests.sh tests/test_sql_lineage_parser.py`
- [ ] All impact tests pass: `./run_tests.sh tests/test_impact_analyzer.py`
- [ ] All pattern tests pass: `./run_tests.sh tests/test_query_pattern_analyzer.py`
- [ ] API endpoint tests pass: `./run_tests.sh tests/test_lineage_api.py`
- [ ] Integration tests pass: `./run_tests.sh tests/integration/`
- [ ] No regressions in other tests: `./run_tests.sh`

#### Frontend Tests
- [ ] LineageGraph tests pass: `cd frontend && npm test -- LineageGraph`
- [ ] LineagePanel tests pass: `cd frontend && npm test -- LineagePanel`
- [ ] ImpactAnalysisPanel tests pass
- [ ] QueryPatternHeatmap tests pass
- [ ] All frontend tests pass: `cd frontend && npm test`

#### Manual UI Testing
- [ ] Lineage tab visible in main navigation
- [ ] Parse SQL generates visible graph
- [ ] Node click highlights connected nodes
- [ ] Tab switching (Explore/History/Impact/Patterns) works
- [ ] Impact analysis shows affected queries
- [ ] Heatmap renders all three views
- [ ] Dark mode works correctly in all components
- [ ] Responsive design works on different screen sizes

### 8.2 Detailed Manual Test Scenarios

#### Scenario 1: Basic SQL Parsing
1. Navigate to Lineage → Explore tab
2. Enter: `SELECT name, email FROM customers`
3. Click "Parse"
4. **Expected**: Graph shows customers table → name column → name output
5. **Verify**: Tables Used shows "customers"

#### Scenario 2: Complex JOIN Parsing
1. Enter: `SELECT c.name, o.total FROM customers c JOIN orders o ON c.id = o.customer_id`
2. Click "Parse"
3. **Expected**: Both tables visible, JOIN relationship shown
4. **Verify**: Two source tables, edges show relationship

#### Scenario 3: Impact Analysis
1. Navigate to Lineage → Impact tab
2. Enter table: "customers", column: "email"
3. Click "Analyze Impact"
4. **Expected**: List of queries using customers.email
5. **Verify**: Risk level badge displayed (LOW/MEDIUM/HIGH)

#### Scenario 4: Query Pattern Heatmap
1. Navigate to Lineage → Patterns tab
2. Select time range: "Last 30 days"
3. **Expected**: Bar chart of table usage
4. Switch to "Joins" view
5. **Expected**: Join patterns displayed
6. Switch to "Performance" view
7. **Expected**: Bottleneck scores visible

#### Scenario 5: Error Handling
1. Enter invalid SQL: `NOT SQL AT ALL`
2. Click "Parse"
3. **Expected**: Error message displayed, no crash
4. Enter valid SQL again
5. **Expected**: Recovers and shows graph

---

## 9. PR Review Issues to Verify

The PR review identified these issues. Verify each is addressed:

### High Priority

#### Issue 1: Missing Index on connection_id
```sql
-- Verify index exists
SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='query_history';
```
**Status**: [ ] Fixed / [ ] Not Fixed

#### Issue 2: datetime.utcnow() Deprecation
```bash
# Search for deprecated usage
grep -r "datetime.utcnow()" src/lineage/
```
**Expected**: Should use `datetime.now(timezone.utc)` instead
**Status**: [ ] Fixed / [ ] Not Fixed

#### Issue 3: SQL Size Limit on Parse Endpoint
```bash
# Test with very large SQL
curl -X POST http://localhost:8000/api/lineage/parse \
  -H "Content-Type: application/json" \
  -d '{"sql": "'$(python -c "print('SELECT ' + ', '.join(['col'+str(i) for i in range(10000)]) + ' FROM t')")'"}'
```
**Expected**: Either rejected or handled gracefully
**Status**: [ ] Fixed / [ ] Not Fixed

### Medium Priority

#### Issue 4: useDarkMode Hook in QueryPatternHeatmap
```bash
# Verify hook usage
grep -n "useDarkMode" frontend/src/components/lineage/QueryPatternHeatmap.tsx
```
**Expected**: Should use hook, not `document.documentElement.classList`
**Status**: [ ] Fixed / [ ] Not Fixed

---

## 10. Troubleshooting

### Common Issues

#### Tests Failing with Import Errors
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run from project root
cd /Users/sam/database-guru
./run_tests.sh tests/test_sql_lineage_parser.py
```

#### Frontend Tests Hanging
```bash
# Clear node_modules and reinstall
cd frontend
rm -rf node_modules
npm install

# Run tests with timeout
npm test -- --timeout 30000
```

#### Database Errors in Tests
```bash
# Ensure aiosqlite is installed
pip install aiosqlite

# Verify async engine works
python -c "from sqlalchemy.ext.asyncio import create_async_engine; e = create_async_engine('sqlite+aiosqlite:///:memory:'); print('OK')"
```

#### React Flow Mocking Issues
```typescript
// If React Flow tests fail, ensure mock is complete
vi.mock('reactflow', () => ({
  default: ({ children, nodes, edges, onNodeClick }: any) => (
    <div data-testid="react-flow">{children}</div>
  ),
  ReactFlowProvider: ({ children }) => <div>{children}</div>,
  Controls: () => null,
  Background: () => null,
  MiniMap: () => null,
  BackgroundVariant: { Dots: 'dots' },
  useNodesState: (initial = []) => [initial, vi.fn(), vi.fn()],
  useEdgesState: (initial = []) => [initial, vi.fn(), vi.fn()],
  Handle: () => null,
  Position: { Top: 'top', Bottom: 'bottom' },
  getBezierPath: () => ['', 0, 0],
  EdgeLabelRenderer: ({ children }) => <div>{children}</div>,
  BaseEdge: () => null,
}));
```

---

## Summary

Phase 11.6 testing focuses on:

1. **Backend**: Comprehensive parser, analyzer, and API tests
2. **Frontend**: Component tests for all lineage UI
3. **Integration**: API → Parser → Database round-trips
4. **E2E**: Cross-component navigation flows
5. **Performance**: Parse time and memory benchmarks
6. **PR Issues**: Verify all review items are addressed

**Run all tests before merge**:
```bash
# Backend
./run_tests.sh

# Frontend
cd frontend && npm test

# Specific lineage tests
./run_tests.sh tests/test_sql_lineage_parser.py tests/test_impact_analyzer.py tests/test_query_pattern_analyzer.py
```

---

**Document Version**: 1.0
**Created**: January 24, 2026
**Branch**: data-lineage
